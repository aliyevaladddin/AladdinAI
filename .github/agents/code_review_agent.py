"""Code Review Agent for GitHub Pull Requests.

Automatically reviews PRs using NVIDIA NIM API and posts feedback via GitHub API.

Environment variables required:
    PATH_TOKEN or GITHUB_TOKEN - GitHub API token
    NIM_API_KEY - NVIDIA NIM API key
    NIM_BASE_URL - NVIDIA NIM base URL (default: https://integrate.api.nvidia.com/v1)
    NIM_MODEL - Model to use (default: meta/llama-3.1-70b-instruct)
    PR_NUMBER - Pull request number
    REPO_OWNER - Repository owner
    REPO_NAME - Repository name

Usage:
    python .github/agents/code_review_agent.py
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

# Add tools to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.github_tools import get_pr_diff, list_pr_files, post_pr_review

try:
    from openai import OpenAI
except ImportError:
    print("Error: openai package not installed. Run: pip install openai", file=sys.stderr)
    sys.exit(1)


REVIEW_PROMPT = """You are a code review agent. Analyze this pull request and provide constructive feedback.

Focus on:
- Code quality and readability
- Potential bugs or logic errors
- Security vulnerabilities (SQL injection, XSS, command injection, etc.)
- Performance issues
- Best practices for the language/framework
- Missing error handling
- Unclear variable/function names

Be concise and actionable. If the code looks good, say so briefly.

Pull Request Diff:
{diff}

Changed Files Summary:
{files_summary}

Provide your review as a single comment body (markdown supported).
"""


async def review_pr(owner: str, repo: str, pr_number: int) -> None:
    """Fetch PR, analyze with Claude, post review."""
    print(f"Reviewing PR #{pr_number} in {owner}/{repo}")

    # Fetch PR diff and files
    print("Fetching PR diff...")
    diff = await get_pr_diff(owner, repo, pr_number)

    print("Fetching changed files...")
    files = await list_pr_files(owner, repo, pr_number)

    files_summary = "\n".join([
        f"- {f['filename']} (+{f['additions']} -{f['deletions']}) [{f['status']}]"
        for f in files
    ])

    # Analyze with NIM
    print("Analyzing with NIM...")
    api_key = os.getenv("NIM_API_KEY")
    if not api_key:
        print("Error: NIM_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    base_url = os.getenv("NIM_BASE_URL", "https://integrate.api.nvidia.com/v1")
    model = os.getenv("NIM_MODEL", "meta/llama-3.1-70b-instruct")

    client = OpenAI(
        base_url=base_url,
        api_key=api_key
    )

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{
                "role": "user",
                "content": REVIEW_PROMPT.format(
                    diff=diff[:50000],  # Limit diff size to avoid token limits
                    files_summary=files_summary
                )
            }],
            temperature=0.2,
            top_p=0.7,
            max_tokens=2000,
        )

        review_body = response.choices[0].message.content

    except Exception as e:
        print(f"Error calling NIM API: {e}", file=sys.stderr)
        sys.exit(1)

    # Post review to GitHub
    print("Posting review to GitHub...")
    try:
        result = await post_pr_review(
            owner=owner,
            repo=repo,
            pr_number=pr_number,
            body=f"## 🤖 Automated Code Review\n\n{review_body}",
            event="COMMENT"
        )
        print(f"✓ Review posted: {result['html_url']}")
    except Exception as e:
        print(f"Error posting review: {e}", file=sys.stderr)
        sys.exit(1)


async def main() -> None:
    """Entry point."""
    pr_number = os.getenv("PR_NUMBER")
    repo_owner = os.getenv("REPO_OWNER")
    repo_name = os.getenv("REPO_NAME")

    if not all([pr_number, repo_owner, repo_name]):
        print(
            "Error: Missing required environment variables.\n"
            "Required: PR_NUMBER, REPO_OWNER, REPO_NAME",
            file=sys.stderr
        )
        sys.exit(1)

    try:
        pr_num = int(pr_number)
    except ValueError:
        print(f"Error: PR_NUMBER must be an integer, got: {pr_number}", file=sys.stderr)
        sys.exit(1)

    await review_pr(repo_owner, repo_name, pr_num)


if __name__ == "__main__":
    asyncio.run(main())
