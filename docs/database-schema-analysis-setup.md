# Database Schema Change Analysis - Setup Guide

## Overview

This feature allows CodeFlow Catalyst to analyze the impact of database schema changes (ALTER TABLE, DROP COLUMN, etc.) on your codebase. It automatically detects which code files use the changed tables/columns and shows database relationships.

## Architecture

```
[Database Change] → [Webhook/Trigger] → [FastAPI Backend] → [Schema Analyzer]
                                                                    ↓
[SQL Extractor] ← [Code Repository] ← [Neo4j Graph] ← [AI Analysis]
                                                                    ↓
                                                            [Dashboard]
```

## Setup Options

### Option 1: Manual API Call (Easiest - For Testing)

Simply call the API endpoint when you make a schema change:

```bash
curl -X POST http://localhost:8000/api/v1/schema/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "sql_statement": "ALTER TABLE transactions ADD COLUMN currency VARCHAR(3) DEFAULT '\''USD'\''",
    "database_name": "banking_db",
    "change_id": "migration_001",
    "repository": "banking-app"
  }'
```

### Option 2: Database Trigger (MySQL/PostgreSQL)

#### MySQL Setup

Create a trigger that calls the webhook when DDL changes occur:

```sql
-- Note: MySQL doesn't support DDL triggers directly
-- Use a workaround with stored procedure + event scheduler
-- Or use MySQL Audit Plugin

-- Alternative: Use a migration tool hook (see Option 3)
```

#### PostgreSQL Setup

PostgreSQL doesn't support DDL triggers, but you can use:

1. **Event Triggers** (PostgreSQL 9.3+):
```sql
CREATE OR REPLACE FUNCTION notify_schema_change()
RETURNS event_trigger AS $$
DECLARE
    payload json;
BEGIN
    payload = json_build_object(
        'tag', tg_tag,
        'sql', current_query()
    );
    PERFORM pg_notify('schema_change', payload::text);
END;
$$ LANGUAGE plpgsql;

CREATE EVENT TRIGGER schema_change_trigger
ON ddl_command_end
EXECUTE FUNCTION notify_schema_change();
```

2. **External Listener** (Python script):
```python
import psycopg2
import requests
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

conn = psycopg2.connect("dbname=banking_db user=postgres")
conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

cursor = conn.cursor()
cursor.execute("LISTEN schema_change;")

while True:
    if conn.poll():
        while conn.notifies:
            notify = conn.notifies.pop(0)
            payload = json.loads(notify.payload)
            
            # Call CodeFlow Catalyst API
            requests.post(
                "http://localhost:8000/api/v1/schema/webhook",
                json={
                    "sql_statement": payload['sql'],
                    "database_name": "banking_db",
                    "repository": "banking-app"
                }
            )
```

### Option 3: Migration Tool Integration

#### Liquibase (Java)

Add to your `liquibase.properties`:

```properties
# After each changeSet, call webhook
liquibase.changeLogFile=changelog.xml
```

Create a Java hook:

```java
public class LiquibaseHook implements ChangeSetExecutedListener {
    @Override
    public void ran(ChangeSet changeSet, DatabaseChangeLog databaseChangeLog, 
                    Database database, ResultSet resultSet) {
        // Extract SQL from changeSet
        String sql = changeSet.getSql();
        
        // Call CodeFlow Catalyst API
        HttpClient.post("http://localhost:8000/api/v1/schema/webhook", {
            "sql_statement": sql,
            "database_name": "banking_db",
            "change_id": changeSet.getId(),
            "repository": "banking-app"
        });
    }
}
```

#### Flyway (Java)

Create a Flyway callback:

```java
public class SchemaChangeCallback implements Callback {
    @Override
    public void afterMigrate(Connection connection, MigrationInfo info) {
        String sql = info.getDescription(); // Get migration SQL
        
        // Call CodeFlow Catalyst API
        HttpClient.post("http://localhost:8000/api/v1/schema/webhook", {
            "sql_statement": sql,
            "database_name": "banking_db",
            "change_id": info.getVersion().toString(),
            "repository": "banking-app"
        });
    }
}
```

#### Alembic (Python)

Add to your `alembic/env.py`:

```python
def run_migrations_online():
    # ... existing code ...
    
    def process_revision_directives(context, revision, directives):
        if getattr(config.cmd_opts, 'autogenerate', False):
            script = directives[0]
            
            # After migration, call webhook
            for upgrade_ops in script.upgrade_ops.ops:
                if hasattr(upgrade_ops, 'sql'):
                    sql = str(upgrade_ops.sql)
                    
                    requests.post(
                        "http://localhost:8000/api/v1/schema/webhook",
                        json={
                            "sql_statement": sql,
                            "database_name": "banking_db",
                            "change_id": revision,
                            "repository": "banking-app"
                        }
                    )

run_migrations_online()
```

### Option 4: CI/CD Pipeline Integration

#### GitHub Actions

```yaml
name: Schema Change Analysis

on:
  push:
    paths:
      - 'migrations/**/*.sql'
      - 'db/migrations/**/*.sql'

jobs:
  analyze-schema:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Extract SQL from migration files
        id: extract-sql
        run: |
          # Extract SQL from changed migration files
          SQL=$(cat migrations/new_migration.sql)
          echo "::set-output name=sql::$SQL"
      
      - name: Trigger Schema Analysis
        run: |
          curl -X POST http://your-backend:8000/api/v1/schema/webhook \
            -H "Content-Type: application/json" \
            -d '{
              "sql_statement": "${{ steps.extract-sql.outputs.sql }}",
              "database_name": "banking_db",
              "change_id": "${{ github.sha }}",
              "repository": "${{ github.repository }}"
            }'
```

## API Endpoints

### POST `/api/v1/schema/analyze`

Analyze a schema change immediately (synchronous).

**Request:**
```json
{
  "sql_statement": "ALTER TABLE transactions ADD COLUMN currency VARCHAR(3)",
  "database_name": "banking_db",
  "change_id": "optional_id",
  "repository": "banking-app"
}
```

**Response:**
```json
{
  "id": "analysis_id",
  "type": "schema_change",
  "schema_change": {
    "change_type": "ADD_COLUMN",
    "table_name": "transactions",
    "column_name": "currency"
  },
  "code_dependencies": [...],
  "database_relationships": {...},
  "risk_score": {...},
  "ai_insights": {...}
}
```

### POST `/api/v1/schema/webhook`

Trigger background analysis (asynchronous).

Same request format as `/analyze`, but returns immediately and processes in background.

### GET `/api/v1/schema/table/{table_name}`

Get all dependencies for a specific table.

**Query Parameters:**
- `database_name`: Name of the database

**Response:**
```json
{
  "table_name": "transactions",
  "database": "banking_db",
  "code_dependencies": [
    {
      "file_name": "TransactionDAO.java",
      "file_path": "src/database/TransactionDAO.java",
      "usage_count": 5,
      "column_name": "currency"
    }
  ],
  "database_relationships": {
    "forward": [...],
    "reverse": [...]
  }
}
```

## How It Works

1. **Schema Change Detection**: Parses SQL DDL statements to identify:
   - Change type (ADD_COLUMN, DROP_COLUMN, etc.)
   - Table name
   - Column name (if applicable)
   - Old/new values

2. **Code Dependency Discovery**: Scans repository for:
   - SQL queries that reference the table/column
   - ORM model definitions (JPA, Hibernate, SQLAlchemy)
   - Raw SQL in code files

3. **Database Relationship Mapping**: Analyzes:
   - Foreign key relationships
   - Views that depend on the table
   - Stored procedures/functions
   - Table inheritance (PostgreSQL)

4. **AI Analysis**: Uses Gemini AI to:
   - Assess impact on application code
   - Identify breaking changes
   - Recommend migration strategies
   - Flag compliance concerns

5. **Risk Scoring**: Calculates risk based on:
   - Change type severity
   - Number of affected code files
   - Database relationship complexity
   - AI-identified risks

## Example Use Cases

### Use Case 1: Add Column

```sql
ALTER TABLE transactions ADD COLUMN currency VARCHAR(3) DEFAULT 'USD';
```

**Analysis Results:**
- Finds all code files that INSERT/UPDATE/SELECT from `transactions` table
- Identifies if new column needs to be added to INSERT statements
- Checks if any code assumes specific column count
- Low risk (backward compatible if DEFAULT provided)

### Use Case 2: Drop Column

```sql
ALTER TABLE transactions DROP COLUMN geo_location;
```

**Analysis Results:**
- Finds all code files using `geo_location` column
- **HIGH RISK**: Will break code that references this column
- Lists exact line numbers where column is used
- Recommends migration strategy

### Use Case 3: Rename Column

```sql
ALTER TABLE transactions RENAME COLUMN trans_date TO transaction_date;
```

**Analysis Results:**
- Finds all SQL queries using old column name
- Identifies ORM models that need updating
- **MEDIUM RISK**: Requires code changes
- Suggests backward-compatible approach (add new column, migrate, drop old)

## Testing

### Test Script

Create `scripts/test_schema_analysis.py`:

```python
import requests
import json

# Test adding a column
response = requests.post(
    "http://localhost:8000/api/v1/schema/analyze",
    json={
        "sql_statement": "ALTER TABLE transactions ADD COLUMN currency VARCHAR(3) DEFAULT 'USD'",
        "database_name": "banking_db",
        "change_id": "test_001",
        "repository": "banking-app"
    }
)

print(json.dumps(response.json(), indent=2))
```

Run: `python scripts/test_schema_analysis.py`

## Next Steps

1. **Set up webhook/trigger** based on your database and migration tool
2. **Test with a sample schema change** using the API
3. **View results in dashboard** at `http://localhost:3000`
4. **Integrate into your workflow** (CI/CD, migration tools, etc.)

## Troubleshooting

### Issue: No code dependencies found

**Solution**: Ensure your repository path is correct. The system searches in `sample-repo/` directory by default.

### Issue: Database relationships not showing

**Solution**: Make sure schema files are in `sample-repo/banking-app/src/schema/` or update the path in `schema_orchestrator.py`.

### Issue: AI analysis timeout

**Solution**: The AI analysis has a 60-second timeout. For complex changes, it will fall back to basic analysis.

