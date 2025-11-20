# GitHub Repository Integration Guide

This guide explains how to use GitHub repositories instead of local folders for code dependency analysis when making MongoDB schema changes.

## Overview

When you make a MongoDB schema change, the system can now fetch code files from a GitHub repository instead of using the local `sample-repo` folder. This allows you to:

- Keep your MongoDB code in a separate GitHub repository
- Always analyze the latest code from your repository
- Work with remote repositories without local copies

## Setup Steps

### 1. Upload Your Code to GitHub

1. Create a new GitHub repository (or use an existing one)
2. Upload your `banking-app-mongodb` folder to the repository
3. Make sure the folder structure is preserved:
   ```
   your-repo/
   └── banking-app-mongodb/
       └── src/
           ├── account/
           ├── database/
           ├── fraud/
           └── payment/
   ```

### 2. Configure the System

You have **three ways** to specify the GitHub repository:

#### Option A: Environment Variable (Recommended for Docker)

Set the environment variable in your `.env` file or Docker Compose:

```bash
# For MongoDB schema changes
GITHUB_REPO_URL_MONGODB=owner/repo-name
# or full URL:
GITHUB_REPO_URL_MONGODB=https://github.com/owner/repo-name.git

# Optional: specify branch (default: main)
GITHUB_BRANCH=main

# Optional: specify cache directory (default: /tmp/github_repos)
GITHUB_CACHE_DIR=/tmp/github_repos
```

#### Option B: API Request Parameter

Include `github_repo_url` in your schema change webhook/API request:

```json
{
  "sql_statement": "db.accounts.createIndex({ status: 1 })",
  "database_name": "mongodb_banking_db",
  "github_repo_url": "owner/repo-name",
  "github_branch": "main"
}
```

#### Option C: Repository Parameter

If your `repository` parameter is a GitHub URL format, it will be used:

```json
{
  "sql_statement": "db.accounts.createIndex({ status: 1 })",
  "database_name": "mongodb_banking_db",
  "repository": "owner/repo-name"
}
```

### 3. Repository URL Formats

The system supports multiple GitHub URL formats:

- **Short format**: `owner/repo-name` (e.g., `myusername/banking-app-mongodb`)
- **HTTPS URL**: `https://github.com/owner/repo-name.git`
- **HTTPS URL (no .git)**: `https://github.com/owner/repo-name`
- **SSH URL**: `git@github.com:owner/repo-name.git`

### 4. How It Works

1. **First Request**: The system clones the repository to a cache directory
2. **Subsequent Requests**: The system updates the cached repository (git pull)
3. **Subfolder Extraction**: For MongoDB, it automatically looks in the `banking-app-mongodb` subfolder
4. **Code Analysis**: The system analyzes code files from the GitHub repository

## Example Usage

### Example 1: Using Environment Variable

**docker-compose.yml:**
```yaml
services:
  backend:
    environment:
      - GITHUB_REPO_URL_MONGODB=myusername/banking-app-mongodb
      - GITHUB_BRANCH=main
```

**MongoDB Schema Change:**
```bash
# Make a schema change in MongoDB
db.accounts.createIndex({ status: 1, created_at: -1 })
```

The system will automatically:
1. Fetch code from `https://github.com/myusername/banking-app-mongodb`
2. Look in the `banking-app-mongodb` subfolder
3. Analyze code dependencies

### Example 2: Using API Request

**API Call:**
```bash
curl -X POST http://localhost:8000/api/v1/schema/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "sql_statement": "db.accounts.createIndex({ status: 1 })",
    "database_name": "mongodb_banking_db",
    "github_repo_url": "myusername/banking-app-mongodb",
    "github_branch": "main"
  }'
```

### Example 3: MongoDB Schema Listener

Update your `mongodb_schema_listener.py` to include the GitHub repo URL:

```python
# In trigger_analysis() function
payload = {
    "sql_statement": operation_statement,
    "database_name": database_name,
    "github_repo_url": "myusername/banking-app-mongodb",  # Add this
    "github_branch": "main"  # Add this
}
```

## Caching

- Repositories are cached locally to avoid re-cloning on every request
- Cache location: `/tmp/github_repos` (or `GITHUB_CACHE_DIR` if set)
- Cache is automatically updated with `git pull` before each analysis
- To clear cache, delete the cache directory or restart the container

## Troubleshooting

### Issue: "Failed to clone repository"

**Solutions:**
1. Check that the repository URL is correct
2. Ensure the repository is public (or use SSH with authentication)
3. Verify git is installed in the Docker container
4. Check network connectivity

### Issue: "Subfolder not found"

**Solutions:**
1. Ensure your repository has the `banking-app-mongodb` folder at the root
2. Check the folder name matches exactly (case-sensitive)
3. Verify the branch contains the folder

### Issue: "Repository already cached, but code is outdated"

**Solutions:**
1. The system auto-updates, but you can manually clear cache:
   ```python
   from app.utils.github_fetcher import github_fetcher
   github_fetcher.clear_cache("owner/repo-name")
   ```
2. Or delete the cache directory: `rm -rf /tmp/github_repos`

### Issue: "Git operation timed out"

**Solutions:**
1. Check network connectivity
2. Try using a different branch
3. Use shallow clone (already enabled with `--depth 1`)

## Private Repositories

For private repositories, you have two options:

### Option 1: SSH Authentication

1. Add SSH key to your Docker container
2. Use SSH URL format: `git@github.com:owner/repo-name.git`

### Option 2: Personal Access Token (PAT)

1. Create a GitHub Personal Access Token
2. Use HTTPS URL with token: `https://TOKEN@github.com/owner/repo-name.git`
3. Store token securely in environment variables

## Fallback Behavior

If GitHub fetch fails, the system automatically falls back to:
1. Local `sample-repo` folder (if available)
2. Shows a warning but continues with available code

## Best Practices

1. **Use Environment Variables**: Set `GITHUB_REPO_URL_MONGODB` for consistent behavior
2. **Specify Branch**: Always specify the branch (default is "main")
3. **Monitor Cache**: Clear cache periodically if you want fresh code
4. **Error Handling**: The system gracefully falls back to local folders if GitHub fetch fails

## Configuration Summary

| Environment Variable | Description | Default |
|---------------------|-------------|---------|
| `GITHUB_REPO_URL_MONGODB` | GitHub repo URL for MongoDB code | None (uses local) |
| `GITHUB_BRANCH` | Branch to checkout | `main` |
| `GITHUB_CACHE_DIR` | Cache directory for repos | `/tmp/github_repos` |

## Next Steps

1. Upload your `banking-app-mongodb` code to GitHub
2. Set the `GITHUB_REPO_URL_MONGODB` environment variable
3. Make a MongoDB schema change
4. Verify the system fetches code from GitHub

The rest of the process (analysis, risk scoring, graph visualization) remains exactly the same!

