import asyncio
import json
import os
import traceback
from contextlib import AsyncExitStack
from typing import Dict, Any, List, Optional, Union, Tuple
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import CallToolResult, TextContent, ImageContent, EmbeddedResource
from app.config import Config

class MCPAuthRequiredError(Exception):
    def __init__(self, server_name: str, auth_config: Dict[str, Any]):
        self.server_name = server_name
        self.auth_config = auth_config
        super().__init__(f"Authentication required for server '{server_name}'")

class MCPClientManager:
    def __init__(self):
        # Global sessions (no env vars required) - long-lived
        self.global_sessions: Dict[str, ClientSession] = {}
        
        self.exit_stack = AsyncExitStack()
        # Threshold for "Large Output" in characters
        self.LARGE_OUTPUT_THRESHOLD = 2000 
        self.large_results: Dict[str, str] = {} # Cache for large results

        # Cache of tool definitions from user-configured servers
        # This avoids needing a live session just to list tools
        # Structure: { user_name: { server_name: [tool_dicts] } }
        self._user_tool_cache: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}

    async def connect(self):
        """Connect to global MCP servers (those with no required env vars)."""
        servers = Config.load_mcp_servers()
        for name, config in servers.items():
            required_env = config.get("required_env", [])
            # Check if all required env vars are already in the OS environment (e.g. from .env)
            all_in_os = all(os.getenv(var) for var in required_env)
            
            if required_env and not all_in_os:
                print(f"Skipping global connection for {name} (requires user config)")
                continue

            try:
                await self._connect_server(name, config, self.global_sessions, self.exit_stack)
                if required_env:
                    print(f"Connected to Global MCP server: {name} (using OS environment)")
                else:
                    print(f"Connected to Global MCP server: {name}")
            except Exception as e:
                print(f"Failed to connect to global server {name}: {e}")

    async def _connect_server(
        self, name: str, config: Dict[str, Any], 
        session_store: Dict[str, ClientSession], 
        stack: AsyncExitStack,
        env_vars: Dict[str, str] = None
    ):
        """Helper to connect to a single server and store in the provided dict."""
        command = config.get("command")
        args = config.get("args", [])
        
        # Start with current OS environment so the subprocess has PATH etc.
        env = dict(os.environ)
        # Overlay any server-specific env from config
        if config.get("env"):
            env.update(config["env"])
        # Overlay user-provided env vars
        if env_vars:
            env.update(env_vars)
            
        # ENSURE ISOLATION: Remove internal app connection string from tool environment
        # to prevent tools from accidentally using the app's database if they misbehave
        if "APP_DB_CONNECTION_STRING" in env:
            del env["APP_DB_CONNECTION_STRING"]
            
        server_params = StdioServerParameters(
            command=command,
            args=args,
            env=env
        )
        
        stdio_transport = await stack.enter_async_context(
            stdio_client(server_params)
        )
        read, write = stdio_transport
        session = await stack.enter_async_context(
            ClientSession(read, write)
        )
        await session.initialize()
        session_store[name] = session

    def _get_user_env_vars(self, server_name: str, user_name: str) -> Optional[Dict[str, str]]:
        """Get user env vars for a server from DB. Returns None if not configured."""
        from app.database import get_user_mcp_configs
        user_configs = get_user_mcp_configs(user_name)
        
        servers_def = Config.load_mcp_servers()
        server_def = servers_def.get(server_name)
        if not server_def:
            return None
        
        required_vars = server_def.get("required_env", [])
        user_env_vars = user_configs.get(server_name)
        
        if required_vars and not user_env_vars:
            # Check for interactive auth config
            if "interactive_auth" in server_def:
                raise MCPAuthRequiredError(server_name, server_def["interactive_auth"])
            return None
        
        if required_vars:
            # A variable is missing if it's not in the dict OR its value is empty/whitespace
            missing = [var for var in required_vars if var not in user_env_vars or not str(user_env_vars[var]).strip()]
            if missing:
                if "interactive_auth" in server_def:
                    raise MCPAuthRequiredError(server_name, server_def["interactive_auth"])
                print(f"User {user_name} missing env vars for {server_name}: {missing}")
                return None
        
        return user_env_vars or {}

    async def _run_with_fresh_session(
        self, server_name: str, user_name: str, 
        action: str, action_fn
    ):
        """
        Create a fresh session for a user-configured server, run an action, and clean up.
        This avoids stale session issues entirely.
        """
        servers_def = Config.load_mcp_servers()
        server_def = servers_def.get(server_name)
        if not server_def:
            raise ValueError(f"Server '{server_name}' not found in config.")
        
        user_env_vars = self._get_user_env_vars(server_name, user_name)
        if user_env_vars is None:
            raise ValueError(f"Server '{server_name}' not configured for user '{user_name}'.")

        # Create a dedicated exit stack for this ephemeral session
        async with AsyncExitStack() as temp_stack:
            temp_sessions = {}
            await self._connect_server(server_name, server_def, temp_sessions, temp_stack, user_env_vars)
            session = temp_sessions[server_name]
            print(f"[{action}] Fresh session for {server_name} (user: {user_name})")
            return await action_fn(session)

    async def list_tools(self, user_name: str = None) -> Tuple[List[Dict[str, Any]], List[str]]:
        """List tools from all available servers for the user (global + configured). Returns (tools, errors)."""
        all_tools = []
        errors = []
        
        # Global tools
        for server_name, session in self.global_sessions.items():
            try:
                result = await session.list_tools()
                for tool in result.tools:
                    tool_dict = tool.model_dump()
                    tool_dict["server_name"] = server_name
                    all_tools.append(tool_dict)
            except Exception as e:
                error_msg = f"Error listing tools for global server {server_name}: {e}"
                print(error_msg)
                errors.append(error_msg)

        # User configured tools - use fresh session each time
        if user_name:
            servers_def = Config.load_mcp_servers()
            from app.database import get_user_mcp_configs
            user_configs = get_user_mcp_configs(user_name)
            
            for server_name in servers_def:
                if server_name in self.global_sessions:
                    continue
                
                if server_name not in user_configs:
                    continue

                # Check cache first
                if user_name in self._user_tool_cache and server_name in self._user_tool_cache[user_name]:
                    all_tools.extend(self._user_tool_cache[user_name][server_name])
                    continue

                try:
                    async def _list(session):
                        result = await session.list_tools()
                        tools = []
                        for tool in result.tools:
                            tool_dict = tool.model_dump()
                            tool_dict["server_name"] = server_name
                            tools.append(tool_dict)
                        return tools
                    
                    user_tools = await self._run_with_fresh_session(
                        server_name, user_name, "list_tools", _list
                    )
                    all_tools.extend(user_tools)
                    
                    # Cache tool definitions so we know which tools exist
                    if user_name not in self._user_tool_cache:
                        self._user_tool_cache[user_name] = {}
                    self._user_tool_cache[user_name][server_name] = user_tools
                    
                except Exception as e:
                    error_msg = f"Error listing tools for user server {server_name}: {type(e).__name__}: {str(e)}"
                    print(error_msg)
                    print(traceback.format_exc())
                    errors.append(error_msg)

        return all_tools, errors

    async def find_server_for_tool(self, tool_name: str, user_name: str = None) -> Optional[str]:
        """Find which server provides the given tool."""
        # Check Global
        for server_name, session in self.global_sessions.items():
            try:
                tools_result = await session.list_tools()
                for tool in tools_result.tools:
                    if tool.name == tool_name:
                        return server_name
            except: pass
            
        if not user_name:
            return None

        # Check cached user tool definitions (populated by list_tools)
        if user_name in self._user_tool_cache:
            for server_name, tools in self._user_tool_cache[user_name].items():
                for tool in tools:
                    if tool["name"] == tool_name:
                        return server_name
        
        # Fallback: iterate over all configured servers
        servers_def = Config.load_mcp_servers()
        from app.database import get_user_mcp_configs
        user_configs = get_user_mcp_configs(user_name)
        
        for server_name in servers_def:
            if server_name in self.global_sessions:
                continue
            if server_name not in user_configs:
                # Log that this server is available but unconfigured
                errors.append(f"Server '{server_name}' is available but not configured for user '{user_name}'. Authentication required.")
                continue
            
            try:
                async def _find(session):
                    tools_result = await session.list_tools()
                    for tool in tools_result.tools:
                        if tool.name == tool_name:
                            return True
                    return False
                
                found = await self._run_with_fresh_session(
                    server_name, user_name, "find_tool", _find
                )
                if found:
                    return server_name
            except:
                pass
                 
        return None

    async def read_large_output(self, result_id: str, offset: int = 0, limit: int = 2000) -> str:
        """Retrieve a specific chunk of a large output."""
        if result_id not in self.large_results:
            return "Error: Result ID not found or expired."
        
        full_text = self.large_results[result_id]
        
        if limit == -1:
            return full_text[offset:]
            
        end = offset + limit
        chunk = full_text[offset:end]
        
        remaining = len(full_text) - end
        if remaining > 0:
            return f"{chunk}\n... ({remaining} characters remaining. Use offset={end} to read more)"
        return chunk
    
    async def call_tool(
        self, 
        server_name: str, 
        tool_name: str, 
        arguments: Dict[str, Any],
        user_name: str = None
    ) -> Union[str, Dict[str, Any]]:
        """
        Call a tool and return the result.
        Intercepts large outputs.
        For user-configured servers, creates a fresh session per call.
        """
        # Global server: use persistent session
        if server_name in self.global_sessions:
            session = self.global_sessions[server_name]
            return await self._execute_tool(session, tool_name, arguments)
        
        # User server: create fresh session
        if not user_name:
            return f"Error: Server '{server_name}' not found or not configured."

        try:
            async def _call(session):
                return await self._execute_tool(session, tool_name, arguments)
            
            return await self._run_with_fresh_session(
                server_name, user_name, f"call_tool({tool_name})", _call
            )
        except Exception as e:
            error_detail = f"Error executing tool {tool_name}: {type(e).__name__}: {str(e)}"
            print(error_detail)
            print(traceback.format_exc())
            return error_detail
    
    async def _execute_tool(self, session: ClientSession, tool_name: str, arguments: Dict[str, Any]) -> Union[str, Dict[str, Any]]:
        """Execute a tool on a given session and handle large output interception."""
        result: CallToolResult = await session.call_tool(tool_name, arguments)
        
        # Combine text content
        full_text = ""
        for content in result.content:
            if isinstance(content, TextContent):
                full_text += content.text
            elif isinstance(content, ImageContent):
                full_text += "[Image Content]"
            elif isinstance(content, EmbeddedResource):
                full_text += "[Embedded Resource]"

        # Check for large output
        if len(full_text) > self.LARGE_OUTPUT_THRESHOLD:
            import uuid
            result_id = str(uuid.uuid4())
            self.large_results[result_id] = full_text
            
            return {
                "type": "large_output_interception",
                "result_id": result_id,
                "summary": f"The tool output is {len(full_text)} characters long.",
                "preview": full_text[:500] + "\n...[truncated]...",
                "system_instruction": (
                    "The output is truncated. You MUST use the `read_large_output` tool "
                    f"with result_id='{result_id}' to read more. "
                    "You can read it in chunks (offset=0, limit=2000) or specify limit=-1 to read all (if you are sure)."
                )
            }

        return full_text

    async def cleanup(self):
        await self.exit_stack.aclose()
