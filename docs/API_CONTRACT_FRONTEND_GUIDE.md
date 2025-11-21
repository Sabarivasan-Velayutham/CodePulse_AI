# API Contract Change Frontend Display

## Overview

The frontend now fully supports displaying API contract changes with detailed consumer information, including file paths, line numbers, and repository sources.

## Features

### 1. API Contract Change Card

When an API contract change is detected, the frontend displays:

- **Header**: Shows file name with 🔌 icon
- **Quick Stats**: 
  - API Changes count
  - Breaking Changes count (highlighted in red)
  - Affected Consumers count
  - Affected Endpoints count

### 2. Detailed View (Click "Show Details")

#### API Contract Changes Section
- Lists all API changes with:
  - HTTP Method (GET, POST, etc.)
  - Endpoint path
  - Change type (BREAKING, MODIFIED, ADDED)
  - Change details

#### Affected Consumers Section
- Groups consumers by API endpoint
- Shows repository source for each consumer
- Displays:
  - **File Path**: Full path to consumer file
  - **Line Number**: Exact line where API is used
  - **Context**: Code snippet showing API usage
  - **GitHub Link**: Direct link to file on GitHub (if available)

#### Analysis Summary
- Total changes
- Breaking changes
- Total consumers
- Affected endpoints

## Example Display

```
🔌 StockController.java
Risk: 7.5/10 - HIGH

Quick Stats:
- API Changes: 5
- Breaking Changes: 2
- Affected Consumers: 8
- Affected Endpoints: 3

[Show Details]

🔌 API Contract Changes (5)
  [POST] /api/stocks/buy [BREAKING]
    Added required accountId parameter
  
  [GET] /api/stocks/{id}/price [MODIFIED]
    Changed path to /api/stocks/{id}/current-price

👥 Affected Consumers (8)
  POST /api/stocks/buy:
    📦 Repository: Sabarivasan-Velayutham/Stocks_Portfolio_Management (3 files)
      - frontend/src/components/Portfolio.js (Line 45)
        fetch('/api/stocks/buy', { method: 'POST', ... })
      - frontend/src/services/stockService.js (Line 123)
        axios.post('/api/stocks/buy', data)
      - mobile/src/api/stockApi.ts (Line 67)
        http.post('/api/stocks/buy', payload)
    
    📦 Repository: Sabarivasan-Velayutham/auctioneer (2 files)
      - client/src/services/stockApi.js (Line 89)
        fetch('/api/stocks/buy', ...)
```

## Data Structure

The frontend expects API contract analysis results in this format:

```json
{
  "id": "analysis-id",
  "type": "api_contract_change",
  "timestamp": "2024-01-01T00:00:00",
  "file_path": "backend-api-service/src/main/java/com/backendapi/StockController.java",
  "risk_score": {
    "score": 7.5,
    "level": "HIGH",
    "color": "#fd7e14"
  },
  "api_changes": [
    {
      "method": "POST",
      "endpoint": "/api/stocks/buy",
      "change_type": "BREAKING",
      "details": "Added required accountId parameter"
    }
  ],
  "consumers": {
    "POST /api/stocks/buy": [
      {
        "file_path": "frontend/src/components/Portfolio.js",
        "line_number": 45,
        "context": "fetch('/api/stocks/buy', { method: 'POST', ... })",
        "source_repo": "Sabarivasan-Velayutham/Stocks_Portfolio_Management",
        "html_url": "https://github.com/owner/repo/blob/main/file.js#L45"
      }
    ]
  },
  "summary": {
    "total_changes": 5,
    "breaking_changes": 2,
    "total_consumers": 8,
    "affected_endpoints": 3
  },
  "ai_insights": {
    "summary": "...",
    "risks": [...],
    "recommendations": [...]
  }
}
```

## Testing

Use the test script to generate sample API contract changes:

```bash
# Run scenario 1 (breaking change)
python scripts/test_backend_api_change.py --scenario 1

# Run all scenarios
python scripts/test_backend_api_change.py --all
```

Then refresh the frontend dashboard to see the results!

## Visual Features

- **Color Coding**:
  - Breaking changes: Red background (#ffebee)
  - Non-breaking: Gray background (#f5f5f5)
  - Breaking changes badge: Red chip
  - Modified changes: Orange chip
  - Added changes: Green chip

- **Repository Grouping**: Consumers are grouped by repository for easy identification

- **Code Context**: Shows actual code snippet where API is used

- **GitHub Links**: Direct links to view files on GitHub (when available)

## Next Steps

1. Run test scenarios to generate API contract changes
2. View results in the frontend dashboard
3. Click "Show Details" to see full consumer information
4. Use for hackathon demo to show cross-repo consumer discovery!

