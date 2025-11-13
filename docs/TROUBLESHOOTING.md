# Troubleshooting Guide

## Issue 1: Repository Path Not Found

**Error**: `⚠️ Repository path not found: /app/sample-repo`

**Solution**: The code now tries multiple paths automatically:
- `/sample-repo` (Docker mount)
- `sample-repo` (relative)
- `/app/sample-repo` (alternative Docker)
- `os.getcwd()/sample-repo` (local)

If you still see this error, check:
1. Docker volume mount in `docker-compose.yml`:
   ```yaml
   volumes:
     - ./sample-repo:/sample-repo
   ```

2. Restart backend:
   ```bash
   docker-compose restart backend
   ```

## Issue 2: Frontend Error - Cannot read properties of undefined (reading 'split')

**Error**: `TypeError: Cannot read properties of undefined (reading 'split')`

**Solution**: Fixed! The frontend now handles both:
- Code change results (have `file_path`)
- Schema change results (have `schema_change.table_name`)

**What was fixed**:
- Added type checking for `analysis.type === "schema_change"`
- Added optional chaining (`analysis.file_path?.split()`)
- Different UI for schema changes vs code changes

## Issue 3: PostgreSQL Trigger Not Working

**Symptom**: ALTER TABLE command doesn't trigger the listener

**Solution Steps**:

1. **Verify event trigger exists**:
   ```sql
   \c banking_db
   SELECT * FROM pg_event_trigger WHERE evtname = 'schema_change_trigger';
   ```

2. **If not exists, create it**:
   ```bash
   psql -U postgres -d banking_db -f docs/postgres-trigger-setup.sql
   ```

3. **Verify function exists**:
   ```sql
   SELECT proname FROM pg_proc WHERE proname = 'notify_schema_change';
   ```

4. **Test notification manually**:
   ```sql
   SELECT pg_notify('schema_change', '{"test": "data"}');
   ```

5. **Make sure listener is running**:
   ```bash
   python scripts/postgres_schema_listener.py
   ```

6. **Check PostgreSQL logs**:
   ```bash
   # On Linux
   tail -f /var/log/postgresql/postgresql-*.log
   
   # On Windows (if using PostgreSQL service)
   # Check Event Viewer or PostgreSQL log directory
   ```

7. **Test with a simple change**:
   ```sql
   \c banking_db
   ALTER TABLE transactions ADD COLUMN test_trigger VARCHAR(10);
   ```

   You should see:
   - A NOTICE message in psql (if RAISE NOTICE is enabled)
   - The listener script should detect the change

## Issue 4: Listener Not Detecting Changes

**Possible Causes**:

1. **Listener not running**: Make sure the script is running in a terminal
   ```bash
   python scripts/postgres_schema_listener.py
   ```

2. **Connection issues**: Check database credentials in the listener script
   ```python
   DB_USER = os.getenv("POSTGRES_USER", "postgres")
   DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "sabari")  # Your password
   ```

3. **Event trigger not created**: Run the setup SQL script
   ```bash
   psql -U postgres -d banking_db -f docs/postgres-trigger-setup.sql
   ```

4. **PostgreSQL version**: Event triggers require PostgreSQL 9.3+
   ```sql
   SELECT version();
   ```

## Issue 5: Backend Not Receiving Webhooks

**Check**:

1. **Backend health**:
   ```bash
   curl http://localhost:8000/health
   ```

2. **Test webhook endpoint**:
   ```bash
   curl -X POST http://localhost:8000/api/v1/schema/webhook \
     -H "Content-Type: application/json" \
     -d '{
       "sql_statement": "ALTER TABLE test ADD COLUMN x INT",
       "database_name": "banking_db",
       "change_id": "test_001",
       "repository": "banking-app"
     }'
   ```

3. **Check backend logs**:
   ```bash
   docker-compose logs -f backend
   ```

## Issue 6: Schema Change Analysis Shows 0 Code Files

**Possible Causes**:

1. **Repository path not found**: Check backend logs for path resolution
2. **No code files use the table**: This is normal if no code references the table
3. **Case sensitivity**: Table names might be case-sensitive

**Solution**: The code now tries multiple paths and logs which one it uses:
```
📁 Using repository path: /sample-repo
```

## Quick Fix Checklist

- [ ] Backend is running: `docker-compose ps`
- [ ] PostgreSQL is running: `psql -U postgres -c "SELECT 1;"`
- [ ] Event trigger exists: `SELECT * FROM pg_event_trigger;`
- [ ] Listener script is running: `python scripts/postgres_schema_listener.py`
- [ ] Sample-repo is mounted: Check `docker-compose.yml` volumes
- [ ] Frontend is updated: Restart frontend if needed
- [ ] Check logs: `docker-compose logs -f backend`

## Still Having Issues?

1. Check all logs:
   ```bash
   docker-compose logs backend
   docker-compose logs frontend
   ```

2. Verify database connection:
   ```bash
   psql -U postgres -d banking_db -c "SELECT current_database();"
   ```

3. Test the API directly:
   ```bash
   curl http://localhost:8000/api/v1/schema/analyze \
     -X POST \
     -H "Content-Type: application/json" \
     -d '{"sql_statement": "ALTER TABLE transactions ADD COLUMN test INT", "database_name": "banking_db"}'
   ```

4. Check Neo4j connection:
   ```bash
   curl http://localhost:7474
   ```

