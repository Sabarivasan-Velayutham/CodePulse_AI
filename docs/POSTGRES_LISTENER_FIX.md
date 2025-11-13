# PostgreSQL Listener Fix

## Problem
The listener script wasn't detecting PostgreSQL notifications even though the trigger was firing.

## Root Causes
1. **Polling Issue**: `conn.poll()` was being called but wasn't actively waiting for notifications
2. **Cross-platform Compatibility**: `select.select()` doesn't work the same way on Windows
3. **Event Trigger Limitation**: `current_query()` doesn't work in event triggers, so we can't capture the full SQL statement

## Solutions Applied

### 1. Improved Listener Polling
- Added proper notification waiting using `select.select()` with timeout (Unix/Linux/Mac)
- Added fallback to `time.sleep()` for Windows compatibility
- Added better error handling and logging

### 2. Fixed Event Trigger Function
- Removed `current_query()` (doesn't work in event triggers)
- Build SQL statement from available metadata (command tag, object identity)
- Added timestamp to notification payload

### 3. Better SQL Reconstruction
- Enhanced SQL statement reconstruction from payload
- Handle different ALTER TABLE operations (ADD COLUMN, DROP COLUMN, etc.)
- Added warnings when SQL is not fully captured

## Testing the Fix

1. **Recreate the trigger** (if needed):
   ```bash
   psql -U postgres -d banking_db -f docs/postgres-trigger-setup.sql
   ```

2. **Start the listener**:
   ```bash
   python scripts/postgres_schema_listener.py
   ```

3. **Make a schema change** in another terminal:
   ```sql
   \c banking_db
   ALTER TABLE transactions ADD COLUMN test_column VARCHAR(10);
   ```

4. **Expected output in listener**:
   ```
   🔔 Received notification on channel: schema_change
   ============================================================
   📨 Schema Change Detected!
   ============================================================
      Type: ALTER TABLE
      Object: public.transactions
      Schema: public
      SQL: ALTER TABLE public.transactions...
      🔄 Triggering analysis...
      ✅ Analysis triggered successfully
   ```

## Limitations

### SQL Statement Capture
- **Full SQL cannot be captured** in event triggers (PostgreSQL limitation)
- We reconstruct SQL from metadata: `ALTER TABLE table_name`
- For operations like `DROP COLUMN`, we know the table but not the exact column name from the event trigger alone

### Workarounds
1. **Use pg_stat_statements extension** (optional):
   ```sql
   CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
   ```
   Then query recent statements to get full SQL (requires additional setup)

2. **Use application-level logging**: Capture SQL statements in your application before executing them

3. **Use database triggers on specific tables**: Instead of event triggers, use regular triggers on `information_schema` changes (more complex)

## Next Steps

If you need full SQL capture, consider:
1. Using a database migration tool (like Alembic, Flyway) that logs SQL
2. Capturing SQL at the application level before execution
3. Using PostgreSQL's audit logging features
4. Implementing a custom solution using `pg_stat_statements`

For most use cases, the reconstructed SQL (table name + operation type) is sufficient for impact analysis.

