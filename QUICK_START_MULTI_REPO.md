# Quick Start: Multi-Repository Setup

## ✅ Step 1: Fix Your `.env` File

Your repositories are currently in full URL format. Update your `.env` file to use the correct format:

### Current (Incorrect):
```bash
API_CONSUMER_REPOSITORIES=https://github.com/Sabarivasan-Velayutham/Stocks_Portfolio_Management/tree/main,https://github.com/Sabarivasan-Velayutham/auctioneer/tree/main,https://github.com/Sabarivasan-Velayutham/MobileStore_Project
```

### ✅ Correct Format (Option 1 - Recommended):
```bash
# .env file
GITHUB_ORG=Sabarivasan-Velayutham
API_CONSUMER_REPOSITORIES=Stocks_Portfolio_Management,auctioneer,MobileStore_Project
SEARCH_ALL_REPOS_FOR_CONSUMERS=true
```

### ✅ Alternative Format (Option 2):
```bash
# .env file
API_CONSUMER_REPOSITORIES=Sabarivasan-Velayutham/Stocks_Portfolio_Management,Sabarivasan-Velayutham/auctioneer,Sabarivasan-Velayutham/MobileStore_Project
SEARCH_ALL_REPOS_FOR_CONSUMERS=true
```

**Note**: Remove `/tree/main` from URLs - just use repo names or `owner/repo` format.

---

## ✅ Step 2: Restart Backend

After updating `.env`, restart your backend:

```bash
# If using Docker Compose
docker-compose restart backend

# If running directly
# Stop your FastAPI server (Ctrl+C) and restart it
cd backend
python -m uvicorn app.main:app --reload
```

---

## ✅ Step 3: Verify Configuration

Test if repositories are loaded correctly. Create a test script:

```bash
# Create test file
cat > test_config.py << 'EOF'
from app.config import get_consumer_repositories
repos = get_consumer_repositories()
print("Configured repositories:")
for repo in repos:
    print(f"  - {repo}")
EOF

# Run test
python test_config.py
```

**Expected Output**:
```
Configured repositories:
  - Sabarivasan-Velayutham/Stocks_Portfolio_Management
  - Sabarivasan-Velayutham/auctioneer
  - Sabarivasan-Velayutham/MobileStore_Project
```

---

## ✅ Step 4: Test API Consumer Discovery

### Option A: Test with Manual API Call

Find an API endpoint in one of your repositories and test:

```bash
# Example: Test with Stocks_Portfolio_Management
curl -X POST http://localhost:8000/api/v1/api/contract/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "backend/src/main/java/com/example/StockController.java",
    "repository": "Stocks_Portfolio_Management",
    "diff": "- @PostMapping(\"/api/stocks/buy\")\n+ @PostMapping(\"/api/stocks/buy\")\n+ // Added required accountId",
    "commit_sha": "test123",
    "github_repo_url": "https://github.com/Sabarivasan-Velayutham/Stocks_Portfolio_Management"
  }'
```

### Option B: Make a Real Change

1. **Find an API file** in `Stocks_Portfolio_Management`:
   - Look in `backend/` folder for Spring Boot controllers
   - Example: `StockController.java` or `TransactionController.java`

2. **Make a small change** (add a comment or parameter)

3. **Commit and push** to GitHub

4. **Trigger analysis** via webhook or manual API call

5. **Check backend logs** - you should see:
   ```
   🔍 Searching for API consumers...
      Additional repositories to search: 3
      📥 Fetching repository: https://github.com/Sabarivasan-Velayutham/auctioneer.git
      ✅ Repository cloned successfully
      📥 Fetching repository: https://github.com/Sabarivasan-Velayutham/MobileStore_Project.git
      ✅ Repository cloned successfully
   ```

---

## ✅ Step 5: Check Results

The analysis result will show:

```json
{
  "consumers": {
    "POST /api/stocks/buy": [
      {
        "file_path": "client/src/api/stockService.js",
        "line_number": 45,
        "source_repo": "Sabarivasan-Velayutham/auctioneer",
        "context": "fetch('/api/stocks/buy', ...)"
      }
    ]
  },
  "summary": {
    "total_consumers": 2,
    "repositories_searched": 3
  }
}
```

---

## 🎯 What Happens Next?

When you make an API change:

1. **System detects** the API change in your repository
2. **Searches current repo** for API definition
3. **Searches all 3 repos** (`Stocks_Portfolio_Management`, `auctioneer`, `MobileStore_Project`) for consumers
4. **Finds consumers** in any repository that uses your API
5. **Shows results** with source repository info

This enables **cross-repository consumer discovery**!

---

## 🔍 Finding API Endpoints in Your Repos

### Stocks_Portfolio_Management (Spring Boot)
- Look in: `backend/src/main/java/` 
- Files: `*Controller.java`
- Example endpoints: `/api/stocks/*`, `/api/transactions/*`, `/api/accounts/*`

### auctioneer (MERN Stack)
- Look in: `server/` folder
- Files: `routes/*.js` or `controllers/*.js`
- Example endpoints: `/api/auctions/*`, `/api/bids/*`

### MobileStore_Project
- Check: `backend/` or `api/` folders
- Look for: Express routes or API controllers

---

## ⚠️ Troubleshooting

### Issue: "Repository not found"
- **Fix**: Ensure repositories are public or you have access
- **Check**: Repository format in `.env` (should be `owner/repo`)

### Issue: "No consumers found"
- **Normal**: If other repos don't actually use this API
- **Check**: Manually verify if repos call the same API endpoint

### Issue: "Failed to clone"
- **Fix**: Check internet connection and repository access
- **Note**: First clone takes time, subsequent searches are faster (uses cache)

---

## 📝 Summary

1. ✅ **Update `.env`** with correct format
2. ✅ **Restart backend**
3. ✅ **Test configuration**
4. ✅ **Make API change** or test manually
5. ✅ **Check results** in logs/API response

You're all set! The system will now search across all 3 repositories when API changes are detected.

