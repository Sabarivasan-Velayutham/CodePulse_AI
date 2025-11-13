# Complete Setup Steps for Database Schema Change Analysis

## Overview

This guide walks you through setting up PostgreSQL and MongoDB with automatic schema change detection that triggers CodeFlow Catalyst analysis.

## Prerequisites

- PostgreSQL 12+ installed and running
- MongoDB 6+ installed and running (optional)
- Python 3.10+ with pip
- CodeFlow Catalyst backend running

## Step 1: Install PostgreSQL Dependencies

```bash
# Install PostgreSQL Python driver
pip install psycopg2-binary

# Or if using requirements.txt
pip install -r backend/requirements.txt
```

## Step 2: Set Up PostgreSQL Database

### 2.1 Connect to PostgreSQL

```bash
psql -U postgres
```

### 2.2 Run Database Setup Script

Copy and paste the SQL from `docs/postgresql-mongodb-setup.md` (Step 1.2-1.4) into psql, or create a file:

```bash
# Create setup file
cat > setup_postgres.sql << 'EOF'
-- Create database
CREATE DATABASE banking_db;

-- Create user
CREATE USER banking_user WITH PASSWORD 'banking123';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE banking_db TO banking_user;

-- Connect to database
\c banking_db

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create tables (copy from docs/postgresql-mongodb-setup.md)
-- ... (tables creation SQL)
EOF

# Run it
psql -U postgres -f setup_postgres.sql
```

### 2.3 Set Up Event Trigger

```sql
-- Connect to banking_db
\c banking_db

-- Create function to notify schema changes
CREATE OR REPLACE FUNCTION notify_schema_change()
RETURNS event_trigger AS $$
DECLARE
    r RECORD;
    sql_text TEXT;
    payload JSONB;
BEGIN
    FOR r IN SELECT * FROM pg_event_trigger_ddl_commands() LOOP
        sql_text := current_query();
        
        payload := jsonb_build_object(
            'tag', r.command_tag,
            'object_type', r.object_type,
            'object_identity', r.object_identity,
            'schema', r.schema_name,
            'sql', sql_text
        );
        
        PERFORM pg_notify('schema_change', payload::text);
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Create event trigger
CREATE EVENT TRIGGER schema_change_trigger
ON ddl_command_end
EXECUTE FUNCTION notify_schema_change();
```

## Step 3: Set Up MongoDB (Optional)

### 3.1 Start MongoDB

```bash
# Start MongoDB service
mongod --dbpath /path/to/data

# Or if installed as service
sudo systemctl start mongod
```

### 3.2 Connect and Create Collections

```bash
mongosh
```

```javascript
use banking_db

// Create sample collections
db.customers.insertOne({
    customer_id: "cust_001",
    first_name: "John",
    last_name: "Doe"
})
```

## Step 4: Start CodeFlow Catalyst Backend

```bash
# Make sure backend is running
docker-compose up -d backend

# Or run directly
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Step 5: Start Schema Change Listeners

### 5.1 PostgreSQL Listener

```bash
# Terminal 1: Start PostgreSQL listener
python scripts/postgres_schema_listener.py
```

### 5.2 MongoDB Listener (Optional)

```bash
# Terminal 2: Start MongoDB listener
python scripts/mongodb_schema_listener.py
```

## Step 6: Test the Setup

### Test 1: Schema Change → Code Analysis

1. **In psql**, make a schema change:
```sql
\c banking_db
ALTER TABLE transactions ADD COLUMN currency VARCHAR(3) DEFAULT 'USD';
```

2. **Watch the listener terminal** - you should see:
   - Schema change detected
   - Analysis triggered
   - Results available

3. **Check dashboard** at `http://localhost:3000` - schema change analysis should appear

### Test 2: Code Commit → Database Analysis

1. **Make a code change** that uses database tables (e.g., modify `TransactionDAO.java`)

2. **Trigger analysis** via API or webhook:
```bash
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "sample-repo/banking-app/src/database/TransactionDAO.java",
    "repository": "banking-app",
    "diff": "your diff here",
    "commit_sha": "test123",
    "commit_message": "test commit"
  }'
```

3. **Check results** - should show:
   - Code dependencies (other files)
   - Database dependencies (tables used)
   - AI insights
   - Risk score

## Step 7: Verify Both Examples Work

### Example 1: Schema Change

**Input**: `ALTER TABLE transactions ADD COLUMN currency VARCHAR(3)`

**Expected Output in Dashboard**:
- ✅ Table dependencies (foreign keys, related tables)
- ✅ Code files using `transactions` table
- ✅ AI insights about schema change impact
- ✅ Risk score
- ✅ Recommendations

### Example 2: Code Commit

**Input**: Change in `TransactionDAO.java`

**Expected Output in Dashboard**:
- ✅ Code dependencies (other Java files)
- ✅ Database tables used in this file (`transactions`, etc.)
- ✅ Related tables (via foreign keys)
- ✅ AI insights about code + database impact
- ✅ Risk score
- ✅ Recommendations

## Troubleshooting

### PostgreSQL Listener Not Working

1. **Check PostgreSQL is running**:
   ```bash
   psql -U postgres -c "SELECT version();"
   ```

2. **Check event trigger exists**:
   ```sql
   SELECT * FROM pg_event_trigger;
   ```

3. **Test notification manually**:
   ```sql
   SELECT pg_notify('schema_change', '{"test": "data"}');
   ```

### MongoDB Listener Not Working

1. **Check MongoDB is running**:
   ```bash
   mongosh --eval "db.adminCommand('ping')"
   ```

2. **Note**: Change streams require replica set for database-level watching
   - For single node, use manual API calls
   - Or set up replica set

### Backend Not Receiving Webhooks

1. **Check backend is running**:
   ```bash
   curl http://localhost:8000/health
   ```

2. **Check listener can reach backend**:
   ```bash
   curl http://localhost:8000/api/v1/schema/analyze \
     -X POST \
     -H "Content-Type: application/json" \
     -d '{"sql_statement": "ALTER TABLE test ADD COLUMN x INT", "database_name": "test"}'
   ```

## Next Steps

1. ✅ Database setup complete
2. ✅ Triggers/listeners configured
3. ✅ Test both examples
4. ⏳ Update frontend to display database dependencies (next step)


