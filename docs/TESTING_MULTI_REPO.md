# Testing Multi-Repository API Consumer Discovery

## Step 1: Format Repository URLs Correctly

The `.env` file should use `owner/repo` format, not full GitHub URLs.

### ❌ Incorrect Format:
```bash
API_CONSUMER_REPOSITORIES=https://github.com/Sabarivasan-Velayutham/Stocks_Portfolio_Management/tree/main,https://github.com/Sabarivasan-Velayutham/auctioneer/tree/main,https://github.com/Sabarivasan-Velayutham/MobileStore_Project
```

### ✅ Correct Format:
```bash
# Option 1: If GITHUB_ORG is set
GITHUB_ORG=Sabarivasan-Velayutham
API_CONSUMER_REPOSITORIES=Stocks_Portfolio_Management,auctioneer,MobileStore_Project

# Option 2: Full owner/repo format
API_CONSUMER_REPOSITORIES=Sabarivasan-Velayutham/Stocks_Portfolio_Management,Sabarivasan-Velayutham/auctioneer,Sabarivasan-Velayutham/MobileStore_Project
```

## Step 2: Update Your `.env` File

Add/update these lines in your `.env` file:

```bash
# GitHub Configuration
GITHUB_ORG=Sabarivasan-Velayutham

# API Consumer Repositories (comma-separated)
API_CONSUMER_REPOSITORIES=Stocks_Portfolio_Management,auctioneer,MobileStore_Project

# Enable cross-repo search
SEARCH_ALL_REPOS_FOR_CONSUMERS=true
```

## Step 3: Restart Backend

After updating `.env`, restart your backend:

```bash
# If using Docker
docker-compose restart backend

# If running directly
# Stop and restart your FastAPI server
```

## Step 4: Test the Configuration

### Test 1: Verify Configuration is Loaded

Check if repositories are configured correctly:

```bash
# In Python shell or add a test endpoint
python -c "from app.config import get_consumer_repositories; print(get_consumer_repositories())"
```

Expected output:
```
['Sabarivasan-Velayutham/Stocks_Portfolio_Management', 'Sabarivasan-Velayutham/auctioneer', 'Sabarivasan-Velayutham/MobileStore_Project']
```

### Test 2: Make an API Change

**Scenario**: Change an API endpoint in one repository and see if consumers are found in others.

#### Example: Change API in `Stocks_Portfolio_Management`

1. **Identify an API endpoint** in `Stocks_Portfolio_Management`:
   - Look for Spring Boot controllers (likely in `backend/` folder)
   - Example: `PaymentController.java` or `StockController.java`

2. **Make a breaking change**:
   ```java
   // BEFORE
   @PostMapping("/api/stocks/buy")
   public Response buyStock(@RequestBody BuyRequest request) {
       // request has: {stockId, quantity}
   }
   
   // AFTER (Breaking change - add required parameter)
   @PostMapping("/api/stocks/buy")
   public Response buyStock(@RequestBody BuyRequest request) {
       // request now REQUIRES: {stockId, quantity, accountId}  // NEW!
   }
   ```

3. **Commit and push** to GitHub

4. **Trigger Analysis**:
   - Via GitHub webhook (if configured)
   - Or manually via API:
   ```bash
   curl -X POST http://localhost:8000/api/v1/api/contract/analyze \
     -H "Content-Type: application/json" \
     -d '{
       "file_path": "backend/src/main/java/com/example/StockController.java",
       "repository": "Stocks_Portfolio_Management",
       "diff": "- @PostMapping(\"/api/stocks/buy\")\n+ @PostMapping(\"/api/stocks/buy\")\n+ // Added required accountId parameter",
       "commit_sha": "abc123",
       "github_repo_url": "https://github.com/Sabarivasan-Velayutham/Stocks_Portfolio_Management"
     }'
   ```

5. **Check Results**:
   - System should search all 3 repositories
   - Find consumers in `auctioneer` and `MobileStore_Project` if they use this API
   - Show results with source repository info

## Step 5: Verify Consumer Discovery

### Check Backend Logs

When analysis runs, you should see:

```
🔍 Searching for API consumers...
   Current repository: /tmp/github_repos/Sabarivasan-Velayutham_Stocks_Portfolio_Management
   Additional repositories to search: 3

   📥 Fetching repository: https://github.com/Sabarivasan-Velayutham/auctioneer.git
   ✅ Repository cloned successfully
   ✅ Found 2 consumers in Sabarivasan-Velayutham/auctioneer

   📥 Fetching repository: https://github.com/Sabarivasan-Velayutham/MobileStore_Project.git
   ✅ Repository cloned successfully
   ✅ Found 1 consumers in Sabarivasan-Velayutham/MobileStore_Project

   ✅ Found 3 API consumers across 1 endpoints
      Searched 3 repositories/sources
```

### Check Analysis Results

The analysis result should include:

```json
{
  "consumers": {
    "POST /api/stocks/buy": [
      {
        "file_path": "client/src/api/stockService.js",
        "line_number": 45,
        "source_repo": "Sabarivasan-Velayutham/auctioneer",
        "context": "fetch('/api/stocks/buy', ...)"
      },
      {
        "file_path": "src/services/stockApi.ts",
        "line_number": 123,
        "source_repo": "Sabarivasan-Velayutham/MobileStore_Project",
        "context": "axios.post('/api/stocks/buy', ...)"
      }
    ]
  },
  "summary": {
    "total_consumers": 3,
    "repositories_searched": 3
  }
}
```

## Troubleshooting

### Issue: "Repository not found" or "Failed to clone"

**Possible causes**:
1. Repository is private (requires authentication)
2. Incorrect repository format
3. Network issues

**Solutions**:
1. **For private repos**: Add GitHub token to `.env`:
   ```bash
   GITHUB_TOKEN=your_github_personal_access_token
   ```
   (Note: This requires updating `GitHubFetcher` to use token)

2. **Verify repository format**: Should be `owner/repo` not full URL

3. **Check repository access**: Ensure repositories are accessible

### Issue: "No consumers found"

**Possible causes**:
1. Other repositories don't actually use this API
2. API path doesn't match (different base path)
3. Consumers use different HTTP client patterns

**Solutions**:
1. **Check actual API usage**: Manually verify if other repos call this API
2. **Verify API path**: Ensure exact path matches (including `/api` prefix)
3. **Check patterns**: System searches for:
   - `fetch('/api/stocks/buy', ...)`
   - `axios.post('/api/stocks/buy', ...)`
   - `http.get('/api/stocks/buy', ...)`
   - etc.

### Issue: "Search taking too long"

**Solutions**:
1. Repositories are cached after first clone
2. Subsequent searches are faster (git pull instead of clone)
3. Consider reducing number of repos if needed

## Next Steps

1. ✅ **Format `.env` correctly** (see Step 1)
2. ✅ **Restart backend** (see Step 3)
3. ✅ **Make an API change** (see Step 4)
4. ✅ **Verify results** (see Step 5)
5. ⏳ **View in dashboard** (once frontend is updated)

## Example Test Scenario

### Setup:
- **Backend API**: `Stocks_Portfolio_Management` (Spring Boot)
- **Frontend**: `auctioneer` (React) - might consume stock API
- **Mobile App**: `MobileStore_Project` - might consume stock API

### Test:
1. Change API in `Stocks_Portfolio_Management`
2. System searches `auctioneer` and `MobileStore_Project`
3. Finds consumers (if they exist)
4. Shows which team/repo is affected

This demonstrates **cross-team consumer discovery** in action!

