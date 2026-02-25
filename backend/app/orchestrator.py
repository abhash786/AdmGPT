import asyncio
import json
import httpx
from typing import List, Dict, Any, AsyncGenerator
from openai import AsyncOpenAI
from app.config import Config
from app.mcp_client import MCPClientManager
from app.database import add_message

class Orchestrator:
    def __init__(self, mcp_manager: MCPClientManager, conversation_id: str, history: List[Dict[str, Any]] = None, model: str = "gpt-4o", user_name: str = None, tool_contexts: Dict[str, str] = None):
        # Configure httpx client to skip SSL verification (for corporate proxy/dev env)
        http_client = httpx.AsyncClient(verify=False)
        self.client = AsyncOpenAI(api_key=Config.OPENAI_API_KEY, http_client=http_client)
        self.mcp_manager = mcp_manager
        self.conversation_id = conversation_id
        self.history = history if history else []
        self.model = model
        self.user_name = user_name
        self.tool_contexts = tool_contexts or {}

    def _sanitize_history(self):
        """Ensure every tool_call in assistant messages has a matching tool response."""
        sanitized = []
        for i, msg in enumerate(self.history):
            sanitized.append(msg)
            if msg.get("role") == "assistant" and msg.get("tool_calls"):
                # Collect all tool_call_ids from this assistant message
                expected_ids = {tc["id"] for tc in msg["tool_calls"]}
                # Look ahead for matching tool responses
                found_ids = set()
                for j in range(i + 1, len(self.history)):
                    next_msg = self.history[j]
                    if next_msg.get("role") == "tool" and next_msg.get("tool_call_id") in expected_ids:
                        found_ids.add(next_msg["tool_call_id"])
                    elif next_msg.get("role") != "tool":
                        break
                # Insert placeholders for missing tool responses
                missing_ids = expected_ids - found_ids
                for mid in missing_ids:
                    sanitized.append({
                        "role": "tool",
                        "tool_call_id": mid,
                        "content": "Tool execution was interrupted or skipped."
                    })
        self.history = sanitized

    async def process_message(self, user_message: str) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Process a user message, orchestrating tool calls and returning a stream of events.
        Events:
        - type: "token", content: str
        - type: "thought", content: str
        """
        self.history.append({"role": "user", "content": user_message})

        # Sanitize history: ensure every tool_call has a matching tool response
        self._sanitize_history()

        # Load tools
        try:
            tools, errors = await self.mcp_manager.list_tools(self.user_name)
            
            # Proactive check for mentioned servers that aren't configured
            if self.user_name:
                servers_def = Config.load_mcp_servers()
                active_servers = {t.get("server_name") for t in tools}
                user_msg_lower = user_message.lower()
                
                for s_name, s_def in servers_def.items():
                    # If server is not active but mentioned in prompt, trigger auth
                    if s_name not in active_servers and s_name.lower() in user_msg_lower:
                        if "interactive_auth" in s_def:
                            yield {
                                "type": "auth_required",
                                "server_name": s_name,
                                "auth_config": s_def["interactive_auth"]
                            }
                            return
        except Exception as e:
            # Check for Auth Required
            from app.mcp_client import MCPAuthRequiredError
            if isinstance(e, MCPAuthRequiredError):
                yield {
                    "type": "auth_required",
                    "server_name": e.server_name,
                    "auth_config": e.auth_config
                }
                return # Stop processing this message until auth is provided
            raise e
        
        # Build explicit tool availability message
        tool_names_by_server = {}
        for tool in tools:
            server = tool.get("server_name", "unknown")
            if server not in tool_names_by_server:
                tool_names_by_server[server] = []
            tool_names_by_server[server].append(tool["name"])

        # Phase 1: Intent Analysis
        intent_response = await self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Summarize the user's intent in one short sentence starting with 'User wants to...'. be very concise."},
                {"role": "user", "content": user_message}
            ]
        )
        intent_text = intent_response.choices[0].message.content
        yield {"type": "intent", "content": intent_text}
        add_message(self.conversation_id, "intent", intent_text)

        # Phase 2: Technical Planning
        active_tool_names = [t["name"] for t in tools]
        planning_prompt = (
            f"User request: {user_message}\n"
            f"Available tools: {', '.join(active_tool_names)}\n\n"
            "Create a concise step-by-step technical plan to fulfill the request. "
            "IMPORTANT: Explicitly specify which SERVER (e.g., 'mssql', 'filesystem') and which TOOL name to use for each step. "
            "If the request is database-related, you MUST use 'mssql' tools. "
            "At the end of your plan, list the REQUIRED SERVERS in the format: 'SERVERS: [server1, server2]'."
        )
        plan_response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a lead technical architect. Create a concise, numbered plan. Specify servers and tools for every step."},
                {"role": "user", "content": planning_prompt}
            ]
        )
        plan_text = plan_response.choices[0].message.content
        yield {"type": "plan", "content": plan_text}
        add_message(self.conversation_id, "plan", plan_text)

        # Implementation of Dynamic Tool Filtering
        required_servers = []
        if "SERVERS:" in plan_text:
            try:
                servers_part = plan_text.split("SERVERS:")[1].strip(" []\n\r")
                required_servers = [s.strip(" '\"") for s in servers_part.split(",")]
            except:
                pass
        
        # Robust parsing: include ALL servers whose names or tools are mentioned in the plan
        all_servers = list(tool_names_by_server.keys())
        plan_lower = plan_text.lower()
        
        # Add servers explicitly mentioned by ID
        for s in all_servers:
            if s.lower() in plan_lower and s not in required_servers:
                required_servers.append(s)
        
        # Add servers whose unique tools are mentioned
        for s, tools_in_s in tool_names_by_server.items():
            for t_name in tools_in_s:
                if t_name.lower() in plan_lower and s not in required_servers:
                    required_servers.append(s)

        # Consolidate Tools
        filtered_tools = tools
        if required_servers:
            filtered_tools = [t for t in tools if t.get("server_name") in required_servers]
            # Safety: always include system tools if they were in the original list
            # But here 'tools' only contains MCP tools. System tools are added later.
        
        openai_tools = []
        for tool in filtered_tools:
            openai_tools.append({
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": tool.get("inputSchema", {})
                }
            })
        
        # Always add system tools
        openai_tools.append({
            "type": "function",
            "function": {
                "name": "read_large_output",
                "description": "Read content of a large output that was intercepted.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "result_id": {"type": "string"},
                        "offset": {"type": "integer", "default": 0},
                        "limit": {"type": "integer", "default": 2000}
                    },
                    "required": ["result_id"]
                }
            }
        })
        openai_tools.append({
            "type": "function",
            "function": {
                "name": "ask_user",
                "description": "Ask the user a question for clarification.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "question": {"type": "string"}
                    },
                    "required": ["question"]
                }
            }
        })

        # BUILD UNIFIED SYSTEM PROMPT
        system_parts = []
        system_parts.append(f"## CURRENT GOAL\n{intent_text}")
        system_parts.append(f"## APPROVED TECHNICAL PLAN\n{plan_text}\nSTRICT REQUIREMENT: You MUST follow this plan exactly. Do NOT use tools outside of the servers listed in this plan.")
        
        tool_desc = "## TOOL ACCESS\nYou have access to the following tools:\n"
        for s in required_servers if required_servers else tool_names_by_server.keys():
            if s in tool_names_by_server:
                tool_desc += f"- {s}: {', '.join(tool_names_by_server[s])}\n"
        system_parts.append(tool_desc)

        if self.tool_contexts:
            ctx_parts = []
            for s_name, ctx in self.tool_contexts.items():
                if ctx and ctx.strip() and (not required_servers or s_name in required_servers):
                    ctx_parts.append(f"### {s_name} Context\n{ctx.strip()}")
            if ctx_parts:
                system_parts.append("## ADDITIONAL TOOL CONTEXT\n" + "\n".join(ctx_parts))

        system_parts.append("## OPERATIONAL CONSTRAINTS\n- If missing arguments, use 'ask_user'.\n- Read ALL chunks of large outputs silently.")
        system_parts.append("## DATA VISUALIZATION\nYou can use 'chart' code blocks for bar/line/pie charts (as JSON).")

        # Create a single system message for this session
        unified_prompt = "\n\n".join(system_parts)
        
        # We replace the previous system messages in history or just append this high-priority one
        # To avoid bloat and conflicting instructions, let's filter the history for old system messages
        self.history = [m for m in self.history if m["role"] != "system"]
        self.history.insert(0, {"role": "system", "content": unified_prompt})

        while True:
            # Filter history to only include roles supported by OpenAI
            # 'intent', 'plan', 'error' are our custom roles for UI orchestration
            sanitized_history = [
                m for m in self.history 
                if m.get("role") in ("system", "user", "assistant", "tool", "function", "developer")
            ]

            # 1. Call OpenAI
            response_stream = await self.client.chat.completions.create(
                model=self.model,
                messages=sanitized_history,
                tools=openai_tools if openai_tools else None,
                stream=True
            )

            current_tool_calls = {} # id -> ToolCall (accumulating)
            current_content = ""

            async for chunk in response_stream:
                delta = chunk.choices[0].delta
                
                # Handle Content
                if delta.content:
                    current_content += delta.content
                    yield {"type": "token", "content": delta.content}

                # Handle Tool Calls
                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        if tc.id:
                            current_tool_calls[tc.index] = {
                                "id": tc.id,
                                "name": tc.function.name,
                                "arguments": tc.function.arguments or ""
                            }
                        elif tc.function.arguments:
                            current_tool_calls[tc.index]["arguments"] += tc.function.arguments

            # 2. Execute tools
            if not current_tool_calls:
                # No tool calls and we finished the stream, so we are done with this turn.
                # However, we must ensure we have captured the full assistant message.
                self.history.append({"role": "assistant", "content": current_content})
                add_message(self.conversation_id, "assistant", current_content)
                break

            # If we had tool calls, we need to record the assistant's message (which includes the tool calls)
            # OpenAI expects the tool_calls array in the assistant message.
            assistant_msg = {
                "role": "assistant",
                "content": current_content,
                "tool_calls": []
            }
            
            # Reconstruct tool calls for history
            for index, tc_data in current_tool_calls.items():
                assistant_msg["tool_calls"].append({
                    "id": tc_data["id"],
                    "type": "function",
                    "function": {
                        "name": tc_data["name"],
                        "arguments": tc_data["arguments"]
                    }
                })
            self.history.append(assistant_msg)
            # Persist assistant message with tool calls
            add_message(self.conversation_id, "assistant", current_content, assistant_msg["tool_calls"])

            # Execute each tool
            tool_call_list = list(current_tool_calls.values())
            ask_user_triggered = False
            for i, tc_data in enumerate(tool_call_list):
                tool_name = tc_data["name"]
                tc_id = tc_data["id"]
                try:
                    args = json.loads(tc_data["arguments"])
                except json.JSONDecodeError:
                    args = {} 
                    yield {"type": "thought", "content": f"Error parsing arguments for {tool_name}"}
                    tool_output = f"Error: Could not parse arguments for tool '{tool_name}'."
                    # Continue to history append for this error
                    
                # Emit thought for meaningful tool calls (not internal pagination)
                if tool_name not in ("read_large_output",):
                    yield {"type": "thought", "content": f"Calling tool: {tool_name}..."}
                
                try:
                    # Special handling for system tools
                    if tool_name == "read_large_output":
                        result = await self.mcp_manager.read_large_output(
                            result_id=args.get("result_id"),
                            offset=args.get("offset", 0),
                            limit=args.get("limit", 2000)
                        )
                        tool_output = str(result)
                        print(f"[DEBUG] System Tool '{tool_name}' output length: {len(tool_output)}")
                    elif tool_name == "ask_user":
                        question = args.get("question")
                        yield {"type": "question", "content": question}
                        
                        tool_output = "User asked: " + question
                        print(f"[DEBUG] System Tool '{tool_name}': {question}")
                        
                        # Append the result so history is valid
                        self.history.append({
                            "role": "tool",
                            "tool_call_id": tc_id,
                            "content": tool_output
                        })
                        add_message(self.conversation_id, "tool", tool_output, tool_call_id=tc_id)
                        
                        # Append placeholder responses for ALL remaining tool calls
                        # so the conversation history stays valid for OpenAI
                        for remaining_tc in tool_call_list[i + 1:]:
                            placeholder = f"Tool execution skipped: waiting for user response to question."
                            self.history.append({
                                "role": "tool",
                                "tool_call_id": remaining_tc["id"],
                                "content": placeholder
                            })
                            add_message(self.conversation_id, "tool", placeholder, tool_call_id=remaining_tc["id"])
                        
                        ask_user_triggered = True
                        break # Stop executing more tools in this turn
                    else:
                        # MCP Tool
                        server_name = await self.mcp_manager.find_server_for_tool(tool_name, self.user_name)
                        if not server_name:
                            tool_output = f"Error: Tool '{tool_name}' not found."
                        else:
                            result = await self.mcp_manager.call_tool(
                                server_name=server_name,
                                tool_name=tool_name,
                                arguments=args,
                                user_name=self.user_name
                            )
                            
                            if isinstance(result, dict) and result.get("type") == "large_output_interception":
                                # Handle large output interception
                                interception_msg = f"Output intercepted. {result['summary']} Use read_large_output with result_id='{result['result_id']}' to read."
                                tool_output = interception_msg
                                print(f"[DEBUG] Tool '{tool_name}' large output intercepted: {result['result_id']}")
                            else:
                                tool_output = str(result)
                except Exception as e:
                    from app.mcp_client import MCPAuthRequiredError
                    if isinstance(e, MCPAuthRequiredError):
                        yield {
                            "type": "auth_required",
                            "server_name": e.server_name,
                            "auth_config": e.auth_config
                        }
                        return
                    tool_output = f"Error: {str(e)}"
                    yield {"type": "error", "content": tool_output}
                
                print(f"[DEBUG] Tool '{tool_name}' output preview: {tool_output[:5000]}...")

                # Append tool result to history
                self.history.append({
                    "role": "tool",
                    "tool_call_id": tc_id,
                    "content": tool_output
                })
                # Persist tool result
                add_message(self.conversation_id, "tool", tool_output, tool_call_id=tc_id)

            # If ask_user was triggered, stop the loop and return to client
            if ask_user_triggered:
                break

            # Loop continues to send tool outputs back to OpenAI

