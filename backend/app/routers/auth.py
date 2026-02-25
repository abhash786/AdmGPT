from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
import httpx
import os
import json
import urllib.parse
from datetime import datetime
from app.database import update_user_mcp_config, get_user_mcp_configs
from app.config import Config

router = APIRouter(prefix="/auth", tags=["auth"])

@router.get("/login/{server_name}")
async def dynamic_login(server_name: str, user_name: str):
    servers = Config.load_mcp_servers()
    server_config = servers.get(server_name)
    if not server_config:
        raise HTTPException(status_code=404, detail=f"Server '{server_name}' not found")
        
    auth_config = server_config.get("interactive_auth")
    if not auth_config or auth_config.get("type") != "oauth":
        raise HTTPException(status_code=400, detail=f"Server '{server_name}' does not support OAuth")

    client_id_env = auth_config.get("client_id_env")
    client_id = os.getenv(client_id_env)
    
    if not client_id:
        raise HTTPException(status_code=500, detail=f"OAuth Client ID ({client_id_env}) not found in .env")
        
    if client_id == "PLACEHOLDER_ID":
        print(f"WARNING: Using placeholder {client_id_env}. GitHub authentication WILL fail.")

    authorize_url = auth_config.get("authorize_url")
    redirect_uri_env = auth_config.get("redirect_uri_env")
    redirect_uri = os.getenv(redirect_uri_env)
    scope = auth_config.get("scope", "")
    
    state_json = json.dumps({"user_name": user_name, "server_name": server_name})
    state = urllib.parse.quote(state_json)
    
    # Construct authorize URL
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": scope,
        "state": state,
        "response_type": "code"
    }
    encoded_params = urllib.parse.urlencode({k: v for k, v in params.items() if v})
    url = f"{authorize_url}?{encoded_params}"
    
    return RedirectResponse(url)

@router.get("/callback/{server_name}")
async def dynamic_callback(server_name: str, code: str, state: str):
    log_file = os.path.join(os.getcwd(), "auth_debug.log")
    with open(log_file, "a") as f:
        f.write(f"\n--- Callback Started for {server_name} at {datetime.now()} ---\n")

    servers = Config.load_mcp_servers()
    server_config = servers.get(server_name)
    auth_config = server_config.get("interactive_auth") if server_config else None
    
    if not auth_config:
        raise HTTPException(status_code=404, detail=f"OAuth config missing for {server_name}")

    client_id_env = auth_config.get("client_id_env")
    client_secret_env = auth_config.get("client_secret_env")
    client_id = os.getenv(client_id_env)
    client_secret = os.getenv(client_secret_env)
    token_url = auth_config.get("token_url")
    redirect_uri = os.getenv(auth_config.get("redirect_uri_env"))
    target_env_var = auth_config.get("target_env_var")

    if not client_secret:
        with open(log_file, "a") as f: f.write(f"Error: {client_secret_env} missing\n")
        raise HTTPException(status_code=500, detail=f"Client Secret ({client_secret_env}) missing")
    
    try:
        decoded_state = urllib.parse.unquote(state)
        state_data = json.loads(decoded_state)
        user_name = state_data.get("user_name")
    except Exception as e:
        with open(log_file, "a") as f: f.write(f"Error parsing state: {e}\n")
        raise HTTPException(status_code=400, detail="Invalid state parameter")

    # Exchange code for token
    async with httpx.AsyncClient() as client:
        response = await client.post(
            token_url,
            headers={"Accept": "application/json"},
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code"
            }
        )
        
        if response.status_code != 200:
            with open(log_file, "a") as f: f.write(f"Error exchanging code: {response.status_code} - {response.text}\n")
            raise HTTPException(status_code=400, detail="Failed to exchange code for token")
        
        data = response.json()
        access_token = data.get("access_token")
        
        if not access_token:
            with open(log_file, "a") as f: f.write(f"Error: No access token in response {data}\n")
            raise HTTPException(status_code=400, detail=f"No access token in response")

        # Save token to user's MCP config
        update_user_mcp_config(
            user_name=user_name,
            server_name=server_name,
            env_vars={target_env_var: access_token}
        )
        with open(log_file, "a") as f: f.write(f"Token saved successfully for user {user_name}.\n")
        
        return (
            "<html><body onload='if(window.opener){window.opener.postMessage(\"oauth-success\", \"*\");}window.close()'>"
            f"<h3>{server_name.capitalize()} Authenticated Successfully!</h3>"
            "<p>You can close this window now.</p>"
            "</body></html>"
        )
