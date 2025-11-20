# Multi-Repository API Consumer Discovery Setup

## Overview

CodePulse AI can now discover API consumers across **multiple repositories**, enabling cross-team consumer discovery in microservices architectures.

## Configuration

### Environment Variables

Add to your `.env` file:

```bash
# GitHub Organization (optional, will be prepended to repo names)
GITHUB_ORG=your-org-name

# List of repositories to search for API consumers
# Format: "owner/repo" or just "repo-name" (if GITHUB_ORG is set)
API_CONSUMER_REPOSITORIES=frontend-web,mobile-app,order-service,notification-service

# Or use the general GitHub repositories list
GITHUB_REPOSITORIES=backend-api,frontend-web,mobile-app,order-service

# Enable/disable cross-repo search (default: true)
SEARCH_ALL_REPOS_FOR_CONSUMERS=true
```

### Example Configuration

**Scenario**: Backend API team wants to find all consumers of their API across different team repositories.

```bash
# .env
GITHUB_ORG=acme-corp
API_CONSUMER_REPOSITORIES=frontend-web,mobile-app-ios,mobile-app-android,order-service,payment-service,notification-service
SEARCH_ALL_REPOS_FOR_CONSUMERS=true
```

This will search:
- `acme-corp/frontend-web`
- `acme-corp/mobile-app-ios`
- `acme-corp/mobile-app-android`
- `acme-corp/order-service`
- `acme-corp/payment-service`
- `acme-corp/notification-service`

## How It Works

### Flow:

1. **API Change Detected** in `backend-api` repository
2. **Extract API Contracts** from changed file
3. **Search Current Repo** for consumers
4. **Search All Configured Repos** for consumers:
   - Clones/searches each configured repository
   - Finds API usage patterns (fetch, axios, http calls, etc.)
   - Aggregates results
5. **Store in Neo4j** with source repository information
6. **Report Results** showing consumers from all repositories

### Example Output:

```
🔍 Searching for API consumers...
   Current repository: /tmp/github_repos/acme-corp_backend-api
   Additional repositories to search: 6

   ✅ Found 3 consumers in acme-corp/frontend-web
   ✅ Found 2 consumers in acme-corp/mobile-app-ios
   ✅ Found 1 consumers in acme-corp/order-service
   ✅ Found 0 consumers in acme-corp/payment-service
   ✅ Found 0 consumers in acme-corp/notification-service

   ✅ Found 6 API consumers across 1 endpoints
      Searched 4 repositories/sources
```

## Benefits

### ✅ Cross-Team Discovery
- Backend team can discover consumers in frontend, mobile, and other microservices
- No need for manual registration
- Automatic discovery across all configured repos

### ✅ Real-Time Updates
- Searches latest code from all repositories
- Updates when consumers change
- Shows current state of API usage

### ✅ Source Tracking
- Each consumer is tagged with source repository
- Know which team owns each consumer
- Easy to identify affected teams

## Limitations

### ⚠️ Repository Access Required
- Requires read access to all configured repositories
- May need GitHub organization permissions
- Private repos require authentication

### ⚠️ Performance
- Cloning/searching multiple repos takes time
- Consider caching strategies for large organizations
- May need rate limiting for GitHub API

## Alternative: API Consumer Registry

If you can't access all repositories, use the **API Consumer Registry** approach:

1. Teams register their services and API dependencies
2. System queries registry instead of searching code
3. Works without code access

See `API_CONSUMER_DISCOVERY_SOLUTIONS.md` for details.

## Best Practices

### 1. Start Small
- Begin with 2-3 most critical consumer repositories
- Expand as needed

### 2. Use Caching
- Repositories are cached locally
- Updates are incremental (git pull)
- Reduces clone time

### 3. Organize by Team
- Group repositories by team ownership
- Makes it easier to notify affected teams

### 4. Monitor Performance
- Track search time across repos
- Consider async/parallel searches for large orgs

## Example: Real-World Scenario

### Setup:
- **Backend API Team** owns `backend-api` repository
- **Frontend Team** owns `frontend-web` repository  
- **Mobile Team** owns `mobile-app` repository
- **Order Team** owns `order-service` repository

### Configuration:
```bash
GITHUB_ORG=acme-corp
API_CONSUMER_REPOSITORIES=frontend-web,mobile-app,order-service
```

### When Backend API Changes:
1. CodePulse AI detects change in `backend-api`
2. Searches `backend-api` → Finds API definition
3. Searches `frontend-web` → Finds 3 consumers
4. Searches `mobile-app` → Finds 2 consumers
5. Searches `order-service` → Finds 1 consumer
6. **Result**: "6 consumers found across 3 repositories"

### Impact Report:
```
API Change: POST /api/payments/process
Breaking Change: Required parameter 'cardNumber' added

Affected Consumers:
- frontend-web (3 files)
  - src/payment/PaymentForm.jsx (line 45)
  - src/checkout/CheckoutPage.jsx (line 123)
  - src/api/paymentClient.js (line 67)
  
- mobile-app (2 files)
  - services/PaymentService.swift (line 89)
  - views/PaymentView.swift (line 156)
  
- order-service (1 file)
  - src/payment/PaymentClient.java (line 45)

Total Impact: 6 consumers across 3 teams
Risk Level: CRITICAL
```

## Troubleshooting

### Issue: "Failed to search repository"
- **Cause**: No access to repository
- **Solution**: Check GitHub permissions or use registry approach

### Issue: "Repository not found"
- **Cause**: Incorrect repository name or organization
- **Solution**: Verify repository path format: `owner/repo` or `repo-name` (if GITHUB_ORG set)

### Issue: "Search taking too long"
- **Cause**: Too many repositories or large codebases
- **Solution**: Reduce number of repos or implement parallel search

## Next Steps

1. **Configure repositories** in `.env`
2. **Test with one API change**
3. **Verify consumers are found** across repos
4. **Expand configuration** as needed

For production, consider implementing:
- API Consumer Registry (for external/restricted repos)
- API Gateway Integration (for runtime usage data)
- Team Notifications (alert affected teams)

