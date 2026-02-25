import os
import sys
import httpx
from dotenv import load_dotenv
from github_client import GitHubConfig, GitHubClient

load_dotenv()

async def check_auth():
    print("Checking GitHub PAT configuration...")
    
    token = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN") or os.getenv("GITHUB_TOKEN")
    if not token:
        print("ERROR: GITHUB_PERSONAL_ACCESS_TOKEN (or GITHUB_TOKEN) environment variable is not set.")
        return

    print(f"Token found (starts with: {token[:4]}...)")
    
    cfg = GitHubConfig(token=token)
    client = GitHubClient(cfg)
    
    try:
        # Check user auth
        user = await client._request("GET", "/user")
        print(f"Successfully authenticated as: {user['login']}")
        
        # Check specific repo access
        repo_name = "Pathlock/pathlock-plc"
        print(f"Checking access to repo: {repo_name}...")
        try:
            repo = await client.get_repo("Pathlock", "pathlock-plc")
            print(f"Successfully accessed repo: {repo['full_name']}")
            print(f"Private: {repo['private']}")
            print(f"Permissions: {repo['permissions']}")
        except Exception as e:
            print(f"Failed to access repo {repo_name}: {e}")
            
    except Exception as e:
        print(f"Authentication failed: {e}")
    finally:
        await client.aclose()

if __name__ == "__main__":
    import asyncio
    asyncio.run(check_auth())
