// MongoDB Schema Change Notification Helper Functions
// Load this in mongosh: load('docs/mongosh-helper.js')
// Or add to ~/.mongoshrc.js to load automatically

// Helper function to notify schema changes
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

// Convenience functions
function notifyCreateCollection(collectionName) {
    return notifySchemaChange("CREATE_COLLECTION", collectionName, null, "CREATE COLLECTION " + collectionName);
}

function notifyDropCollection(collectionName) {
    return notifySchemaChange("DROP_COLLECTION", collectionName, null, "DROP COLLECTION " + collectionName);
}

function notifyCreateIndex(collectionName, indexName, operationStatement) {
    return notifySchemaChange("CREATE_INDEX", collectionName, indexName, operationStatement || ("db." + collectionName + ".createIndex(...)"));
}

function notifyDropIndex(collectionName, indexName) {
    return notifySchemaChange("DROP_INDEX", collectionName, indexName, "db." + collectionName + ".dropIndex('" + indexName + "')");
}

// Wrapper functions that do the operation AND notify
function createCollectionWithNotify(collectionName) {
    db.createCollection(collectionName);
    notifyCreateCollection(collectionName);
    print("✅ Collection created and notified: " + collectionName);
}

function dropCollectionWithNotify(collectionName) {
    db[collectionName].drop();
    notifyDropCollection(collectionName);
    print("✅ Collection dropped and notified: " + collectionName);
}

print("\n✅ Schema change notification helpers loaded!");
print("   Available functions:");
print("   - notifySchemaChange(operation, collection, indexName, operationStatement)");
print("   - notifyCreateCollection(collectionName)");
print("   - notifyDropCollection(collectionName)");
print("   - notifyCreateIndex(collectionName, indexName, operationStatement)");
print("   - notifyDropIndex(collectionName, indexName)");
print("   - createCollectionWithNotify(collectionName)");
print("   - dropCollectionWithNotify(collectionName)");
print("\n   Example: notifyCreateCollection('payments')");

