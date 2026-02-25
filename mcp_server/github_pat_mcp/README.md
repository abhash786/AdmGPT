## github-pat-mcp (Python MCP server)

### Setup
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

### Run (stdio)
set GITHUB_PERSONAL_ACCESS_TOKEN=ghp_...
python server.py

### Optional (GitHub Enterprise)
set GITHUB_API_BASE=https://github.your-company.com/api/v3