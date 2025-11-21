# Test Scenarios Summary

## Overview

The test script now includes **6 scenarios** that test API contract change detection across all 3 consumer repositories:

- **Scenarios 1-3**: WITH consumer impact (endpoints used by consumer repos)
- **Scenarios 4-6**: WITHOUT consumer impact (endpoints not used by any repo)

---

## Scenarios WITH Consumer Impact

### Scenario 1: Change GET /api/stocks Response
- **File**: `StockController.java`
- **Change**: Response changed from array to `StockListResponse` object (BREAKING)
- **Expected Consumer**: `Stocks_Portfolio_Management` (Portfolio.js uses `axios.get('/api/stocks')`)
- **Impact**: HIGH - Frontend will break when expecting array but receiving object

### Scenario 2: Add Required Parameter to POST /api/auctions/{id}/bid
- **File**: `AuctionController.java`
- **Change**: Added required `paymentMethod` parameter (BREAKING)
- **Expected Consumer**: `auctioneer` (uses this endpoint for bidding)
- **Impact**: HIGH - Bidding functionality will fail without the new parameter

### Scenario 3: Change GET /api/products Response Structure
- **File**: `ProductController.java`
- **Change**: Response changed from array to `ProductListResponse` object (BREAKING)
- **Expected Consumer**: `MobileStore_Project` (uses this endpoint for product catalog)
- **Impact**: HIGH - Product listing will break when expecting array but receiving object

---

## Scenarios WITHOUT Consumer Impact

### Scenario 4: Add Required Parameter to POST /api/stocks/buy
- **File**: `StockController.java`
- **Change**: Added required `verificationCode` parameter (BREAKING)
- **Expected Consumers**: **None** (endpoint not used by any consumer repo)
- **Impact**: LOW - Breaking change but no consumers affected

### Scenario 5: Change GET /api/transactions/account/{accountId} Path
- **File**: `TransactionController.java`
- **Change**: Path changed from `/account/{accountId}` to `/by-account/{accountId}` (BREAKING)
- **Expected Consumers**: **None** (endpoint not used by any consumer repo)
- **Impact**: LOW - Breaking change but no consumers affected

### Scenario 6: Remove Required Field from PUT /api/accounts/{id}
- **File**: `AccountController.java`
- **Change**: Made `email` field optional (previously required) (BREAKING)
- **Expected Consumers**: **None** (endpoint not used by any consumer repo)
- **Impact**: LOW - Breaking change but no consumers affected

---

## Usage

### Run a specific scenario:
```bash
python scripts/test_backend_api_change.py --scenario 1
```

### Run all scenarios:
```bash
python scripts/test_backend_api_change.py --all
```

### Expected Results

**Scenarios 1-3 (WITH IMPACT)**:
- ✅ Should find consumers in respective repositories
- ✅ Risk score: HIGH (5.5-7.5/10) or CRITICAL (7.5-10/10)
- ✅ AI insights should identify breaking changes and recommend fixes

**Scenarios 4-6 (NO IMPACT)**:
- ✅ Should find 0 consumers
- ✅ Risk score: MEDIUM (3.5-5.5/10) - breaking change but no consumers
- ✅ AI insights should still identify breaking changes but note no current consumers

---

## Backend Service Code Updates

All backend service controller files have been updated with comments indicating:
- Which scenarios test which endpoints
- Whether endpoints are used by consumer repos
- What breaking changes are being tested

### Updated Files:
1. `StockController.java` - Scenarios 1 & 4
2. `AuctionController.java` - Scenario 2
3. `ProductController.java` - Scenario 3
4. `TransactionController.java` - Scenario 5
5. `AccountController.java` - Scenario 6

---

## Testing Strategy

This setup allows you to:

1. **Test consumer discovery**: Scenarios 1-3 verify that the system correctly finds consumers across different repos
2. **Test breaking change detection**: All scenarios test breaking change detection
3. **Test impact assessment**: Compare risk scores between scenarios with and without consumers
4. **Test cross-repo search**: Verify that all 3 consumer repos are searched correctly

---

## Next Steps

1. **Add actual API usage** to consumer repos (if needed):
   - Add `POST /api/auctions/{id}/bid` usage to `auctioneer` repo
   - Add `GET /api/products` usage to `MobileStore_Project` repo
   - (Portfolio.js already uses `GET /api/stocks`)

2. **Run tests** to verify:
   - Consumer discovery works correctly
   - Breaking changes are detected
   - Risk scores reflect consumer impact
   - AI insights provide actionable recommendations

3. **Compare results**:
   - Scenarios 1-3 should show consumers and higher risk scores
   - Scenarios 4-6 should show 0 consumers but still detect breaking changes

