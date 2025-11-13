# Reverse SQL Queries - Restore Schema State

This document provides SQL queries to reverse/undo the sample schema changes for repeated testing.

## Important Notes

⚠️ **Data Loss Warning**: Some reverse operations (especially DROP COLUMN) will permanently delete data. Always backup your database before running destructive operations.

⚠️ **Type Compatibility**: When reversing MODIFY COLUMN, ensure existing data is compatible with the original type, or you'll get errors.

---

## Query 1: Reverse ADD COLUMN currency

### Original Query
```sql
ALTER TABLE transactions ADD COLUMN currency VARCHAR(3) DEFAULT 'USD';
```

### Reverse Query
```sql
ALTER TABLE transactions DROP COLUMN currency;
```

### Verification
```sql
-- Check if column was removed
SELECT column_name 
FROM information_schema.columns 
WHERE table_name = 'transactions' AND column_name = 'currency';
-- Should return 0 rows
```

---

## Query 2: Reverse DROP COLUMN fee

### Original Query
```sql
ALTER TABLE transactions DROP COLUMN fee;
```

### Reverse Query
```sql
-- Restore fee column with original definition
-- Based on typical banking schema, fee is usually DECIMAL(10, 2) DEFAULT 0.00
ALTER TABLE transactions ADD COLUMN fee DECIMAL(10, 2) DEFAULT 0.00;
```

### If You Don't Know Original Type

**Option 1: Check Migration History**
```sql
-- If using Alembic/Flyway, check migration files
-- Look for the CREATE TABLE or original ADD COLUMN statement
```

**Option 2: Query Backup Database**
```sql
-- If you have a backup, query it:
SELECT column_name, data_type, column_default, is_nullable
FROM information_schema.columns
WHERE table_name = 'transactions' AND column_name = 'fee';
```

**Option 3: Check Schema Documentation**
```sql
-- Check docs/banking-database-schema.sql for original definition
-- Fee column is typically: fee DECIMAL(10, 2) DEFAULT 0.00
```

### Verification
```sql
-- Check if column was restored
SELECT column_name, data_type, column_default
FROM information_schema.columns 
WHERE table_name = 'transactions' AND column_name = 'fee';
-- Should show: fee | numeric | 0.00
```

---

## Query 3: Reverse MODIFY COLUMN amount

### Original Query
```sql
ALTER TABLE transactions ALTER COLUMN amount TYPE DECIMAL(20, 4);
```

### Reverse Query (Simple)
```sql
-- Restore to original type (DECIMAL(15, 2) based on schema)
ALTER TABLE transactions ALTER COLUMN amount TYPE DECIMAL(15, 2);
```

**⚠️ Warning**: This may fail if any existing data has more than 2 decimal places or exceeds DECIMAL(15,2) range.

### Reverse Query (Safe - Preserves Data)

If the simple reverse fails due to data incompatibility:

```sql
-- Step 1: Create backup column
ALTER TABLE transactions ADD COLUMN amount_backup DECIMAL(20, 4);
UPDATE transactions SET amount_backup = amount;

-- Step 2: Change original column type
ALTER TABLE transactions ALTER COLUMN amount TYPE DECIMAL(15, 2) USING amount::DECIMAL(15, 2);

-- Step 3: Verify data (check for any truncation)
SELECT COUNT(*) FROM transactions WHERE amount_backup != amount::DECIMAL(20, 4);

-- Step 4: If verification passes, drop backup column
ALTER TABLE transactions DROP COLUMN amount_backup;
```

### Verification
```sql
-- Check column type
SELECT column_name, data_type, numeric_precision, numeric_scale
FROM information_schema.columns 
WHERE table_name = 'transactions' AND column_name = 'amount';
-- Should show: amount | numeric | 15 | 2
```

---

## Query 4: Reverse ADD COLUMN on Related Table

### Original Query
```sql
ALTER TABLE accounts ADD COLUMN overdraft_limit DECIMAL(15, 2) DEFAULT 0.00;
```

### Reverse Query
```sql
ALTER TABLE accounts DROP COLUMN overdraft_limit;
```

### Verification
```sql
SELECT column_name 
FROM information_schema.columns 
WHERE table_name = 'accounts' AND column_name = 'overdraft_limit';
-- Should return 0 rows
```

---

## Complete Reset Script

Use this script to reset the `transactions` table to its original state:

```sql
-- reset_transactions_table.sql

\c banking_db

-- Remove test columns (if they exist)
ALTER TABLE transactions DROP COLUMN IF EXISTS currency;
ALTER TABLE transactions DROP COLUMN IF EXISTS test_col;

-- Restore fee column if it was dropped
-- (Only run if fee column doesn't exist)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'transactions' AND column_name = 'fee'
    ) THEN
        ALTER TABLE transactions ADD COLUMN fee DECIMAL(10, 2) DEFAULT 0.00;
    END IF;
END $$;

-- Restore amount column type if it was changed
-- Check current type first
DO $$
DECLARE
    current_type TEXT;
BEGIN
    SELECT data_type || '(' || numeric_precision || ',' || numeric_scale || ')' 
    INTO current_type
    FROM information_schema.columns 
    WHERE table_name = 'transactions' AND column_name = 'amount';
    
    -- If type is not DECIMAL(15,2), restore it
    IF current_type != 'numeric(15,2)' THEN
        ALTER TABLE transactions ALTER COLUMN amount TYPE DECIMAL(15, 2);
    END IF;
END $$;

-- Verify final state
SELECT 
    column_name, 
    data_type, 
    numeric_precision, 
    numeric_scale,
    column_default
FROM information_schema.columns 
WHERE table_name = 'transactions'
ORDER BY ordinal_position;
```

---

## Quick Check: Current Schema State

Run this to see current state of transactions table:

```sql
SELECT 
    column_name,
    data_type,
    CASE 
        WHEN numeric_precision IS NOT NULL 
        THEN data_type || '(' || numeric_precision || ',' || numeric_scale || ')'
        ELSE data_type
    END AS full_type,
    column_default,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'transactions'
ORDER BY ordinal_position;
```

**Expected Original State** (based on schema):
```
transaction_id    | character varying | VARCHAR(50)     | NULL | NO
customer_id       | character varying | VARCHAR(50)    | NULL | NO
account_id         | character varying | VARCHAR(50)    | NULL | NO
amount             | numeric          | DECIMAL(15,2)  | NULL | NO
fee                | numeric          | DECIMAL(10,2)  | 0.00 | YES
currency           | character varying | VARCHAR(3)    | USD  | YES  (if added)
type               | character varying | VARCHAR(20)    | NULL | NO
status             | character varying | VARCHAR(20)    | PENDING | YES
processed_at       | timestamp        | TIMESTAMP      | CURRENT_TIMESTAMP | YES
device_id          | character varying | VARCHAR(100)  | NULL | YES
ip_address         | character varying | VARCHAR(45)   | NULL | YES
geo_location       | character varying | VARCHAR(100)  | NULL | YES
requires_manual_review | boolean      | BOOLEAN        | false | YES
```

---

## Testing Workflow with Reverses

### Recommended Sequence

1. **Check Current State**
   ```sql
   SELECT column_name FROM information_schema.columns 
   WHERE table_name = 'transactions';
   ```

2. **Run Test Query** (e.g., ADD COLUMN)
   ```sql
   ALTER TABLE transactions ADD COLUMN currency VARCHAR(3) DEFAULT 'USD';
   ```

3. **Wait for Analysis** (check dashboard)

4. **Run Reverse Query**
   ```sql
   ALTER TABLE transactions DROP COLUMN currency;
   ```

5. **Verify State Restored**
   ```sql
   SELECT column_name FROM information_schema.columns 
   WHERE table_name = 'transactions' AND column_name = 'currency';
   -- Should return 0 rows
   ```

6. **Run Next Test Query**

---

## Common Issues and Solutions

### Issue 1: "Column does not exist" when reversing DROP

**Problem**: You're trying to DROP a column that was already dropped.

**Solution**: Check if column exists first:
```sql
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'transactions' AND column_name = 'currency'
    ) THEN
        ALTER TABLE transactions DROP COLUMN currency;
    END IF;
END $$;
```

### Issue 2: "Cannot change type" when reversing MODIFY

**Problem**: Existing data doesn't fit the original type.

**Solution**: Use USING clause to convert:
```sql
ALTER TABLE transactions 
ALTER COLUMN amount TYPE DECIMAL(15, 2) 
USING amount::DECIMAL(15, 2);
```

### Issue 3: "Column already exists" when reversing ADD

**Problem**: Column wasn't actually dropped, or was re-added.

**Solution**: Check current state and use IF NOT EXISTS (PostgreSQL 9.5+):
```sql
-- PostgreSQL doesn't support IF NOT EXISTS for ADD COLUMN
-- Use DO block instead:
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'transactions' AND column_name = 'fee'
    ) THEN
        ALTER TABLE transactions ADD COLUMN fee DECIMAL(10, 2) DEFAULT 0.00;
    END IF;
END $$;
```

---

## Backup Before Destructive Operations

Always backup before running DROP operations:

```sql
-- Create backup table
CREATE TABLE transactions_backup AS SELECT * FROM transactions;

-- Or export to file
\copy transactions TO '/path/to/backup.csv' CSV HEADER;

-- After testing, restore if needed
-- INSERT INTO transactions SELECT * FROM transactions_backup;
```

---

## Summary Table

| Test Query | Reverse Query | Data Loss? | Notes |
|------------|---------------|------------|-------|
| `ADD COLUMN currency` | `DROP COLUMN currency` | ✅ Yes | Column and data deleted |
| `DROP COLUMN fee` | `ADD COLUMN fee TYPE` | ⚠️ Partial | Need original type definition |
| `ALTER COLUMN amount TYPE` | `ALTER COLUMN amount TYPE original` | ⚠️ Possible | May fail if data incompatible |
| `RENAME COLUMN old TO new` | `RENAME COLUMN new TO old` | ❌ No | Simple rename |
| `ADD CONSTRAINT` | `DROP CONSTRAINT name` | ❌ No | Need constraint name |
| `DROP CONSTRAINT` | `ADD CONSTRAINT ...` | ❌ No | Need original definition |

---

## Quick Reference Commands

```sql
-- Check if column exists
SELECT EXISTS (
    SELECT 1 FROM information_schema.columns 
    WHERE table_name = 'transactions' AND column_name = 'currency'
);

-- Get column definition
SELECT column_name, data_type, column_default, is_nullable
FROM information_schema.columns
WHERE table_name = 'transactions' AND column_name = 'fee';

-- List all columns
SELECT column_name, data_type 
FROM information_schema.columns
WHERE table_name = 'transactions'
ORDER BY ordinal_position;

-- Safe DROP (only if exists)
DO $$ 
BEGIN 
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'transactions' AND column_name = 'currency') 
    THEN 
        ALTER TABLE transactions DROP COLUMN currency; 
    END IF; 
END $$;
```

