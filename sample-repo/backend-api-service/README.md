# Backend API Service

This is the **central backend API service** that provides common API endpoints consumed by multiple applications:

- **Stocks_Portfolio_Management** - Portfolio management frontend
- **auctioneer** - Auction platform
- **MobileStore_Project** - Mobile store application

## API Endpoints

### Stock Management APIs
- `GET /api/stocks` - Get all stocks
- `GET /api/stocks/{id}` - Get stock by ID
- `POST /api/stocks/buy` - Buy stock
- `POST /api/stocks/sell` - Sell stock

### Transaction APIs
- `GET /api/transactions` - Get all transactions
- `POST /api/transactions` - Create transaction
- `GET /api/transactions/{id}` - Get transaction by ID

### Account APIs
- `GET /api/accounts/{id}` - Get account details
- `POST /api/accounts` - Create account
- `PUT /api/accounts/{id}` - Update account

### Auction APIs (for auctioneer app)
- `GET /api/auctions` - Get all auctions
- `POST /api/auctions` - Create auction
- `POST /api/auctions/{id}/bid` - Place bid

### Product APIs (for MobileStore)
- `GET /api/products` - Get all products
- `GET /api/products/{id}` - Get product by ID
- `POST /api/products` - Create product

## Usage

When you make changes to API endpoints in this repository, CodePulse AI will:
1. Detect the API contract change
2. Search all consumer repositories (Stocks_Portfolio_Management, auctioneer, MobileStore_Project)
3. Find all code files that consume the changed API
4. Calculate impact and risk score
5. Show which teams/repos are affected

## Testing

Make a breaking change to any endpoint and trigger analysis:

```bash
# Example: Add required parameter to /api/stocks/buy
curl -X POST http://localhost:8000/api/v1/api/contract/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "src/main/java/com/backendapi/StockController.java",
    "repository": "backend-api-service",
    "diff": "- @PostMapping(\"/api/stocks/buy\")\n+ @PostMapping(\"/api/stocks/buy\")\n+ // Added required accountId parameter",
    "commit_sha": "test123",
    "github_repo_url": "https://github.com/your-org/backend-api-service"
  }'
```

