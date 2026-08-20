# NOTICE: This file is protected under RCF-PL
"""GitHub tools package for Claude Code agents.

Standalone tools — no AladdinAI backend dependencies.
Requires: httpx, PATH_TOKEN or GITHUB_TOKEN env var.

Install deps:
    pip install httpx

Available tools:
    # Pull Requests
    get_pr_diff(owner, repo, pr_number)
    list_pr_files(owner, repo, pr_number)
    list_prs(owner, repo, state="open", per_page=30)
    post_pr_review(owner, repo, pr_number, body, event="COMMENT")
    list_commits(owner, repo, sha="main", per_page=20)

    # Issues
    list_issues(owner, repo, state="open", per_page=30)
    get_issue(owner, repo, issue_number)
    create_issue(owner, repo, title, body="", labels=None, assignees=None)
    add_labels(owner, repo, issue_number, labels)
    post_issue_comment(owner, repo, issue_number, body)
    close_issue(owner, repo, issue_number, reason="completed")

    # Files
    get_file_content(owner, repo, path, ref="main")

CLI usage:
    python .github/tools/github_tools.py list_issues '{"owner":"aliyevaladddin","repo":"AladdinAI"}'
"""
from .github_tools import (
    add_labels,
    close_issue,
    create_issue,
    # Files
    get_file_content,
    get_issue,
    # Pull Requests
    get_pr_diff,
    list_commits,
    # Issues
    list_issues,
    list_pr_files,
    list_prs,
    post_issue_comment,
    post_pr_review,
)

__all__ = [
    "add_labels",
    "close_issue",
    "create_issue",
    "get_file_content",
    "get_issue",
    "get_pr_diff",
    "list_commits",
    "list_issues",
    "list_pr_files",
    "list_prs",
    "post_issue_comment",
    "post_pr_review",
]
