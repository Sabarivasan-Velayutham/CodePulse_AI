# Backend API Service Setup Guide

## Overview

The **Backend API Service** (`sample-repo/backend-api-service`) is a central API service that provides common endpoints consumed by multiple applications:

- **Stocks_Portfolio_Management** - Portfolio management frontend
- **auctioneer** - Auction platform  
- **MobileStore_Project** - Mobile store application

When you make changes to this backend service, CodePulse AI automatically searches all consumer repositories to find affected code.

## Repository Structure

```
sample-repo/backend-api-service/
├── src/main/java/com/backendapi/
│   ├── StockController.java      # Stock management APIs
│   ├── TransactionController.java # Transaction APIs
│   ├── AccountController.java     # Account management APIs
│   ├── AuctionController.java     # Auction APIs (for auctioneer)
│   └── ProductController.java     # Product APIs (for MobileStore)
└── README.md
```

## API Endpoints

### Stock Management
- `GET /api/stocks` - Get all stocks
- `GET /api/stocks/{id}` - Get stock by ID
- `POST /api/stocks/buy` - Buy stock (consumed by all 3 apps)
- `POST /api/stocks/sell` - Sell stock
- `GET /api/stocks/{id}/price` - Get stock price

### Transactions
- `GET /api/transactions` - Get all transactions
- `POST /api/transactions` - Create transaction
- `GET /api/transactions/{id}` - Get transaction by ID
- `GET /api/transactions/account/{accountId}` - Get transactions by account

### Accounts
- `GET /api/accounts/{id}` - Get account details
- `POST /api/accounts` - Create account
- `PUT /api/accounts/{id}` - Update account
- `GET /api/accounts/{id}/balance` - Get account balance

### Auctions (for auctioneer)
- `GET /api/auctions` - Get all auctions
- `GET /api/auctions/{id}` - Get auction by ID
- `POST /api/auctions` - Create auction
- `POST /api/auctions/{id}/bid` - Place bid

### Products (for MobileStore)
- `GET /api/products` - Get all products
- `GET /api/products/{id}` - Get product by ID
- `POST /api/products` - Create product
- `PUT /api/products/{id}` - Update product

## How It Works

### Flow:

1. **You make a change** to an API endpoint in `backend-api-service`
   - Example: Add required parameter to `POST /api/stocks/buy`

2. **CodePulse AI detects** the API contract change
   - Extracts API definition from changed file
   - Identifies breaking changes

3. **System searches consumer repos**:
   - `Stocks_Portfolio_Management` - Finds frontend code using this API
   - `auctioneer` - Finds auction platform code using this API
   - `MobileStore_Project` - Finds mobile store code using this API

4. **Results show**:
   - Which files in which repos use this API
   - Exact line numbers and code context
   - Risk score based on breaking changes and consumer count
   - Recommendations for migration

## Testing

### Option 1: Use Test Script

```bash
# Run the test script
python scripts/test_backend_api_change.py
```

This simulates a breaking change to `POST /api/stocks/buy` and shows:
- API changes detected
- Consumers found in all 3 repos
- Risk score and recommendations

### Option 2: Manual API Call

```bash
curl -X POST http://localhost:8000/api/v1/api/contract/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "src/main/java/com/backendapi/StockController.java",
    "repository": "backend-api-service",
    "diff": "- // Required fields: stockId, quantity\n+ // Required fields: stockId, quantity, accountId",
    "commit_sha": "test123",
    "github_repo_url": "https://github.com/Sabarivasan-Velayutham/backend-api-service"
  }'
```

### Option 3: Real Git Commit

1. **Make a change** to `StockController.java`:
   ```java
   // BEFORE
   @PostMapping("/buy")
   public ResponseEntity<?> buyStock(@RequestBody Map<String, Object> request) {
       // Required fields: stockId, quantity
   }
   
   // AFTER (Breaking change)
   @PostMapping("/buy")
   public ResponseEntity<?> buyStock(@RequestBody Map<String, Object> request) {
       // Required fields: stockId, quantity, accountId  // NEW!
   }
   ```

2. **Commit and push** to GitHub

3. **Trigger analysis** via webhook or manual API call

4. **Check results** - System will search all 3 consumer repos

## Expected Results

When you make a breaking change, you should see:

```
🔍 Searching for API consumers...
   Current repository: backend-api-service
   Additional repositories to search: 3

   📥 Fetching repository: https://github.com/Sabarivasan-Velayutham/Stocks_Portfolio_Management.git
   ✅ Found 2 consumers in Stocks_Portfolio_Management

   📥 Fetching repository: https://github.com/Sabarivasan-Velayutham/auctioneer.git
   ✅ Found 1 consumers in auctioneer

   📥 Fetching repository: https://github.com/Sabarivasan-Velayutham/MobileStore_Project.git
   ✅ Found 1 consumers in MobileStore_Project

   ✅ Found 4 API consumers across 1 endpoints
      Searched 4 repositories/sources
```

## Configuration

Make sure your `.env` file has:

```bash
GITHUB_ORG=Sabarivasan-Velayutham
API_CONSUMER_REPOSITORIES=Stocks_Portfolio_Management,auctioneer,MobileStore_Project
SEARCH_ALL_REPOS_FOR_CONSUMERS=true
```

## Example Scenarios

### Scenario 1: Breaking Change
**Change**: Add required `accountId` parameter to `POST /api/stocks/buy`

**Impact**:
- Stocks_Portfolio_Management: 2 files affected
- auctioneer: 1 file affected
- MobileStore_Project: 1 file affected

**Result**: Risk Score 8.5/10 (CRITICAL) - 4 consumers need updates

### Scenario 2: Non-Breaking Change
**Change**: Add optional `notes` field to `POST /api/transactions`

**Impact**: None (optional field)

**Result**: Risk Score 2.0/10 (LOW) - Safe to deploy

### Scenario 3: Endpoint Removal
**Change**: Remove `GET /api/products/{id}/reviews`

**Impact**: MobileStore_Project: 1 file affected

**Result**: Risk Score 7.0/10 (HIGH) - Breaking change, 1 consumer affected

## Benefits

✅ **Centralized API Management** - All API changes in one place
✅ **Automatic Consumer Discovery** - Finds all affected code automatically
✅ **Cross-Team Impact Analysis** - Shows which teams are affected
✅ **Risk Assessment** - Calculates risk based on breaking changes and consumers
✅ **Migration Guidance** - Provides recommendations for updating consumers

## Next Steps

1. ✅ Backend API service created
2. ✅ Test script ready
3. ⏳ Make a real API change and test
4. ⏳ Verify consumers are found in all 3 repos
5. ⏳ Check risk score and recommendations

This setup simulates a **real-world microservices architecture** where a backend API team owns the service, and multiple frontend/mobile teams consume it!

