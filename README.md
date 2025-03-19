# Git Changelog Generator

A command-line tool for automatically generating professional changelogs from git commit history using Claude AI.

## Purpose

This tool analyzes git commits in your repository and uses Claude AI to generate a well-structured, user-friendly changelog in the style of leading tech companies like Mintlify and Vercel. It helps maintainers:

- Create consistent, professional changelogs with minimal effort
- Translate technical commit messages into user-focused change descriptions
- Group and categorize changes intelligently
- Save time on release documentation

## Features

- Processes commits from any git repository
- Intelligently groups and categorizes changes
- Filters and prioritizes significant commits when handling large numbers of changes
- Generates clean, professional Markdown for easy integration with documentation
- Follows industry-standard changelog style conventions

## Requirements

- Python 3.6+
- Git
- Required Python packages:
  - requests>=2.25.0
  - setuptools (for installation)

### Tips for Best Results

- Focus on quality commit messages for better changelog generation
- Use standard prefixes in commit messages (`feat:`, `fix:`, `docs:`, etc.)
- Include enough commit history to provide context (10-20 commits recommended)

## How It Works

1. Fetches the specified number of commits from the git repository
2. Processes and filters commits based on importance and relevance
3. Sends the commit information to Claude AI with a specialized prompt
4. Receives and formats the generated changelog
5. Outputs the result as markdown or plain text

## Code Structure

- `cli.py`: Main script containing all functionality
  - `parse_args()`: Processes command-line arguments
  - `get_git_commits()`: Fetches commit data from git repository
  - `preprocess_commits()`: Filters and scores commits by importance
  - `generate_changelog_with_claude()`: Interfaces with Claude AI API
  - `main()`: Orchestrates the overall process
  - `setup_package()`: Handles package installation

## Package Installation

### Option 1: Direct Installation

```bash
# Navigate to the repository directory
cd cli-changelog

# Install using the built-in command
python src/cli.py install
```

### Option 2: Using pip

```bash
# Navigate to the repository directory
cd cli-changelog

# Create a setup.py file
echo 'from setuptools import setup, find_packages

setup(
    name="git-changelog",
    version="0.1.0",
    packages=find_packages(),
    py_modules=["src.cli"],
    entry_points={
        "console_scripts": [
            "git-changelog=src.cli:main",
        ],
    },
    install_requires=["requests>=2.25.0"],
)' > setup.py

# Install the package
pip install -e .
```

### Option 3: Manual Installation

```bash
# Make the script executable
chmod +x src/cli.py

# Create a symlink in a directory in your PATH
ln -s "$(pwd)/src/cli.py" ~/.local/bin/git-changelog

# Add ~/.local/bin to PATH if not already there
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc  # or ~/.zshrc
source ~/.bashrc  # or source ~/.zshrc
```

## Usage

### Basic Usage

```bash
# Generate a changelog from the last 10 commits
git-changelog 10

# Generate a changelog from the last 20 commits
git-changelog 20
```

## Security Considerations

The API key is currently hardcoded in the script. For improved security:

1. Consider using environment variables instead
2. Do not share your API key
3. Be mindful of commit data sent to the API

## License

MIT License