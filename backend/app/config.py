import os
import json
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()

class Config:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    MCP_SERVERS_FILE = os.getenv("MCP_SERVERS_FILE", "mcp_servers.json")
    DB_CONNECTION_STRING = os.getenv("APP_DB_CONNECTION_STRING")

    @staticmethod
    def load_mcp_servers() -> Dict[str, Any]:
        if not os.path.exists(Config.MCP_SERVERS_FILE):
            return {}
        try:
            with open(Config.MCP_SERVERS_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading MCP servers config: {e}")
            return {}
