from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple
import httpx


class GitHubAPIError(RuntimeError):
    def __init__(self, status_code: int, message: str, details: Any | None = None):
        super().__init__(f"GitHub API error {status_code}: {message}")
        self.status_code = status_code
        self.message = message
        self.details = details


@dataclass(frozen=True)
class GitHubConfig:
    token: str
    api_base: str = "https://api.github.com"  # GitHub.com REST base
    user_agent: str = "github-pat-mcp/1.0"

    @staticmethod
    def from_env() -> "GitHubConfig":
        token = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN") or os.getenv("GITHUB_TOKEN")
        if not token:
            raise RuntimeError("Missing env var: GITHUB_PERSONAL_ACCESS_TOKEN (or GITHUB_TOKEN)")
        api_base = os.getenv("GITHUB_API_BASE", "https://api.github.com").rstrip("/")
        user_agent = os.getenv("GITHUB_USER_AGENT", "github-pat-mcp/1.0")
        return GitHubConfig(token=token, api_base=api_base, user_agent=user_agent)


class GitHubClient:
    """
    Thin REST client around GitHub's API using PAT auth.
    Uses Accept v3, and sets Authorization: Bearer <PAT>.
    """

    def __init__(self, cfg: GitHubConfig):
        self.cfg = cfg
        self._client = httpx.AsyncClient(
            base_url=self.cfg.api_base,
            headers={
                "Authorization": f"Bearer {self.cfg.token}",
                "Accept": "application/vnd.github+json",
                "User-Agent": self.cfg.user_agent,
                "X-GitHub-Api-Version": os.getenv("GITHUB_API_VERSION", "2022-11-28"),
            },
            timeout=httpx.Timeout(30.0),
        )

    async def aclose(self):
        await self._client.aclose()

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: Dict[str, Any] | None = None,
        json: Dict[str, Any] | None = None,
        extra_headers: Dict[str, str] | None = None,
    ) -> Any:
        headers = extra_headers or {}
        resp = await self._client.request(method, path, params=params, json=json, headers=headers)

        if resp.status_code >= 400:
            try:
                payload = resp.json()
            except Exception:
                payload = {"raw": resp.text}
            msg = payload.get("message") if isinstance(payload, dict) else str(payload)
            raise GitHubAPIError(resp.status_code, msg or "Request failed", payload)

        # Some endpoints return 204 No Content
        if resp.status_code == 204 or not resp.content:
            return None

        # JSON by default
        ctype = resp.headers.get("content-type", "")
        if "application/json" in ctype:
            return resp.json()

        # Fallback: text
        return resp.text

    # ---------- Repo ----------
    async def get_repo(self, owner: str, repo: str) -> Any:
        return await self._request("GET", f"/repos/{owner}/{repo}")

    async def list_repo_branches(self, owner: str, repo: str, *, per_page: int = 100, page: int = 1) -> Any:
        return await self._request("GET", f"/repos/{owner}/{repo}/branches", params={"per_page": per_page, "page": page})

    async def create_branch(self, owner: str, repo: str, *, new_branch: str, from_branch: str) -> Any:
        # Get SHA of from_branch
        ref = await self._request("GET", f"/repos/{owner}/{repo}/git/ref/heads/{from_branch}")
        sha = ref["object"]["sha"]
        body = {"ref": f"refs/heads/{new_branch}", "sha": sha}
        return await self._request("POST", f"/repos/{owner}/{repo}/git/refs", json=body)

    # ---------- Contents ----------
    async def get_file_contents(self, owner: str, repo: str, *, path: str, ref: str | None = None) -> Any:
        params = {"ref": ref} if ref else None
        return await self._request("GET", f"/repos/{owner}/{repo}/contents/{path.lstrip('/')}", params=params)

    async def create_or_update_file(
        self,
        owner: str,
        repo: str,
        *,
        path: str,
        message: str,
        content_base64: str,
        branch: str | None = None,
        sha: str | None = None,
        committer_name: str | None = None,
        committer_email: str | None = None,
    ) -> Any:
        body: Dict[str, Any] = {"message": message, "content": content_base64}
        if branch:
            body["branch"] = branch
        if sha:
            body["sha"] = sha
        if committer_name and committer_email:
            body["committer"] = {"name": committer_name, "email": committer_email}
        return await self._request("PUT", f"/repos/{owner}/{repo}/contents/{path.lstrip('/')}", json=body)

    # ---------- Pull Requests ----------
    async def list_pull_requests(
        self,
        owner: str,
        repo: str,
        *,
        state: str = "open",
        sort: str = "created",
        direction: str = "desc",
        per_page: int = 30,
        page: int = 1,
        base: str | None = None,
        head: str | None = None,
    ) -> Any:
        params: Dict[str, Any] = {
            "state": state,
            "sort": sort,
            "direction": direction,
            "per_page": per_page,
            "page": page,
        }
        if base:
            params["base"] = base
        if head:
            params["head"] = head
        return await self._request("GET", f"/repos/{owner}/{repo}/pulls", params=params)

    async def get_pull_request(self, owner: str, repo: str, *, pull_number: int) -> Any:
        return await self._request("GET", f"/repos/{owner}/{repo}/pulls/{pull_number}")

    async def create_pull_request(
        self,
        owner: str,
        repo: str,
        *,
        title: str,
        head: str,
        base: str,
        body: str | None = None,
        draft: bool = False,
    ) -> Any:
        payload: Dict[str, Any] = {"title": title, "head": head, "base": base, "draft": draft}
        if body is not None:
            payload["body"] = body
        return await self._request("POST", f"/repos/{owner}/{repo}/pulls", json=payload)

    async def merge_pull_request(
        self,
        owner: str,
        repo: str,
        *,
        pull_number: int,
        commit_title: str | None = None,
        commit_message: str | None = None,
        merge_method: str | None = None,  # merge | squash | rebase
    ) -> Any:
        payload: Dict[str, Any] = {}
        if commit_title:
            payload["commit_title"] = commit_title
        if commit_message:
            payload["commit_message"] = commit_message
        if merge_method:
            payload["merge_method"] = merge_method
        return await self._request("PUT", f"/repos/{owner}/{repo}/pulls/{pull_number}/merge", json=payload)

    # ---------- Issues ----------
    async def list_issues(
        self,
        owner: str,
        repo: str,
        *,
        state: str = "open",
        labels: str | None = None,
        since: str | None = None,
        per_page: int = 30,
        page: int = 1,
    ) -> Any:
        params: Dict[str, Any] = {"state": state, "per_page": per_page, "page": page}
        if labels:
            params["labels"] = labels
        if since:
            params["since"] = since
        return await self._request("GET", f"/repos/{owner}/{repo}/issues", params=params)

    async def create_issue(
        self,
        owner: str,
        repo: str,
        *,
        title: str,
        body: str | None = None,
        labels: list[str] | None = None,
        assignees: list[str] | None = None,
    ) -> Any:
        payload: Dict[str, Any] = {"title": title}
        if body is not None:
            payload["body"] = body
        if labels:
            payload["labels"] = labels
        if assignees:
            payload["assignees"] = assignees
        return await self._request("POST", f"/repos/{owner}/{repo}/issues", json=payload)

    async def add_issue_comment(self, owner: str, repo: str, *, issue_number: int, body: str) -> Any:
        return await self._request(
            "POST",
            f"/repos/{owner}/{repo}/issues/{issue_number}/comments",
            json={"body": body},
        )