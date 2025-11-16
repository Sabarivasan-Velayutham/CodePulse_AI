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

-- Enhanced function to capture complete SQL using pg_stat_statements or query history
-- Note: PostgreSQL event triggers don't have direct access to the SQL statement
-- We'll use a combination of approaches to reconstruct the SQL

-- Function 1: Handle DROP operations (sql_drop event trigger)
-- This function can use pg_event_trigger_dropped_objects()
CREATE OR REPLACE FUNCTION notify_schema_drop()
RETURNS event_trigger AS $$
DECLARE
    d RECORD;
    sql_text TEXT;
    payload JSONB;
    schema_name TEXT;
    table_name TEXT;
    dropped_column TEXT;
BEGIN
    -- pg_event_trigger_dropped_objects() is ONLY available in sql_drop triggers
    FOR d IN SELECT * FROM pg_event_trigger_dropped_objects() LOOP
        IF d.object_type = 'column' THEN
            -- A column was dropped!
            dropped_column := d.object_name;
            
            -- object_identity format: schema.table.column or table.column
            -- Extract table name and schema
            -- Count dots: 2 dots = schema.table.column, 1 dot = table.column
            IF position('.' in d.object_identity) > 0 THEN
                -- Check if we have 2 dots (schema.table.column) or 1 dot (table.column)
                IF length(d.object_identity) - length(replace(d.object_identity, '.', '')) = 2 THEN
                    -- Three parts: schema.table.column
                    schema_name := split_part(d.object_identity, '.', 1);
                    table_name := split_part(d.object_identity, '.', 2);
                ELSE
                    -- Two parts: table.column
                    schema_name := 'public';
                    table_name := split_part(d.object_identity, '.', 1);
                END IF;
            ELSE
                -- Single part (shouldn't happen for columns, but handle it)
                schema_name := 'public';
                table_name := d.object_identity;
            END IF;
            
            -- Reconstruct complete SQL for DROP COLUMN
            sql_text := 'ALTER TABLE ' || schema_name || '.' || table_name || ' DROP COLUMN ' || dropped_column;
            
            -- Build payload with complete information
            payload := jsonb_build_object(
                'tag', 'ALTER TABLE',
                'object_type', 'column',
                'object_identity', d.object_identity,
                'schema', schema_name,
                'table_name', table_name,
                'column_name', dropped_column,
                'operation', 'DROP_COLUMN',
                'sql', sql_text,
                'timestamp', NOW()::text
            );
            
            -- Notify
            PERFORM pg_notify('schema_change', payload::text);
            RAISE NOTICE 'Schema change detected: DROP COLUMN % from %', dropped_column, table_name;
            RAISE NOTICE 'SQL: %', sql_text;
            RAISE NOTICE 'Notification sent to channel: schema_change';
        END IF;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Function 2: Handle ADD/MODIFY operations (ddl_command_end event trigger)
-- This function handles ALTER TABLE ADD COLUMN, MODIFY COLUMN, etc.
CREATE OR REPLACE FUNCTION notify_schema_change()
RETURNS event_trigger AS $$
DECLARE
    r RECORD;
    sql_text TEXT;
    payload JSONB;
    cmd_tag TEXT;
    obj_identity TEXT;
    schema_name TEXT;
    table_name TEXT;
    full_sql TEXT;
BEGIN
    -- Check for DDL commands (ADD, MODIFY, etc.)
    FOR r IN SELECT * FROM pg_event_trigger_ddl_commands() LOOP
        cmd_tag := r.command_tag;
        obj_identity := r.object_identity;
        schema_name := COALESCE(r.schema_name, 'public');
        
        -- Extract table name from object_identity (format: schema.table or table)
        IF position('.' in obj_identity) > 0 THEN
            table_name := split_part(obj_identity, '.', 2);
        ELSE
            table_name := obj_identity;
        END IF;
        
        -- Try to get the actual SQL from pg_stat_statements if available
        -- Otherwise, reconstruct from available information
        IF cmd_tag = 'ALTER TABLE' THEN
            -- For ALTER TABLE, try to get more details from pg_stat_statements
            -- This requires pg_stat_statements extension to be enabled
            BEGIN
                SELECT query INTO full_sql
                FROM pg_stat_statements
                WHERE query LIKE '%ALTER TABLE%' || table_name || '%'
                ORDER BY calls DESC, mean_exec_time DESC
                LIMIT 1;
                
                -- If we found a query, use it
                IF full_sql IS NOT NULL THEN
                    sql_text := full_sql;
                ELSE
                    -- Fallback: reconstruct from available info
                    sql_text := cmd_tag || ' ' || schema_name || '.' || table_name;
                END IF;
            EXCEPTION WHEN OTHERS THEN
                -- pg_stat_statements not available or query failed
                sql_text := cmd_tag || ' ' || schema_name || '.' || table_name;
            END;
        ELSE
            sql_text := cmd_tag || ' ' || obj_identity;
        END IF;
        
        -- Build payload with all available information
        payload := jsonb_build_object(
            'tag', cmd_tag,
            'object_type', r.object_type,
            'object_identity', obj_identity,
            'schema', schema_name,
            'table_name', table_name,
            'sql', sql_text,
            'timestamp', NOW()::text
        );
        
        -- Notify via pg_notify
        PERFORM pg_notify('schema_change', payload::text);
        
        -- Debug output
        RAISE NOTICE 'Schema change detected: % on %', cmd_tag, obj_identity;
        RAISE NOTICE 'SQL: %', sql_text;
        RAISE NOTICE 'Notification sent to channel: schema_change';
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Step 3: Create event triggers
-- Drop if exists first
DROP EVENT TRIGGER IF EXISTS schema_change_trigger;
DROP EVENT TRIGGER IF EXISTS schema_drop_trigger;

-- Trigger 1: Handle DROP operations (sql_drop event)
CREATE EVENT TRIGGER schema_drop_trigger
ON sql_drop
EXECUTE FUNCTION notify_schema_drop();

-- Trigger 2: Handle ADD/MODIFY operations (ddl_command_end event)
CREATE EVENT TRIGGER schema_change_trigger
ON ddl_command_end
EXECUTE FUNCTION notify_schema_change();

-- Step 4: Verify triggers are created
SELECT * FROM pg_event_trigger WHERE evtname IN ('schema_change_trigger', 'schema_drop_trigger');

-- Step 5: Test the trigger
-- Make a test change:
-- ALTER TABLE transactions ADD COLUMN test_column VARCHAR(10);

-- If you see a NOTICE message, the trigger is working!
-- The listener script should pick up the notification

-- Troubleshooting:
-- 1. Check if event triggers exist:
--    SELECT * FROM pg_event_trigger WHERE evtname IN ('schema_change_trigger', 'schema_drop_trigger');

-- 2. Check if functions exist:
--    SELECT proname FROM pg_proc WHERE proname IN ('notify_schema_change', 'notify_schema_drop');

-- 3. Test notification manually:
--    SELECT pg_notify('schema_change', '{"test": "data"}');

-- 4. Check PostgreSQL logs for errors:
--    tail -f /var/log/postgresql/postgresql-*.log

-- 5. Make sure the listener script is running:
--    python scripts/postgres_schema_listener.py

