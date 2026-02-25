import json
import asyncio
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from contextlib import asynccontextmanager
from app.mcp_client import MCPClientManager
from app.orchestrator import Orchestrator
from app.database import init_db, create_conversation, get_conversation_history, add_message

# Global Manager
mcp_manager = MCPClientManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Connecting to MCP servers and initializing DB...")
    init_db()
    await mcp_manager.connect()
    yield
    # Shutdown
    print("Closing MCP connections...")
    await mcp_manager.cleanup()

app = FastAPI(lifespan=lifespan)

# CORS Configuration
origins = [
    "http://localhost:5173", # Vite Dev Server
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

import jwt
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from fastapi import Header, HTTPException, Depends, status, Body
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
    
from app.database import (
    init_db, create_conversation, get_conversation_history, add_message,
    get_user_conversations, get_conversation, update_conversation_title,
    get_user_preferences, update_user_preferences, get_last_empty_conversation,
    delete_conversation, get_user_mcp_configs, update_user_mcp_config,
    get_user_tool_contexts
)

SECRET_KEY = "supersecretkey" # In production, load from env
ALGORITHM = "HS256"

security = HTTPBearer()

# Models
class Token(BaseModel):
    access_token: str
    token_type: str
    user_name: str

class LoginRequest(BaseModel):
    user_name: str

class ChatStartRequest(BaseModel):
    pass # user_name comes from token now

class ChatRequest(BaseModel):
    message: str
    conversation_id: str

class ConversationSummary(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: Optional[str]

class ConversationDetail(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: Optional[str]
    messages: List[Dict[str, Any]]

class UserPreferences(BaseModel):
    model: str
    fontFamily: str
    fontSize: str

class InteractiveAuthConfig(BaseModel):
    type: str # "browser" (PAT) or "oauth" (SSO)
    instructions: str
    target_env_var: str
    button_text: Optional[str] = None
    auth_url: Optional[str] = None
    # OAuth specific (dynamic)
    authorize_url: Optional[str] = None
    token_url: Optional[str] = None
    scope: Optional[str] = None
    client_id_env: Optional[str] = None
    client_secret_env: Optional[str] = None
    redirect_uri_env: Optional[str] = None

class MCPServerInfo(BaseModel):
    name: str
    required_env: List[str]
    interactive_auth: Optional[InteractiveAuthConfig] = None

# Include Routers
from app.routers import auth
app.include_router(auth.router)

class UserMCPConfig(BaseModel):
    server_name: str
    env_vars: Dict[str, str]
    tool_context: Optional[str] = None

class MCPAuthSubmit(BaseModel):
    server_name: str
    token: str
    token_name: str

# Auth Helpers
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=1440) # 24 hours
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_name: str = payload.get("sub")
        if user_name is None:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        return user_name
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

# Endpoints

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.post("/login", response_model=Token)
async def login(request: LoginRequest):
    if not request.user_name:
         raise HTTPException(status_code=400, detail="User name is required")
    access_token = create_access_token(data={"sub": request.user_name})
    return {"access_token": access_token, "token_type": "bearer", "user_name": request.user_name}

@app.get("/conversations", response_model=List[ConversationSummary])
async def list_conversations(user_name: str = Depends(get_current_user)):
    convs = get_user_conversations(user_name, limit=20)
    return convs

@app.get("/conversations/{conversation_id}", response_model=ConversationDetail)
async def get_conversation_detail(conversation_id: str, user_name: str = Depends(get_current_user)):
    conv = get_conversation(conversation_id, user_name)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    history = get_conversation_history(conversation_id)
    return {
        "id": conv["id"],
        "title": conv["title"],
        "created_at": conv["created_at"],
        "updated_at": conv["updated_at"],
        "messages": history
    }

@app.delete("/conversations/{conversation_id}")
async def delete_conversation_endpoint(conversation_id: str, user_name: str = Depends(get_current_user)):
    success = delete_conversation(conversation_id, user_name)
    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found or access denied")
    return {"status": "success", "id": conversation_id}

@app.get("/user/preferences", response_model=UserPreferences)
async def get_preferences(user_name: str = Depends(get_current_user)):
    prefs = get_user_preferences(user_name)
    return prefs

@app.put("/user/preferences", response_model=UserPreferences)
async def update_preferences(prefs: UserPreferences, user_name: str = Depends(get_current_user)):
    update_user_preferences(user_name, prefs.dict())
    return prefs

@app.get("/mcp/servers", response_model=List[MCPServerInfo])
async def list_mcp_servers():
    from app.config import Config
    servers = Config.load_mcp_servers()
    result = []
    for name, config in servers.items():
        result.append({
            "name": name,
            "required_env": config.get("required_env", []),
            "interactive_auth": config.get("interactive_auth")
        })
    return result

@app.get("/user/mcp-configs", response_model=Dict[str, Dict[str, str]])
async def get_user_mcp_configs_endpoint(user_name: str = Depends(get_current_user)):
    return get_user_mcp_configs(user_name)

@app.post("/user/mcp-configs")
async def update_user_mcp_config_endpoint(config: UserMCPConfig, user_name: str = Depends(get_current_user)):
    update_user_mcp_config(user_name, config.server_name, config.env_vars, config.tool_context)
    return {"status": "success"}

@app.post("/user/mcp-auth")
async def update_user_mcp_auth_endpoint(auth: MCPAuthSubmit, user_name: str = Depends(get_current_user)):
    # Load existing config
    configs = get_user_mcp_configs(user_name)
    env_vars = configs.get(auth.server_name, {})
    # Update with new token
    env_vars[auth.token_name] = auth.token
    # Save back
    update_user_mcp_config(user_name, auth.server_name, env_vars)
    return {"status": "success"}

@app.get("/user/tool-contexts")
async def get_tool_contexts_endpoint(user_name: str = Depends(get_current_user)):
    return get_user_tool_contexts(user_name)

@app.post("/chat/start")
async def start_chat(request: ChatStartRequest, user_name: str = Depends(get_current_user)):
    # Check for existing empty conversation
    empty_conv_id = get_last_empty_conversation(user_name)
    if empty_conv_id:
        return {"conversation_id": empty_conv_id, "message": f"Hello again {user_name}! I see you have an open conversation. How can I help?"}

    # Create conversation with default title
    conversation_id = create_conversation(user_name, title="New Conversation")
    return {"conversation_id": conversation_id, "message": f"Hello {user_name}! How can I help you today?"}

@app.post("/chat")
async def chat_endpoint(request: ChatRequest = Body(...), user_name: str = Depends(get_current_user)):
    # Verify conversation belongs to user
    conv = get_conversation(request.conversation_id, user_name)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found or access denied")
        
    # Load history
    history = get_conversation_history(request.conversation_id)
    
    # Simple Title Generation Logic (on first user message)
    if conv["title"] == "New Conversation" and len(history) == 0:
        new_title = request.message[:50] + "..." if len(request.message) > 50 else request.message
        update_conversation_title(request.conversation_id, new_title)
    
    # Save user message
    add_message(request.conversation_id, "user", request.message)

    # Get user preferences for model
    prefs = get_user_preferences(user_name)
    model = prefs.get("model", "gpt-4o")

    # Get tool contexts
    tool_contexts = get_user_tool_contexts(user_name)

    orchestrator = Orchestrator(mcp_manager, request.conversation_id, history, model=model, user_name=user_name, tool_contexts=tool_contexts)
    
    # We need a generator that yields SSE formatted data
    async def event_generator():
        async for event in orchestrator.process_message(request.message):
            # SSE format: "data: <json>\n\n"
            yield f"data: {json.dumps(event)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
