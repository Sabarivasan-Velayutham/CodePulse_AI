# MySQL Compatibility Guide

## Current Status: ❌ **Not Compatible with MySQL**

The project is **heavily PostgreSQL-specific** and requires significant modifications to work with MySQL.

## PostgreSQL-Specific Features Used

### 1. **PostgreSQL Event Triggers** ⚠️
**Location**: `docs/postgres-trigger-setup.sql`

PostgreSQL uses **event triggers** that fire on DDL commands:
```sql
CREATE EVENT TRIGGER schema_change_trigger
ON ddl_command_end
EXECUTE FUNCTION notify_schema_change();
```

**MySQL Equivalent**: MySQL doesn't have event triggers. You need to use:
- **MySQL Triggers** (table-level, not DDL-level)
- **MySQL General Query Log** (requires file access)
- **MySQL Binlog** (requires replication setup)
- **Application-level hooks** (migration tools)

### 2. **pg_notify / LISTEN** ⚠️
**Location**: `scripts/postgres_schema_listener.py`

PostgreSQL uses `pg_notify()` and `LISTEN` for asynchronous notifications:
```python
cursor.execute("LISTEN schema_change;")
```

**MySQL Equivalent**: MySQL doesn't have a notification system. Alternatives:
- Poll MySQL's `information_schema` periodically
- Use MySQL triggers to write to a notification table
- Use external message queue (Redis, RabbitMQ)

### 3. **PostgreSQL System Catalogs** ⚠️
**Location**: `backend/app/engine/schema_orchestrator.py`

Queries PostgreSQL-specific system catalogs:
```sql
SELECT * FROM pg_attribute a
JOIN pg_class c ON a.attrelid = c.oid
JOIN pg_namespace n ON c.relnamespace = n.oid
WHERE n.nspname = 'public'
AND c.relname = 'transactions'
```

**MySQL Equivalent**: Use MySQL's `information_schema`:
```sql
SELECT * FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = 'banking_db'
AND TABLE_NAME = 'transactions'
```

### 4. **psycopg2 Database Adapter** ⚠️
**Location**: `backend/requirements.txt`, `backend/app/engine/schema_orchestrator.py`

Uses `psycopg2` for PostgreSQL connections:
```python
import psycopg2
conn = psycopg2.connect(...)
```

**MySQL Equivalent**: Use MySQL connector:
```python
import mysql.connector
# or
import pymysql
```

### 5. **PostgreSQL-Specific SQL Syntax** ⚠️
**Location**: `backend/app/services/schema_analyzer.py`

Handles PostgreSQL syntax:
- `ALTER COLUMN ... TYPE` (PostgreSQL)
- `MODIFY COLUMN ...` (MySQL)

**Current Support**: The analyzer already supports both syntaxes, but detection logic is PostgreSQL-focused.

## What Would Need to Change

### 1. **Database Connection Layer**

**Current** (`backend/app/engine/schema_orchestrator.py`):
```python
import psycopg2
conn = psycopg2.connect(
    host=db_host,
    port=db_port,
    database=db_name,
    user=db_user,
    password=db_password
)
```

**MySQL Version**:
```python
import mysql.connector
conn = mysql.connector.connect(
    host=db_host,
    port=db_port,
    database=db_name,
    user=db_user,
    password=db_password
)
```

### 2. **Schema Change Detection**

**PostgreSQL**: Event triggers + `pg_notify`

**MySQL Options**:

#### Option A: MySQL Triggers (Limited)
```sql
DELIMITER $$
CREATE TRIGGER schema_change_trigger
AFTER INSERT ON schema_changes_log
FOR EACH ROW
BEGIN
    -- Write to notification table
    INSERT INTO schema_notifications (change_sql) VALUES (NEW.sql_statement);
END$$
DELIMITER ;
```

**Limitation**: MySQL triggers can't detect DDL changes directly. You'd need to manually log changes.

#### Option B: Information Schema Polling
```python
# Poll information_schema periodically
def detect_schema_changes():
    current_schema = get_current_schema()
    previous_schema = get_stored_schema()
    changes = compare_schemas(current_schema, previous_schema)
    return changes
```

#### Option C: Binlog Parsing
```python
# Use mysql-replication or python-mysql-replication
from pymysqlreplication import BinLogStreamReader
stream = BinLogStreamReader(...)
for binlogevent in stream:
    if binlogevent.event_type == "QUERY_EVENT":
        if "ALTER TABLE" in binlogevent.query:
            analyze_change(binlogevent.query)
```

#### Option D: Migration Tool Integration (Recommended)
```python
# Hook into Alembic/Flyway/Liquibase
# Before migration: capture SQL
# Send to API: /api/v1/schema/analyze
```

### 3. **System Catalog Queries**

**PostgreSQL**:
```sql
SELECT a.attname, pg_catalog.format_type(a.atttypid, a.atttypmod)
FROM pg_attribute a
JOIN pg_class c ON a.attrelid = c.oid
```

**MySQL**:
```sql
SELECT COLUMN_NAME, DATA_TYPE, COLUMN_TYPE
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = 'banking_db'
AND TABLE_NAME = 'transactions'
```

### 4. **Listener Script**

**PostgreSQL** (`scripts/postgres_schema_listener.py`):
```python
cursor.execute("LISTEN schema_change;")
conn.poll()  # Wait for notifications
```

**MySQL**: Would need to:
- Poll a notification table
- Use message queue (Redis/RabbitMQ)
- Use webhook from migration tool

### 5. **SQL Syntax Differences**

| Operation | PostgreSQL | MySQL |
|-----------|------------|-------|
| Modify Column Type | `ALTER COLUMN ... TYPE` | `MODIFY COLUMN ...` |
| Set Default | `ALTER COLUMN ... SET DEFAULT` | `ALTER COLUMN ... SET DEFAULT` ✅ |
| Drop Default | `ALTER COLUMN ... DROP DEFAULT` | `ALTER COLUMN ... DROP DEFAULT` ✅ |
| Set NOT NULL | `ALTER COLUMN ... SET NOT NULL` | `MODIFY COLUMN ... NOT NULL` |
| Drop NOT NULL | `ALTER COLUMN ... DROP NOT NULL` | `MODIFY COLUMN ... NULL` |

**Good News**: The `schema_analyzer.py` already handles both syntaxes via regex patterns!

## What Would Work As-Is

✅ **Schema Analyzer** (`backend/app/services/schema_analyzer.py`)
- Regex patterns work for both PostgreSQL and MySQL SQL syntax
- Already supports `MODIFY COLUMN` (MySQL) and `ALTER COLUMN` (PostgreSQL)

✅ **Code Dependency Analysis**
- Works independently of database type
- Scans code files for SQL queries and table references

✅ **Risk Scoring**
- Database-agnostic logic
- Works for any schema change type

✅ **Frontend**
- Displays analysis results regardless of database type

✅ **Neo4j Storage**
- Graph database is independent of source database

## Migration Path to MySQL

### Step 1: Create Database Abstraction Layer

```python
# backend/app/services/db_adapter.py
class DatabaseAdapter:
    def connect(self, host, port, database, user, password):
        raise NotImplementedError
    
    def get_table_columns(self, table_name):
        raise NotImplementedError
    
    def get_foreign_keys(self, table_name):
        raise NotImplementedError

class PostgreSQLAdapter(DatabaseAdapter):
    def connect(self, ...):
        return psycopg2.connect(...)
    
    def get_table_columns(self, table_name):
        # Query pg_attribute, pg_class

class MySQLAdapter(DatabaseAdapter):
    def connect(self, ...):
        return mysql.connector.connect(...)
    
    def get_table_columns(self, table_name):
        # Query information_schema.COLUMNS
```

### Step 2: Create MySQL Schema Change Detector

**Option A: Information Schema Polling**
```python
# scripts/mysql_schema_poller.py
def poll_mysql_schema():
    current = get_mysql_schema()
    previous = load_stored_schema()
    changes = detect_changes(current, previous)
    for change in changes:
        send_to_api(change)
```

**Option B: Migration Tool Hook**
```python
# Integrate with Alembic
@event.listens_for(Operations, "before_execute")
def capture_sql(conn, clauseelement, multiparams, params):
    if "ALTER TABLE" in str(clauseelement):
        send_to_api(str(clauseelement))
```

### Step 3: Update Configuration

```python
# backend/config.py
DATABASE_TYPE = os.getenv("DATABASE_TYPE", "postgresql")  # or "mysql"

if DATABASE_TYPE == "mysql":
    from app.services.mysql_adapter import MySQLAdapter
    db_adapter = MySQLAdapter()
else:
    from app.services.postgres_adapter import PostgreSQLAdapter
    db_adapter = PostgreSQLAdapter()
```

### Step 4: Create MySQL Trigger Setup

```sql
-- mysql-trigger-setup.sql
-- Note: MySQL triggers can't detect DDL, so we use a workaround

-- Create a log table
CREATE TABLE schema_changes_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    sql_statement TEXT,
    table_name VARCHAR(255),
    change_type VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Manual logging (or via migration tool)
-- INSERT INTO schema_changes_log (sql_statement, table_name, change_type)
-- VALUES ('ALTER TABLE transactions ADD COLUMN currency VARCHAR(3)', 'transactions', 'ADD_COLUMN');
```

## Recommended Approach for MySQL

### **Best Option: Direct API Calls**

Since MySQL doesn't have event triggers, the most reliable approach is:

1. **Use Migration Tools** (Alembic, Flyway, Liquibase)
2. **Hook into migration execution**
3. **Send full SQL to API before/after execution**

```python
# In your migration tool
def execute_migration(sql):
    # Before execution
    response = requests.post(
        "http://localhost:8000/api/v1/schema/analyze",
        json={
            "sql_statement": sql,
            "database_name": "banking_db",
            "change_id": f"migration_{timestamp}",
            "repository": "banking-app"
        }
    )
    
    # Execute migration
    execute_sql(sql)
```

### **Alternative: Information Schema Polling**

```python
# scripts/mysql_schema_poller.py
import time
from app.services.mysql_adapter import MySQLAdapter

def poll_schema_changes():
    adapter = MySQLAdapter()
    previous_schema = load_schema_snapshot()
    
    while True:
        current_schema = adapter.get_all_tables()
        changes = compare_schemas(previous_schema, current_schema)
        
        for change in changes:
            send_to_api(change)
        
        previous_schema = current_schema
        time.sleep(60)  # Poll every minute
```

## Summary

| Component | PostgreSQL | MySQL | Status |
|-----------|------------|-------|--------|
| Event Triggers | ✅ Native | ❌ Not available | Needs alternative |
| Notifications | ✅ pg_notify | ❌ Not available | Needs polling/queue |
| System Catalogs | ✅ pg_* | ✅ information_schema | Needs adapter |
| SQL Parser | ✅ Both syntaxes | ✅ Both syntaxes | ✅ Works |
| Code Analysis | ✅ Works | ✅ Works | ✅ Works |
| Risk Scoring | ✅ Works | ✅ Works | ✅ Works |

## Conclusion

**Current State**: ❌ **Not compatible with MySQL**

**To Make It Work**:
1. Create database adapter abstraction
2. Replace PostgreSQL event triggers with MySQL-compatible detection
3. Replace `pg_notify` with polling or message queue
4. Update system catalog queries to use `information_schema`
5. Update connection code to use MySQL connector

**Estimated Effort**: 2-3 days of development

**Recommended**: Use **direct API calls** from migration tools for MySQL, as it's the most reliable approach without native event triggers.

