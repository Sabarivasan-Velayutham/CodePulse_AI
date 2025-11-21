# GitHub API Search - Alternative to Cloning

## Overview

CodePulse AI now supports **two methods** for finding API consumers across repositories:

1. **Clone Method** (default): Clones repositories locally and searches files
2. **GitHub API Method**: Searches repositories directly via GitHub Search API (no cloning)

---

## Why Use GitHub API Search?

### ✅ Advantages:
- **No Disk Space**: Doesn't require cloning repositories
- **Faster for Small Searches**: Quick API calls vs full clone
- **No Git Required**: Works without git installed
- **Good for Demos**: Perfect for hackathon presentations
- **Public Repos Only**: Works with public repositories

### ⚠️ Limitations:
- **Rate Limits**: 
  - Without token: 10 requests/hour
  - With token: 5,000 requests/hour
- **No Exact Line Numbers**: GitHub API doesn't provide exact line numbers
- **Public Repos Only**: Cannot search private repositories (unless authenticated)
- **Less Precise**: May miss some matches compared to full code analysis

---

## Configuration

### Option 1: Use GitHub API Search (No Cloning)

Add to your `.env` file:

```bash
# Use GitHub API instead of cloning
CONSUMER_SEARCH_METHOD=api

# Optional: GitHub token for higher rate limits
# Get token from: https://github.com/settings/tokens
GITHUB_TOKEN=ghp_your_token_here
```

### Option 2: Use Clone Method (Default)

```bash
# Use local cloning (default)
CONSUMER_SEARCH_METHOD=clone
```

---

## How It Works

### GitHub API Search Flow:

1. **API Change Detected** in `backend-api-service`
2. **Extract API Contracts** from changed file
3. **For Each Consumer Repo**:
   - Build GitHub Search API query: `repo:owner/repo "/api/stocks/buy"`
   - Call GitHub Search API: `GET https://api.github.com/search/code?q=...`
   - Parse results: Get file paths and GitHub URLs
4. **Aggregate Results**: Combine all consumers from all repos
5. **Return Analysis**: Show consumers with GitHub file links

### Example Search Query:

```
repo:Sabarivasan-Velayutham/Stocks_Portfolio_Management "/api/stocks/buy"
```

This searches for the exact string `/api/stocks/buy` in the repository.

---

## Rate Limits

### Without GitHub Token:
- **10 requests/hour** per IP address
- **Limited to public repos only**
- ⚠️ **Not suitable for production** - will hit limits quickly

### With GitHub Token:
- **5,000 requests/hour** per token
- **Can search private repos** (if token has access)
- ✅ **Suitable for production** use

### Getting a GitHub Token:

1. Go to: https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Select scopes:
   - `public_repo` (for public repos)
   - `repo` (for private repos, if needed)
4. Copy token and add to `.env`:
   ```bash
   GITHUB_TOKEN=ghp_your_token_here
   ```

---

## Comparison: Clone vs API

| Feature | Clone Method | GitHub API Method |
|---------|-------------|-------------------|
| **Speed** | Slower (clone + search) | Faster (API calls) |
| **Disk Space** | Requires space | No disk space |
| **Rate Limits** | None | 10/hour (no token) or 5,000/hour (with token) |
| **Line Numbers** | Exact line numbers | No line numbers |
| **Precision** | Very precise | Good (may miss some) |
| **Private Repos** | Yes (with access) | Yes (with token) |
| **Git Required** | Yes | No |
| **Best For** | Production, deep analysis | Demos, quick checks |

---

## Example Output

### With Clone Method:
```json
{
  "file_path": "frontend/src/api/stockService.js",
  "line_number": 45,
  "context": "const response = await fetch('/api/stocks/buy', {...})",
  "source_repo": "Sabarivasan-Velayutham/Stocks_Portfolio_Management"
}
```

### With GitHub API Method:
```json
{
  "file_path": "frontend/src/api/stockService.js",
  "line_number": 0,
  "context": "Found in stockService.js",
  "source": "github_api",
  "html_url": "https://github.com/owner/repo/blob/main/frontend/src/api/stockService.js",
  "repository": "Sabarivasan-Velayutham/Stocks_Portfolio_Management"
}
```

---

## When to Use Each Method

### Use **Clone Method** when:
- ✅ You need exact line numbers
- ✅ You're doing deep code analysis
- ✅ You have disk space available
- ✅ You're in production
- ✅ You need to search private repos without tokens

### Use **GitHub API Method** when:
- ✅ You're in a hackathon/demo
- ✅ You have limited disk space
- ✅ You want faster results
- ✅ You're doing quick consumer discovery
- ✅ You have a GitHub token for rate limits

---

## Troubleshooting

### Rate Limit Exceeded

**Error:**
```
⚠️ GitHub API rate limit exceeded for owner/repo (remaining: 0)
💡 Tip: Set GITHUB_TOKEN in .env for higher rate limits (5000/hour)
```

**Solution:**
1. Add `GITHUB_TOKEN` to `.env`
2. Or wait 1 hour for rate limit reset
3. Or switch to `CONSUMER_SEARCH_METHOD=clone`

### No Results Found

**Possible Causes:**
1. API path doesn't match exactly in consumer code
2. Repository is private (need token with access)
3. Search query too specific

**Solution:**
1. Check if API path is used exactly as defined
2. Verify repository is public or token has access
3. Try clone method for more thorough search

### Authentication Failed

**Error:**
```
⚠️ GitHub API authentication failed for owner/repo
```

**Solution:**
1. Check if `GITHUB_TOKEN` is valid
2. Verify token hasn't expired
3. Ensure token has correct scopes (`public_repo` or `repo`)

---

## Quick Start

### For Hackathon Demo:

1. **Add to `.env`:**
   ```bash
   CONSUMER_SEARCH_METHOD=api
   GITHUB_TOKEN=ghp_your_token_here  # Optional but recommended
   ```

2. **Run your test:**
   ```bash
   python scripts/test_backend_api_change.py
   ```

3. **Check output:**
   ```
   🔍 Searching Sabarivasan-Velayutham/Stocks_Portfolio_Management via GitHub API...
   ✅ Found 2 consumers in Sabarivasan-Velayutham/Stocks_Portfolio_Management (via API)
   ```

---

## Summary

**Question**: Can we search GitHub repos without cloning?

**Answer**: **Yes!** Use `CONSUMER_SEARCH_METHOD=api` in your `.env` file.

**Benefits**:
- No disk space needed
- Faster for quick searches
- Perfect for demos
- Works with GitHub token for higher limits

**Trade-offs**:
- Rate limits (10/hour without token, 5,000/hour with token)
- No exact line numbers
- Less precise than full code analysis

**Best Use Case**: Hackathon demos, quick consumer discovery, when cloning isn't feasible.

