
import base64
import re
from urllib.parse import quote

import requests
from github import Github

from agents.state import QAInput


def _get_pr_data(api_url: str, headers: dict[str, str]) -> dict:
    response = requests.get(api_url, headers=headers, timeout=30)
    response.raise_for_status()
    return response.json()


def get_PR_data_from_url(pr_url: str, github_token: str) -> QAInput:
    """Fetch the pull request data used to start the QA workflow."""
    # Extract owner, repo, and pull number using regex
    match = re.match(r"https://github\.com/([^/]+)/([^/]+)/pull/(\d+)", pr_url)
    if not match:
        raise ValueError("Invalid GitHub PR URL format.")
    
    owner, repo, pull_number = match.groups()

    # GitHub API endpoint for pull request details
    api_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pull_number}"

    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }

    pr_data = _get_pr_data(api_url, headers)
    head_sha = pr_data["head"]["sha"]
    changed_files = get_changed_files_content(owner, repo, pull_number, headers, pr_data)
    diff_response = requests.get(pr_data["diff_url"], headers=headers, timeout=30)
    diff_response.raise_for_status()

    # The PR diff and file listing follow the PR as its revisions change.
    latest = _get_pr_data(api_url, headers)
    if latest["head"]["sha"] != head_sha or latest["base"]["sha"] != pr_data["base"]["sha"]:
        raise RuntimeError("The pull request changed during fetch. Retry the review.")

    return {
        "pr_url": pr_url,
        "pr_sha": head_sha,
        "pr_title": pr_data.get("title", ""),
        "pr_desc": pr_data.get("body") or "",
        "raw_diff": diff_response.text,
        "changed_files": changed_files,
    }


def get_changed_files_content(owner, repo, pull_number, headers, pr_data):
    """Fetch changed files from the PR head repository at its exact commit."""
    head = pr_data["head"]
    head_repo = head["repo"]
    if head_repo is None:
        raise ValueError("The pull request's head repository is no longer available.")

    files_api_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pull_number}/files"
    files_response = requests.get(files_api_url, headers=headers, timeout=30)
    files_response.raise_for_status()

    contents_base = f"https://api.github.com/repos/{head_repo['full_name']}/contents"
    file_contents = {}
    for file in files_response.json():
        if file["status"] == "removed":
            continue
        filename = file["filename"]
        content_response = requests.get(
            f"{contents_base}/{quote(filename)}",
            headers=headers,
            params={"ref": head["sha"]},
            timeout=30,
        )
        content_response.raise_for_status()
        content_data = content_response.json()
        file_contents[filename] = base64.b64decode(content_data["content"]).decode("utf-8")

    return file_contents



# You already have a regex in get_PR_data_from_url that extracts owner, repo, and pull_number from a PR URL. You'll need those same three values again here.
# Write a new function — call it post_report_to_pr(pr_url, report, github_token) — that:

# Re-parses owner, repo, pull_number from pr_url (same regex pattern you already have)
# Creates a Github(github_token) instance
# Gets the repo and the specific PR
# Calls .create_issue_comment(report) on it

def post_report_to_pr(pr_url: str, report: str, github_token: str):
    """
    Posts the final QA report as a comment on the specified GitHub Pull Request.
    """
    # Extract owner, repo, and pull number using regex
    match = re.match(r"https://github\.com/([^/]+)/([^/]+)/pull/(\d+)", pr_url)
    if not match:
        raise ValueError("Invalid GitHub PR URL format.")
    
    owner, repo, pull_number = match.groups()

    # Create a Github instance
    g = Github(github_token)

    # Get the repository and the specific pull request
    repository = g.get_repo(f"{owner}/{repo}")
    pull_request = repository.get_pull(int(pull_number))

    # Post the report as a comment on the PR
    comment = pull_request.create_issue_comment(report)
    print(f"✅ Comment posted: {comment.html_url}")
