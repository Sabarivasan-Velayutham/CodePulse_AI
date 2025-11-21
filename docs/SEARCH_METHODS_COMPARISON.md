# Consumer Search Methods - Quick Reference

## Answer to Your Question

**Q: "Suppose if the judges ask if cloning the repos are not feasible, then is it possible to search it in the github repo itself instead of cloning them?"**

**A: Yes!** CodePulse AI now supports **GitHub API search** as an alternative to cloning.

---

## Two Methods Available

### Method 1: Clone & Search Locally (Default)
- Clones repositories to `/tmp/github_repos/`
- Searches files locally
- **Best for**: Production, exact line numbers, deep analysis

### Method 2: GitHub API Search (New!)
- Searches via GitHub Search API
- No cloning required
- **Best for**: Hackathon demos, quick checks, limited disk space

---

## Quick Switch

### To Use GitHub API (No Cloning):

Add to `.env`:
```bash
CONSUMER_SEARCH_METHOD=api
GITHUB_TOKEN=ghp_your_token_here  # Optional but recommended
```

### To Use Clone Method (Default):

```bash
CONSUMER_SEARCH_METHOD=clone
# or just remove the line (clone is default)
```

---

## What Judges Will See

### With Clone Method:
```
📥 Fetching repository: https://github.com/owner/repo.git
📁 Cache path: /tmp/github_repos/owner_repo
✅ Repository cloned successfully
✅ Found 3 consumers in owner/repo (via clone)
```

### With GitHub API Method:
```
🔍 Searching owner/repo via GitHub API...
✅ Found 3 consumers in owner/repo (via API)
```

**Both methods produce the same results** - just different approaches!

---

## For Your Hackathon Demo

**Recommended Setup:**

```bash
# .env
CONSUMER_SEARCH_METHOD=api
GITHUB_TOKEN=ghp_your_token_here  # Get from GitHub Settings > Developer Settings > Tokens
```

**Why?**
- ✅ Faster (no cloning wait time)
- ✅ No disk space needed
- ✅ Cleaner demo (no file system operations)
- ✅ Shows flexibility of the solution

**What to Tell Judges:**

> "CodePulse AI supports two search methods: local cloning for deep analysis and GitHub API search for quick discovery. We're using API search for this demo to show fast cross-repository consumer discovery without requiring local storage."

---

## Technical Details

See:
- `docs/GITHUB_API_SEARCH_GUIDE.md` - Full GitHub API guide
- `docs/HOW_CONSUMER_SEARCH_WORKS.md` - Clone method details

---

## Summary

✅ **Yes, you can search GitHub repos without cloning!**

Just set `CONSUMER_SEARCH_METHOD=api` in your `.env` file.

The system will automatically use GitHub Search API instead of cloning repositories.

