// MongoDB Schema Change Notification Setup
// This script sets up the notification collection for schema change detection
// Run this in mongosh: Get-Content docs/mongodb-trigger-setup.js | mongosh mongodb://localhost:27017/banking_db
// Or: mongosh mongodb://localhost:27017/banking_db < docs/mongodb-trigger-setup.js

print("Setting up MongoDB schema notification collection...\n");

// Create notification collection
print("Creating notification collection...");
db.schema_notifications.drop(); // Clear existing
db.schema_notifications.insertOne({
    type: "init",
    message: "Schema notification collection initialized",
    timestamp: new Date()
});

// Create indexes for efficient queries
print("Creating indexes...");
db.schema_notifications.createIndex({ timestamp: 1 });
db.schema_notifications.createIndex({ processed: 1 }, { sparse: true });

print("\n✅ MongoDB schema notification setup complete!");
print("   Notification collection: schema_notifications");
print("   Indexes created: timestamp, processed");
print("\n   To notify schema changes, use the Python helper script:");
print("   python scripts/mongodb_schema_notifier.py CREATE_COLLECTION payments");
print("   python scripts/mongodb_schema_notifier.py CREATE_INDEX transactions amount_idx");
print("\n   Or insert directly in mongosh:");
print("   db.schema_notifications.insertOne({");
print("     operation: 'CREATE_COLLECTION',");
print("     collection: 'payments',");
print("     operation_statement: 'CREATE COLLECTION payments',");
print("     timestamp: new Date().getTime() / 1000,");
print("     processed: false");
print("   });");

