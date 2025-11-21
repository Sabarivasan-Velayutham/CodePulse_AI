# GitHub API Rate Limit Solution

## Problem

You're seeing:
```
⚠️ GitHub API rate limit exceeded (remaining: 0)
```

This happens because:
- **Without GitHub token**: 10 requests/hour limit
- **5 API endpoints** × **3 repos** × **multiple queries** = **Too many API calls**

## Solutions

### Solution 1: Add GitHub Token (Recommended for API Search)

**Get a token:**
1. Go to: https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Select scope: `public_repo`
4. Copy the token

**Add to `.env`:**
```bash
GITHUB_TOKEN=ghp_your_token_here
```

**Result:**
- ✅ 5,000 requests/hour (instead of 10)
- ✅ Can search private repos (if token has access)
- ✅ No rate limit issues

---

### Solution 2: Use Clone Method (Recommended for Production)

**Switch to clone method in `.env`:**
```bash
CONSUMER_SEARCH_METHOD=clone
```

**Result:**
- ✅ No rate limits
- ✅ More thorough search
- ✅ Exact line numbers
- ⚠️ Requires disk space
- ⚠️ Slower (clones repos)

---

### Solution 3: Wait for Rate Limit Reset

Rate limits reset every hour. You can:
- Wait 1 hour
- Or use Solution 1 or 2 above

---

## Current Status

**API Extraction**: ✅ Working (found 5 contracts)
**Consumer Search**: ⚠️ Rate limited (0 consumers found)

**Next Steps:**
1. Add `GITHUB_TOKEN` to `.env` (Solution 1) - **Best for demos**
2. Or switch to `CONSUMER_SEARCH_METHOD=clone` (Solution 2) - **Best for production**

---

## Quick Fix

**For your hackathon demo, add this to `.env`:**

```bash
# Use clone method (no rate limits)
CONSUMER_SEARCH_METHOD=clone

# OR use API with token (faster, but needs token)
# CONSUMER_SEARCH_METHOD=api
# GITHUB_TOKEN=ghp_your_token_here
```

**Then restart your backend container.**

