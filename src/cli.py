"""
Generates a changelog for the last n commits of a git repository using the Claude API.

Usage as a script:
    python cli.py <number_of_commits>

Installation as a package:
    python cli.py install

After installation, use as:
    git-changelog <number_of_commits>

Examples:
    python cli.py 10
"""

import argparse
import json
import subprocess
import sys
import os
from dotenv import load_dotenv

import requests
from setuptools import setup

# Load environment variables from .env file
load_dotenv()

# Claude API credentials and endpoint
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
ANTHROPIC_PROXY = os.getenv("ANTHROPIC_PROXY")


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Generate a changelog for the last n commits of a git repository."
    )
    parser.add_argument(
        "n", type=int, help="Number of commits to include in the changelog."
    )
    parser.add_argument(
        "--format",
        choices=["markdown", "text"],
        default="markdown",
        help="Output format for the changelog. Default is markdown.",
    )
    return parser.parse_args()


def get_git_commits(n):
    """Fetch the last n commits from the git repository."""
    try:
        # Check if we're in a git repository
        subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except subprocess.CalledProcessError:
        print(
            "Error: Not a git repository. Please run this command in a git repository."
        )
        sys.exit(1)

    try:
        # Format: commit hash, author, date, and commit message
        format_string = "%H%n%an%n%ad%n%s%n%b%n----------"
        result = subprocess.run(
            ["git", "log", f"-{n}", f"--pretty=format:{format_string}"],
            check=True,
            stdout=subprocess.PIPE,
            text=True,
        )
        commits_raw = result.stdout.split("----------")[
            :-1
        ]  # Remove the last empty element

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
                    "body": "\n".join(lines[4:]) if len(lines) > 4 else "",
                }
                commits.append(commit)

        return commits
    except subprocess.CalledProcessError as e:
        print(f"Error fetching git commits: {e}")
        sys.exit(1)


def preprocess_commits(commits, max_commits=50):
    """Preprocess and potentially filter/group commits for better changelog generation."""
    if len(commits) > max_commits:
        # If too many commits, focus on the more significant ones
        # Strategy: keep commits with longer messages, filter out obvious typo fixes

        # Score commits by message length and keywords
        scored_commits = []
        for commit in commits:
            score = len(commit["subject"] + commit["body"])

            # Boost score for important keywords
            keywords = [
                "add",
                "added",
                "feature",
                "featured",
                "improve",
                "improved",
                "fix",
                "fixed",
                "implement",
                "implemented",
                "update",
                "updated",
                "updates",
                "support",
                "supported",
                "refactor",
                "refactored",
            ]
            lowered = (commit["subject"] + commit["body"]).lower()

            for keyword in keywords:
                if keyword in lowered:
                    score += 10

            # Reduce score for trivial changes
            trivial = [
                "typo",
                "whitespace",
                "comment",
                "formatting",
                "format",
                "spacing",
                "linting",
            ]
            for word in trivial:
                if word in lowered:
                    score -= 15

            scored_commits.append((score, commit))

        # Sort by score and take top max_commits
        scored_commits.sort(reverse=True)
        return [commit for _, commit in scored_commits[:max_commits]]

    return commits


def generate_changelog_with_claude(commits):
    """Generate a changelog using the Claude API."""
    # Create a prompt for Claude

    commit_details = "\n\n".join(
        [
            f"Commit: {commit['hash']}\n"
            f"Author: {commit['author']}\n"
            f"Date: {commit['date']}\n"
            f"Subject: {commit['subject']}\n"
            f"Body: {commit['body']}"
            for commit in commits
        ]
    )

    prompt = f"""
            ### INSTRUCTIONS ###
            Create a professional changelog based on the git commits below. Your task is to analyze these commits and produce a well-organized, user-friendly changelog that follows the style of leading tech companies like Mintlify and Vercel.

            ### KEY POINTS ###
            - Consolidate similar/small commits; skip trivial changes
            - Translate technical details into user benefits
            - Use clear categories and consistent formatting
            - Include month/year heading and descriptive section headings
            - Some commits may be trivial (typo fixes, minor adjustments) and should be aggregated
            - Similar changes across multiple commits should be consolidated

            ### FORMAT ###
            - Clean Markdown without emojis
            - ## for category headings (New Features, Improvements, Bug Fixes, etc.)
            - Bullet points with **bold** feature names
            - Brief descriptions focused on user value
            - Include step-by-step guides for major features

            ### RESPONSE FORMAT ###
            IMPORTANT: Provide ONLY raw markdown with no commentary or code blocks.
            Start directly with "# Month Year" heading.
            
            ### COMMIT DETAILS ###
            {commit_details}
            
            ### EXAMPLE OUTPUT ###
            # March 2025

            ## New Configuration Schema

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

            * Added authentication requirement for preview deployments
            * Improved responsiveness across all documentation pages
            
            ### NOTE ###
            The generated changelog should follow this style but with appropriate content based on the commit details provided. Remember, provide ONLY the raw markdown content in your response.
            """

    # Prepare the API request
    headers = {
        "x-api-key": CLAUDE_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    payload = {
        "model": "claude-3-5-sonnet-latest",
        "system": "You are an expert analyst specializing in analyzing software changes and creating clear, user-focused changelogs. You excel at identifying patterns across commits, grouping related changes, and communicating technical updates in business-friendly language. Your changelogs are well-structured, emphasize user impact, and maintain professional tone.",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 4096,
        "temperature": 0.5,
    }

    try:
        response = requests.post(
            ANTHROPIC_PROXY, json=payload, headers=headers, timeout=10
        )

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
            changelog_content = changelog_content.replace("\\n", "\n")
            return changelog_content
        else:
            print("Unexpected API response format. Could not extract changelog.")
            print(f"Response: {json.dumps(result, indent=2)}")
            sys.exit(1)

    except requests.exceptions.RequestException as e:
        print(f"Error calling Claude API: {e}")
        if hasattr(e, "response") and e.response:
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
    commits = preprocess_commits(commits)
    changelog = generate_changelog_with_claude(commits)

    print("\n===== CHANGELOG =====\n")
    print(changelog)


def setup_package():
    """Set up the package for installation."""
    try:
        setup(
            name="git-changelog",
            version="0.1.0",
            description="Generate changelogs from git commits using Claude AI",
            author="Deeraj Gurram",
            author_email="djgurram@gmail.com",
            py_modules=["cli"],
            entry_points={
                "console_scripts": [
                    "git-changelog=cli:main",
                ],
            },
            install_requires=[
                "requests>=2.25.0",
                "python-dotenv>=0.15.0",
            ],
            classifiers=[
                "Programming Language :: Python :: 3",
                "License :: OSI Approved :: MIT License",
                "Operating System :: OS Independent",
            ],
            # Include the .env file in the package
            data_files=[('.', ['.env'])],
            # Alternative approach using package_data
            package_data={
                '': ['.env'],
            },
        )
        print(
            "Package installed successfully. You can now run 'git-changelog' from anywhere."
        )
    except ImportError:
        print(
            "setuptools not found. Run 'pip install setuptools' to enable package installation."
        )


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "install":
        setup_package()
    else:
        main()
