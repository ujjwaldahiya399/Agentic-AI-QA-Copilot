
import re
import requests
import base64
from github import Github

def get_PR_data_from_url(pr_url: str, github_token: str) -> dict:
    """
   Parses a standard GitHub PR URL, fetches its metadata and raw diff from 
    the GitHub API, and returns a structured dictionary with pr_url, pr_title, pr_desc, and raw_diff for the LangGraph state.
    """
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

    response = requests.get(api_url, headers=headers)
    
    if response.status_code != 200:
        raise Exception(f"Failed to fetch PR data: {response.status_code} - {response.text}")

    pr_data = response.json()
    changed_files = get_changed_files_content(owner, repo, pull_number, headers, pr_data)
    return {
        "pr_url": pr_url,
        "pr_title": pr_data.get("title", ""),
        "pr_desc": pr_data.get("body", ""),
        "raw_diff": requests.get(pr_data.get("diff_url"), headers=headers).text,
        "changed_files": changed_files
    }



def get_changed_files_content(owner,repo,pull_number,headers, pr_data):
    """
    Hits /pulls/{pull_number}/files to get the list of changed filenames
    Gets the branch name from pr_data["head"]["ref"] (you already have pr_data in your existing function)
    For each filename, hits the Contents API to get its content
    Returns a dict of {filename: content}
    """
    files_api_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pull_number}/files"
    files_response = requests.get(files_api_url, headers=headers)
    
    if files_response.status_code != 200:
        raise Exception(f"Failed to fetch changed files: {files_response.status_code} - {files_response.text}")

    changed_files = files_response.json()
    branch_name = pr_data["head"]["ref"]

    file_contents = {}
    for file in changed_files:
        filename = file["filename"]
        content_api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{filename}?ref={branch_name}"
        content_response = requests.get(content_api_url, headers=headers)
        
        if content_response.status_code == 200:
            content_data = content_response.json()
            decoded_content = base64.b64decode(content_data["content"]).decode("utf-8")
            file_contents[filename] = decoded_content

        else:
            file_contents[filename] = "Failed to fetch content"

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
