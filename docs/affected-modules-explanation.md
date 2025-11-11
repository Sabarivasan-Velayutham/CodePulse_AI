# Understanding "Affected Modules" in CodePulse AI Dashboard

## What are "Affected Modules"?

**Affected Modules** are files/modules that **will be impacted** by your code change. These are files that **depend on** the file you changed (also called **reverse dependencies**).

### Key Concept:
- **You changed**: `AccountBalance.java`
- **Affected Modules**: Files that **use** `AccountBalance.java` and will be affected by your change

---

## Real-World Example: Changing `AccountBalance.java`

### Scenario
You modify `AccountBalance.java` to change how balance is calculated (e.g., including pending transactions).

### Your Change:
```java
// AccountBalance.java (YOU CHANGED THIS)
public class AccountBalance {
    public double getBalance(String accountId) {
        // NEW LOGIC: Include pending transactions
        // ... your changes here ...
    }
}
```

### Affected Modules (Files that USE AccountBalance):

#### 1. PaymentProcessor.java
```java
// PaymentProcessor.java (AFFECTED MODULE #1)
import com.bank.account.AccountBalance;  // ← Uses AccountBalance

public class PaymentProcessor {
    private AccountBalance accountBalance;  // ← Depends on AccountBalance
    
    public PaymentResult processPayment(Payment payment) {
        // Step 1: Check if account has enough balance
        double currentBalance = accountBalance.getBalance(payment.getAccountId());  // ← CALLS YOUR CHANGED METHOD
        
        if (currentBalance < payment.getAmount()) {
            return PaymentResult.failed("Insufficient funds");
        }
        // ... rest of payment processing ...
    }
}
```

**Why it's affected**: 
- `PaymentProcessor` calls `accountBalance.getBalance()` 
- If you change how balance is calculated, `PaymentProcessor` might get different results
- This could break payment processing logic!

#### 2. OverdraftManager.java
```java
// OverdraftManager.java (AFFECTED MODULE #2)
import com.bank.account.AccountBalance;  // ← Uses AccountBalance

public class OverdraftManager {
    public boolean isEligibleForOverdraft(String accountId) {
        AccountBalance balance = new AccountBalance();  // ← USES YOUR CHANGED CLASS
        double currentBalance = balance.getBalance(accountId);  // ← CALLS YOUR CHANGED METHOD
        
        // Business logic based on balance
        if (currentBalance < 0) {
            return false;  // Already overdrawn
        }
        return currentBalance < 1000;  // Eligible if balance is low
    }
}
```

**Why it's affected**:
- `OverdraftManager` uses `AccountBalance` to check eligibility
- If balance calculation changes, overdraft decisions might be wrong
- This could cause financial issues!

#### 3. AccountService.java (Indirectly Affected)
```java
// AccountService.java (INDIRECTLY AFFECTED)
import com.bank.payment.PaymentProcessor;  // ← Uses PaymentProcessor

public class AccountService {
    private PaymentProcessor paymentProcessor;  // ← Uses PaymentProcessor
    
    public void transferFunds(String fromAccount, String toAccount, double amount) {
        // Uses PaymentProcessor, which uses AccountBalance
        PaymentResult result = paymentProcessor.processPayment(...);
        // ...
    }
}
```

**Why it's indirectly affected**:
- `AccountService` uses `PaymentProcessor`
- `PaymentProcessor` uses `AccountBalance` (your changed file)
- So `AccountService` is indirectly affected

---

## Dashboard Display

### On the Dashboard Card:
```
AccountBalance.java
Risk Score: 5.5/10 (HIGH)
Direct Dependencies: 4
Indirect Dependencies: 1
Affected Modules: 2  ← THIS IS WHAT WE'RE EXPLAINING
```

### What "Affected Modules: 2" Means:
- **2 files** will be impacted by your change to `AccountBalance.java`
- These are: `PaymentProcessor.java` and `OverdraftManager.java`
- These files **must be tested** before deploying your change

---

## Visual Representation

```
                    AccountBalance.java
                    (YOUR CHANGE)
                           │
                           │
        ┌──────────────────┴──────────────────┐
        │                                      │
   DIRECT DEPENDENCIES              AFFECTED MODULES
   (what you use)                    (what uses you)
        │                                      │
        ↓                                      ↓
   TransactionDAO.java              PaymentProcessor.java ← AFFECTED
        │                                      │
        ↓                                      │
   DatabaseConnection.java          OverdraftManager.java ← AFFECTED
```

**Legend**:
- **Solid gray arrows (→)**: Direct dependencies (what `AccountBalance` uses)
- **Dashed red arrows (←)**: Affected modules (what uses `AccountBalance`)

---

## Why "Affected Modules" is Critical

### 1. **Breaking Changes Risk**
If you change `AccountBalance.getBalance()` to return a different value:
- `PaymentProcessor` might reject valid payments
- `OverdraftManager` might make wrong decisions
- **Result**: System breaks, customers affected!

### 2. **Testing Requirements**
You must test:
- ✅ Your changed file (`AccountBalance.java`)
- ✅ **All affected modules** (`PaymentProcessor`, `OverdraftManager`)
- ✅ Integration tests for the full flow

### 3. **Deployment Planning**
- **High number of affected modules** = Higher risk
- **Critical modules affected** (like PaymentProcessor) = **VERY HIGH RISK**
- May need:
  - More thorough testing
  - Staged rollout
  - Rollback plan

---

## Example: High-Risk Scenario

### Change: Modify `PaymentProcessor.java` fee calculation

**Affected Modules:**
1. `PaymentAPI.java` - Exposes payment endpoints
2. `NotificationService.java` - Sends fee notifications
3. `BillingService.java` - Calculates monthly fees
4. `ReportGenerator.java` - Generates payment reports

**Impact:**
- **4 affected modules** = High risk
- All are critical business components
- **Risk Level**: **CRITICAL** ⚠️

**Action Required:**
- ✅ Test all 4 affected modules
- ✅ Run integration tests
- ✅ Review with team before deployment
- ✅ Plan for rollback if issues occur

---

## Example: Low-Risk Scenario

### Change: Add logging to `AccountBalance.java`

**Affected Modules:**
- None (or very few)

**Impact:**
- **0-1 affected modules** = Low risk
- Logging doesn't change behavior
- **Risk Level**: **LOW** ✅

**Action Required:**
- ✅ Basic testing of your change
- ✅ Verify logs appear correctly
- ✅ Can deploy with less concern

---

## Summary Table

| Metric | Meaning | Example |
|--------|---------|---------|
| **Direct Dependencies** | Files your changed file uses | `AccountBalance` → `TransactionDAO` |
| **Indirect Dependencies** | Files used through direct deps | `AccountBalance` → `TransactionDAO` → `DatabaseConnection` |
| **Affected Modules** | Files that use your changed file | `PaymentProcessor` → `AccountBalance` (YOUR CHANGE) |

---

## Key Takeaway

**Affected Modules = Files that will break if your change is wrong!**

- **High count** = More things to test
- **Critical modules** = Higher risk
- **Always test affected modules** before deployment

The dashboard shows this count so you know:
1. How many files need testing
2. The scope of your change's impact
3. The risk level of your deployment

---

## How to Use This Information

1. **Before making changes**: Check affected modules to understand impact
2. **During development**: Test affected modules
3. **Before deployment**: Verify all affected modules work correctly
4. **After deployment**: Monitor affected modules for issues

**Remember**: Affected modules are the "blast radius" of your change. The more affected modules, the bigger the potential impact!

