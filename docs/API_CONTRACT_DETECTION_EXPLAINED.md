# API Contract Change Detection - Complete Guide

## What is an API Contract?

An **API Contract** is a formal specification that defines:
- **What endpoints exist** (e.g., `/api/users`, `/api/payments`)
- **What data they accept** (request parameters, body structure)
- **What data they return** (response format, status codes)
- **How to call them** (HTTP methods, authentication)

Think of it as a "promise" between the API provider and consumers about how the API works.

---

## Real-World Example: Banking API

### Scenario: Payment Processing API

**API Provider** (Backend Team):
```java
// PaymentController.java
@RestController
@RequestMapping("/api/payments")
public class PaymentController {
    
    @PostMapping("/process")
    public PaymentResponse processPayment(@RequestBody PaymentRequest request) {
        // Process payment
        return new PaymentResponse(amount, status, transactionId);
    }
}
```

**API Contract** (What this defines):
```
POST /api/payments/process
Request Body:
{
  "amount": 100.00,
  "currency": "USD",
  "accountId": "12345"
}

Response:
{
  "transactionId": "txn_abc123",
  "status": "success",
  "amount": 100.00
}
```

**API Consumers** (Other services that use this API):
1. **Mobile App** - Calls this API when user makes a payment
2. **Web Frontend** - Calls this API for checkout
3. **Fraud Detection Service** - Calls this API to verify transactions
4. **Reporting Service** - Calls this API to get payment data

---

## What is API Contract Change Detection?

**API Contract Change Detection** automatically identifies when API contracts change and determines if those changes will break existing consumers.

### Example: Breaking Change

#### Before (Original API):
```java
@PostMapping("/process")
public PaymentResponse processPayment(
    @RequestBody PaymentRequest request  // Has: amount, currency, accountId
) {
    // ...
}
```

#### After (Changed API):
```java
@PostMapping("/process")
public PaymentResponse processPayment(
    @RequestBody PaymentRequest request  // Now requires: amount, currency, accountId, cardNumber
) {
    // Developer added required field: cardNumber
}
```

**This is a BREAKING CHANGE** because:
- Old consumers send: `{amount, currency, accountId}`
- New API requires: `{amount, currency, accountId, cardNumber}`
- Result: **All existing consumers will fail!**

---

## Who Uses API Contracts?

### 1. **Microservices Teams**
- **Problem**: Multiple services communicate via APIs
- **Need**: Know when API changes break other services
- **Example**: Payment service changes API → Order service breaks

### 2. **Frontend Developers**
- **Problem**: Frontend depends on backend API structure
- **Need**: Know when backend changes break frontend
- **Example**: Backend removes field → Frontend shows errors

### 3. **Mobile App Developers**
- **Problem**: Mobile apps depend on backend APIs
- **Need**: Know when API changes require app updates
- **Example**: API changes response format → App crashes

### 4. **Third-Party Integrators**
- **Problem**: External partners use your API
- **Need**: Know when changes affect partners
- **Example**: API version change → Partner integrations break

### 5. **DevOps/Platform Teams**
- **Problem**: Need to prevent breaking changes in production
- **Need**: Automated detection and blocking
- **Example**: Block deployment if breaking change detected

---

## Types of API Contract Changes

### 1. **Breaking Changes** (Will Break Consumers) ❌

#### a) Removed Endpoint
```java
// BEFORE
@GetMapping("/users/{id}")
public User getUser(@PathVariable String id) { ... }

// AFTER
// Endpoint removed entirely
```
**Impact**: All consumers calling `/api/users/{id}` will get 404 errors

#### b) Changed Request Structure
```java
// BEFORE
@PostMapping("/payments")
public Response createPayment(@RequestBody PaymentRequest req) {
    // req has: {amount, currency}
}

// AFTER
@PostMapping("/payments")
public Response createPayment(@RequestBody PaymentRequest req) {
    // req now REQUIRES: {amount, currency, cardNumber}  // NEW REQUIRED FIELD
}
```
**Impact**: Consumers not sending `cardNumber` will get validation errors

#### c) Changed Response Structure
```java
// BEFORE
return {
    "transactionId": "123",
    "status": "success"
}

// AFTER
return {
    "id": "123",           // Field renamed!
    "status": "success",
    "timestamp": "2024-01-01"  // New field (OK, but renaming breaks consumers)
}
```
**Impact**: Consumers expecting `transactionId` will fail

#### d) Changed HTTP Method
```java
// BEFORE
@GetMapping("/users/{id}")  // GET request

// AFTER
@PostMapping("/users/{id}")  // Changed to POST
```
**Impact**: Consumers using GET will get 405 Method Not Allowed

### 2. **Non-Breaking Changes** (Safe) ✅

#### a) Added Optional Field
```java
// BEFORE
return { "id": "123", "name": "John" }

// AFTER
return { "id": "123", "name": "John", "email": "john@example.com" }  // New optional field
```
**Impact**: None - old consumers still work

#### b) Added New Endpoint
```java
// BEFORE
@GetMapping("/users/{id}")

// AFTER
@GetMapping("/users/{id}")
@GetMapping("/users/{id}/profile")  // New endpoint added
```
**Impact**: None - doesn't affect existing endpoints

#### c) Added Optional Request Parameter
```java
// BEFORE
@GetMapping("/users")
public List<User> getUsers() { ... }

// AFTER
@GetMapping("/users")
public List<User> getUsers(@RequestParam(required=false) String filter) { ... }
```
**Impact**: None - parameter is optional

---

## How CodePulse AI Detects API Contract Changes

### Step 1: Parse API Definitions from Code

**Input**: Code files (Java, Python, JavaScript, etc.)

**Example - Spring Boot (Java)**:
```java
@RestController
@RequestMapping("/api/payments")
public class PaymentController {
    
    @PostMapping("/process")
    public PaymentResponse processPayment(@RequestBody PaymentRequest request) {
        // ...
    }
}
```

**CodePulse AI Extracts**:
- Endpoint: `POST /api/payments/process`
- Request Type: `PaymentRequest`
- Response Type: `PaymentResponse`
- Method: `processPayment`

### Step 2: Compare Before/After

**Before Commit**:
```
POST /api/payments/process
Request: PaymentRequest {amount, currency, accountId}
Response: PaymentResponse {transactionId, status}
```

**After Commit**:
```
POST /api/payments/process
Request: PaymentRequest {amount, currency, accountId, cardNumber}  // NEW REQUIRED FIELD
Response: PaymentResponse {transactionId, status}
```

**Detection**: Breaking change detected! `cardNumber` is now required.

### Step 3: Find All Consumers

**CodePulse AI searches codebase for**:
```javascript
// Frontend code
fetch('/api/payments/process', {
    method: 'POST',
    body: JSON.stringify({
        amount: 100,
        currency: 'USD',
        accountId: '123'
        // Missing cardNumber! Will break!
    })
})
```

**Finds**:
- 3 frontend files using this endpoint
- 2 mobile app services
- 1 internal microservice

### Step 4: Calculate Impact

**Risk Score**: HIGH (7.5/10)
- Breaking change detected
- 6 consumers affected
- Payment processing (critical domain)

**Recommendation**: 
- Add `cardNumber` as optional first
- Deprecate old version
- Provide migration guide

---

## Real-World Scenarios

### Scenario 1: Microservices Architecture

**Setup**:
- **Order Service** → calls → **Payment Service** API
- **Inventory Service** → calls → **Payment Service** API
- **Notification Service** → calls → **Payment Service** API

**Change**: Payment Service removes `/api/payments/refund` endpoint

**Without CodePulse AI**:
- ❌ Order Service breaks (tries to call refund)
- ❌ Production incident
- ❌ Hours of debugging
- ❌ Customer complaints

**With CodePulse AI**:
- ✅ Detects breaking change immediately
- ✅ Shows all 3 services affected
- ✅ Blocks deployment
- ✅ Suggests: Keep endpoint, mark as deprecated

### Scenario 2: Frontend-Backend Integration

**Setup**:
- React Frontend → calls → Node.js Backend API
- Mobile App → calls → Node.js Backend API

**Change**: Backend changes response field name:
```javascript
// Before
{ userId: "123", name: "John" }

// After
{ id: "123", name: "John" }  // userId → id
```

**Without CodePulse AI**:
- ❌ Frontend shows "undefined" for user ID
- ❌ Mobile app crashes
- ❌ Users can't log in
- ❌ Production outage

**With CodePulse AI**:
- ✅ Detects field rename
- ✅ Finds 2 frontend files using `userId`
- ✅ Shows exact code locations
- ✅ Suggests: Keep both fields during transition

### Scenario 3: Third-Party Integration

**Setup**:
- Partner Company → uses → Your Public API
- Your Mobile App → uses → Your Public API

**Change**: You add required authentication header

**Without CodePulse AI**:
- ❌ Partner integrations break
- ❌ Contract violations
- ❌ Legal issues
- ❌ Lost partnerships

**With CodePulse AI**:
- ✅ Detects authentication requirement change
- ✅ Identifies external consumers
- ✅ Suggests: Version API (v1, v2)
- ✅ Provides migration timeline

---

## Benefits of API Contract Detection

### 1. **Prevent Production Incidents**
- Catch breaking changes before deployment
- Avoid customer-facing errors
- Reduce downtime

### 2. **Save Development Time**
- Automatic detection vs. manual testing
- Immediate feedback vs. debugging in production
- Clear migration path

### 3. **Improve Team Communication**
- Visual impact graph shows affected services
- Clear documentation of changes
- Better coordination across teams

### 4. **Maintain API Stability**
- Enforce backward compatibility
- Version APIs properly
- Smooth deprecation process

---

## How CodePulse AI is Different

### Existing Tools:
- ❌ Require manual OpenAPI spec maintenance
- ❌ Only check at CI/CD time
- ❌ Don't find consumers automatically
- ❌ Limited to REST APIs

### CodePulse AI:
- ✅ **Automatic**: Parses code directly, no manual specs
- ✅ **Real-Time**: Detects changes as code is committed
- ✅ **Smart Discovery**: Uses dependency graph to find all consumers
- ✅ **Multi-Protocol**: REST, GraphQL, gRPC support
- ✅ **Visual**: Interactive graph showing API → Consumer relationships
- ✅ **AI-Powered**: Repository-specific recommendations

---

## Example: Complete Flow

### 1. Developer Makes Change
```java
// Changed PaymentController.java
@PostMapping("/process")
public PaymentResponse processPayment(
    @RequestBody PaymentRequest request  // Added: @Valid annotation
) {
    // Added validation: cardNumber is now required
}
```

### 2. CodePulse AI Detects Change
```
🔍 Analyzing API Contract Changes...

📊 Detected Changes:
   Endpoint: POST /api/payments/process
   Change Type: BREAKING
   Reason: Required field added (cardNumber)

⚠️  Breaking Change Detected!
```

### 3. Finds Consumers
```
🔗 Found 6 Consumers:

1. Frontend/src/payment/PaymentForm.jsx (Line 45)
   - Missing: cardNumber field
   - Risk: HIGH

2. MobileApp/services/PaymentService.swift (Line 123)
   - Missing: cardNumber field
   - Risk: HIGH

3. OrderService/src/payment/PaymentClient.java (Line 67)
   - Missing: cardNumber field
   - Risk: CRITICAL (production service)

... (3 more)
```

### 4. Calculates Risk
```
📈 Risk Score: 8.5/10 (CRITICAL)

Breakdown:
- Breaking Change: 3.0/3.0
- Affected Consumers: 6 services
- Domain Criticality: Payment processing (HIGH)
- AI Analysis: High risk of production failure
```

### 5. Provides Recommendations
```
💡 Recommendations:

1. Make cardNumber optional initially
   - Add @RequestParam(required=false) or make field optional
   - Allows gradual migration

2. Version the API
   - Keep /api/v1/payments/process (old)
   - Add /api/v2/payments/process (new)
   - Deprecate v1 after migration

3. Update Consumers First
   - Update all 6 consumers before deploying API change
   - Coordinate with frontend, mobile, and order service teams

4. Add Feature Flag
   - Use feature flag to toggle new validation
   - Roll back easily if issues occur
```

### 6. Visual Graph
```
[Payment API] ──→ [Frontend]
                └─→ [Mobile App]
                └─→ [Order Service]
                └─→ [Notification Service]
                └─→ [Reporting Service]
                └─→ [Partner Integration]
```

---

## Summary

**API Contract Change Detection** is about:
1. **Understanding** what your API promises to consumers
2. **Detecting** when those promises change
3. **Identifying** who will be affected
4. **Preventing** breaking changes from reaching production

**CodePulse AI** makes this:
- ✅ **Automatic** (no manual work)
- ✅ **Real-Time** (immediate feedback)
- ✅ **Comprehensive** (finds all consumers)
- ✅ **Visual** (easy to understand)
- ✅ **Actionable** (clear next steps)

This is critical for:
- Microservices architectures
- Frontend-backend teams
- Mobile app development
- Third-party integrations
- Production stability

