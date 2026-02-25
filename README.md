# AdmGPT

AdmGPT is a powerful AI-driven application featuring a FastAPI backend, a modern React frontend, and specialized Model Context Protocol (MCP) servers for extended capabilities.

## Project Structure

- `backend/`: FastAPI application handling logic, persistence, and API endpoints.
- `frontend/`: React + Vite application providing the user interface.
- `mcp_server/`: Collection of MCP servers:
    - `azure-devops-mcp`: For interacting with Azure DevOps work items and projects.
    - `github_pat_mcp`: For GitHub repository and issue management.
    - `sql_server`: For querying and managing SQL Server databases.

## Getting Started

### Prerequisites

- **Python 3.10+**
- **Node.js 18+**

### Backend Setup

1. Navigate to the backend folder:
   ```bash
   cd backend
   ```
2. Create and activate a virtual environment:
   ```powershell
   python -m venv venv
   .\venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the server:
   ```bash
   python -m app.main
   ```

### Frontend Setup

1. Navigate to the frontend folder:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Run the development server:
   ```bash
   npm run dev
   ```

## MCP Servers Setup

Refer to the specific setup steps in `backend/commands.txt` or follow these quick links:

- **Azure DevOps**: Run `npm install && npm run build` in `mcp_server/azure-devops-mcp`.
- **GitHub**: Create a venv and install `requirements.txt` in `mcp_server/github_pat_mcp`.
- **SQL Server**: Create a venv and install `fastmcp pyodbc python-dotenv` in `mcp_server/sql_server`.

## Project Maintenance

To clean up all temporary files and build artifacts before uploading to Git, use the PowerShell command from the root folder:

```powershell
Get-ChildItem -Path . -Include node_modules,dist,venv,__pycache__,.pytest_cache -Recurse | Remove-Item -Recurse -Force
```

Full details on all available commands can be found in [backend/commands.txt](file:///d:/Projects/AdmGPT/backend/commands.txt).
