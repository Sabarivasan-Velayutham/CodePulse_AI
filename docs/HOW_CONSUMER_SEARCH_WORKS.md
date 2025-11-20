# How Consumer Search Works - Technical Details

## Answer: Repositories are **Cloned Locally First**, Then Searched

The system does **NOT** search GitHub directly. Instead, it:

1. **Clones repositories** to a local cache directory
2. **Searches the cloned code** locally on your machine
3. **Caches repositories** for faster subsequent searches

---

## Step-by-Step Process

### Step 1: Clone Consumer Repositories

When you trigger API contract analysis, the system:

```python
# In api_contract_orchestrator.py, line 266-269
other_repo_path = await self.github_fetcher.fetch_repository(
    repo_identifier,  # e.g., "Sabarivasan-Velayutham/Stocks_Portfolio_Management"
    branch="main"
)
```

**What happens**:
- Calls `GitHubFetcher.fetch_repository()`
- Uses `git clone` to download the repository
- Stores it in: `/tmp/github_repos/Sabarivasan-Velayutham_Stocks_Portfolio_Management/`
- Returns the local path

### Step 2: Search Cloned Code Locally

After cloning, the system searches the local files:

```python
# In api_contract_orchestrator.py, line 272
consumers = self.api_extractor.find_api_consumers(endpoint, method, other_repo_path)
```

**What happens**:
- Takes the local cloned path (e.g., `/tmp/github_repos/.../Stocks_Portfolio_Management/`)
- Recursively searches all code files (`.js`, `.jsx`, `.ts`, `.java`, `.py`, etc.)
- Looks for API usage patterns like:
  - `fetch('/api/stocks/buy', ...)`
  - `axios.post('/api/stocks/buy', ...)`
  - `http.get('/api/stocks/buy', ...)`
- Returns matching files with line numbers

---

## Where Are Repositories Cloned?

### Default Location

**Linux/Mac/Docker**:
```
/tmp/github_repos/
  ├── Sabarivasan-Velayutham_Stocks_Portfolio_Management/
  ├── Sabarivasan-Velayutham_auctioneer/
  └── Sabarivasan-Velayutham_MobileStore_Project/
```

**Windows**:
```
C:\Users\<username>\AppData\Local\Temp\github_repos\
  ├── Sabarivasan-Velayutham_Stocks_Portfolio_Management\
  ├── Sabarivasan-Velayutham_auctioneer\
  └── Sabarivasan-Velayutham_MobileStore_Project\
```

### Custom Location

You can set a custom cache directory via environment variable:

```bash
# .env
GITHUB_CACHE_DIR=/path/to/your/cache
```

---

## Caching Strategy

### First Time
- **Action**: Clones repository (takes time)
- **Time**: ~10-30 seconds per repo (depending on size)

### Subsequent Searches
- **Action**: Updates existing clone (`git pull`)
- **Time**: ~1-5 seconds per repo (much faster)

### Cache Persistence
- Repositories stay cached between runs
- Only updates when you trigger analysis
- Cache persists until you clear it or restart

---

## Code Flow

### 1. GitHubFetcher.fetch_repository() 
```python
# backend/app/utils/github_fetcher.py, line 75-167

def fetch_repository(self, repo_url, branch="main"):
    # 1. Determine cache path
    repo_cache_path = /tmp/github_repos/{repo_name}
    
    # 2. Check if already cloned
    if repo_cache_path.exists():
        # Update existing: git pull
        git pull origin main
    else:
        # Clone new: git clone
        git clone --depth 1 --branch main {repo_url} {repo_cache_path}
    
    # 3. Return local path
    return str(repo_cache_path)
```

### 2. APIContractExtractor.find_api_consumers()
```python
# backend/app/services/api_extractor.py, line 342-377

def find_api_consumers(self, api_path, api_method, repository_path):
    # repository_path = /tmp/github_repos/Stocks_Portfolio_Management/
    
    # Search patterns
    patterns = [
        f"fetch('{api_path}', ...)",
        f"axios.post('{api_path}', ...)",
        ...
    ]
    
    # Search locally
    for file in repository_path.rglob('*.js'):  # Recursive search
        if pattern matches:
            consumers.append(file)
    
    return consumers
```

### 3. _search_in_repository()
```python
# backend/app/services/api_extractor.py, line 379-411

def _search_in_repository(self, repo_path, pattern, api_path):
    # repo_path = /tmp/github_repos/Stocks_Portfolio_Management/
    
    # Recursively find all code files
    for file_path in Path(repo_path).rglob('*'):
        if file_path.suffix in ['.js', '.jsx', '.ts', '.java', '.py']:
            # Read file locally
            with open(file_path) as f:
                content = f.read()
            
            # Search for API usage
            if pattern matches in content:
                consumers.append({
                    'file_path': relative_path,
                    'line_number': line_num,
                    'context': matching_line
                })
    
    return consumers
```

---

## Example: What Happens When You Run Test

### Input:
```python
API Change: POST /api/stocks/buy
Consumer Repos: [
    "Sabarivasan-Velayutham/Stocks_Portfolio_Management",
    "Sabarivasan-Velayutham/auctioneer", 
    "Sabarivasan-Velayutham/MobileStore_Project"
]
```

### Process:

1. **Clone Repo 1**:
   ```
   git clone https://github.com/Sabarivasan-Velayutham/Stocks_Portfolio_Management.git
   → /tmp/github_repos/Sabarivasan-Velayutham_Stocks_Portfolio_Management/
   ```

2. **Search Repo 1 Locally**:
   ```
   Search: /tmp/github_repos/.../Stocks_Portfolio_Management/
   Pattern: fetch('/api/stocks/buy', ...)
   Found: frontend/src/api/stockService.js (line 45)
   ```

3. **Clone Repo 2**:
   ```
   git clone https://github.com/Sabarivasan-Velayutham/auctioneer.git
   → /tmp/github_repos/Sabarivasan-Velayutham_auctioneer/
   ```

4. **Search Repo 2 Locally**:
   ```
   Search: /tmp/github_repos/.../auctioneer/
   Pattern: axios.post('/api/stocks/buy', ...)
   Found: client/src/services/stockApi.js (line 123)
   ```

5. **Clone Repo 3**:
   ```
   git clone https://github.com/Sabarivasan-Velayutham/MobileStore_Project.git
   → /tmp/github_repos/Sabarivasan-Velayutham_MobileStore_Project/
   ```

6. **Search Repo 3 Locally**:
   ```
   Search: /tmp/github_repos/.../MobileStore_Project/
   Pattern: fetch('/api/stocks/buy', ...)
   Found: src/api/stockClient.ts (line 67)
   ```

### Result:
```
Found 3 consumers across 3 repositories:
- Stocks_Portfolio_Management: frontend/src/api/stockService.js
- auctioneer: client/src/services/stockApi.js
- MobileStore_Project: src/api/stockClient.ts
```

---

## Benefits of Local Cloning

### ✅ Advantages:
1. **Fast Search**: Local file system access is much faster than GitHub API
2. **No Rate Limits**: GitHub API has rate limits, local search doesn't
3. **Full Code Access**: Can read entire files, not just snippets
4. **Caching**: Repositories cached for faster subsequent searches
5. **Offline Capable**: Once cloned, can search without internet (until cache expires)

### ⚠️ Considerations:
1. **Disk Space**: Each cloned repo takes disk space
2. **Initial Clone Time**: First clone takes time (10-30s per repo)
3. **Cache Management**: Old caches need cleanup

---

## Cache Management

### View Cached Repositories:
```bash
# Linux/Mac/Docker
ls -la /tmp/github_repos/

# Windows
dir %TEMP%\github_repos\
```

### Clear Cache:
```python
from app.utils.github_fetcher import github_fetcher

# Clear specific repo
github_fetcher.clear_cache("Sabarivasan-Velayutham/Stocks_Portfolio_Management")

# Clear all repos
github_fetcher.clear_cache()
```

### Set Custom Cache Location:
```bash
# .env
GITHUB_CACHE_DIR=/path/to/custom/cache
```

---

## Summary

**Question**: Where does the search happen - GitHub or locally?

**Answer**: **Locally** - Repositories are cloned to `/tmp/github_repos/` (or custom location), then searched locally using file system operations.

**Flow**:
1. GitHub → Clone → Local Cache (`/tmp/github_repos/`)
2. Local Cache → Search Files → Find API Usage
3. Results → Return to Analysis

**Why**: Faster, no rate limits, full code access, cacheable.

---

## Check What's Happening

When you run the test, check your backend logs. You should see:

```
Step 4/7: Finding API consumers...
   🔍 Searching for API consumers...
      Additional repositories to search: 3
      
   📥 Fetching repository: https://github.com/Sabarivasan-Velayutham/Stocks_Portfolio_Management.git
   📁 Cache path: /tmp/github_repos/Sabarivasan-Velayutham_Stocks_Portfolio_Management
   ✅ Repository cloned successfully
      ✅ Found 2 consumers in Sabarivasan-Velayutham/Stocks_Portfolio_Management
   
   📥 Fetching repository: https://github.com/Sabarivasan-Velayutham/auctioneer.git
   📁 Cache path: /tmp/github_repos/Sabarivasan-Velayutham_auctioneer
   ✅ Repository cloned successfully
      ✅ Found 1 consumers in Sabarivasan-Velayutham/auctioneer
```

This shows the cloning and local search process!

