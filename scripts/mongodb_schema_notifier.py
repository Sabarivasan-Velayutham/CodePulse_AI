"""
MongoDB Schema Change Notifier Helper
Writes notifications to schema_notifications collection when schema changes occur
This can be called manually or integrated into your MongoDB operations
"""

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
import os
import sys
import time

# Configuration
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = os.getenv("MONGO_DB", "banking_db")
NOTIFICATION_COLLECTION = "schema_notifications"

def notify_schema_change(
    operation: str,
    collection: str,
    index_name: str = None,
    operation_statement: str = None
):
    """
    Write a schema change notification to MongoDB
    
    Args:
        operation: CREATE_COLLECTION, DROP_COLLECTION, CREATE_INDEX, DROP_INDEX
        collection: Collection name
        index_name: Index name (for index operations)
        operation_statement: Full operation statement
    """
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        db = client[DB_NAME]
        notification_coll = db[NOTIFICATION_COLLECTION]
        
        # Build operation statement if not provided
        if not operation_statement:
            if operation == "CREATE_COLLECTION":
                operation_statement = f"CREATE COLLECTION {collection}"
            elif operation == "DROP_COLLECTION":
                operation_statement = f"DROP COLLECTION {collection}"
            elif operation == "CREATE_INDEX":
                operation_statement = f"db.{collection}.createIndex(...)"
            elif operation == "DROP_INDEX":
                operation_statement = f"db.{collection}.dropIndex('{index_name}')"
            else:
                operation_statement = f"{operation} on {collection}"
        
        # Insert notification
        notification = {
            "operation": operation,
            "collection": collection,
            "index_name": index_name,
            "operation_statement": operation_statement,
            "timestamp": time.time(),
            "processed": False
        }
        
        notification_coll.insert_one(notification)
        print(f"✅ Schema change notification written: {operation} on {collection}")
        
        client.close()
        return True
    
    except Exception as e:
        print(f"❌ Error writing notification: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python mongodb_schema_notifier.py <operation> <collection> [index_name]")
        print("\nOperations: CREATE_COLLECTION, DROP_COLLECTION, CREATE_INDEX, DROP_INDEX")
        print("\nExample:")
        print("  python mongodb_schema_notifier.py CREATE_COLLECTION payments")
        print("  python mongodb_schema_notifier.py CREATE_INDEX transactions amount")
        sys.exit(1)
    
    operation = sys.argv[1]
    collection = sys.argv[2]
    index_name = sys.argv[3] if len(sys.argv) > 3 else None
    
    notify_schema_change(operation, collection, index_name)

