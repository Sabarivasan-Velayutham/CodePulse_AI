# Sample SQL Queries for Schema Change Analysis

This document provides 3 sample SQL queries that demonstrate different types of dependency connections in the frontend.

## Prerequisites

Before running these queries, ensure:
1. The banking database schema is set up (`docs/banking-database-schema.sql`)
2. The PostgreSQL event trigger is active (`docs/postgres-trigger-setup.sql`)
3. The schema change listener is running (`python scripts/postgres_schema_listener.py`)
4. The backend is running and connected to PostgreSQL

## Understanding Schema Change Detection

### How the Trigger Works

1. **PostgreSQL Event Trigger** fires when DDL command completes
2. **Limitation**: Event triggers CANNOT access the full SQL statement
3. **What we get**: Only `command_tag` (e.g., "ALTER TABLE") and `object_identity` (e.g., "public.transactions")
4. **What we DON'T get**: Column name, operation type (ADD/DROP/MODIFY), data type

### How We Detect Exact Changes

Since PostgreSQL doesn't provide full SQL, we use **regex parsing** on the incomplete SQL:

```python
# Received: "ALTER TABLE public.transactions"
# We try to detect patterns:
- "ADD COLUMN" → ADD_COLUMN
- "DROP COLUMN" → DROP_COLUMN  
- "ALTER COLUMN ... TYPE" → MODIFY_COLUMN
- "RENAME COLUMN" → RENAME_COLUMN
```

**Current Status**:
- ✅ Works when SQL is complete (via direct API calls)
- ⚠️ Limited when SQL is incomplete (from event trigger)
- 🔄 Enhancement: We're working on querying PostgreSQL schema to detect actual changes

### For Accurate Detection

**Option 1**: Use direct API calls with full SQL (most accurate):
```bash
curl -X POST http://localhost:8000/api/v1/schema/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "sql_statement": "ALTER TABLE transactions ADD COLUMN currency VARCHAR(3) DEFAULT '\''USD'\''",
    "database_name": "banking_db"
  }'
```

**Option 2**: Use event trigger (works but may show generic "ALTER_TABLE"):
- The system will still analyze dependencies and relationships
- Change type may be generic if SQL is incomplete

---

## Query 1: ADD COLUMN - Low Risk, Multiple Code Dependencies

**Purpose**: Demonstrates adding a new column with default value, showing:
- Direct code dependencies (TransactionDAO.java)
- Transitive dependencies (PaymentProcessor.java → TransactionDAO.java)
- Database relationships (foreign keys, views)

**SQL Query**:
```sql
ALTER TABLE transactions ADD COLUMN currency VARCHAR(3) DEFAULT 'USD';
```

**Expected Impact**:
- **Change Type**: `ADD_COLUMN`
- **Table**: `TRANSACTIONS`
- **Column**: `CURRENCY`
- **Code Dependencies**:
  - Direct: `TransactionDAO.java` (uses transactions table)
  - Transitive: `PaymentProcessor.java` → `TransactionDAO.java`
- **Database Relationships**:
  - Forward: `TRANSACTIONS` → `CUSTOMERS` (FK), `TRANSACTIONS` → `ACCOUNTS` (FK)
  - Reverse: `FRAUD_ALERTS` → `TRANSACTIONS` (FK), `ACCOUNT_BALANCES` → `TRANSACTIONS` (FK)
  - Views: `customer_transaction_summary`, `account_activity_summary`
  - Triggers: `trigger_update_account_balance`
- **Risk Level**: LOW to MEDIUM (backward compatible, but affects all existing rows)

**Graph Visualization**:
```
[PaymentProcessor.java] --DEPENDS_ON--> [TransactionDAO.java] --USES_TABLE--> [TRANSACTIONS]
[TRANSACTIONS] --FOREIGN_KEY--> [CUSTOMERS]
[TRANSACTIONS] --FOREIGN_KEY--> [ACCOUNTS]
[FRAUD_ALERTS] --REFERENCED_BY--> [TRANSACTIONS]
[ACCOUNT_BALANCES] --REFERENCED_BY--> [TRANSACTIONS]
```

---

## Query 2: DROP COLUMN - High Risk, Breaking Change

**Purpose**: Demonstrates a destructive change that will break code:
- Shows high risk score
- Identifies all code files using the column
- Warns about breaking changes

**SQL Query**:
```sql
ALTER TABLE transactions DROP COLUMN fee;
```

**Expected Impact**:
- **Change Type**: `DROP_COLUMN`
- **Table**: `TRANSACTIONS`
- **Column**: `FEE`
- **Code Dependencies**:
  - Direct: `TransactionDAO.java` (uses fee column in INSERT/SELECT)
  - Transitive: `PaymentProcessor.java` → `TransactionDAO.java`
  - Also: `FeeCalculator.java` (if it references fee column)
- **Database Relationships**:
  - Same as Query 1 (table relationships unchanged)
- **Risk Level**: CRITICAL (breaking change - code will fail)
- **Breaking Changes**:
  - `TransactionDAO.save()` - INSERT statement will fail
  - `TransactionDAO.mapResultSetToPayment()` - ResultSet access will fail
  - Any code reading `payment.getFee()` will get null/error

**Graph Visualization**:
```
[PaymentProcessor.java] --DEPENDS_ON--> [TransactionDAO.java] --USES_TABLE--> [TRANSACTIONS]
[FeeCalculator.java] --DEPENDS_ON--> [TransactionDAO.java]
[TRANSACTIONS] --FOREIGN_KEY--> [CUSTOMERS]
[TRANSACTIONS] --FOREIGN_KEY--> [ACCOUNTS]
```

**⚠️ Warning**: This query will break the application! Only run in test environment.

---

## Query 3: MODIFY COLUMN TYPE - Medium Risk, Data Migration Required

**Purpose**: Demonstrates changing a column type, requiring:
- Code updates (type casting)
- Data migration
- Potential data loss

**SQL Query**:
```sql
ALTER TABLE transactions ALTER COLUMN amount TYPE DECIMAL(20, 4);
```

**Expected Impact**:
- **Change Type**: `MODIFY_COLUMN`
- **Table**: `TRANSACTIONS`
- **Column**: `AMOUNT`
- **Old Value**: `DECIMAL(15, 2)` (assumed)
- **New Value**: `DECIMAL(20, 4)`
- **Code Dependencies**:
  - Direct: `TransactionDAO.java` (uses amount in INSERT/SELECT)
  - Transitive: `PaymentProcessor.java` → `TransactionDAO.java`
  - Also: `AccountBalance.java` (if it uses amount)
- **Database Relationships**:
  - Same as Query 1
- **Risk Level**: MEDIUM to HIGH
- **Migration Required**: Yes - existing data needs conversion
- **Code Changes Required**:
  - Update `TransactionDAO` to handle new precision
  - Update `Payment` model to use new type
  - Update any calculations using amount

**Graph Visualization**:
```
[PaymentProcessor.java] --DEPENDS_ON--> [TransactionDAO.java] --USES_TABLE--> [TRANSACTIONS]
[AccountBalance.java] --DEPENDS_ON--> [TransactionDAO.java]
[TRANSACTIONS] --FOREIGN_KEY--> [CUSTOMERS]
[TRANSACTIONS] --FOREIGN_KEY--> [ACCOUNTS]
```

---

## Query 4: ALTER TABLE on Related Table - Cascading Impact

**Purpose**: Shows how changes to a related table affect the main table through foreign keys.

**SQL Query**:
```sql
ALTER TABLE accounts ADD COLUMN overdraft_limit DECIMAL(15, 2) DEFAULT 0.00;
```

**Expected Impact**:
- **Change Type**: `ADD_COLUMN`
- **Table**: `ACCOUNTS`
- **Column**: `OVERDRAFT_LIMIT`
- **Code Dependencies**:
  - Direct: `AccountBalance.java` (uses accounts table)
  - Transitive: `PaymentProcessor.java` → `AccountBalance.java`
- **Database Relationships**:
  - Forward: `ACCOUNTS` → `CUSTOMERS` (FK)
  - Reverse: `TRANSACTIONS` → `ACCOUNTS` (FK), `TRANSFER_RECORDS` → `ACCOUNTS` (FK)
- **Impact on TRANSACTIONS**:
  - Indirect: Changes to `accounts` affect `transactions` through FK relationship
  - Views: `account_activity_summary` will include new column

**Graph Visualization**:
```
[PaymentProcessor.java] --DEPENDS_ON--> [AccountBalance.java] --USES_TABLE--> [ACCOUNTS]
[ACCOUNTS] --FOREIGN_KEY--> [CUSTOMERS]
[TRANSACTIONS] --REFERENCED_BY--> [ACCOUNTS]
[TRANSFER_RECORDS] --REFERENCED_BY--> [ACCOUNTS]
```

---

## How to Run These Queries

### Step 1: Connect to PostgreSQL
```bash
psql -U postgres -d banking_db
```

### Step 2: Run the Query
Copy and paste one of the SQL queries above.

### Step 3: Watch the Listener
The listener should detect the change and trigger analysis:
```
🔔 Received notification on channel: schema_change
📨 Schema Change Detected!
   Type: ALTER TABLE
   Object: public.transactions
   🔄 Triggering analysis...
   ✅ Analysis triggered successfully
```

### Step 4: View Results
1. Check backend logs for analysis details
2. Open dashboard at `http://localhost:3000`
3. View the dependency graph showing:
   - Table nodes (blue)
   - Code file nodes (green)
   - Relationship edges (arrows)

---

## Understanding the Graph

### Node Types
- **Table Nodes** (Blue): Database tables
- **Code Nodes** (Green): Source code files

### Edge Types
- **USES_TABLE**: Code file directly uses a table
- **DEPENDS_ON**: Code file depends on another code file
- **FOREIGN_KEY**: Table references another table
- **REFERENCED_BY**: Another table references this table
- **VIEW**: View depends on table
- **TRIGGER**: Trigger on table

### Risk Colors
- **Green (LOW)**: Safe change, backward compatible
- **Yellow (MEDIUM)**: Requires attention, may need code updates
- **Red (CRITICAL)**: Breaking change, will cause errors

---

## Reverse/Undo Queries

Use these queries to reverse the changes and restore the original schema state:

### Reverse Query 1: Remove Currency Column

**Original**: `ALTER TABLE transactions ADD COLUMN currency VARCHAR(3) DEFAULT 'USD';`

**Reverse**:
```sql
ALTER TABLE transactions DROP COLUMN currency;
```

**Note**: This will permanently delete the column and all its data. Make sure you have a backup if needed.

---

### Reverse Query 2: Restore Fee Column

**Original**: `ALTER TABLE transactions DROP COLUMN fee;`

**Reverse**:
```sql
-- First, check the original column definition from your schema
-- Based on the schema, fee was likely DECIMAL(10, 2) DEFAULT 0.00
ALTER TABLE transactions ADD COLUMN fee DECIMAL(10, 2) DEFAULT 0.00;
```

**Note**: If you dropped the column, you'll need to know the original data type. Check your migration history or schema documentation.

**To find original column definition**:
```sql
-- If you have a backup or migration history, check there
-- Or query information_schema from a backup database
SELECT column_name, data_type, column_default, is_nullable
FROM information_schema.columns
WHERE table_name = 'transactions' AND column_name = 'fee';
```

---

### Reverse Query 3: Restore Original Amount Column Type

**Original**: `ALTER TABLE transactions ALTER COLUMN amount TYPE DECIMAL(20, 4);`

**Reverse**:
```sql
-- Restore to original type (likely DECIMAL(15, 2) based on schema)
ALTER TABLE transactions ALTER COLUMN amount TYPE DECIMAL(15, 2);
```

**⚠️ Warning**: Changing column type may fail if existing data doesn't fit the new type. You may need to:
1. Convert data first
2. Or drop and recreate the column (loses data!)

**Safe Reverse (with data preservation)**:
```sql
-- Step 1: Create temporary column with original type
ALTER TABLE transactions ADD COLUMN amount_old DECIMAL(15, 2);

-- Step 2: Copy and convert data
UPDATE transactions SET amount_old = amount::DECIMAL(15, 2);

-- Step 3: Drop original column
ALTER TABLE transactions DROP COLUMN amount;

-- Step 4: Rename temporary column
ALTER TABLE transactions RENAME COLUMN amount_old TO amount;
```

---

### Reverse Query 4: Remove Overdraft Limit Column

**Original**: `ALTER TABLE accounts ADD COLUMN overdraft_limit DECIMAL(15, 2) DEFAULT 0.00;`

**Reverse**:
```sql
ALTER TABLE accounts DROP COLUMN overdraft_limit;
```

---

## Quick Reference: Common Reverse Operations

| Original Operation | Reverse Operation |
|-------------------|-------------------|
| `ADD COLUMN col TYPE` | `DROP COLUMN col` |
| `DROP COLUMN col` | `ADD COLUMN col TYPE [DEFAULT value]` |
| `ALTER COLUMN col TYPE new_type` | `ALTER COLUMN col TYPE original_type` |
| `RENAME COLUMN old TO new` | `RENAME COLUMN new TO old` |
| `ADD CONSTRAINT ...` | `DROP CONSTRAINT constraint_name` |
| `DROP CONSTRAINT ...` | `ADD CONSTRAINT ...` (need original definition) |

---

## Testing Workflow

### Recommended Testing Sequence

1. **Run Original Query** (e.g., ADD COLUMN)
   ```sql
   ALTER TABLE transactions ADD COLUMN currency VARCHAR(3) DEFAULT 'USD';
   ```

2. **Verify in Dashboard**
   - Check change type detection
   - Review dependency graph
   - Verify risk score

3. **Run Reverse Query** (to restore state)
   ```sql
   ALTER TABLE transactions DROP COLUMN currency;
   ```

4. **Run Next Test Query**
   - Repeat with different change types

### Automated Test Script

You can create a test script to run queries and their reverses:

```sql
-- test_schema_changes.sql

-- Test 1: ADD COLUMN
ALTER TABLE transactions ADD COLUMN currency VARCHAR(3) DEFAULT 'USD';
-- Wait for analysis...
ALTER TABLE transactions DROP COLUMN currency;  -- Reverse

-- Test 2: MODIFY COLUMN (if column exists)
ALTER TABLE transactions ALTER COLUMN amount TYPE DECIMAL(20, 4);
-- Wait for analysis...
ALTER TABLE transactions ALTER COLUMN amount TYPE DECIMAL(15, 2);  -- Reverse

-- Test 3: DROP COLUMN (if column exists and you know original type)
-- ALTER TABLE transactions DROP COLUMN fee;
-- Wait for analysis...
-- ALTER TABLE transactions ADD COLUMN fee DECIMAL(10, 2) DEFAULT 0.00;  -- Reverse
```

---

## Best Practices

1. **Always test in development first**
2. **Review the dependency graph before deploying**
3. **Check AI insights for recommendations**
4. **Plan data migration for MODIFY_COLUMN changes**
5. **Coordinate with team for breaking changes**
6. **Keep reverse queries ready** - Document how to undo each change
7. **Backup before destructive changes** - DROP COLUMN, DROP TABLE, etc.

---

## Troubleshooting

### Query doesn't trigger analysis
- Check event trigger exists: `SELECT * FROM pg_event_trigger;`
- Verify listener is running: `python scripts/postgres_schema_listener.py`
- Check PostgreSQL logs for errors

### Graph doesn't show dependencies
- Ensure code files exist in `sample-repo`
- Check Neo4j is running: `docker-compose ps neo4j`
- Verify code analysis has run (check backend logs)

### Connection errors
- Verify PostgreSQL is accessible from Docker: `host.docker.internal:5432`
- Check environment variables in `docker-compose.yml`
- Test connection: `psql -h host.docker.internal -U postgres -d banking_db`

