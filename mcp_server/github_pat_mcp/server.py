from __future__ import annotations

import base64
from typing import Any, Optional

from dotenv import load_dotenv

load_dotenv()

from fastmcp import FastMCP
from github_client import GitHubClient, GitHubConfig, GitHubAPIError

mcp = FastMCP("github-pat-mcp")

_client: GitHubClient | None = None


async def get_client() -> GitHubClient:
    global _client
    if _client is None:
        cfg = GitHubConfig.from_env()
        _client = GitHubClient(cfg)
    return _client


def _compact_pr(pr: dict) -> dict:
    return {
        "number": pr.get("number"),
        "title": pr.get("title"),
        "state": pr.get("state"),
        "created_at": pr.get("created_at"),
        "updated_at": pr.get("updated_at"),
        "user": (pr.get("user") or {}).get("login"),
        "head": ((pr.get("head") or {}).get("ref")),
        "base": ((pr.get("base") or {}).get("ref")),
        "url": pr.get("html_url"),
    }


def _compact_issue(it: dict) -> dict:
    return {
        "number": it.get("number"),
        "title": it.get("title"),
        "state": it.get("state"),
        "created_at": it.get("created_at"),
        "updated_at": it.get("updated_at"),
        "user": (it.get("user") or {}).get("login"),
        "labels": [l.get("name") for l in (it.get("labels") or []) if isinstance(l, dict)],
        "url": it.get("html_url"),
    }


@mcp.tool
async def get_repository(owner: str, repo: str) -> Any:
    """Get detailed repository information."""
    gh = await get_client()
    return await gh.get_repo(owner, repo)


@mcp.tool
async def list_branches(owner: str, repo: str, per_page: int = 100, page: int = 1) -> Any:
    """List branches in a repository."""
    gh = await get_client()
    return await gh.list_repo_branches(owner, repo, per_page=per_page, page=page)


@mcp.tool
async def create_branch(owner: str, repo: str, new_branch: str, from_branch: str) -> Any:
    """Create a new branch from an existing branch."""
    gh = await get_client()
    return await gh.create_branch(owner, repo, new_branch=new_branch, from_branch=from_branch)


@mcp.tool
async def get_file_contents(owner: str, repo: str, path: str, ref: str | None = None) -> Any:
    """
    Get file contents metadata via GitHub contents API.
    NOTE: GitHub returns base64 in many cases; use decode_file_content for plain text.
    """
    gh = await get_client()
    return await gh.get_file_contents(owner, repo, path=path, ref=ref)


@mcp.tool
async def decode_file_content(content_base64: str) -> str:
    """Decode base64 content (use with get_file_contents)."""
    return base64.b64decode(content_base64).decode("utf-8", errors="replace")


@mcp.tool
async def create_or_update_file(
    owner: str,
    repo: str,
    path: str,
    message: str,
    content_text: str,
    branch: str | None = None,
    sha: str | None = None,
) -> Any:
    """Create or update a single file (content is sent as text, encoded to base64)."""
    gh = await get_client()
    content_b64 = base64.b64encode(content_text.encode("utf-8")).decode("ascii")
    return await gh.create_or_update_file(
        owner,
        repo,
        path=path,
        message=message,
        content_base64=content_b64,
        branch=branch,
        sha=sha,
    )


@mcp.tool
async def list_pull_requests(
    owner: str,
    repo: str,
    state: str = "open",
    sort: str = "created",
    direction: str = "desc",
    per_page: int = 30,
    page: int = 1,
    compact: bool = True,
) -> Any:
    """List pull requests."""
    gh = await get_client()
    prs = await gh.list_pull_requests(
        owner, repo, state=state, sort=sort, direction=direction, per_page=per_page, page=page
    )
    if not compact:
        return prs
    return [_compact_pr(pr) for pr in prs]


@mcp.tool
async def get_pull_request(owner: str, repo: str, pull_number: int) -> Any:
    """Get a pull request by number."""
    gh = await get_client()
    return await gh.get_pull_request(owner, repo, pull_number=pull_number)


@mcp.tool
async def create_pull_request(
    owner: str,
    repo: str,
    title: str,
    head: str,
    base: str,
    body: str | None = None,
    draft: bool = False,
) -> Any:
    """Create a pull request."""
    gh = await get_client()
    return await gh.create_pull_request(owner, repo, title=title, head=head, base=base, body=body, draft=draft)


@mcp.tool
async def merge_pull_request(
    owner: str,
    repo: str,
    pull_number: int,
    merge_method: str | None = None,
    commit_title: str | None = None,
    commit_message: str | None = None,
) -> Any:
    """Merge a pull request."""
    gh = await get_client()
    return await gh.merge_pull_request(
        owner,
        repo,
        pull_number=pull_number,
        merge_method=merge_method,
        commit_title=commit_title,
        commit_message=commit_message,
    )


@mcp.tool
async def list_issues(
    owner: str,
    repo: str,
    state: str = "open",
    labels: str | None = None,
    since: str | None = None,
    per_page: int = 30,
    page: int = 1,
    compact: bool = True,
) -> Any:
    """List issues (PRs may appear too; GitHub models PRs as issues in some endpoints)."""
    gh = await get_client()
    items = await gh.list_issues(owner, repo, state=state, labels=labels, since=since, per_page=per_page, page=page)
    if not compact:
        return items
    # Filter out PRs if you want only issues:
    out = []
    for it in items:
        if isinstance(it, dict) and it.get("pull_request"):
            continue
        out.append(_compact_issue(it))
    return out


@mcp.tool
async def create_issue(
    owner: str,
    repo: str,
    title: str,
    body: str | None = None,
    labels: list[str] | None = None,
    assignees: list[str] | None = None,
) -> Any:
    """Create an issue."""
    gh = await get_client()
    return await gh.create_issue(owner, repo, title=title, body=body, labels=labels, assignees=assignees)


@mcp.tool
async def add_issue_comment(owner: str, repo: str, issue_number: int, body: str) -> Any:
    """Add a comment to an issue."""
    gh = await get_client()
    return await gh.add_issue_comment(owner, repo, issue_number=issue_number, body=body)


# Optional: friendlier error surface for LLMs / clients
@mcp.tool
async def health() -> dict:
    """Simple health check and token validation (calls GitHub API rate_limit)."""
    gh = await get_client()
    try:
        data = await gh._request("GET", "/rate_limit")
        core = (data.get("resources") or {}).get("core") or {}
        return {"ok": True, "limit": core.get("limit"), "remaining": core.get("remaining"), "reset": core.get("reset")}
    except GitHubAPIError as e:
        return {"ok": False, "status": e.status_code, "message": e.message, "details": e.details}


if __name__ == "__main__":
    # stdio transport (Claude Desktop / local orchestrators)
    mcp.run()