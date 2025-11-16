# PostgreSQL Full SQL Capture Guide

## Problem
PostgreSQL event triggers don't have direct access to the full SQL statement. They only provide:
- Command tag (e.g., "ALTER TABLE")
- Object identity (e.g., "public.fraud_alerts")
- Object type

This means we can't automatically detect the exact operation (ADD COLUMN, DROP COLUMN, etc.) from incomplete SQL like `ALTER TABLE public.fraud_alerts`.

## Solution: Enable pg_stat_statements Extension

The `pg_stat_statements` extension tracks all SQL statements executed in PostgreSQL, allowing us to retrieve the full SQL statement.

### Step 1: Enable pg_stat_statements

Connect to your PostgreSQL database and run:

```sql
-- Enable the extension
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Verify it's enabled
SELECT * FROM pg_extension WHERE extname = 'pg_stat_statements';
```

### Step 2: Configure PostgreSQL (if needed)

If the extension isn't available, you may need to add it to `postgresql.conf`:

```conf
shared_preload_libraries = 'pg_stat_statements'
pg_stat_statements.track = all
pg_stat_statements.max = 10000
```

Then restart PostgreSQL.

### Step 3: Update the Trigger Function

The trigger function in `docs/postgres-trigger-setup.sql` has been updated to query `pg_stat_statements` for the full SQL. It will:

1. Try to get the full SQL from `pg_stat_statements`
2. Fall back to reconstructed SQL if not available
3. Log helpful messages about what was captured

### Step 4: Verify It Works

After enabling the extension, test with:

```sql
ALTER TABLE fraud_alerts ADD COLUMN risk_score DECIMAL(5, 2) DEFAULT 0.00;
```

Check the listener output - it should show:
```
✅ Retrieved full SQL from pg_stat_statements
```

## Alternative: Use Direct API Calls

If `pg_stat_statements` is not available, you can use direct API calls with the full SQL:

```bash
curl -X POST http://localhost:8000/api/v1/schema/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "sql_statement": "ALTER TABLE fraud_alerts ADD COLUMN risk_score DECIMAL(5, 2) DEFAULT 0.00",
    "database_name": "banking_db",
    "change_id": "manual_001",
    "repository": "banking-app"
  }'
```

This bypasses the trigger and provides the full SQL directly.

## Alternative Solution: System Catalog Detection

Since `pg_stat_statements` requires a PostgreSQL restart, we've implemented an alternative approach that **doesn't require any configuration**:

### How It Works

When the SQL statement is incomplete (e.g., `ALTER TABLE public.transactions`), the system:

1. **Queries PostgreSQL system catalogs** (`pg_attribute`, `pg_class`) to inspect the actual table structure
2. **Identifies the most recently added column** by checking column attributes
3. **Extracts column details** including:
   - Column name
   - Data type
   - Default value (if any)

This works **automatically** without any PostgreSQL configuration changes!

### Example

When you run:
```sql
ALTER TABLE transactions ADD COLUMN currency VARCHAR(3) DEFAULT 'USD';
```

Even if the trigger only captures `ALTER TABLE public.transactions`, the system will:
1. Query the `transactions` table structure
2. Find the `currency` column (newest by `attnum`)
3. Detect it as `ADD_COLUMN` with type `VARCHAR(3)` and default `'USD'`

### Current Status

The system will:
1. ✅ Try to detect ADD_COLUMN from incomplete SQL using improved regex
2. ✅ Query PostgreSQL system catalogs to detect actual changes (NEW - no config needed!)
3. ✅ Query `pg_stat_statements` if available (optional)
4. ✅ Fall back to generic ALTER_TABLE if all methods fail
5. ✅ Still proceed with dependency analysis even with incomplete SQL

**The system now automatically detects ADD_COLUMN changes even without `pg_stat_statements`!**

