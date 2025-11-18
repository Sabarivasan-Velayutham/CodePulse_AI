# MongoDB Schema Change Notification Examples

## Quick Reference

After making schema changes in MongoDB, notify the system using one of these methods:

### Method 1: Python Helper Script (Recommended)

```bash
# After creating a collection
python scripts/mongodb_schema_notifier.py CREATE_COLLECTION payments

# After creating an index
python scripts/mongodb_schema_notifier.py CREATE_INDEX transactions amount_idx

# After dropping a collection
python scripts/mongodb_schema_notifier.py DROP_COLLECTION payments

# After dropping an index
python scripts/mongodb_schema_notifier.py DROP_INDEX transactions amount_idx
```

### Method 2: Direct Insert in mongosh

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

// After dropping a collection
db.schema_notifications.insertOne({
    operation: "DROP_COLLECTION",
    collection: "payments",
    operation_statement: "DROP COLLECTION payments",
    timestamp: new Date().getTime() / 1000,
    processed: false
});

// After dropping an index
db.schema_notifications.insertOne({
    operation: "DROP_INDEX",
    collection: "transactions",
    index_name: "amount_idx",
    operation_statement: "db.transactions.dropIndex('amount_idx')",
    timestamp: new Date().getTime() / 1000,
    processed: false
});
```

### Method 3: Create Helper Function in mongosh

Since `db.system.js.save` is deprecated, you can create a local helper function:

```javascript
// In mongosh, define a helper function
function notifySchemaChange(operation, collection, indexName, operationStatement) {
    var notification = {
        operation: operation,
        collection: collection,
        index_name: indexName || null,
        operation_statement: operationStatement || (operation + " on " + collection),
        timestamp: new Date().getTime() / 1000,
        processed: false
    };
    
    db.schema_notifications.insertOne(notification);
    print("✅ Schema change notification written: " + operation + " on " + collection);
    return true;
}

// Usage
notifySchemaChange("CREATE_COLLECTION", "payments");
notifySchemaChange("CREATE_INDEX", "transactions", "amount_idx");
```

**Note**: This function only exists in your current mongosh session. You'll need to redefine it each time you open mongosh, or use the Python script instead.

## Complete Workflow Example

### Step 1: Make Schema Change

```javascript
// In mongosh
use banking_db
db.payments.insertOne({
    payment_id: "pay_001",
    customer_id: "cust_001",
    amount: 100.00,
    status: "PENDING"
});
```

### Step 2: Notify the Change

```bash
# In terminal
python scripts/mongodb_schema_notifier.py CREATE_COLLECTION payments
```

### Step 3: Create Index and Notify

```javascript
// In mongosh
db.payments.createIndex({customer_id: 1, status: 1}, {name: "customer_status_idx"});
```

```bash
# In terminal
python scripts/mongodb_schema_notifier.py CREATE_INDEX payments customer_status_idx
```

## Integration with Your Workflow

### Option 1: Add to Your Scripts

Create a wrapper script that combines operations:

```bash
#!/bin/bash
# create_collection.sh
COLLECTION_NAME=$1

# Create collection in MongoDB
mongosh mongodb://localhost:27017/banking_db --eval "db.$COLLECTION_NAME.insertOne({init: true})"

# Notify the change
python scripts/mongodb_schema_notifier.py CREATE_COLLECTION $COLLECTION_NAME
```

### Option 2: Use in Migration Scripts

```python
# In your Python migration script
from pymongo import MongoClient
from scripts.mongodb_schema_notifier import notify_schema_change

client = MongoClient("mongodb://localhost:27017/")
db = client["banking_db"]

# Create collection
db.payments.insert_one({"init": True})

# Notify
notify_schema_change("CREATE_COLLECTION", "payments")
```

### Option 3: MongoDB Shell Alias

Add to your `~/.mongoshrc.js`:

```javascript
// ~/.mongoshrc.js
function notifySchemaChange(operation, collection, indexName, operationStatement) {
    var notification = {
        operation: operation,
        collection: collection,
        index_name: indexName || null,
        operation_statement: operationStatement || (operation + " on " + collection),
        timestamp: new Date().getTime() / 1000,
        processed: false
    };
    
    db.schema_notifications.insertOne(notification);
    print("✅ Schema change notification written: " + operation + " on " + collection);
    return true;
}
```

Then you can use it directly in mongosh:

```javascript
db.payments.insertOne({test: "data"});
notifySchemaChange("CREATE_COLLECTION", "payments");
```

## Verification

Check if notifications are being written:

```javascript
// In mongosh
db.schema_notifications.find().sort({timestamp: -1}).limit(5).pretty();
```

Check if listener is processing them:

```bash
# In listener terminal, you should see:
📨 MongoDB Schema Change Detected!
   Operation: CREATE_COLLECTION
   Collection: payments
```

## Troubleshooting

### Notifications not detected

1. **Check notification collection**:
   ```javascript
   db.schema_notifications.find({processed: false}).count();
   ```

2. **Check listener is running**:
   ```bash
   ps aux | grep mongodb_schema_listener
   ```

3. **Check notification format**:
   ```javascript
   db.schema_notifications.findOne({processed: false});
   ```
   Should have: `operation`, `collection`, `timestamp`, `processed: false`

### Listener not receiving notifications

1. **Verify Change Streams are working**:
   - Check listener logs for "Change Stream active"
   - If you see "replica set" error, it will fall back to lightweight polling

2. **Test notification manually**:
   ```javascript
   db.schema_notifications.insertOne({
       operation: "TEST",
       collection: "test",
       timestamp: new Date().getTime() / 1000,
       processed: false
   });
   ```
   Listener should detect it within 1 second.

