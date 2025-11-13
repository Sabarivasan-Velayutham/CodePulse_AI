"""
MongoDB Schema Change Listener
Listens for collection/index changes and triggers CodeFlow Catalyst analysis
"""

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
import requests
import json
import os
import sys

# Configuration
BACKEND_URL = os.getenv("CODEFLOW_BACKEND_URL", "http://localhost:8000")
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = os.getenv("MONGO_DB", "banking_db")
REPOSITORY = os.getenv("REPOSITORY_NAME", "banking-app")

def listen_for_mongodb_changes():
    """Listen for MongoDB schema/index changes"""
    print("="*60)
    print("🔍 MongoDB Schema Change Listener")
    print("="*60)
    print(f"   Database: {DB_NAME}")
    print(f"   URI: {MONGO_URI}")
    print(f"   Backend: {BACKEND_URL}")
    print(f"   Repository: {REPOSITORY}")
    print("\n✅ Listening for MongoDB schema changes...")
    print("   Create/drop collections or indexes to trigger analysis\n")
    
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        # Test connection
        client.admin.command('ping')
        print("   ✅ Connected to MongoDB\n")
        
        db = client[DB_NAME]
        
        # Watch for database-level changes (collections, indexes)
        # Note: MongoDB change streams require replica set for database-level watching
        # For single node, we'll watch individual collections
        
        print("   📋 Watching collections:")
        collections = db.list_collection_names()
        for coll in collections:
            print(f"      - {coll}")
        
        if not collections:
            print("      (No collections found - create one to start watching)")
        
        print("\n   💡 To test: Create a new collection or index in MongoDB\n")
        
        # Watch all collections in the database
        pipeline = [
            {"$match": {
                "$or": [
                    {"operationType": "insert"},
                    {"operationType": "create"},
                    {"operationType": "drop"}
                ]
            }}
        ]
        
        try:
            with db.watch(pipeline) as stream:
                for change in stream:
                    operation = change.get("operationType")
                    collection = change.get("ns", {}).get("coll", "unknown")
                    
                    print(f"\n{'='*60}")
                    print(f"📨 MongoDB Change Detected!")
                    print(f"{'='*60}")
                    print(f"   Operation: {operation}")
                    print(f"   Collection: {collection}")
                    
                    # Build SQL-like statement for MongoDB changes
                    if operation == "create" or operation == "insert":
                        sql_statement = f"CREATE COLLECTION {collection}"
                    elif operation == "drop":
                        sql_statement = f"DROP COLLECTION {collection}"
                    else:
                        sql_statement = f"MODIFY COLLECTION {collection}"
                    
                    print(f"   SQL Equivalent: {sql_statement}")
                    
                    # Call CodeFlow Catalyst API
                    try:
                        print(f"\n   🔄 Triggering analysis...")
                        response = requests.post(
                            f"{BACKEND_URL}/api/v1/schema/webhook",
                            json={
                                "sql_statement": sql_statement,
                                "database_name": f"mongodb_{DB_NAME}",
                                "change_id": f"mongo_{collection}_{operation}",
                                "repository": REPOSITORY
                            },
                            timeout=30
                        )
                        
                        if response.status_code == 202:
                            print(f"   ✅ Analysis triggered successfully")
                            print(f"   🌐 View results at: http://localhost:3000")
                        else:
                            print(f"   ⚠️  Analysis request failed: {response.status_code}")
                            print(f"      {response.text[:200]}")
                    
                    except requests.exceptions.ConnectionError:
                        print(f"   ❌ Cannot connect to backend at {BACKEND_URL}")
                        print(f"      Make sure backend is running: docker-compose up -d backend")
                    except Exception as e:
                        print(f"   ❌ Error calling API: {e}")
        
        except Exception as e:
            if "replica set" in str(e).lower() or "change streams" in str(e).lower():
                print(f"\n⚠️  MongoDB Change Streams require a replica set")
                print(f"   For single-node MongoDB, use manual API calls instead")
                print(f"   Or set up a replica set: https://docs.mongodb.com/manual/replication/")
                print(f"\n   Alternative: Use manual API calls when making schema changes")
            else:
                raise
    
    except ConnectionFailure:
        print(f"\n❌ MongoDB Connection Error")
        print(f"\n   Make sure MongoDB is running and accessible:")
        print(f"   - URI: {MONGO_URI}")
        print(f"   - Database: {DB_NAME}")
        print(f"\n   Test connection: mongosh {MONGO_URI}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n👋 Listener stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    listen_for_mongodb_changes()

