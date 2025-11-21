"""
Script to check what APIs are actually used in the Stocks_Portfolio_Management repository
"""
import requests
import re
import json

def search_github_repo_for_apis(repo_owner, repo_name, api_paths):
    """Search GitHub repository for API endpoint usage"""
    results = {}
    
    for api_path in api_paths:
        # Search for the API path in the repository
        query = f'repo:{repo_owner}/{repo_name} "{api_path}"'
        url = 'https://api.github.com/search/code'
        params = {'q': query}
        
        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                items = data.get('items', [])
                results[api_path] = items
                print(f"\n[OK] Found {len(items)} files using '{api_path}':")
                for item in items[:5]:  # Show first 5
                    print(f"   - {item['path']}")
            else:
                print(f"\n[WARNING] Search failed for '{api_path}': Status {response.status_code}")
                results[api_path] = []
        except Exception as e:
            print(f"\n[ERROR] Error searching for '{api_path}': {e}")
            results[api_path] = []
    
    return results

def get_file_content(repo_owner, repo_name, file_path):
    """Get file content from GitHub"""
    url = f'https://raw.githubusercontent.com/{repo_owner}/{repo_name}/main/{file_path}'
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.text
        return None
    except Exception as e:
        print(f"Error fetching {file_path}: {e}")
        return None

# Repository info
repo_owner = "Sabarivasan-Velayutham"
repo_name = "Stocks_Portfolio_Management"

# APIs to search for (from backend-api-service)
api_paths = [
    "/api/stocks",
    "/api/stocks/buy",
    "/api/stocks/sell",
    "/api/stocks/{id}",
    "/api/stocks/{id}/price",
    "/api/stocks/{id}/current-price"
]

print("=" * 60)
print(f"Searching {repo_owner}/{repo_name} for API usage")
print("=" * 60)

# Search for each API
results = search_github_repo_for_apis(repo_owner, repo_name, api_paths)

# Get Portfolio.js content to verify
print("\n" + "=" * 60)
print("Verifying Portfolio.js content:")
print("=" * 60)
portfolio_content = get_file_content(repo_owner, repo_name, "frontend/src/components/Portfolio.js")
if portfolio_content:
    print("\n[FILE] Portfolio.js content:")
    print(portfolio_content[:500])
    
    # Extract API calls
    api_calls = re.findall(r'(axios|fetch)\.(get|post|put|delete)\([\'"]?([^\'"\)]+)[\'"]?', portfolio_content, re.IGNORECASE)
    print(f"\n[API CALLS] Found in Portfolio.js:")
    for call in api_calls:
        print(f"   {call[0]}.{call[1]}('{call[2]}')")

print("\n" + "=" * 60)
print("Summary:")
print("=" * 60)
for api_path, items in results.items():
    print(f"  {api_path}: {len(items)} files")

