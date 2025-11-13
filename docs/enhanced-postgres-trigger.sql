-- ============================================================
-- Enhanced PostgreSQL Event Trigger for Schema Changes
-- ============================================================
-- This trigger captures more detailed information about schema changes
-- including foreign keys, views, triggers, and functions
-- ============================================================

\c banking_db

-- Drop existing trigger if exists
DROP EVENT TRIGGER IF EXISTS schema_change_trigger;
DROP FUNCTION IF EXISTS notify_schema_change();

-- Enhanced function to capture DDL changes with more context
CREATE OR REPLACE FUNCTION notify_schema_change()
RETURNS event_trigger AS $$
DECLARE
    r RECORD;
    sql_text TEXT;
    payload JSONB;
    cmd_tag TEXT;
    obj_identity TEXT;
    schema_name TEXT;
    object_type TEXT;
    affected_objects TEXT[];
    relationship_info JSONB;
BEGIN
    -- Get the command tag and SQL
    FOR r IN SELECT * FROM pg_event_trigger_ddl_commands() LOOP
        cmd_tag := r.command_tag;
        obj_identity := r.object_identity;
        schema_name := COALESCE(r.schema_name, 'public');
        object_type := r.object_type;
        
        -- Try to extract more information based on object type
        affected_objects := ARRAY[]::TEXT[];
        relationship_info := '{}'::JSONB;
        
        -- For ALTER TABLE, try to get more details
        IF cmd_tag = 'ALTER TABLE' THEN
            -- Try to detect if it's a foreign key, column, or constraint change
            -- This is limited by what event triggers can see, but we try our best
            sql_text := cmd_tag || ' ' || obj_identity;
            
            -- Try to get foreign key information if available
            BEGIN
                SELECT jsonb_agg(
                    jsonb_build_object(
                        'referenced_table', confrelid::regclass::text,
                        'referenced_column', a2.attname,
                        'local_column', a1.attname
                    )
                ) INTO relationship_info
                FROM pg_constraint c
                JOIN pg_class t1 ON c.conrelid = t1.oid
                JOIN pg_class t2 ON c.confrelid = t2.oid
                JOIN pg_attribute a1 ON a1.attrelid = t1.oid AND a1.attnum = ANY(c.conkey)
                JOIN pg_attribute a2 ON a2.attrelid = t2.oid AND a2.attnum = ANY(c.confkey)
                WHERE t1.relname = SPLIT_PART(obj_identity, '.', 2)
                AND c.contype = 'f'
                LIMIT 1;
            EXCEPTION
                WHEN OTHERS THEN
                    relationship_info := '{}'::JSONB;
            END;
        ELSE
            sql_text := cmd_tag || ' ' || obj_identity;
        END IF;
        
        -- Build comprehensive payload
        payload := jsonb_build_object(
            'tag', cmd_tag,
            'object_type', object_type,
            'object_identity', obj_identity,
            'schema', schema_name,
            'sql', sql_text,
            'timestamp', NOW()::text,
            'relationships', relationship_info,
            'affected_objects', affected_objects
        );
        
        -- Notify via pg_notify
        PERFORM pg_notify('schema_change', payload::text);
        
        -- Debug output
        RAISE NOTICE 'Schema change detected: % on %', cmd_tag, obj_identity;
        RAISE NOTICE 'Notification sent to channel: schema_change';
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Create event trigger
CREATE EVENT TRIGGER schema_change_trigger
ON ddl_command_end
EXECUTE FUNCTION notify_schema_change();

-- Verify trigger is created
SELECT * FROM pg_event_trigger WHERE evtname = 'schema_change_trigger';

-- ============================================================
-- Additional Helper Function: Get Table Dependencies
-- ============================================================
-- This function can be called to get all dependencies for a table
-- Useful for impact analysis

CREATE OR REPLACE FUNCTION get_table_dependencies(p_table_name TEXT)
RETURNS JSONB AS $$
DECLARE
    result JSONB;
    fk_info JSONB;
    view_info JSONB;
    trigger_info JSONB;
    function_info JSONB;
BEGIN
    -- Get foreign key relationships
    SELECT jsonb_agg(
        jsonb_build_object(
            'type', 'FOREIGN_KEY',
            'local_table', t1.relname,
            'local_column', a1.attname,
            'referenced_table', t2.relname,
            'referenced_column', a2.attname,
            'constraint_name', c.conname
        )
    ) INTO fk_info
    FROM pg_constraint c
    JOIN pg_class t1 ON c.conrelid = t1.oid
    JOIN pg_class t2 ON c.confrelid = t2.oid
    JOIN pg_attribute a1 ON a1.attrelid = t1.oid AND a1.attnum = ANY(c.conkey)
    JOIN pg_attribute a2 ON a2.attrelid = t2.oid AND a2.attnum = ANY(c.confkey)
    WHERE t1.relname = p_table_name
    AND c.contype = 'f';
    
    -- Get reverse foreign keys (tables that reference this table)
    SELECT jsonb_agg(
        jsonb_build_object(
            'type', 'REFERENCED_BY',
            'referencing_table', t1.relname,
            'referencing_column', a1.attname,
            'referenced_table', t2.relname,
            'referenced_column', a2.attname,
            'constraint_name', c.conname
        )
    ) INTO view_info
    FROM pg_constraint c
    JOIN pg_class t1 ON c.conrelid = t1.oid
    JOIN pg_class t2 ON c.confrelid = t2.oid
    JOIN pg_attribute a1 ON a1.attrelid = t1.oid AND a1.attnum = ANY(c.conkey)
    JOIN pg_attribute a2 ON a2.attrelid = t2.oid AND a2.attnum = ANY(c.confkey)
    WHERE t2.relname = p_table_name
    AND c.contype = 'f';
    
    -- Get views that depend on this table
    SELECT jsonb_agg(
        jsonb_build_object(
            'type', 'VIEW',
            'view_name', v.viewname,
            'definition', v.definition
        )
    ) INTO view_info
    FROM pg_views v
    WHERE v.viewdefinition LIKE '%' || p_table_name || '%';
    
    -- Get triggers on this table
    SELECT jsonb_agg(
        jsonb_build_object(
            'type', 'TRIGGER',
            'trigger_name', t.tgname,
            'function_name', p.proname
        )
    ) INTO trigger_info
    FROM pg_trigger t
    JOIN pg_class c ON t.tgrelid = c.oid
    JOIN pg_proc p ON t.tgfoid = p.oid
    WHERE c.relname = p_table_name
    AND NOT t.tgisinternal;
    
    -- Build result
    result := jsonb_build_object(
        'table_name', p_table_name,
        'foreign_keys', COALESCE(fk_info, '[]'::JSONB),
        'referenced_by', COALESCE(view_info, '[]'::JSONB),
        'views', COALESCE(view_info, '[]'::JSONB),
        'triggers', COALESCE(trigger_info, '[]'::JSONB)
    );
    
    RETURN result;
END;
$$ LANGUAGE plpgsql;

-- Test the function
-- SELECT get_table_dependencies('transactions');

