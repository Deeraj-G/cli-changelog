"""
Generates a changelog for the last n commits of a git repository using the Claude API.

Usage:
    python3 cli.py <number_of_commits>

Example:
    python3 cli.py 10
"""
import sys
import json
import subprocess
import argparse
import requests

# Claude API credentials and endpoint
CLAUDE_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJlbWFpbCI6ImRqZ3VycmFtQGdtYWlsLmNvbSIsImFzc2Vzc21lbnQiOiJhaSIsImNyZWF0ZWRfYXQiOiIyMDI1LTAzLTE5VDAxOjU3OjM3LjAzNjI5ODA3NVoiLCJpYXQiOjE3NDIzNDk0NTd9.fgjvGkXDqiExxbBcZmeZm-XjT0kjZScfZN7HQ_1A-ZI"
BASE_URL = "https://mintlify-take-home.com"
API_ENDPOINT = f"{BASE_URL}/api/message"

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Generate a changelog for the last n commits of a git repository."
    )
    parser.add_argument(
        "n", 
        type=int, 
        help="Number of commits to include in the changelog."
    )
    parser.add_argument(
        "--format", 
        choices=["markdown", "text"], 
        default="markdown",
        help="Output format for the changelog. Default is markdown."
    )
    return parser.parse_args()

def get_git_commits(n):
    """Fetch the last n commits from the git repository."""
    try:
        # Check if we're in a git repository
        subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], 
                      check=True, 
                      stdout=subprocess.PIPE, 
                      stderr=subprocess.PIPE)
    except subprocess.CalledProcessError:
        print("Error: Not a git repository. Please run this command in a git repository.")
        sys.exit(1)
    
    try:
        # Format: commit hash, author, date, and commit message
        format_string = "%H%n%an%n%ad%n%s%n%b%n----------"
        result = subprocess.run(
            ["git", "log", f"-{n}", f"--pretty=format:{format_string}"],
            check=True,
            stdout=subprocess.PIPE,
            text=True
        )
        commits_raw = result.stdout.split("----------")[:-1]  # Remove the last empty element
        
        # Parse the raw commit data
        commits = []
        for commit_raw in commits_raw:
            lines = commit_raw.strip().split("\n")
            if len(lines) >= 4:
                commit = {
                    "hash": lines[0],
                    "author": lines[1],
                    "date": lines[2],
                    "subject": lines[3],
                    "body": "\n".join(lines[4:]) if len(lines) > 4 else ""
                }
                commits.append(commit)
        
        return commits
    except subprocess.CalledProcessError as e:
        print(f"Error fetching git commits: {e}")
        sys.exit(1)

def generate_changelog_with_claude(commits):
    """Generate a changelog using the Claude API."""
    # Create a prompt for Claude
    commit_details = "\n\n".join([
        f"Commit: {commit['hash']}\n"
        f"Author: {commit['author']}\n"
        f"Date: {commit['date']}\n"
        f"Subject: {commit['subject']}\n"
        f"Body: {commit['body']}"
        for commit in commits
    ])
    
    prompt = f"""Based on the following git commits, generate a user-friendly changelog that summarizes the changes in a way that would be meaningful to end-users. 
The changelog should be similar in style to changelogs found on company websites.
Group related changes together under appropriate headings.
Focus on user-facing changes rather than implementation details unless they're significant.

Here are the commits:

{commit_details}"""

    # Prepare the API request
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {CLAUDE_API_KEY}"
    }
    
    payload = {
        "model": "claude-3-5-sonnet-latest",
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "max_tokens": 4096,
        "temperature": 0.5
    }
    
    try:
        response = requests.post(API_ENDPOINT, json=payload, headers=headers, timeout=10)
        response.raise_for_status()  # Raise an exception for HTTP errors
        
        # Parse the JSON response
        result = response.json()
        
        # Extract the generated changelog from the response
        # The structure may vary based on the actual API response format
        if "content" in result:
            return result["content"]
        else:
            print("Unexpected API response format. Could not extract changelog.")
            print(f"Response: {json.dumps(result, indent=2)}")
            sys.exit(1)
    
    except requests.exceptions.RequestException as e:
        print(f"Error calling Claude API: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"Response status code: {e.response.status_code}")
            print(f"Response body: {e.response.text}")
        sys.exit(1)

def main():
    """Main function to run the CLI application."""
    args = parse_args()
    
    print(f"Fetching the last {args.n} commits...")
    commits = get_git_commits(args.n)
    
    if not commits:
        print("No commits found.")
        sys.exit(0)
    
    print(f"Found {len(commits)} commits. Generating changelog...")
    changelog = generate_changelog_with_claude(commits)
    
    print("\n===== CHANGELOG =====\n")
    print(changelog)

if __name__ == "__main__":
    main()


