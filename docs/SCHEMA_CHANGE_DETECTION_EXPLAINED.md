# How Schema Change Detection Works

## The Challenge: PostgreSQL Event Trigger Limitations

### What PostgreSQL Event Triggers CANNOT Do

PostgreSQL event triggers have a **fundamental limitation**: they **cannot access the full SQL statement** that triggered the change.

**Why?** Event triggers fire **after** the DDL command completes, and PostgreSQL doesn't store the original SQL statement in a way that's accessible to event triggers.

### What PostgreSQL Event Triggers CAN Provide

When a schema change occurs, the event trigger receives:

```json
{
  "tag": "ALTER TABLE",           // Command type (generic)
  "object_type": "table",         // Type of object changed
  "object_identity": "public.transactions",  // Table name
  "schema": "public"               // Schema name
}
```

**Notice**: There's NO information about:
- ❌ What column was added/dropped/modified
- ❌ The column data type
- ❌ The full SQL statement
- ❌ Whether it was ADD, DROP, or MODIFY

## Current Detection Flow

### Step 1: PostgreSQL Event Trigger (`docs/postgres-trigger-setup.sql`)

```sql
CREATE OR REPLACE FUNCTION notify_schema_change()
RETURNS event_trigger AS $$
BEGIN
    FOR r IN SELECT * FROM pg_event_trigger_ddl_commands() LOOP
        -- We only get: command_tag, object_identity, object_type
        sql_text := cmd_tag || ' ' || obj_identity;  -- "ALTER TABLE public.transactions"
        
        PERFORM pg_notify('schema_change', payload::text);
    END LOOP;
END;
$$ LANGUAGE plpgsql;
```

**Output**: `"ALTER TABLE public.transactions"` (incomplete!)

### Step 2: Listener Script (`scripts/postgres_schema_listener.py`)

The listener receives the notification and tries to reconstruct:

```python
sql_statement = payload.get('sql', '')  # "ALTER TABLE public.transactions"
if not sql_statement or len(sql_statement.split()) <= 2:
    # Try to reconstruct - but still incomplete!
    sql_statement = f"ALTER TABLE {object_identity}"  # Still just "ALTER TABLE public.transactions"
```

**Output**: `"ALTER TABLE public.transactions"` (still incomplete!)

### Step 3: Backend Schema Analyzer (`backend/app/services/schema_analyzer.py`)

The backend tries to parse the SQL:

```python
def parse_schema_change(self, sql_statement: str):
    # sql_statement = "ALTER TABLE public.transactions"
    
    # Try to find ADD COLUMN
    add_col_match = re.search(r'ADD\s+COLUMN\s+`?(\w+)`?', sql_upper)
    # ❌ Fails - "ADD COLUMN" not in the string!
    
    # Try to find DROP COLUMN
    drop_col_match = re.search(r'DROP\s+COLUMN\s+`?(\w+)`?', sql_upper)
    # ❌ Fails - "DROP COLUMN" not in the string!
    
    # Falls back to generic
    return SchemaChange(change_type="ALTER_TABLE", ...)  # Generic!
```

**Output**: `ALTER_TABLE` (generic, no column details)

### Step 4: Enhancement (`backend/app/engine/schema_orchestrator.py`)

We try to enhance by parsing the SQL more carefully:

```python
async def _enhance_schema_change_from_db(self, schema_change, database_name):
    sql_upper = schema_change.sql_statement.upper()  # "ALTER TABLE PUBLIC.TRANSACTIONS"
    
    # Try to detect ADD COLUMN
    if 'ADD' in sql_upper and 'COLUMN' in sql_upper:
        # ❌ Still fails - these keywords aren't in the incomplete SQL!
    
    return schema_change  # Still generic ALTER_TABLE
```

**Result**: We can't detect the exact change from incomplete SQL!

## The Solution: Better SQL Reconstruction

### Option 1: Query Database After Change (Recommended)

We can query PostgreSQL **after** the change to see what actually changed:

```python
# After detecting "ALTER TABLE transactions"
# Query the database to see what columns exist now vs. what we stored before
# Compare to detect: new column = ADD_COLUMN, missing column = DROP_COLUMN
```

### Option 2: Use pg_stat_statements (Limited)

Enable `pg_stat_statements` extension to capture recent SQL:

```sql
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Query recent statements
SELECT query FROM pg_stat_statements 
WHERE query LIKE 'ALTER TABLE%' 
ORDER BY calls DESC LIMIT 1;
```

**Limitation**: Only works if the extension is enabled and the query is recent.

### Option 3: Application-Level Capture (Best for Production)

Capture SQL at the application/migration tool level:

```python
# In your migration tool (Alembic, Flyway, etc.)
# Before executing: ALTER TABLE transactions ADD COLUMN currency VARCHAR(3)
# Send full SQL to webhook: /api/v1/schema/analyze
```

## Current Implementation Status

### What Works Now

✅ **Table Name Detection**: We can extract the table name from incomplete SQL
✅ **Generic Change Detection**: We know "ALTER TABLE" happened
✅ **Database Relationships**: We can query PostgreSQL for FK, views, triggers
✅ **Code Dependencies**: We can find code files using the table

### What Doesn't Work Yet

❌ **Exact Operation Type**: Can't reliably detect ADD vs DROP vs MODIFY from incomplete SQL
❌ **Column Name**: Can't extract column name from incomplete SQL
❌ **Column Type**: Can't extract data type from incomplete SQL

### Workaround: Manual API Calls

For testing, you can call the API directly with full SQL:

```bash
curl -X POST http://localhost:8000/api/v1/schema/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "sql_statement": "ALTER TABLE transactions ADD COLUMN currency VARCHAR(3) DEFAULT '\''USD'\''",
    "database_name": "banking_db",
    "change_id": "test_001",
    "repository": "banking-app"
  }'
```

This will work perfectly because we have the full SQL!

## Recommended Improvements

### 1. Query Database Schema After Change

```python
async def _detect_actual_change(self, table_name, database_name):
    """Query PostgreSQL to detect what actually changed"""
    # Get current columns
    cursor.execute("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = %s
    """, (table_name.lower(),))
    current_columns = {row[0]: row[1] for row in cursor.fetchall()}
    
    # Compare with stored schema (from Neo4j or cache)
    # Detect: new columns = ADD_COLUMN, missing = DROP_COLUMN, changed type = MODIFY_COLUMN
```

### 2. Store Schema Snapshot

Before each change, store a snapshot of the table schema in Neo4j, then compare after.

### 3. Use Migration Tool Integration

Integrate with Alembic/Flyway to capture full SQL before execution.

## Summary

**Current State**:
- ✅ Detects that a schema change occurred
- ✅ Identifies which table was changed
- ❌ Cannot detect exact operation (ADD/DROP/MODIFY) from event trigger
- ❌ Cannot extract column name/type from incomplete SQL

**Why**: PostgreSQL event triggers don't provide full SQL - this is a PostgreSQL limitation, not a bug in our code.

**Solution**: Use direct API calls with full SQL for accurate detection, or implement database schema comparison to detect actual changes.

