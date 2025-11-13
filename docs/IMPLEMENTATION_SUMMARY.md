# Implementation Summary: Bidirectional Database Schema Analysis

## What Was Implemented

### 1. **Code Analysis → Database Dependencies** ✅
When you analyze a code change, the system now:
- Extracts SQL queries from the code file
- Identifies database tables and columns used
- Stores relationships in Neo4j
- Includes database dependencies in AI analysis
- Shows database tables in the analysis results

### 2. **Schema Change → Code Dependencies** ✅
When you make a database schema change, the system:
- Parses the SQL DDL statement
- Finds all code files that use the affected table/column
- Analyzes database relationships (foreign keys, etc.)
- Provides AI insights about the impact
- Calculates risk score

### 3. **PostgreSQL & MongoDB Listeners** ✅
Created listener scripts that:
- Monitor PostgreSQL for DDL changes (ALTER TABLE, etc.)
- Monitor MongoDB for collection/index changes
- Automatically trigger CodeFlow Catalyst analysis
- Display results in the dashboard

## Files Created/Modified

### New Files:
1. `docs/postgresql-mongodb-setup.md` - Complete PostgreSQL/MongoDB setup guide
2. `docs/setup-steps.md` - Step-by-step setup instructions
3. `scripts/postgres_schema_listener.py` - PostgreSQL change listener
4. `scripts/mongodb_schema_listener.py` - MongoDB change listener

### Modified Files:
1. `backend/app/engine/orchestrator.py` - Added database dependency analysis
2. `backend/app/engine/ai_analyzer.py` - Enhanced to include database context
3. `backend/app/engine/risk_scorer.py` - Added database risk factors
4. `backend/app/api/schema.py` - Updated webhook to return 202 status
5. `backend/requirements.txt` - Added psycopg2-binary, pymongo, requests

## Setup Steps (Quick Reference)

### Step 1: Install Dependencies
```bash
pip install -r backend/requirements.txt
```

### Step 2: Set Up PostgreSQL
```bash
# Connect to PostgreSQL
psql -U postgres

# Run SQL from docs/postgresql-mongodb-setup.md (Step 1.2-1.4)
# This creates:
# - banking_db database
# - Sample tables (customers, accounts, transactions, etc.)
# - Event trigger for schema changes
```

### Step 3: Start Backend
```bash
docker-compose up -d backend
# Or: cd backend && python -m uvicorn app.main:app --reload
```

### Step 4: Start Listeners
```bash
# Terminal 1: PostgreSQL listener
python scripts/postgres_schema_listener.py

# Terminal 2: MongoDB listener (optional)
python scripts/mongodb_schema_listener.py
```

### Step 5: Test Example 1 (Schema Change)
```sql
-- In psql
\c banking_db
ALTER TABLE transactions ADD COLUMN currency VARCHAR(3) DEFAULT 'USD';
```

**Expected Result**: Dashboard shows:
- Table dependencies
- Code files using `transactions` table
- AI insights
- Risk score

### Step 6: Test Example 2 (Code Commit)
```bash
# Trigger analysis for a code file
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "sample-repo/banking-app/src/database/TransactionDAO.java",
    "repository": "banking-app",
    "diff": "...",
    "commit_sha": "test123",
    "commit_message": "test"
  }'
```

**Expected Result**: Dashboard shows:
- Code dependencies (other files)
- Database tables used (`transactions`, etc.)
- AI insights
- Risk score

## API Endpoints

### Schema Change Webhook
```bash
POST /api/v1/schema/webhook
{
  "sql_statement": "ALTER TABLE transactions ADD COLUMN currency VARCHAR(3)",
  "database_name": "banking_db",
  "change_id": "optional_id",
  "repository": "banking-app"
}
```

### Code Change Analysis
```bash
POST /api/v1/analyze
{
  "file_path": "sample-repo/banking-app/src/database/TransactionDAO.java",
  "repository": "banking-app",
  "diff": "...",
  "commit_sha": "...",
  "commit_message": "..."
}
```

## What's Next

### Frontend Updates (TODO)
The frontend needs to be updated to display:
1. Database dependencies in code change analysis results
2. Schema change analysis results (new type)
3. Visual representation of code ↔ database relationships

### Current Status
- ✅ Backend fully supports bidirectional analysis
- ✅ Listeners created and ready
- ✅ API endpoints working
- ⏳ Frontend display (pending)

## Troubleshooting

### Listener Not Detecting Changes
1. Check PostgreSQL event trigger is created:
   ```sql
   SELECT * FROM pg_event_trigger;
   ```

2. Test notification manually:
   ```sql
   SELECT pg_notify('schema_change', '{"test": "data"}');
   ```

### Backend Not Receiving Webhooks
1. Check backend health:
   ```bash
   curl http://localhost:8000/health
   ```

2. Check listener can reach backend:
   ```bash
   curl http://localhost:8000/api/v1/schema/webhook \
     -X POST \
     -H "Content-Type: application/json" \
     -d '{"sql_statement": "ALTER TABLE test ADD COLUMN x INT", "database_name": "test"}'
   ```

## Example Outputs

### Example 1: Schema Change Analysis
```json
{
  "type": "schema_change",
  "schema_change": {
    "change_type": "ADD_COLUMN",
    "table_name": "transactions",
    "column_name": "currency"
  },
  "code_dependencies": [
    {
      "file_path": "src/database/TransactionDAO.java",
      "usage_count": 5
    }
  ],
  "database_relationships": {
    "forward": [],
    "reverse": [{"source_table": "accounts"}]
  },
  "risk_score": {
    "score": 3.5,
    "level": "MEDIUM"
  }
}
```

### Example 2: Code Change Analysis
```json
{
  "type": "code_change",
  "file_path": "src/database/TransactionDAO.java",
  "dependencies": {
    "direct": [...],
    "indirect": [...]
  },
  "database_dependencies": {
    "tables": [
      {
        "table_name": "transactions",
        "usage_count": 5,
        "columns": ["amount", "status", "processed_at"]
      }
    ]
  },
  "risk_score": {
    "score": 6.5,
    "level": "HIGH"
  }
}
```

## Notes

- The system now supports **bidirectional analysis**: code changes show database impact, and schema changes show code impact
- Both analyses include AI insights and risk scoring
- All relationships are stored in Neo4j for graph visualization
- Listeners run continuously and automatically trigger analysis


