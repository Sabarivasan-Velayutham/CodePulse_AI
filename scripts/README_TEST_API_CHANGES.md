# API Contract Change Test Script

## Overview

This script tests API contract change detection with cross-repository consumer discovery. It includes multiple test scenarios to demonstrate different types of API changes.

## Usage

### Run Single Scenario

```bash
# Run scenario 1 (default)
python scripts/test_backend_api_change.py

# Run specific scenario (1-5)
python scripts/test_backend_api_change.py --scenario 2
```

### Run All Scenarios

```bash
python scripts/test_backend_api_change.py --all
```

## Test Scenarios

### Scenario 1: Breaking Change - Add Required Parameter
- **Change**: Adds required `accountId` parameter to `POST /api/stocks/buy`
- **Impact**: All existing consumers will break
- **Expected**: High risk score, consumers found across repos

### Scenario 2: Breaking Change - Remove Endpoint
- **Change**: Removes `POST /api/stocks/sell` endpoint
- **Impact**: All consumers of this endpoint will break
- **Expected**: Critical risk score, all consumers identified

### Scenario 3: Breaking Change - Change Endpoint Path
- **Change**: Changes path from `/{id}/price` to `/{id}/current-price`
- **Impact**: All consumers using old path will break
- **Expected**: High risk score, consumers found

### Scenario 4: Non-Breaking - Add Optional Parameter
- **Change**: Adds optional `format` parameter to `GET /api/stocks/{id}`
- **Impact**: No breaking changes, backward compatible
- **Expected**: Low risk score, consumers still work

### Scenario 5: Breaking Change - Change Response Type
- **Change**: Changes response type from generic to `StockListResponse`
- **Impact**: Consumers expecting generic response will break
- **Expected**: Medium-High risk score

## Expected Output

For each scenario, you should see:

```
[SCENARIO] Breaking Change: Add Required Parameter
   File: backend-api-service/src/main/java/com/backendapi/StockController.java
   Expected: System should search all 3 consumer repos

[OK] Analysis Complete!
   Analysis ID: ...
   Type: api_contract_change

[*] API Changes Detected: 5
   - GET /api/stocks: ADDED
   - GET /api/stocks/{id}: ADDED
   - POST /api/stocks/buy: ADDED
   ...

[*] Consumers Found: X
   GET /api/stocks:
      [REPO] Sabarivasan-Velayutham/Stocks_Portfolio_Management (X files):
         - frontend/src/components/Portfolio.js (line 9)
         ...

[*] Risk Score: X/10 - LEVEL
```

## Configuration

Make sure your `.env` file has:

```bash
# Consumer repositories to search
API_CONSUMER_REPOSITORIES=Sabarivasan-Velayutham/Stocks_Portfolio_Management,Sabarivasan-Velayutham/auctioneer,Sabarivasan-Velayutham/MobileStore_Project

# Search method (clone or api)
CONSUMER_SEARCH_METHOD=clone

# Optional: GitHub token for API search method
# GITHUB_TOKEN=ghp_your_token_here
```

## Troubleshooting

### No Consumers Found
- Check if consumer repos actually use the API endpoints
- Verify repository names in `.env` are correct
- Check backend logs for search errors

### Rate Limit Errors
- If using `CONSUMER_SEARCH_METHOD=api`, add `GITHUB_TOKEN` to `.env`
- Or switch to `CONSUMER_SEARCH_METHOD=clone`

### Connection Errors
- Ensure backend is running on `http://localhost:8000`
- Check Docker container is up: `docker-compose ps`

