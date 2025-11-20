# API Contract Testing Guide

## Current Status

✅ **Backend API Service Created**: `sample-repo/backend-api-service/`
✅ **Test Script Created**: `scripts/test_backend_api_change.py`
✅ **Configuration Working**: Multi-repo consumer discovery configured
⚠️ **Issue**: API contracts not being extracted (0 changes detected)

## The Problem

The test shows:
- ✅ Analysis runs successfully
- ❌ 0 API changes detected
- ❌ 0 consumers found

## Root Causes

### 1. File Path Issue
The GitHub repository structure is:
```
backend-api-service/
  └── backend-api-service/
      └── src/main/java/com/backendapi/
          └── StockController.java
```

But the file path in the test is:
```
backend-api-service/src/main/java/com/backendapi/StockController.java
```

**Solution**: The orchestrator needs to handle nested repository structures better.

### 2. API Contract Extraction
The Spring Boot extractor might not be finding annotations correctly, or the file isn't being read.

**Solution**: Check backend logs to see if file is found and contracts extracted.

### 3. Consumer Discovery
The consumer repos (Stocks_Portfolio_Management, auctioneer, MobileStore_Project) might not actually have code that uses these APIs yet.

**Solution**: Either:
- Add sample consumer code to those repos
- Or test with repos that actually use the APIs

## Next Steps

### Step 1: Check Backend Logs

When you run the test, check your backend console/logs. You should see:
```
Step 1/7: Extracting API contracts from current code...
   📄 Found file at: [path]
   ✅ Extracted X API contracts from StockController.java
      - GET /api/stocks
      - POST /api/stocks/buy
      ...
```

If you see "File not found" or "0 API contracts", that's the issue.

### Step 2: Verify File Path

The repository structure on GitHub is nested. Update the test script file path:

**Current**:
```python
"file_path": "backend-api-service/src/main/java/com/backendapi/StockController.java"
```

**Try**:
```python
"file_path": "src/main/java/com/backendapi/StockController.java"  # Remove duplicate folder
```

Or check what the actual cloned structure is in `/tmp/github_repos/`.

### Step 3: Test with Real Change

Instead of using the test script, make a **real change** to your GitHub repository:

1. **Go to**: https://github.com/Sabarivasan-Velayutham/backend-api-service
2. **Edit**: `backend-api-service/src/main/java/com/backendapi/StockController.java`
3. **Make a change**: Add a required parameter to `buyStock` method
4. **Commit and push**
5. **Trigger analysis** via webhook or API call

### Step 4: Add Sample Consumer Code

To test consumer discovery, add sample code to your consumer repos that uses the API:

**In Stocks_Portfolio_Management** (frontend):
```javascript
// src/api/stockService.js
export const buyStock = async (stockId, quantity, accountId) => {
  const response = await fetch('/api/stocks/buy', {
    method: 'POST',
    body: JSON.stringify({ stockId, quantity, accountId })
  });
  return response.json();
};
```

**In auctioneer** (if it uses stocks):
```javascript
// client/src/services/stockApi.js
axios.post('/api/stocks/buy', { stockId, quantity, accountId })
```

Then run the test again - consumers should be found!

## Quick Fix: Test with Local File

To quickly test if extraction works, use the local file:

```python
# In test script, use local path instead of GitHub
test_data = {
    "file_path": "src/main/java/com/backendapi/StockController.java",  # Try without nested folder
    "repository": "backend-api-service",
    # Don't provide github_repo_url - will use local sample-repo
    ...
}
```

## Expected Behavior

When working correctly, you should see:

```
Step 1/7: Extracting API contracts from current code...
   📄 Found file at: /tmp/github_repos/.../StockController.java
   ✅ Extracted 5 API contracts from StockController.java
      - GET /api/stocks
      - GET /api/stocks/{id}
      - POST /api/stocks/buy
      - POST /api/stocks/sell
      - GET /api/stocks/{id}/price

Step 4/7: Finding API consumers...
   🔍 Searching for API consumers...
      Additional repositories to search: 3
      📥 Fetching repository: Stocks_Portfolio_Management
      ✅ Found 2 consumers in Stocks_Portfolio_Management
      📥 Fetching repository: auctioneer
      ✅ Found 1 consumers in auctioneer
      📥 Fetching repository: MobileStore_Project
      ✅ Found 0 consumers in MobileStore_Project
   ✅ Found 3 API consumers across 1 endpoints
```

## Debugging Commands

### Check if file exists in cloned repo:
```bash
# Find where GitHub fetcher stores repos
ls /tmp/github_repos/Sabarivasan-Velayutham_backend-api-service/

# Check file structure
find /tmp/github_repos -name "StockController.java"
```

### Test API extraction directly:
```python
from app.services.api_extractor import APIContractExtractor

extractor = APIContractExtractor()
with open('sample-repo/backend-api-service/src/main/java/com/backendapi/StockController.java') as f:
    content = f.read()
contracts = extractor.extract_api_contracts('StockController.java', content)
print(contracts)
```

## Summary

The system is set up correctly, but:
1. **File path** might need adjustment for nested repo structure
2. **Consumer repos** might not have code using these APIs yet
3. **Backend logs** will show exactly what's happening

Check your backend console when running the test to see detailed logs!

