-- PostgreSQL Event Trigger Setup for Schema Change Detection
-- Run this script in your PostgreSQL database to enable automatic schema change notifications

-- Connect to your database first:
-- \c banking_db

-- Step 1: Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_notify";

-- Step 2: Create function to capture DDL changes
-- Note: We need to use pg_stat_statements or capture SQL differently
-- since current_query() doesn't work in event triggers

-- First, enable pg_stat_statements extension (optional but helpful)
-- CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

CREATE OR REPLACE FUNCTION notify_schema_change()
RETURNS event_trigger AS $$
DECLARE
    r RECORD;
    sql_text TEXT;
    payload JSONB;
    cmd_tag TEXT;
    obj_identity TEXT;
    schema_name TEXT;
    column_name TEXT := NULL;
BEGIN
    -- Get the command tag and SQL
    FOR r IN SELECT * FROM pg_event_trigger_ddl_commands() LOOP
        cmd_tag := r.command_tag;
        obj_identity := r.object_identity;
        schema_name := COALESCE(r.schema_name, 'public');
        
        -- Try to extract column name for ALTER TABLE operations
        -- This is a best-effort approach since we can't get the full SQL in event triggers
        IF cmd_tag = 'ALTER TABLE' THEN
            -- For ALTER TABLE, we'll need to parse the object_identity
            -- Format is usually: schema.table or just table
            -- We can't get the exact SQL, but we can notify with what we have
            sql_text := cmd_tag || ' ' || obj_identity;
        ELSE
            sql_text := cmd_tag || ' ' || obj_identity;
        END IF;
        
        -- Build payload with all available information
        payload := jsonb_build_object(
            'tag', cmd_tag,
            'object_type', r.object_type,
            'object_identity', obj_identity,
            'schema', schema_name,
            'sql', sql_text,
            'timestamp', NOW()::text
        );
        
        -- Notify via pg_notify
        PERFORM pg_notify('schema_change', payload::text);
        
        -- Debug output
        RAISE NOTICE 'Schema change detected: % on %', cmd_tag, obj_identity;
        RAISE NOTICE 'Notification sent to channel: schema_change';
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Step 3: Create event trigger
-- Drop if exists first
DROP EVENT TRIGGER IF EXISTS schema_change_trigger;

CREATE EVENT TRIGGER schema_change_trigger
ON ddl_command_end
EXECUTE FUNCTION notify_schema_change();

-- Step 4: Verify trigger is created
SELECT * FROM pg_event_trigger WHERE evtname = 'schema_change_trigger';

-- Step 5: Test the trigger
-- Make a test change:
-- ALTER TABLE transactions ADD COLUMN test_column VARCHAR(10);

-- If you see a NOTICE message, the trigger is working!
-- The listener script should pick up the notification

-- Troubleshooting:
-- 1. Check if event trigger exists:
--    SELECT * FROM pg_event_trigger;

-- 2. Check if function exists:
--    SELECT proname FROM pg_proc WHERE proname = 'notify_schema_change';

-- 3. Test notification manually:
--    SELECT pg_notify('schema_change', '{"test": "data"}');

-- 4. Check PostgreSQL logs for errors:
--    tail -f /var/log/postgresql/postgresql-*.log

-- 5. Make sure the listener script is running:
--    python scripts/postgres_schema_listener.py

