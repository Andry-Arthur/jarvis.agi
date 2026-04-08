"""GitHub integration via PyGithub.

Required env vars:
  GITHUB_TOKEN  — Personal access token
"""

from __future__ import annotations

import logging
import os

from jarvis.core.tools import Tool
from jarvis.integrations.base import Integration

logger = logging.getLogger(__name__)


def _gh():
    from github import Github  # type: ignore[import]

    return Github(os.environ["GITHUB_TOKEN"])


class GitHubListReposTool(Tool):
    name = "github_list_repos"
    description = "List your GitHub repositories."
    parameters = {
        "type": "object",
        "properties": {
            "limit": {"type": "integer", "description": "Max repos to return (default 10)"},
        },
    }

    async def execute(self, limit: int = 10) -> str:
        try:
            gh = _gh()
            repos = list(gh.get_user().get_repos())[:limit]
            if not repos:
                return "No repositories found."
            lines = [
                f"• {r.full_name} ({'private' if r.private else 'public'}) — {r.description or ''}"
                for r in repos
            ]
            return "\n".join(lines)
        except Exception as exc:
            logger.error("github_list_repos failed: %s", exc)
            return f"Error listing repos: {exc}"


class GitHubOpenIssueTool(Tool):
    name = "github_open_issue"
    description = "Open a new GitHub issue in a repository."
    parameters = {
        "type": "object",
        "properties": {
            "repo": {"type": "string", "description": "Repository in format owner/repo"},
            "title": {"type": "string", "description": "Issue title"},
            "body": {"type": "string", "description": "Issue body"},
            "labels": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional labels",
            },
        },
        "required": ["repo", "title"],
    }

    async def execute(
        self, repo: str, title: str, body: str = "", labels: list | None = None
    ) -> str:
        try:
            gh = _gh()
            repository = gh.get_repo(repo)
            kwargs: dict = {"title": title, "body": body}
            if labels:
                kwargs["labels"] = labels
            issue = repository.create_issue(**kwargs)
            return f"Issue created: {issue.html_url}"
        except Exception as exc:
            logger.error("github_open_issue failed: %s", exc)
            return f"Error opening issue: {exc}"


class GitHubListIssuesTools(Tool):
    name = "github_list_issues"
    description = "List open issues in a GitHub repository."
    parameters = {
        "type": "object",
        "properties": {
            "repo": {"type": "string", "description": "owner/repo"},
            "state": {
                "type": "string",
                "description": "Issue state: 'open', 'closed', or 'all' (default 'open')",
            },
            "limit": {"type": "integer", "description": "Max issues (default 10)"},
        },
        "required": ["repo"],
    }

    async def execute(self, repo: str, state: str = "open", limit: int = 10) -> str:
        try:
            gh = _gh()
            repository = gh.get_repo(repo)
            issues = list(repository.get_issues(state=state))[:limit]
            if not issues:
                return f"No {state} issues found in {repo}."
            lines = [
                f"• #{i.number} {i.title} ({i.state}) — {i.html_url}"
                for i in issues
            ]
            return "\n".join(lines)
        except Exception as exc:
            logger.error("github_list_issues failed: %s", exc)
            return f"Error listing issues: {exc}"


class GitHubCreateBranchTool(Tool):
    name = "github_create_branch"
    description = "Create a new branch in a GitHub repository."
    parameters = {
        "type": "object",
        "properties": {
            "repo": {"type": "string", "description": "owner/repo"},
            "branch_name": {"type": "string", "description": "New branch name"},
            "from_branch": {
                "type": "string",
                "description": "Source branch (default: main)",
            },
        },
        "required": ["repo", "branch_name"],
    }

    async def execute(self, repo: str, branch_name: str, from_branch: str = "main") -> str:
        try:
            gh = _gh()
            repository = gh.get_repo(repo)
            source = repository.get_branch(from_branch)
            repository.create_git_ref(
                ref=f"refs/heads/{branch_name}", sha=source.commit.sha
            )
            return f"Branch '{branch_name}' created from '{from_branch}' in {repo}."
        except Exception as exc:
            logger.error("github_create_branch failed: %s", exc)
            return f"Error creating branch: {exc}"


class GitHubIntegration(Integration):
    name = "github"

    def is_configured(self) -> bool:
        return bool(os.getenv("GITHUB_TOKEN"))

    def get_tools(self) -> list[Tool]:
        return [
            GitHubListReposTool(),
            GitHubOpenIssueTool(),
            GitHubListIssuesTools(),
            GitHubCreateBranchTool(),
        ]
