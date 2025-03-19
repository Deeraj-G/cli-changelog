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
ANTHROPIC_PROXY = "https://mintlify-take-home.com/api/message"

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
    
    prompt = f"""
            ### INSTRUCTIONS ###
            Create a professional changelog based on the git commits below. Your task is to analyze these commits and produce a well-organized, user-friendly changelog that follows the style of leading tech companies like Mintlify and Vercel.

            ### REQUIREMENTS ###
            1. Start with a clear heading that includes the month and year (e.g., "March 2025")
            2. Group changes into relevant categories such as:
               - New Features
               - Improvements
               - Bug Fixes
               - Performance
               - Documentation
            3. Write concise, clear descriptions that explain the value to users
            4. Use consistent formatting throughout
            5. Prioritize user-facing changes over technical implementation details
            6. For important features, include a brief one-sentence description below the main bullet point

            ### FORMAT SPECIFICATIONS ###
            - Use clean, professional Markdown formatting without emojis
            - Use ## for category headings
            - Use bullet points with clear, concise descriptions
            - Bold key terms or feature names for emphasis
            - Keep descriptions brief but informative
            - For major features, include a "Learn more" link placeholder
            
            ### COMMIT DETAILS ###
            {commit_details}
            
            ### OUTPUT EXAMPLE ###
            ```markdown
            # March 2025

            ## New Configuration Schema `docs.json`

            We've introduced a new `docs.json` schema as a replacement for `mint.json`, to support better multi-level versioning, easier visual comprehension, and more consistent terminology.

            Upgrade from `mint.json` to `docs.json` with the following steps:
            1. Make sure your CLI is the latest version
            2. In your docs repository, run the upgrade command
            3. Delete your old mint.json file and push your changes

            ## API Improvements

            * **Enhanced Performance** - API calls are now 30% faster with improved caching
            * **New Endpoints** - Added support for additional data types and formats
            * Fixed intermittent timeout issues when processing large requests

            ## Quality Improvements

            * Support for requiring authentication to access preview deployments
            * Improved mobile responsiveness across all documentation pages
            ```
            
            Your changelog should follow this style but with appropriate content based on the commit details provided.
            """

    # Prepare the API request
    headers = {
        "x-api-key": CLAUDE_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    
    payload = {
        "model": "claude-3-5-sonnet-latest",
        "system": "You are an expert analyst specializing in analyzing software changes and creating clear, user-focused changelogs. You excel at identifying patterns across commits, grouping related changes, and communicating technical updates in business-friendly language. Your changelogs are well-structured, emphasize user impact, and maintain professional tone.",
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "max_tokens": 4096,
        "temperature": 0.5,
    }
    
    try:
        response = requests.post(ANTHROPIC_PROXY, json=payload, headers=headers, timeout=10)
        
        # Don't raise_for_status yet so we can see the error response
        if response.status_code >= 400:
            print(f"Error response body: {response.text}")
            response.raise_for_status()  # Now raise the exception
        
        # Parse the JSON response
        result = response.json()
        
        # Extract the generated changelog from the response
        if "content" in result:
            # Remove any escape sequences (like \n) and return the raw markdown
            changelog_content = result["content"][0]["text"]
            # Convert escaped newlines to actual newlines if needed
            changelog_content = changelog_content.replace('\\n', '\n')
            return changelog_content
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


