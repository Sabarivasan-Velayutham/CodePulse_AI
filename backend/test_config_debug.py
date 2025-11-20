"""
Debug script to check configuration loading
"""

import os
from dotenv import load_dotenv

# Load .env file explicitly
load_dotenv()

print("=" * 60)
print("Configuration Debug")
print("=" * 60)

# Check if .env is being loaded
env_file = os.path.join(os.path.dirname(__file__), '.env')
print(f"\n1. .env file location: {env_file}")
print(f"   Exists: {os.path.exists(env_file)}")

# Check environment variables
print("\n2. Environment Variables:")
print(f"   GITHUB_ORG: {os.getenv('GITHUB_ORG', 'NOT SET')}")
print(f"   API_CONSUMER_REPOSITORIES: {os.getenv('API_CONSUMER_REPOSITORIES', 'NOT SET')}")
print(f"   GITHUB_REPOSITORIES: {os.getenv('GITHUB_REPOSITORIES', 'NOT SET')}")
print(f"   SEARCH_ALL_REPOS_FOR_CONSUMERS: {os.getenv('SEARCH_ALL_REPOS_FOR_CONSUMERS', 'NOT SET')}")

# Try importing config
print("\n3. Importing config module...")
try:
    from app.config import (
        GITHUB_ORG,
        API_CONSUMER_REPOSITORIES,
        GITHUB_REPOSITORIES,
        SEARCH_ALL_REPOS_FOR_CONSUMERS,
        get_consumer_repositories
    )
    
    print(f"   GITHUB_ORG: {GITHUB_ORG}")
    print(f"   API_CONSUMER_REPOSITORIES: {API_CONSUMER_REPOSITORIES}")
    print(f"   GITHUB_REPOSITORIES: {GITHUB_REPOSITORIES}")
    print(f"   SEARCH_ALL_REPOS_FOR_CONSUMERS: {SEARCH_ALL_REPOS_FOR_CONSUMERS}")
    
    print("\n4. Calling get_consumer_repositories()...")
    repos = get_consumer_repositories()
    print(f"   Result: {repos}")
    print(f"   Count: {len(repos)}")
    
    if not repos:
        print("\n⚠️  No repositories found!")
        print("\nPossible issues:")
        print("   1. .env file not in backend/ directory")
        print("   2. Environment variables not set correctly")
        print("   3. SEARCH_ALL_REPOS_FOR_CONSUMERS might be 'false'")
        print("   4. API_CONSUMER_REPOSITORIES might be empty")
        
except Exception as e:
    print(f"   ❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)

