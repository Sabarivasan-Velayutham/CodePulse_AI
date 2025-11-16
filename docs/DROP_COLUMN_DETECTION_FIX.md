# DROP COLUMN Detection Fix

## Problem
When running `DROP COLUMN` commands, the system was incorrectly detecting them as `ADD_COLUMN` and showing wrong information.

### Root Cause
1. **PostgreSQL trigger** only sent incomplete SQL: `ALTER TABLE public.transactions` (missing `DROP COLUMN currency`)
2. **System catalog detection** assumed the newest column was added, incorrectly detecting `ADD_COLUMN` for `DROP` operations
3. **Regex parsing** couldn't detect `DROP COLUMN` from incomplete SQL

## Solution

### 1. Enhanced PostgreSQL Trigger
Updated `docs/postgres-trigger-setup.sql` to use `pg_event_trigger_dropped_objects()`:

```sql
-- First, check for dropped objects (DROP COLUMN, etc.)
FOR d IN SELECT * FROM pg_event_trigger_dropped_objects() LOOP
    IF d.object_type = 'column' THEN
        -- A column was dropped!
        dropped_column := d.object_name;
        -- Reconstruct full SQL: ALTER TABLE schema.table DROP COLUMN column_name
        sql_text := 'ALTER TABLE ' || schema_name || '.' || table_name || ' DROP COLUMN ' || dropped_column;
    END IF;
END LOOP;
```

**Benefits:**
- ✅ Detects exact column name that was dropped
- ✅ Reconstructs complete SQL statement
- ✅ Works without `pg_stat_statements`

### 2. Improved Listener
Updated `scripts/postgres_schema_listener.py` to handle `DROP_COLUMN` operation from trigger payload:

```python
operation = payload.get('operation', '')  # DROP_COLUMN
column_name = payload.get('column_name', '')

if operation == 'DROP_COLUMN' and column_name:
    sql_statement = f"ALTER TABLE {schema}.{table_name} DROP COLUMN {column_name}"
```

### 3. Fixed Backend Detection Logic
Updated `backend/app/engine/schema_orchestrator.py`:

**Key Changes:**
1. **Check DROP operations FIRST** (before ADD detection)
2. **Only use system catalog detection for ADD operations** (when `DROP` is not in SQL)
3. **Improved regex patterns** for DROP COLUMN detection

```python
# Check DROP first to avoid false positives
if 'DROP' in sql_upper and 'COLUMN' in sql_upper:
    # Detect DROP COLUMN
    return DROP_COLUMN

# Only use system catalog for ADD operations
if 'DROP' not in sql_upper:
    # Query system catalogs to find newest column (ADD operation)
    ...
```

### 4. Enhanced Schema Analyzer
Updated `backend/app/services/schema_analyzer.py` with better DROP COLUMN regex:

```python
# More flexible pattern
drop_col_match = re.search(r'DROP\s+(?:COLUMN\s+)?`?(\w+)`?', sql_upper, re.IGNORECASE)
```

## How It Works Now

### For DROP COLUMN:
1. **PostgreSQL trigger** detects dropped column via `pg_event_trigger_dropped_objects()`
2. **Reconstructs full SQL**: `ALTER TABLE public.transactions DROP COLUMN currency`
3. **Listener** receives complete SQL with `operation: DROP_COLUMN`
4. **Backend** correctly detects `DROP_COLUMN` change type
5. **Frontend** shows correct information

### For ADD COLUMN:
1. **PostgreSQL trigger** sends incomplete SQL: `ALTER TABLE public.transactions`
2. **System catalog detection** queries PostgreSQL to find newest column
3. **Backend** detects `ADD_COLUMN` with correct column name and type
4. **Frontend** shows correct information

## Testing

After updating the trigger, test with:

```sql
-- This should now correctly detect DROP_COLUMN
ALTER TABLE transactions DROP COLUMN currency;

-- This should correctly detect ADD_COLUMN
ALTER TABLE transactions ADD COLUMN currency VARCHAR(3) DEFAULT 'USD';
```

## Expected Results

**Before Fix:**
- ❌ `DROP COLUMN currency` → Detected as `ADD_COLUMN` with wrong column info

**After Fix:**
- ✅ `DROP COLUMN currency` → Detected as `DROP_COLUMN` with correct column name
- ✅ `ADD COLUMN currency` → Detected as `ADD_COLUMN` with correct column info

## Next Steps

1. **Update the trigger** in your PostgreSQL database:
   ```sql
   -- Run the updated trigger setup script
   \i docs/postgres-trigger-setup.sql
   ```

2. **Restart the listener** (if running):
   ```bash
   python scripts/postgres_schema_listener.py
   ```

3. **Test DROP COLUMN** commands - they should now be detected correctly!

