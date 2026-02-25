import asyncio
import json
import os
from unittest.mock import MagicMock, AsyncMock
from app.mcp_client import MCPClientManager

# Mock config to avoid loading real file if needed, or just rely on the file and handling failures.
# For this test, we want to test the Logic of interception, so we can mock the session.

async def test_large_output_interception():
    manager = MCPClientManager()
    
    # Mock a session
    mock_session = AsyncMock()
    mock_result = MagicMock()
    
    # Create a large text
    large_text = "A" * 2500
    mock_result.content = [MagicMock(text=large_text)]
    mock_result.content[0].__class__.__name__ = "TextContent" # Hack for isinstance check if needed, but better to mock properly
    
    # Actually, let's just properly mock the result object structure
    from mcp.types import CallToolResult, TextContent
    
    # TextContent is a Pydantic model, so we instantiate it directly
    text_content = TextContent(type="text", text=large_text)
    mock_result = CallToolResult(content=[text_content])

    
    mock_session.call_tool.return_value = mock_result
    manager.sessions["test_server"] = mock_session
    
    print("Testing Large Output Interception...")
    result = await manager.call_tool("test_server", "test_tool", {})
    
    if isinstance(result, dict) and result.get("type") == "large_output_interception":
        print("PASS: Large output intercepted.")
        print("Summary:", result["summary"])
    else:
        print("FAIL: Large output NOT intercepted.")
        print("Result type:", type(result))

async def main():
    await test_large_output_interception()

if __name__ == "__main__":
    asyncio.run(main())
