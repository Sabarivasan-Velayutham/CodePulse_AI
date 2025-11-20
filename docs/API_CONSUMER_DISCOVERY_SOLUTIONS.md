# API Consumer Discovery - Real-World Solutions

## The Problem

In real-world microservices architectures:
- **Backend API Team** owns the API service
- **Frontend Team** owns the web frontend
- **Mobile Team** owns mobile apps
- **Other Microservices Teams** own their services
- **External Partners** use your public API

**Challenge**: Backend team doesn't have access to consumer codebases!

---

## Current Implementation (Limitation)

**Current Approach**: Code analysis within a single repository
- ✅ Works for: Monorepos, same-team services
- ❌ Doesn't work for: Cross-team, cross-repo, external consumers

---

## Solutions for Real-World Scenarios

### Solution 1: **Multi-Repository Configuration** ⭐ (Recommended)

**How it works**:
- Configure multiple GitHub repositories in settings
- System searches across all configured repos
- Finds API consumers in any connected repository

**Implementation**:
```python
# Configuration
REPOSITORIES = [
    {"name": "backend-api", "url": "github.com/org/backend-api", "team": "backend"},
    {"name": "frontend-web", "url": "github.com/org/frontend-web", "team": "frontend"},
    {"name": "mobile-app", "url": "github.com/org/mobile-app", "team": "mobile"},
    {"name": "order-service", "url": "github.com/org/order-service", "team": "orders"}
]

# When API changes:
# 1. Search backend-api for API definition
# 2. Search ALL other repos for API usage
# 3. Report consumers from all repos
```

**Benefits**:
- ✅ Works across teams
- ✅ Automatic discovery
- ✅ No manual registration needed

**Limitations**:
- Requires access to all repositories
- May need GitHub organization permissions

---

### Solution 2: **API Consumer Registry** ⭐⭐ (Enterprise-Ready)

**How it works**:
- Teams register their services and API dependencies
- Maintains a registry: "Service X consumes API Y"
- Queries registry when API changes occur

**Implementation**:
```python
# Teams register their services
POST /api/v1/registry/register
{
  "service_name": "frontend-web",
  "team": "frontend",
  "consumed_apis": [
    {"endpoint": "/api/payments/process", "method": "POST"},
    {"endpoint": "/api/users/{id}", "method": "GET"}
  ],
  "repository_url": "github.com/org/frontend-web"
}

# When API changes:
# 1. Query registry for all services consuming this API
# 2. Notify affected teams
# 3. Show impact across all registered services
```

**Benefits**:
- ✅ Works without code access
- ✅ Teams self-register
- ✅ Supports external partners
- ✅ Can include contact info for notifications

**Limitations**:
- Requires manual registration (but can be automated via CI/CD)

---

### Solution 3: **Runtime API Gateway Integration** ⭐⭐⭐ (Most Accurate)

**How it works**:
- Integrate with API Gateway (Kong, AWS API Gateway, etc.)
- Monitor actual API calls at runtime
- Track which services call which endpoints
- Use this data for impact analysis

**Implementation**:
```python
# API Gateway webhook sends usage data
POST /api/v1/gateway/usage
{
  "endpoint": "/api/payments/process",
  "method": "POST",
  "consumers": [
    {"service": "frontend-web", "calls_per_day": 10000},
    {"service": "mobile-app", "calls_per_day": 5000},
    {"service": "order-service", "calls_per_day": 2000}
  ]
}

# When API changes:
# 1. Query gateway data for actual consumers
# 2. Show real usage statistics
# 3. Prioritize by call volume
```

**Benefits**:
- ✅ Most accurate (real usage data)
- ✅ Works for external consumers
- ✅ Shows actual impact (call volume)
- ✅ No code access needed

**Limitations**:
- Requires API Gateway integration
- May miss services that haven't called API yet

---

### Solution 4: **Hybrid Approach** (Best of All Worlds)

**Combines**:
1. **Code Analysis** - For repos you have access to
2. **Registry** - For teams to self-register
3. **API Gateway** - For runtime usage data
4. **OpenAPI/Swagger** - If teams publish specs

**Priority**:
1. Check API Gateway (most accurate)
2. Check Registry (manual but reliable)
3. Check Code Analysis (automatic for accessible repos)
4. Check OpenAPI specs (if available)

---

## Recommended Implementation for CodePulse AI

### Phase 1: Multi-Repository Support (Quick Win)

**Add to configuration**:
```python
# .env or config file
GITHUB_REPOSITORIES=backend-api,frontend-web,mobile-app,order-service
GITHUB_ORG=your-org-name
```

**Enhanced Consumer Discovery**:
```python
async def _find_all_consumers(self, contracts, repo_path):
    """Find consumers across all configured repositories"""
    consumers = {}
    
    # 1. Search in current repository
    consumers.update(self._search_in_repo(repo_path, contracts))
    
    # 2. Search in other configured repositories
    for repo_name in CONFIGURED_REPOS:
        other_repo_path = await self.github_fetcher.fetch_repository(
            f"{GITHUB_ORG}/{repo_name}", "main"
        )
        consumers.update(self._search_in_repo(other_repo_path, contracts))
    
    return consumers
```

### Phase 2: API Consumer Registry (Enterprise Feature)

**Add registry endpoints**:
```python
POST /api/v1/registry/register - Register service and API dependencies
GET /api/v1/registry/consumers/{endpoint} - Get all registered consumers
DELETE /api/v1/registry/unregister - Remove service registration
```

**Store in Neo4j**:
```cypher
// Service node
CREATE (s:Service {name: "frontend-web", team: "frontend"})

// API endpoint node
CREATE (api:APIEndpoint {endpoint: "/api/payments/process", method: "POST"})

// Registered consumer relationship
CREATE (s)-[:REGISTERED_CONSUMER]->(api)
```

### Phase 3: API Gateway Integration (Future)

**Integrate with**:
- AWS API Gateway
- Kong API Gateway
- Azure API Management
- Custom API Gateway

**Webhook from Gateway**:
```python
POST /api/v1/gateway/webhook
{
  "source": "api_gateway",
  "usage_data": {
    "/api/payments/process": {
      "consumers": [
        {"service": "frontend", "calls": 10000, "last_called": "2024-01-01"}
      ]
    }
  }
}
```

---

## How CodePulse AI Handles This

### Current Implementation:
- ✅ **Works for**: Same repository, monorepos
- ⚠️ **Limited for**: Cross-repo, cross-team

### Enhanced Implementation (Recommended):

#### Option A: Multi-Repository Configuration
```python
# Configuration
API_CONSUMER_REPOS = [
    "github.com/org/frontend-web",
    "github.com/org/mobile-app", 
    "github.com/org/order-service"
]

# When API changes:
# 1. Clone/search all configured repos
# 2. Find API usage in each
# 3. Aggregate results
```

#### Option B: API Consumer Registry
```python
# Teams register via API or CI/CD
# Registry stores: Service → API dependencies
# When API changes: Query registry for affected services
```

#### Option C: Hybrid (Best)
```python
# 1. Try code analysis (if repos accessible)
# 2. Check registry (if teams registered)
# 3. Use API Gateway data (if integrated)
# 4. Show all sources in results
```

---

## Real-World Example

### Scenario: Payment API Team

**Backend API Team** changes:
```java
POST /api/payments/process
// Added required parameter: cardNumber
```

**CodePulse AI with Multi-Repo**:
1. Searches `backend-api` repo → Finds API definition
2. Searches `frontend-web` repo → Finds 3 files using this API
3. Searches `mobile-app` repo → Finds 2 files using this API
4. Searches `order-service` repo → Finds 1 file using this API
5. **Result**: "6 consumers found across 3 repositories"

**CodePulse AI with Registry**:
1. Queries registry: "Who consumes `/api/payments/process`?"
2. Registry returns:
   - frontend-web (registered by Frontend Team)
   - mobile-app (registered by Mobile Team)
   - order-service (registered by Order Team)
3. **Result**: "3 registered consumers found"

**CodePulse AI with API Gateway**:
1. Queries API Gateway: "Which services call `/api/payments/process`?"
2. Gateway returns:
   - frontend-web: 10,000 calls/day
   - mobile-app: 5,000 calls/day
   - order-service: 2,000 calls/day
3. **Result**: "3 active consumers, 17,000 calls/day total"

---

## Implementation Priority

### For Hackathon (Quick Implementation):
1. ✅ **Multi-Repository Support** - Allow configuring multiple repos
2. ✅ **Enhanced Consumer Discovery** - Search across all repos
3. ⏳ **Registry Endpoints** - Basic registration API

### For Production (Full Solution):
1. ✅ Multi-Repository Support
2. ✅ API Consumer Registry
3. ✅ API Gateway Integration
4. ✅ OpenAPI/Swagger Integration
5. ✅ Team Notifications

---

## Code Changes Needed

### 1. Add Multi-Repository Configuration
```python
# backend/app/config.py
GITHUB_REPOSITORIES = os.getenv("GITHUB_REPOSITORIES", "").split(",")
GITHUB_ORG = os.getenv("GITHUB_ORG", "")
```

### 2. Enhance Consumer Discovery
```python
# In api_contract_orchestrator.py
async def _find_all_consumers(self, contracts, repo_path):
    all_consumers = {}
    
    # Search in current repo
    all_consumers.update(self._search_in_repo(repo_path, contracts))
    
    # Search in other configured repos
    for repo_name in GITHUB_REPOSITORIES:
        if repo_name:
            other_repo = await self.github_fetcher.fetch_repository(
                f"{GITHUB_ORG}/{repo_name}", "main"
            )
            all_consumers.update(self._search_in_repo(other_repo, contracts))
    
    return all_consumers
```

### 3. Add Registry Endpoints (Optional)
```python
# backend/app/api/registry.py
@router.post("/registry/register")
async def register_service(service: ServiceRegistration):
    # Store in Neo4j
    # Link service to API endpoints
```

---

## Summary

**Current State**: Works for same repository/monorepo

**Enhanced State**: 
- Multi-repository search (if repos accessible)
- API Consumer Registry (teams self-register)
- API Gateway integration (runtime data)

**Best Practice**: Use **Hybrid Approach**
- Code analysis for accessible repos
- Registry for cross-team services
- API Gateway for runtime validation

This makes CodePulse AI work in **real enterprise microservices** scenarios!

