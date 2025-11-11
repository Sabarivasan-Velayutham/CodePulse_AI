# Understanding Dependency Types in CodePulse AI

## Overview

When you change a file, CodePulse AI analyzes three types of dependencies to understand the full impact of your change:

1. **Direct Dependencies** - Files/modules directly used by the changed file
2. **Indirect Dependencies** - Files/modules used indirectly (through other dependencies)
3. **Affected Modules** - All modules that will be impacted by the change (direct + reverse dependencies)

---

## 1. Direct Dependencies

**Definition**: Files or modules that the changed file **directly imports, calls, or uses**.

**How it's detected**: 
- `import` statements
- Direct method calls
- Direct class instantiation
- Direct field access

### Example: Changing `AccountBalance.java`

**Changed File**: `AccountBalance.java`

```java
// AccountBalance.java
import com.bank.database.TransactionDAO;  // ← DIRECT DEPENDENCY

public class AccountBalance {
    private TransactionDAO transactionDAO;  // ← DIRECT DEPENDENCY
    
    public double getBalance(String accountId) {
        List<Transaction> transactions = 
            transactionDAO.findByAccountId(accountId);  // ← DIRECT CALL
        // ...
    }
}
```

**Direct Dependencies**:
- `TransactionDAO.java` (imported and used directly)

**Why it matters**: If you change `AccountBalance.java`, you need to ensure `TransactionDAO` still works as expected.

---

## 2. Indirect Dependencies

**Definition**: Files or modules that the changed file uses **through other dependencies** (transitive dependencies).

**How it's detected**: 
- Dependencies of your direct dependencies
- Chain: Your File → Direct Dep → Indirect Dep

### Example: Changing `AccountBalance.java`

**Dependency Chain**:
```
AccountBalance.java
    ↓ (direct)
TransactionDAO.java
    ↓ (TransactionDAO depends on)
DatabaseConnection.java  ← INDIRECT DEPENDENCY
transactions (database table)  ← INDIRECT DEPENDENCY
```

**Indirect Dependencies**:
- `DatabaseConnection.java` (used by TransactionDAO, which AccountBalance uses)
- `transactions` table (accessed by TransactionDAO)

**Why it matters**: Changes to `AccountBalance` might affect how `TransactionDAO` works, which in turn affects `DatabaseConnection`. You need to test the entire chain.

---

## 3. Affected Modules (Reverse Dependencies)

**Definition**: Files or modules that **depend on the changed file**. These are files that will be impacted by your change.

**How it's detected**: 
- Files that import the changed file
- Files that call methods from the changed file
- Files that instantiate classes from the changed file

### Example: Changing `AccountBalance.java`

**Changed File**: `AccountBalance.java`

**Files that depend on AccountBalance**:

```java
// PaymentProcessor.java
import com.bank.account.AccountBalance;  // ← DEPENDS ON AccountBalance

public class PaymentProcessor {
    private AccountBalance accountBalance;  // ← DEPENDS ON AccountBalance
    
    public PaymentResult processPayment(Payment payment) {
        // Step 3: Check account balance
        double currentBalance = accountBalance.getBalance(payment.getAccountId());  // ← CALLS AccountBalance
        // ...
    }
}
```

```java
// OverdraftManager.java
import com.bank.account.AccountBalance;  // ← DEPENDS ON AccountBalance

public class OverdraftManager {
    public boolean isEligible(String accountId) {
        AccountBalance balance = new AccountBalance();  // ← USES AccountBalance
        double currentBalance = balance.getBalance(accountId);
        // ...
    }
}
```

**Affected Modules** (Reverse Dependencies):
- `PaymentProcessor.java` (calls `accountBalance.getBalance()`)
- `OverdraftManager.java` (uses `AccountBalance` class)

**Why it matters**: If you change `AccountBalance.getBalance()`, these files might break or behave differently. They need to be tested and potentially updated.

---

## Complete Example: Changing `AccountBalance.java`

### Scenario
You modify `AccountBalance.java` to include pending transactions in balance calculation.

### Dependency Analysis Results:

#### Direct Dependencies (1):
- `TransactionDAO.java` - AccountBalance directly calls `transactionDAO.findByAccountId()`

#### Indirect Dependencies (2):
- `DatabaseConnection.java` - Used by TransactionDAO
- `transactions` table - Queried by TransactionDAO

#### Affected Modules / Reverse Dependencies (2):
- `PaymentProcessor.java` - Calls `accountBalance.getBalance()` at line 73
- `OverdraftManager.java` - Uses `AccountBalance` class

#### Total Affected Modules: 3
- Direct: 1 (TransactionDAO)
- Reverse: 2 (PaymentProcessor, OverdraftManager)

---

## Visual Representation

```
                    AccountBalance.java (CHANGED FILE)
                           │
        ┌──────────────────┴──────────────────┐
        │                                      │
   DIRECT DEPENDENCIES              REVERSE DEPENDENCIES
   (this file uses)                 (other files use this)
        │                                      │
        ↓                                      ↓
   TransactionDAO.java              PaymentProcessor.java
        │                                      │
        ↓                                      │
   DatabaseConnection.java          OverdraftManager.java
        │
        ↓
   transactions table
```

**Legend**:
- **Solid gray arrows (→)**: Direct dependencies (forward)
- **Dashed red arrows (←)**: Reverse dependencies (affected modules)

---

## Why This Matters

### 1. **Testing Scope**
- **Direct**: Test that your changes work with direct dependencies
- **Indirect**: Test the entire dependency chain
- **Affected**: Test all files that use your changed file

### 2. **Risk Assessment**
- More affected modules = Higher risk
- Critical modules (like PaymentProcessor) = Higher risk
- Database dependencies = Higher risk

### 3. **Deployment Planning**
- **Direct dependencies**: May need to be updated first
- **Affected modules**: Must be tested before deployment
- **Indirect dependencies**: May cause cascading failures

---

## Real-World Example: FeeCalculator Change

**Changed File**: `FeeCalculator.java` (fee calculation logic)

### Direct Dependencies:
- `CustomerDAO.java` - Used to check if customer is premium

### Indirect Dependencies:
- `Customer` class - Used by CustomerDAO
- `customers` database table - Queried by CustomerDAO

### Affected Modules (Reverse):
- `PaymentProcessor.java` - Calls `feeCalculator.calculate()` at line 106
- `PaymentAPI.java` - Uses PaymentProcessor (indirectly affected)
- `NotificationService.java` - Sends fee notifications (indirectly affected)

### Impact:
- **High Risk**: PaymentProcessor directly uses the fee calculation
- **Medium Risk**: PaymentAPI and NotificationService are indirectly affected
- **Total Impact**: 3+ modules need testing

---

## Summary Table

| Type | Definition | Example | Risk Level |
|------|-----------|---------|------------|
| **Direct** | Files directly used by changed file | `AccountBalance` → `TransactionDAO` | Medium |
| **Indirect** | Files used through direct dependencies | `AccountBalance` → `TransactionDAO` → `DatabaseConnection` | Low-Medium |
| **Affected (Reverse)** | Files that depend on changed file | `PaymentProcessor` → `AccountBalance` | **HIGH** (most critical) |

---

## Key Takeaway

**Affected Modules (Reverse Dependencies) are the most critical** because:
1. They will be impacted by your changes
2. They may break if your change is incompatible
3. They need thorough testing before deployment
4. They represent the "blast radius" of your change

The dependency graph shows all three types, with reverse dependencies highlighted in red dashed lines to emphasize their importance.

