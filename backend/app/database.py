import pyodbc
import json
import uuid
import re
from datetime import datetime
from typing import List, Dict, Any, Optional
from app.config import Config


def _parse_db_name(connection_string: str) -> Optional[str]:
    """Extract the DATABASE name from an ODBC connection string."""
    match = re.search(r'DATABASE=([^;]+)', connection_string, re.IGNORECASE)
    return match.group(1) if match else None


def _get_master_connection_string(connection_string: str) -> str:
    """Replace the DATABASE in the connection string with 'master'."""
    return re.sub(r'DATABASE=[^;]+', 'DATABASE=master', connection_string, flags=re.IGNORECASE)


def _ensure_database_exists():
    """Connect to 'master' and create the target database if it does not exist."""
    conn_str = Config.DB_CONNECTION_STRING
    db_name = _parse_db_name(conn_str)
    if not db_name:
        print("Warning: Could not parse DATABASE name from connection string. Skipping auto-create.")
        return

    print(f"[DEBUG] Ensuring database exists: {db_name}")
    master_conn_str = _get_master_connection_string(conn_str)
    print(f"[DEBUG] Connecting to master: {master_conn_str}")
    try:
        conn = pyodbc.connect(master_conn_str, autocommit=True, timeout=10)
        print("[DEBUG] Connected to master.")
        cursor = conn.cursor()
        cursor.execute("SELECT DB_ID(?)", (db_name,))
        row = cursor.fetchone()
        if row[0] is None:
            print(f"Database '{db_name}' not found. Creating...")
            cursor.execute(f"CREATE DATABASE [{db_name}]")
            print(f"Database '{db_name}' created successfully.")
        else:
            print(f"Database '{db_name}' already exists.")
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"[ERROR] Failed to ensure database exists: {e}")
        # Re-raise so startup fails visibly
        raise


def get_db():
    """Get a new database connection using the configured connection string."""
    print(f"[DEBUG] Getting DB connection: {Config.DB_CONNECTION_STRING}")
    try:
        conn = pyodbc.connect(Config.DB_CONNECTION_STRING, timeout=10)
        print("[DEBUG] DB connection successful.")
        return conn
    except Exception as e:
        print(f"[ERROR] DB connection failed: {e}")
        raise


def _rows_to_dicts(cursor) -> List[Dict[str, Any]]:
    """Convert pyodbc cursor results to a list of dicts."""
    if not cursor.description:
        return []
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def _row_to_dict(cursor) -> Optional[Dict[str, Any]]:
    """Fetch one row from cursor and return as dict, or None."""
    if not cursor.description:
        return None
    columns = [col[0] for col in cursor.description]
    row = cursor.fetchone()
    if row is None:
        return None
    return dict(zip(columns, row))


def init_db():
    """Initialize database and tables if they do not exist."""
    _ensure_database_exists()
    conn = get_db()
    cursor = conn.cursor()

    # Conversations table
    cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'conversations')
        CREATE TABLE conversations (
            id NVARCHAR(36) PRIMARY KEY,
            user_name NVARCHAR(255) NOT NULL,
            title NVARCHAR(500),
            created_at DATETIME2 DEFAULT GETUTCDATE(),
            updated_at DATETIME2 DEFAULT GETUTCDATE()
        )
    """)

    # Messages table
    cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'messages')
        CREATE TABLE messages (
            id INT IDENTITY(1,1) PRIMARY KEY,
            conversation_id NVARCHAR(36) NOT NULL,
            role NVARCHAR(50) NOT NULL,
            content NVARCHAR(MAX),
            tool_calls NVARCHAR(MAX),
            tool_call_id NVARCHAR(255),
            created_at DATETIME2 DEFAULT GETUTCDATE(),
            FOREIGN KEY(conversation_id) REFERENCES conversations(id)
        )
    """)

    # Users table
    cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'users')
        CREATE TABLE users (
            user_name NVARCHAR(255) PRIMARY KEY,
            preferences NVARCHAR(MAX)
        )
    """)

    # MCP Configs table
    cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'user_mcp_configs')
        CREATE TABLE user_mcp_configs (
            user_name NVARCHAR(255),
            server_name NVARCHAR(255),
            env_vars NVARCHAR(MAX),
            tool_context NVARCHAR(MAX),
            updated_at DATETIME2 DEFAULT GETUTCDATE(),
            PRIMARY KEY (user_name, server_name),
            FOREIGN KEY(user_name) REFERENCES users(user_name)
        )
    """)

    conn.commit()

    # Schema migrations — add columns if missing
    _ensure_schema_updates(conn)

    cursor.close()
    conn.close()
    print("Database initialized successfully (SQL Server).")


def _ensure_schema_updates(conn):
    """Add any missing columns for schema evolution."""
    cursor = conn.cursor()

    # Check for 'title' column in conversations
    cursor.execute("""
        IF NOT EXISTS (
            SELECT * FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = 'conversations' AND COLUMN_NAME = 'title'
        )
        ALTER TABLE conversations ADD title NVARCHAR(500)
    """)

    # Check for 'updated_at' column in conversations
    cursor.execute("""
        IF NOT EXISTS (
            SELECT * FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = 'conversations' AND COLUMN_NAME = 'updated_at'
        )
        BEGIN
            ALTER TABLE conversations ADD updated_at DATETIME2
            UPDATE conversations SET updated_at = created_at WHERE updated_at IS NULL
        END
    """)

    # Check for 'tool_context' column in user_mcp_configs
    cursor.execute("""
        IF NOT EXISTS (
            SELECT * FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = 'user_mcp_configs' AND COLUMN_NAME = 'tool_context'
        )
        ALTER TABLE user_mcp_configs ADD tool_context NVARCHAR(MAX)
    """)

    conn.commit()
    cursor.close()


def create_conversation(user_name: str, title: Optional[str] = None) -> str:
    conn = get_db()
    cursor = conn.cursor()
    conv_id = str(uuid.uuid4())
    cursor.execute(
        "INSERT INTO conversations (id, user_name, title) VALUES (?, ?, ?)",
        (conv_id, user_name, title)
    )
    conn.commit()
    cursor.close()
    conn.close()
    return conv_id


def get_user_conversations(user_name: str, limit: int = 20) -> List[Dict[str, Any]]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT TOP (?) id, title, created_at, updated_at
        FROM conversations
        WHERE user_name = ?
        ORDER BY updated_at DESC
    """, (limit, user_name))
    rows = _rows_to_dicts(cursor)
    cursor.close()
    conn.close()

    conversations = []
    for row in rows:
        conversations.append({
            "id": row["id"],
            "title": row["title"] or "New Conversation",
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
        })
    return conversations


def get_user_mcp_configs(user_name: str) -> Dict[str, Dict[str, str]]:
    """Get all MCP configurations for a user."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT server_name, env_vars FROM user_mcp_configs WHERE user_name = ?",
        (user_name,)
    )
    rows = _rows_to_dicts(cursor)
    cursor.close()
    conn.close()

    configs = {}
    for row in rows:
        try:
            configs[row["server_name"]] = json.loads(row["env_vars"])
        except:
            configs[row["server_name"]] = {}
    return configs


def _ensure_user_exists(user_name: str, conn=None):
    """Ensure user exists in the users table (insert if missing)."""
    close_conn = False
    if conn is None:
        conn = get_db()
        close_conn = True
    cursor = conn.cursor()
    cursor.execute("""
        IF NOT EXISTS (SELECT 1 FROM users WHERE user_name = ?)
        INSERT INTO users (user_name) VALUES (?)
    """, (user_name, user_name))
    conn.commit()
    cursor.close()
    if close_conn:
        conn.close()


def update_user_mcp_config(user_name: str, server_name: str, env_vars: Dict[str, str], tool_context: str = None):
    """Update or insert MCP configuration for a user. If env_vars is empty (after filtering empty strings), the config is removed."""
    conn = get_db()
    _ensure_user_exists(user_name, conn)
    cursor = conn.cursor()
    
    # Filter out empty string values
    filtered_env = {k: v for k, v in env_vars.items() if v and v.strip()}
    
    if not filtered_env and not tool_context:
        # If everything is cleared, delete the configuration
        cursor.execute("""
            DELETE FROM user_mcp_configs 
            WHERE user_name = ? AND server_name = ?
        """, (user_name, server_name))
        print(f"Deleted MCP config for user '{user_name}', server '{server_name}'")
    else:
        env_json = json.dumps(filtered_env)
        # SQL Server MERGE for upsert
        cursor.execute("""
            MERGE user_mcp_configs AS target
            USING (SELECT ? AS user_name, ? AS server_name) AS source
            ON target.user_name = source.user_name AND target.server_name = source.server_name
            WHEN MATCHED THEN
                UPDATE SET env_vars = ?, tool_context = ?, updated_at = GETUTCDATE()
            WHEN NOT MATCHED THEN
                INSERT (user_name, server_name, env_vars, tool_context, updated_at)
                VALUES (?, ?, ?, ?, GETUTCDATE());
        """, (user_name, server_name, env_json, tool_context, user_name, server_name, env_json, tool_context))
        print(f"Updated MCP config for user '{user_name}', server '{server_name}'")

    conn.commit()
    cursor.close()
    conn.close()


def get_user_tool_contexts(user_name: str) -> Dict[str, str]:
    """Get all non-empty tool contexts for a user, keyed by server_name."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT server_name, tool_context FROM user_mcp_configs WHERE user_name = ? AND tool_context IS NOT NULL AND tool_context != ''",
        (user_name,)
    )
    rows = _rows_to_dicts(cursor)
    cursor.close()
    conn.close()
    return {row["server_name"]: row["tool_context"] for row in rows}


def get_conversation(conversation_id: str, user_name: str) -> Optional[Dict[str, Any]]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, user_name, title, created_at, updated_at FROM conversations WHERE id = ? AND user_name = ?",
        (conversation_id, user_name)
    )
    row = _row_to_dict(cursor)
    cursor.close()
    conn.close()

    if not row:
        return None

    return {
        "id": row["id"],
        "user_name": row["user_name"],
        "title": row["title"],
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
    }


def delete_conversation(conversation_id: str, user_name: str) -> bool:
    """Deletes a conversation and its messages if it belongs to the user."""
    conn = get_db()
    cursor = conn.cursor()

    # Check ownership
    cursor.execute(
        "SELECT id FROM conversations WHERE id = ? AND user_name = ?",
        (conversation_id, user_name)
    )
    if not cursor.fetchone():
        cursor.close()
        conn.close()
        return False

    # Delete messages first (no CASCADE)
    cursor.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
    # Delete conversation
    cursor.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))

    conn.commit()
    cursor.close()
    conn.close()
    return True


def get_last_empty_conversation(user_name: str) -> Optional[str]:
    """
    Returns the ID of the most recent conversation with no messages for the user.
    Performs a case-insensitive lookup and updates the username to match current session if needed.
    """
    conn = get_db()
    cursor = conn.cursor()
    # SQL Server collation is typically case-insensitive by default,
    # but we use LOWER() for safety
    cursor.execute("""
        SELECT TOP 1 c.id, c.user_name
        FROM conversations c
        LEFT JOIN messages m ON c.id = m.conversation_id
        WHERE LOWER(c.user_name) = LOWER(?) AND m.id IS NULL
        ORDER BY c.updated_at DESC
    """, (user_name,))
    row = _row_to_dict(cursor)

    if row:
        conv_id = row["id"]
        # If case mismatch, update it to match current user_name so ownership checks pass
        if row["user_name"] != user_name:
            cursor.execute(
                "UPDATE conversations SET user_name = ? WHERE id = ?",
                (user_name, conv_id)
            )
            conn.commit()

        cursor.close()
        conn.close()
        return conv_id

    cursor.close()
    conn.close()
    return None


def update_conversation_title(conversation_id: str, title: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE conversations SET title = ? WHERE id = ?",
        (title, conversation_id)
    )
    conn.commit()
    cursor.close()
    conn.close()


def touch_conversation(conversation_id: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE conversations SET updated_at = GETUTCDATE() WHERE id = ?",
        (conversation_id,)
    )
    conn.commit()
    cursor.close()
    conn.close()


def add_message(
    conversation_id: str,
    role: str,
    content: Optional[str] = None,
    tool_calls: Optional[List[Dict]] = None,
    tool_call_id: Optional[str] = None
):
    conn = get_db()
    cursor = conn.cursor()

    tool_calls_json = json.dumps(tool_calls) if tool_calls else None

    cursor.execute("""
        INSERT INTO messages (conversation_id, role, content, tool_calls, tool_call_id)
        VALUES (?, ?, ?, ?, ?)
    """, (conversation_id, role, content, tool_calls_json, tool_call_id))

    conn.commit()
    cursor.close()
    conn.close()

    # Update parent conversation timestamp
    touch_conversation(conversation_id)


def get_conversation_history(conversation_id: str) -> List[Dict[str, Any]]:
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT role, content, tool_calls, tool_call_id FROM messages WHERE conversation_id = ? ORDER BY id ASC",
        (conversation_id,)
    )
    rows = _rows_to_dicts(cursor)

    history = []
    for row in rows:
        msg = {
            "role": row["role"],
            "content": row["content"]
        }
        if row["tool_calls"]:
            msg["tool_calls"] = json.loads(row["tool_calls"])
        if row["tool_call_id"]:
            msg["tool_call_id"] = row["tool_call_id"]

        history.append(msg)

    cursor.close()
    conn.close()
    return history


def get_user_preferences(user_name: str) -> Dict[str, Any]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT preferences FROM users WHERE user_name = ?", (user_name,))
    row = _row_to_dict(cursor)
    cursor.close()
    conn.close()

    if row and row["preferences"]:
        try:
            return json.loads(row["preferences"])
        except json.JSONDecodeError:
            pass

    # Default preferences
    return {
        "model": "gpt-4o",
        "fontFamily": "Inter",
        "fontSize": "Medium"
    }


def update_user_preferences(user_name: str, preferences: Dict[str, Any]):
    conn = get_db()
    cursor = conn.cursor()
    # SQL Server MERGE for upsert
    cursor.execute("""
        MERGE users AS target
        USING (SELECT ? AS user_name) AS source
        ON target.user_name = source.user_name
        WHEN MATCHED THEN
            UPDATE SET preferences = ?
        WHEN NOT MATCHED THEN
            INSERT (user_name, preferences) VALUES (?, ?);
    """, (user_name, json.dumps(preferences), user_name, json.dumps(preferences)))
    conn.commit()
    cursor.close()
    conn.close()
