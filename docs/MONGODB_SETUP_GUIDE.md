# MongoDB Schema Change Detection Setup Guide

## Overview

This guide sets up MongoDB schema change detection and analysis, similar to the PostgreSQL setup. The system monitors MongoDB collections and indexes for changes and automatically triggers dependency analysis.

## Prerequisites

- MongoDB 6+ installed (or use Docker)
- Python 3.8+ with pymongo
- CodeFlow Catalyst backend running

## Step 1: Start MongoDB

### Option A: Using Docker (Recommended)

```bash
# Start MongoDB container
docker-compose up -d mongodb

# Or manually
docker run -d \
  --name codeflow-mongodb \
  -p 27017:27017 \
  -e MONGO_INITDB_DATABASE=banking_db \
  -v mongodb_data:/data/db \
  mongo:7.0
```

### Option B: Local Installation

```bash
# Start MongoDB service
sudo systemctl start mongod

# Or manually
mongod --dbpath /path/to/data
```

## Step 2: Load Sample Data

```bash
# Load sample banking data
python scripts/load_mongodb_data.py
```

This will create:
- `customers` collection (3 documents)
- `accounts` collection (5 documents)
- `transactions` collection (4 documents)
- `fraud_alerts` collection (2 documents)
- Indexes on key fields

## Step 3: Set Up Notification Collection

```bash
# Initialize notification collection
mongosh mongodb://localhost:27017/banking_db < docs/mongodb-trigger-setup.js
```

Or manually:

```javascript
// In mongosh
use banking_db
db.schema_notifications.insertOne({type: "init", timestamp: new Date()});
db.schema_notifications.createIndex({timestamp: 1});
```

## Step 4: Start MongoDB Schema Listener

```bash
# Set environment variables (optional)
export MONGO_URI="mongodb://localhost:27017/"
export MONGO_DB="banking_db"
export CODEFLOW_BACKEND_URL="http://localhost:8000"
export REPOSITORY_NAME="banking-app"

# Start listener
python scripts/mongodb_schema_listener.py
```

The listener will:
- ✅ Use Change Streams for real-time notifications (no polling!)
- ✅ Watch notification collection for schema changes
- ✅ Automatically trigger backend analysis
- ✅ Fall back to lightweight polling if Change Streams unavailable

## Step 5: Test Schema Changes

### Test 1: Create a New Collection

```bash
# In mongosh
use banking_db
db.test_collection.insertOne({test: "data"})

# Notify the change (in another terminal or after the operation)
python scripts/mongodb_schema_notifier.py CREATE_COLLECTION test_collection
```

**Expected Result:**
- Listener detects notification instantly via Change Streams
- Backend analyzes impact
- Results appear in dashboard

### Test 2: Create an Index

```bash
# In mongosh
use banking_db
db.transactions.createIndex({amount: 1}, {name: "amount_idx"})

# Notify the change
python scripts/mongodb_schema_notifier.py CREATE_INDEX transactions amount_idx
```

**Expected Result:**
- Listener detects notification instantly
- Backend analyzes impact on transactions collection
- Shows code dependencies and relationships

### Test 3: Drop an Index

```javascript
// In mongosh
use banking_db
db.transactions.dropIndex("amount_1")
```

**Expected Result:**
- Listener detects `DROP_INDEX`
- Backend analyzes impact
- Risk score reflects index removal

### Test 4: Drop a Collection

```javascript
// In mongosh
use banking_db
db.test_collection.drop()
```

**Expected Result:**
- Listener detects `DROP_COLLECTION`
- Backend analyzes impact
- High risk score for data loss

## Step 6: Manual API Calls (Alternative)

If the listener isn't running, you can trigger analysis manually:

```bash
curl -X POST http://localhost:8000/api/v1/schema/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "sql_statement": "CREATE COLLECTION transactions",
    "database_name": "mongodb_banking_db",
    "change_id": "manual_001",
    "repository": "banking-app",
    "database_type": "mongodb"
  }'
```

## How It Works

### 1. Schema Change Detection

MongoDB doesn't have triggers like PostgreSQL, so we use **Change Streams** with a notification collection:

- **Notification Collection**: Special collection stores schema change events
- **Change Streams**: Listener watches this collection for real-time notifications
- **Helper Scripts**: Write notifications when schema changes occur
- **Automatic Detection**: Similar to PostgreSQL's `pg_notify` pattern

**Flow:**
1. Schema change occurs → Write notification to `schema_notifications` collection
2. Change Stream detects new notification → Listener receives it instantly
3. Listener triggers backend analysis → Results appear in dashboard

### 2. Change Types Detected

| Operation | Change Type | Example |
|-----------|-------------|---------|
| Create Collection | `CREATE_COLLECTION` | `db.customers.insertOne({...})` |
| Drop Collection | `DROP_COLLECTION` | `db.customers.drop()` |
| Create Index | `CREATE_INDEX` | `db.transactions.createIndex({amount: 1})` |
| Drop Index | `DROP_INDEX` | `db.transactions.dropIndex("amount_1")` |
| Modify Collection | `MODIFY_COLLECTION` | Generic change detection |

### 3. Analysis Flow

1. **Listener detects change** → Polls MongoDB schema
2. **Sends to backend** → POST to `/api/v1/schema/webhook`
3. **Backend analyzes**:
   - Parses MongoDB operation
   - Finds code files using the collection
   - Queries MongoDB for relationships
   - Generates AI insights
   - Calculates risk score
4. **Stores in Neo4j** → Dependency graph
5. **Frontend displays** → Dashboard with graph and insights

## MongoDB vs PostgreSQL

| Feature | PostgreSQL | MongoDB |
|---------|-----------|---------|
| Change Detection | Event Triggers | Change Streams + Notifications |
| Notifications | `pg_notify` | Change Streams on notification collection |
| Latency | Real-time | Real-time (with Change Streams) |
| Schema Queries | System catalogs | Collection metadata |
| Relationships | Foreign keys | Reference fields |
| Index Detection | System catalogs | Index list |
| Setup | Native triggers | Notification collection pattern |

## Configuration

### Environment Variables

```bash
# MongoDB connection
MONGO_URI=mongodb://localhost:27017/
MONGO_DB=banking_db

# Backend
CODEFLOW_BACKEND_URL=http://localhost:8000
REPOSITORY_NAME=banking-app

# Polling interval (seconds)
MONGO_POLL_INTERVAL=5
```

### Docker Compose

MongoDB is already configured in `docker-compose.yml`:

```yaml
mongodb:
  image: mongo:7.0
  ports:
    - "27017:27017"
  environment:
    - MONGO_INITDB_DATABASE=banking_db
```

## Troubleshooting

### Issue: Listener can't connect to MongoDB

```bash
# Test connection
mongosh mongodb://localhost:27017/

# Check if MongoDB is running
docker ps | grep mongodb
# or
sudo systemctl status mongod
```

### Issue: Changes not detected

- Ensure listener is running
- Check polling interval (default: 5 seconds)
- Verify MongoDB connection in listener logs
- Check backend logs for analysis errors

### Issue: Backend can't connect to MongoDB

```bash
# For Docker: Use service name
MONGO_URI=mongodb://mongodb:27017/

# For local: Use localhost
MONGO_URI=mongodb://localhost:27017/
```

## Sample MongoDB Operations

### Create Collection with Index

```javascript
use banking_db
db.payments.insertOne({
  payment_id: "pay_001",
  customer_id: "cust_001",
  amount: 100.00,
  status: "PENDING"
})

// Create index
db.payments.createIndex({customer_id: 1, status: 1})
```

### Drop Collection

```javascript
use banking_db
db.payments.drop()
```

### Create Compound Index

```javascript
use banking_db
db.transactions.createIndex(
  {customer_id: 1, processed_at: -1},
  {name: "customer_transaction_idx"}
)
```

### Drop Index

```javascript
use banking_db
db.transactions.dropIndex("customer_transaction_idx")
```

## Next Steps

1. **Load sample data**: `python scripts/load_mongodb_data.py`
2. **Set up notifications**: `mongosh < docs/mongodb-trigger-setup.js`
3. **Start listener**: `python scripts/mongodb_schema_listener.py`
4. **Make schema changes** in MongoDB and notify using helper script
5. **View results** at `http://localhost:3000`

## Quick Reference

### Notify Schema Changes

```bash
# After creating collection
python scripts/mongodb_schema_notifier.py CREATE_COLLECTION payments

# After creating index
python scripts/mongodb_schema_notifier.py CREATE_INDEX transactions amount_idx

# After dropping collection
python scripts/mongodb_schema_notifier.py DROP_COLLECTION payments

# After dropping index
python scripts/mongodb_schema_notifier.py DROP_INDEX transactions amount_idx
```

See `docs/MONGODB_CHANGE_STREAMS_SETUP.md` for detailed setup and integration options.

## Integration with Code

The system automatically detects code files that use MongoDB collections by:
- Searching for collection names in code
- Finding MongoDB query patterns (e.g., `db.transactions.find()`)
- Detecting reference fields (e.g., `customer_id`)

All dependencies are visualized in the dependency graph!

