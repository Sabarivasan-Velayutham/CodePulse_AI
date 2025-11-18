# MongoDB Change Streams Setup for Real-Time Schema Notifications

## Overview

MongoDB doesn't have built-in triggers like PostgreSQL, but we can use **Change Streams** for real-time notifications. This setup provides automatic schema change detection similar to PostgreSQL's `pg_notify`.

## How It Works

### Architecture

1. **Notification Collection**: A special collection (`schema_notifications`) stores schema change events
2. **Change Streams**: The listener watches this collection for new notifications
3. **Helper Functions**: MongoDB functions or Python scripts write notifications when schema changes occur

### Two Approaches

#### Approach 1: Change Streams (Best - Real-time)

- Uses MongoDB Change Streams to watch the notification collection
- **Requires**: Works on single-node MongoDB (for collection-level watching)
- **Real-time**: Instant notifications when changes occur
- **Efficient**: No polling overhead

#### Approach 2: Lightweight Polling (Fallback)

- If Change Streams aren't available, uses lightweight polling on notification collection
- **Requires**: Any MongoDB setup
- **Efficient**: Only polls notification collection (not full schema)
- **Fast**: 1-second intervals (vs 5 seconds for full schema polling)

## Setup Steps

### Step 1: Initialize Notification Collection

```bash
# Option A: Using mongosh
mongosh mongodb://localhost:27017/banking_db
```

```javascript
// In mongosh
use banking_db

// Create notification collection
db.schema_notifications.insertOne({
    type: "init",
    message: "Schema notification collection initialized",
    timestamp: new Date()
});

// Create indexes
db.schema_notifications.createIndex({ timestamp: 1 });
db.schema_notifications.createIndex({ processed: 1 }, { sparse: true });
```

Or use the setup script:

```bash
mongosh mongodb://localhost:27017/banking_db < docs/mongodb-trigger-setup.js
```

### Step 2: Start the Listener

```bash
python scripts/mongodb_schema_listener.py
```

The listener will:
- ✅ Connect to MongoDB
- ✅ Set up notification collection
- ✅ Start watching with Change Streams (or lightweight polling)
- ✅ Wait for schema change notifications

### Step 3: Notify Schema Changes

When you make schema changes, notify the system:

#### Option A: Using Helper Script (Recommended)

```bash
# After creating a collection
python scripts/mongodb_schema_notifier.py CREATE_COLLECTION payments

# After creating an index
python scripts/mongodb_schema_notifier.py CREATE_INDEX transactions amount_idx

# After dropping a collection
python scripts/mongodb_schema_notifier.py DROP_COLLECTION payments
```

#### Option B: Direct Insert in mongosh

```javascript
// After creating a collection
db.schema_notifications.insertOne({
    operation: "CREATE_COLLECTION",
    collection: "payments",
    operation_statement: "CREATE COLLECTION payments",
    timestamp: new Date().getTime() / 1000,
    processed: false
});

// After creating an index
db.schema_notifications.insertOne({
    operation: "CREATE_INDEX",
    collection: "transactions",
    index_name: "amount_idx",
    operation_statement: "db.transactions.createIndex({amount: 1}, {name: 'amount_idx'})",
    timestamp: new Date().getTime() / 1000,
    processed: false
});
```

**Note**: MongoDB stored JavaScript functions (`db.system.js.save`) are deprecated in newer versions. Use the Python helper script or direct inserts instead.

#### Option C: Load Helper Functions in mongosh

Load helper functions from a file:

```javascript
// In mongosh
load('docs/mongosh-helper.js')

// Now you can use:
notifyCreateCollection("payments");
notifyCreateIndex("transactions", "amount_idx");
createCollectionWithNotify("payments");  // Creates AND notifies
```

Or add to `~/.mongoshrc.js` to load automatically in every mongosh session:

```javascript
// ~/.mongoshrc.js
load('docs/mongosh-helper.js');
```

Then you can use the helper functions directly:

```javascript
notifyCreateCollection("payments");
notifyDropCollection("payments");
notifyCreateIndex("transactions", "amount_idx");
```

## Automatic Detection (Advanced)

For fully automatic detection without manual notifications, you can:

### Option 1: Wrap MongoDB Operations

Create wrapper functions that automatically notify:

```javascript
// In mongosh (define in your session or ~/.mongoshrc.js)
function createCollectionWithNotify(name) {
    db.createCollection(name);
    db.schema_notifications.insertOne({
        operation: "CREATE_COLLECTION",
        collection: name,
        operation_statement: "CREATE COLLECTION " + name,
        timestamp: new Date().getTime() / 1000,
        processed: false
    });
    print("✅ Collection created and notified: " + name);
}

// Usage
createCollectionWithNotify("payments");
```

### Option 2: Use MongoDB Oplog (Replica Set Required)

If you have a replica set, you can watch the oplog for schema changes:

```python
# Advanced: Watch oplog for DDL operations
# Requires replica set
oplog = client.local.oplog.rs
for change in oplog.find({'op': {'$in': ['c']}}):  # 'c' = command operations
    if 'create' in change.get('o', {}):
        # Collection created
        notify_schema_change('CREATE_COLLECTION', ...)
```

### Option 3: Integration with Migration Tools

Integrate with your migration tools (Mongoose, Mongoose Migrate, etc.):

```python
# In your Python migration script
from pymongo import MongoClient
from scripts.mongodb_schema_notifier import notify_schema_change

client = MongoClient("mongodb://localhost:27017/")
db = client["banking_db"]

# After schema change
db.payments.insert_one({"init": True})
notify_schema_change("CREATE_COLLECTION", "payments")
```

## Testing

### Test 1: Create Collection

```bash
# Terminal 1: Start listener
python scripts/mongodb_schema_listener.py

# Terminal 2: Create collection and notify
mongosh mongodb://localhost:27017/banking_db
use banking_db
db.payments.insertOne({test: "data"})

# Notify the change
python scripts/mongodb_schema_notifier.py CREATE_COLLECTION payments
```

**Expected**: Listener detects change immediately and triggers analysis

### Test 2: Create Index

```bash
# In mongosh
db.transactions.createIndex({amount: 1}, {name: "amount_idx"})

# Notify
python scripts/mongodb_schema_notifier.py CREATE_INDEX transactions amount_idx
```

**Expected**: Listener detects index creation and triggers analysis

## Comparison: Change Streams vs Polling

| Feature | Change Streams | Polling (Old) |
|---------|----------------|--------------|
| **Latency** | Real-time (< 1s) | 5 seconds |
| **Efficiency** | Event-driven | CPU intensive |
| **Resource Usage** | Low | High |
| **Requires** | Notification collection | Full schema scan |
| **Works On** | Single node + Replica set | Any setup |

## Troubleshooting

### Issue: Change Streams not working

**Symptom**: "change streams require replica set" error

**Solution**: The listener automatically falls back to lightweight polling on the notification collection (1-second intervals)

### Issue: Notifications not detected

**Check**:
1. Is the listener running?
2. Is the notification collection created?
3. Are notifications being written correctly?

```javascript
// Check notifications
db.schema_notifications.find().sort({timestamp: -1}).limit(5)
```

### Issue: Backend not receiving notifications

**Check**:
1. Backend URL is correct: `CODEFLOW_BACKEND_URL=http://localhost:8000`
2. Backend is running: `docker-compose ps backend`
3. Check listener logs for API errors

## Best Practices

1. **Always notify after schema changes**: Use the helper script or function
2. **Include operation statement**: Provides full context for analysis
3. **Clean up processed notifications**: Periodically remove old processed notifications
4. **Monitor notification collection**: Check for unprocessed notifications

```javascript
// Clean up old processed notifications (run periodically)
db.schema_notifications.deleteMany({
    processed: true,
    timestamp: {$lt: new Date().getTime() / 1000 - 86400} // Older than 24 hours
});
```

## Summary

✅ **Real-time notifications** using Change Streams  
✅ **No polling overhead** - event-driven  
✅ **Automatic fallback** to lightweight polling if needed  
✅ **Easy integration** - helper scripts and functions  
✅ **Similar to PostgreSQL** - notification-based system  

The system now works like PostgreSQL: write a notification, and the listener picks it up instantly via Change Streams!

