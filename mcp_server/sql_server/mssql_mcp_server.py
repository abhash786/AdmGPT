# ==========================================
# 1. CORPORATE POLICY & PYTHON 3.14 BYPASS
# ==========================================
import sys
from types import ModuleType

# Create a 'fake' uuid_utils module to satisfy internal library checks
# without triggering the blocked DLL load on corporate machines.
mock_uuid = ModuleType("uuid_utils")
mock_uuid.compat = ModuleType("uuid_utils.compat")
mock_uuid.uuid7 = lambda: None
mock_uuid.compat.uuid7 = lambda: None

sys.modules["uuid_utils"] = mock_uuid
sys.modules["uuid_utils.compat"] = mock_uuid.compat

# ==========================================
# 2. CORE IMPORTS & SERVER SETUP
# ==========================================
import os
import pyodbc
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP for SQL
mcp = FastMCP("mssql")

def get_db_connection():
    """Establishes connection using the provided connection string."""
    conn_str = os.getenv("DB_CONNECTION_STRING")
    if not conn_str:
        raise ValueError("DB_CONNECTION_STRING not found in environment.")
    return pyodbc.connect(conn_str)

# ==========================================
# 3. MCP TOOL DEFINITIONS (The Black Box)
# ==========================================

@mcp.tool()
def list_tables() -> str:
    """Lists all available tables in the database."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE='BASE TABLE'")
            tables = [row.TABLE_NAME for row in cursor.fetchall()]
            return f"Available Tables: {', '.join(tables)}"
    except Exception as e:
        return f"Error listing tables: {str(e)}"

@mcp.tool()
def query_db(sql_query: str) -> str:
    """
    Executes a read-only SQL query and returns the results.
    Args:
        sql_query: The T-SQL query to execute.
    """
    # Basic safety: Prevent destructive operations in this tool
    forbidden = ["DROP", "DELETE", "TRUNCATE", "UPDATE", "INSERT"]
    if any(cmd in sql_query.upper() for cmd in forbidden):
        return "Error: Only SELECT queries are permitted via this tool."

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql_query)
            columns = [column[0] for column in cursor.description]
            rows = cursor.fetchall()
            
            # Format results as a simple string for the LLM
            result = [dict(zip(columns, row)) for row in rows]
            return str(result)
    except Exception as e:
        return f"Database Error: {str(e)}"
    
@mcp.tool()
def describe_table(table_name: str) -> str:
    """Returns the column names and types for a specific table."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = ?", (table_name,))
            columns = cursor.fetchall()
            if not columns: return f"Table '{table_name}' not found."
            return "\n".join([f"{col.COLUMN_NAME} ({col.DATA_TYPE})" for col in columns])
    except Exception as e:
        return f"Error: {str(e)}"    

# ==========================================
# 4. SERVER ENTRY POINT
# ==========================================
if __name__ == "__main__":
    # FastMCP handles the stdio transport automatically for the registry.
    mcp.run()