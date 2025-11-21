"""
Configuration for CodePulse AI
"""

import os
from typing import List, Optional
from pathlib import Path

# Load .env file if it exists
try:
    from dotenv import load_dotenv
    # Try to find .env file in backend directory or project root
    env_paths = [
        Path(__file__).parent.parent / '.env',  # backend/.env
        Path(__file__).parent.parent.parent / '.env',  # project root/.env
    ]
    for env_path in env_paths:
        if env_path.exists():
            load_dotenv(env_path)
            break
except ImportError:
    # python-dotenv not installed, skip
    pass

# GitHub Configuration
GITHUB_ORG = os.getenv("GITHUB_ORG", "")
GITHUB_REPOSITORIES = [
    repo.strip() 
    for repo in os.getenv("GITHUB_REPOSITORIES", "").split(",") 
    if repo.strip()
]

# API Consumer Discovery Configuration
# List of repositories to search for API consumers
# Format: "owner/repo" or full URL
API_CONSUMER_REPOSITORIES = [
    repo.strip()
    for repo in os.getenv("API_CONSUMER_REPOSITORIES", "").split(",")
    if repo.strip()
] or GITHUB_REPOSITORIES  # Fallback to GITHUB_REPOSITORIES if not set

# Whether to search all configured repos for API consumers
SEARCH_ALL_REPOS_FOR_CONSUMERS = os.getenv("SEARCH_ALL_REPOS_FOR_CONSUMERS", "true").lower() == "true"

# GitHub API Configuration
# Set to "api" to use GitHub API search (no cloning), "clone" to clone repos locally
CONSUMER_SEARCH_METHOD = os.getenv("CONSUMER_SEARCH_METHOD", "clone").lower()  # "clone" or "api"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")  # Optional: for higher API rate limits

def get_consumer_repositories() -> List[str]:
    """
    Get list of repositories to search for API consumers
    
    Returns:
        List of repository identifiers (owner/repo format)
    """
    if not SEARCH_ALL_REPOS_FOR_CONSUMERS:
        return []
    
    repos = API_CONSUMER_REPOSITORIES.copy()
    
    # Normalize repository identifiers
    normalized_repos = []
    for repo in repos:
        repo = repo.strip()
        
        # If it's a full GitHub URL, extract owner/repo
        if 'github.com' in repo:
            # Extract from URL: https://github.com/owner/repo/tree/main -> owner/repo
            parts = repo.split('github.com/')
            if len(parts) > 1:
                repo_path = parts[1].split('/')
                if len(repo_path) >= 2:
                    normalized_repos.append(f"{repo_path[0]}/{repo_path[1]}")
                    continue
        
        # If it's already owner/repo format, use as is
        if '/' in repo and not repo.startswith('http'):
            normalized_repos.append(repo)
            continue
        
        # If GITHUB_ORG is set and repo doesn't have org, prepend org
        if GITHUB_ORG and '/' not in repo:
            normalized_repos.append(f"{GITHUB_ORG}/{repo}")
            continue
        
        # Fallback: use as is (might be just repo name)
        normalized_repos.append(repo)
    
    return normalized_repos

