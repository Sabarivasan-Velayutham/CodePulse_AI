# Database Setup Guide for Enhanced Schema Analysis

## Overview

This guide helps you set up a comprehensive banking database with interconnected tables, views, triggers, and functions. This enables the system to perform detailed impact analysis when schema changes occur.

## Step 1: Create the Database Schema

Run the comprehensive schema script:

```bash
psql -U postgres -d banking_db -f docs/banking-database-schema.sql
```

This creates:
- **7 interconnected tables** with foreign key relationships
- **3 views** that depend on multiple tables
- **2 triggers** that reference tables
- **1 function** that queries tables

## Step 2: Set Up Enhanced Event Trigger

Replace the basic trigger with the enhanced version:

```bash
psql -U postgres -d banking_db -f docs/enhanced-postgres-trigger.sql
```

This enhanced trigger:
- Captures more detailed schema change information
- Includes relationship context
- Provides better SQL reconstruction

## Step 3: Verify the Setup

### Check Tables and Relationships

```sql
\c banking_db

-- List all tables
\dt

-- Check foreign key relationships
SELECT
    tc.table_name,
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
    ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
ORDER BY tc.table_name;
```

### Check Views

```sql
SELECT table_name, view_definition
FROM information_schema.views
WHERE table_schema = 'public';
```

### Check Triggers

```sql
SELECT 
    t.tgname AS trigger_name,
    c.relname AS table_name,
    p.proname AS function_name
FROM pg_trigger t
JOIN pg_class c ON t.tgrelid = c.oid
JOIN pg_proc p ON t.tgfoid = p.oid
WHERE NOT t.tgisinternal;
```

## Step 4: Test Schema Change Detection

### Test 1: Add Column to Transactions Table

```sql
ALTER TABLE transactions ADD COLUMN currency VARCHAR(3) DEFAULT 'USD';
```

**Expected Impact:**
- Direct: `transactions` table modified
- Code Impact: `TransactionDAO.java` (4 usages)
- Related Tables: `accounts` (via FK), `fraud_alerts` (via FK), `account_balances` (via FK)
- Views Affected: `customer_transaction_summary`, `account_activity_summary`
- Triggers Affected: `trigger_update_account_balance`

### Test 2: Modify Foreign Key

```sql
ALTER TABLE transactions 
DROP CONSTRAINT transactions_customer_id_fkey,
ADD CONSTRAINT transactions_customer_id_fkey 
FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE;
```

**Expected Impact:**
- Direct: `transactions` table constraint changed
- Related Tables: `customers` (referenced table)
- Code Impact: Any code that deletes customers or transactions

### Test 3: Drop Column

```sql
ALTER TABLE transactions DROP COLUMN currency;
```

**Expected Impact:**
- Direct: `transactions` table column removed
- Code Impact: `TransactionDAO.java` (if it uses currency column)
- Breaking Change: HIGH RISK

## Step 5: Start the Listener

```bash
python scripts/postgres_schema_listener.py
```

## Database Structure Overview

### Table Relationships

```
customers (parent)
    ├── accounts (FK: customer_id)
    │   ├── transactions (FK: account_id)
    │   │   ├── fraud_alerts (FK: transaction_id)
    │   │   └── account_balances (FK: transaction_id)
    │   └── transfer_records (FK: from_account_id, to_account_id)
    └── transactions (FK: customer_id)
        └── fraud_alerts (FK: customer_id, transaction_id)
```

### Views Dependencies

1. **customer_transaction_summary**
   - Depends on: `customers`, `transactions`

2. **account_activity_summary**
   - Depends on: `accounts`, `transactions`, `fraud_alerts`

3. **high_risk_customers**
   - Depends on: `customers`, `fraud_alerts`, `transactions`

### Trigger Dependencies

1. **trigger_update_account_balance**
   - On: `transactions` table
   - Updates: `accounts`, `account_balances` tables

2. **trigger_update_customer_timestamp**
   - On: `customers` table

## Understanding the Dependency Graph

When you make a schema change, the system will:

1. **Parse the change** - Identify what changed (table, column, constraint, etc.)

2. **Find code dependencies** - Search codebase for files using the table/column

3. **Query database relationships** - Get:
   - Foreign keys (forward and reverse)
   - Views that depend on the table
   - Triggers on the table
   - Functions that use the table

4. **Build dependency graph** showing:
   - **Table nodes** (blue) - Database tables
   - **Code nodes** (green) - Code files
   - **Relationship edges**:
     - `FOREIGN_KEY` - Table references another table
     - `REFERENCED_BY` - Another table references this table
     - `USES_TABLE` - Code file uses table
     - `VIEW` - View depends on table
     - `TRIGGER` - Trigger on table

## Example: Impact of Adding Column to Transactions

When you run:
```sql
ALTER TABLE transactions ADD COLUMN currency VARCHAR(3);
```

The system will show:

**Direct Impact:**
- `transactions` table modified

**Code Impact:**
- `TransactionDAO.java` (4 SQL queries use transactions table)

**Database Relationships:**
- Forward: None (transactions doesn't reference other tables via FK)
- Reverse: 
  - `fraud_alerts` references `transactions` (FK)
  - `account_balances` references `transactions` (FK)
  - `transfer_records` references `transactions` (FK)

**Views Affected:**
- `customer_transaction_summary` (uses transactions)
- `account_activity_summary` (uses transactions)
- `high_risk_customers` (uses transactions)

**Triggers Affected:**
- `trigger_update_account_balance` (on transactions table)

**Dependency Graph Will Show:**
```
[TransactionDAO.java] --USES_TABLE--> [TRANSACTIONS]
[TRANSACTIONS] --REFERENCED_BY--> [FRAUD_ALERTS]
[TRANSACTIONS] --REFERENCED_BY--> [ACCOUNT_BALANCES]
[TRANSACTIONS] --REFERENCED_BY--> [TRANSFER_RECORDS]
[TRANSACTIONS] --VIEW--> [customer_transaction_summary]
[TRANSACTIONS] --VIEW--> [account_activity_summary]
```

## Troubleshooting

### Listener Not Detecting Changes

1. Verify trigger exists:
   ```sql
   SELECT * FROM pg_event_trigger WHERE evtname = 'schema_change_trigger';
   ```

2. Test notification manually:
   ```sql
   SELECT pg_notify('schema_change', '{"test": "data"}');
   ```

3. Check PostgreSQL logs for errors

### No Relationships Found

1. Verify foreign keys exist:
   ```sql
   SELECT * FROM information_schema.table_constraints 
   WHERE constraint_type = 'FOREIGN KEY';
   ```

2. Check if psycopg2 is installed:
   ```bash
   pip install psycopg2-binary
   ```

3. Verify database connection settings in environment variables

### Graph Not Showing

1. Check Neo4j is running:
   ```bash
   docker-compose ps neo4j
   ```

2. Verify data is stored in Neo4j:
   - Open Neo4j Browser: http://localhost:7474
   - Run: `MATCH (t:Table) RETURN t LIMIT 10`

3. Check backend logs for errors

## Next Steps

1. **Run the schema setup**: `psql -U postgres -d banking_db -f docs/banking-database-schema.sql`
2. **Update the trigger**: `psql -U postgres -d banking_db -f docs/enhanced-postgres-trigger.sql`
3. **Start the listener**: `python scripts/postgres_schema_listener.py`
4. **Make a test change**: `ALTER TABLE transactions ADD COLUMN test_col VARCHAR(10);`
5. **View results**: Check the dashboard at http://localhost:3000

