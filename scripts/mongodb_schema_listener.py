"""
MongoDB Schema Change Listener
Automatically detects schema changes using Change Streams (similar to PostgreSQL triggers)
Watches for:
- Collection creation/dropping (via database-level Change Streams)
- Index creation/dropping (via system collection monitoring)
"""

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure
from pymongo.change_stream import ChangeStream
import requests
import json
import os
import sys
import time
import threading
from typing import Dict, Optional, Set
from datetime import datetime

# Configuration
BACKEND_URL = os.getenv("CODEFLOW_BACKEND_URL", "http://localhost:8000")
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = os.getenv("MONGO_DB", "banking_db")
REPOSITORY = os.getenv("REPOSITORY_NAME", "banking-app")

# Track known collections and indexes to detect changes
KNOWN_COLLECTIONS: Set[str] = set()
KNOWN_INDEXES: Dict[str, Set[str]] = {}  # collection_name -> set of index names

def get_all_collections(db) -> Set[str]:
    """Get all collection names in the database"""
    return set(db.list_collection_names())

def get_all_indexes(db) -> Dict[str, Set[str]]:
    """Get all indexes for all collections"""
    indexes = {}
    for coll_name in db.list_collection_names():
        if coll_name.startswith("system."):
            continue
        try:
            coll = db[coll_name]
            index_list = coll.list_indexes()
            index_names = {idx["name"] for idx in index_list}
            indexes[coll_name] = index_names
        except Exception as e:
            print(f"   ⚠️  Could not get indexes for {coll_name}: {e}")
    return indexes

def detect_collection_changes(db, old_collections: Set[str], new_collections: Set[str]):
    """Detect collection creation/dropping"""
    created = new_collections - old_collections
    dropped = old_collections - new_collections
    
    changes = []
    
    for coll_name in created:
        changes.append({
            "operation": "CREATE_COLLECTION",
            "collection": coll_name,
            "operation_statement": f"CREATE COLLECTION {coll_name}",
            "timestamp": time.time()
        })
    
    for coll_name in dropped:
        changes.append({
            "operation": "DROP_COLLECTION",
            "collection": coll_name,
            "operation_statement": f"DROP COLLECTION {coll_name}",
            "timestamp": time.time()
        })
    
    return changes

def detect_index_changes(db, old_indexes: Dict[str, Set[str]], new_indexes: Dict[str, Set[str]]):
    """Detect index creation/dropping"""
    changes = []
    
    # Check all collections
    all_collections = set(old_indexes.keys()) | set(new_indexes.keys())
    
    for coll_name in all_collections:
        old_idx = old_indexes.get(coll_name, set())
        new_idx = new_indexes.get(coll_name, set())
        
        created = new_idx - old_idx
        dropped = old_idx - new_idx
        
        for idx_name in created:
            # Skip default _id index
            if idx_name == "_id_":
                continue
            changes.append({
                "operation": "CREATE_INDEX",
                "collection": coll_name,
                "index_name": idx_name,
                "operation_statement": f"db.{coll_name}.createIndex(...)",
                "timestamp": time.time()
            })
        
        for idx_name in dropped:
            if idx_name == "_id_":
                continue
            changes.append({
                "operation": "DROP_INDEX",
                "collection": coll_name,
                "index_name": idx_name,
                "operation_statement": f"db.{coll_name}.dropIndex('{idx_name}')",
                "timestamp": time.time()
            })
    
    return changes

def trigger_analysis(change: Dict):
    """Trigger backend analysis for a schema change"""
    operation = change.get("operation", "")
    collection_name = change.get("collection", "")
    index_name = change.get("index_name", "")
    operation_statement = change.get("operation_statement", "")
    
    if not operation or not collection_name:
        return False
    
    print(f"\n{'='*60}")
    print(f"📨 MongoDB Schema Change Detected!")
    print(f"{'='*60}")
    print(f"   Operation: {operation}")
    print(f"   Collection: {collection_name}")
    if index_name:
        print(f"   Index: {index_name}")
    print(f"   Statement: {operation_statement}")
    
    try:
        print(f"\n   🔄 Triggering analysis...")
        
        response = requests.post(
            f"{BACKEND_URL}/api/v1/schema/webhook",
            json={
                "sql_statement": operation_statement,
                "database_name": f"mongodb_{DB_NAME}",
                "change_id": f"mongo_{collection_name}_{operation}_{int(time.time())}",
                "repository": REPOSITORY,
                "database_type": "mongodb"
            },
            timeout=30
        )
        
        if response.status_code == 202:
            print(f"   ✅ Analysis triggered successfully")
            print(f"   🌐 View results at: http://localhost:3000")
            return True
        else:
            print(f"   ⚠️  Analysis request failed: {response.status_code}")
            print(f"      {response.text[:200]}")
            return False
    
    except requests.exceptions.ConnectionError:
        print(f"   ❌ Cannot connect to backend at {BACKEND_URL}")
        print(f"      Make sure backend is running: docker-compose up -d backend")
        return False
    except Exception as e:
        print(f"   ❌ Error calling API: {e}")
        return False

def watch_collections_with_change_streams(db):
    """Watch for collection creation/dropping using Change Streams"""
    try:
        # Watch the database for collection-level changes
        print("   📋 Setting up Change Streams for collection monitoring...")
        
        # Create change stream on the database
        pipeline = [
            {
                "$match": {
                    "$or": [
                        {"operationType": "insert", "ns.coll": {"$exists": True}},
                        {"operationType": "invalidate"}
                    ]
                }
            }
        ]
        
        # Watch database-level changes (collection creation/dropping)
        with db.watch(pipeline, full_document='updateLookup') as stream:
            print("   ✅ Change Stream active - watching for collection changes...\n")
            
            for change in stream:
                try:
                    # Collection creation is detected when first document is inserted
                    # Collection dropping is detected via invalidate event
                    op_type = change.get("operationType")
                    
                    if op_type == "invalidate":
                        # Collection was dropped
                        ns = change.get("ns", {})
                        coll_name = ns.get("coll", "")
                        if coll_name and coll_name not in ["schema_notifications"]:
                            change_info = {
                                "operation": "DROP_COLLECTION",
                                "collection": coll_name,
                                "operation_statement": f"DROP COLLECTION {coll_name}",
                                "timestamp": time.time()
                            }
                            trigger_analysis(change_info)
                    
                    elif op_type == "insert":
                        # New collection might be created (first insert)
                        ns = change.get("ns", {})
                        coll_name = ns.get("coll", "")
                        if coll_name and coll_name not in ["schema_notifications"]:
                            # Check if this is a new collection
                            current_collections = get_all_collections(db)
                            if coll_name in current_collections and coll_name not in KNOWN_COLLECTIONS:
                                change_info = {
                                    "operation": "CREATE_COLLECTION",
                                    "collection": coll_name,
                                    "operation_statement": f"CREATE COLLECTION {coll_name}",
                                    "timestamp": time.time()
                                }
                                KNOWN_COLLECTIONS.add(coll_name)
                                trigger_analysis(change_info)
                
                except Exception as e:
                    print(f"   ⚠️  Error processing change stream event: {e}")
                    continue
    
    except OperationFailure as e:
        error_msg = str(e).lower()
        if "change streams" in error_msg or "replica set" in error_msg:
            print(f"   ⚠️  Change Streams require a replica set for database-level watching")
            print(f"   💡 Falling back to lightweight polling...\n")
            return False
        else:
            raise
    except Exception as e:
        print(f"   ⚠️  Error in Change Streams: {e}")
        return False
    
    return True

def monitor_indexes_with_polling(db, poll_interval=2):
    """Monitor index changes using lightweight polling"""
    print(f"   📋 Monitoring collections and indexes (polling every {poll_interval}s)...")
    print("   💡 Waiting for schema changes... (Press Ctrl+C to stop)\n")
    
    global KNOWN_COLLECTIONS, KNOWN_INDEXES
    
    while True:
        try:
            time.sleep(poll_interval)
            
            # Get current state
            current_collections = get_all_collections(db)
            current_indexes = get_all_indexes(db)
            
            # Detect collection changes
            collection_changes = detect_collection_changes(db, KNOWN_COLLECTIONS, current_collections)
            for change in collection_changes:
                if change["operation"] == "CREATE_COLLECTION":
                    KNOWN_COLLECTIONS.add(change["collection"])
                elif change["operation"] == "DROP_COLLECTION":
                    KNOWN_COLLECTIONS.discard(change["collection"])
                    KNOWN_INDEXES.pop(change["collection"], None)
                trigger_analysis(change)
            
            # Detect index changes
            index_changes = detect_index_changes(db, KNOWN_INDEXES, current_indexes)
            for change in index_changes:
                coll_name = change["collection"]
                idx_name = change.get("index_name", "")
                
                if change["operation"] == "CREATE_INDEX":
                    if coll_name not in KNOWN_INDEXES:
                        KNOWN_INDEXES[coll_name] = set()
                    KNOWN_INDEXES[coll_name].add(idx_name)
                elif change["operation"] == "DROP_INDEX":
                    if coll_name in KNOWN_INDEXES:
                        KNOWN_INDEXES[coll_name].discard(idx_name)
                
                trigger_analysis(change)
            
            # Update known state
            KNOWN_COLLECTIONS = current_collections
            KNOWN_INDEXES = current_indexes
        
        except KeyboardInterrupt:
            raise
        except Exception as e:
            print(f"   ⚠️  Error during monitoring: {e}")
            time.sleep(poll_interval)

def listen_for_mongodb_changes():
    """Main listener function - automatically detects schema changes"""
    print("="*60)
    print("🔍 MongoDB Schema Change Listener (Automatic Detection)")
    print("="*60)
    print(f"   Database: {DB_NAME}")
    print(f"   URI: {MONGO_URI}")
    print(f"   Backend: {BACKEND_URL}")
    print(f"   Repository: {REPOSITORY}")
    print("\n✅ Listening for MongoDB schema changes...")
    print("   Automatic detection enabled (no manual notifications needed)\n")
    
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        print("   ✅ Connected to MongoDB\n")
        
        db = client[DB_NAME]
        
        # Initialize known state
        print("   📋 Initializing schema state...")
        global KNOWN_COLLECTIONS, KNOWN_INDEXES
        KNOWN_COLLECTIONS = get_all_collections(db)
        KNOWN_INDEXES = get_all_indexes(db)
        print(f"   ✅ Found {len(KNOWN_COLLECTIONS)} collections")
        print(f"   ✅ Found {sum(len(idxs) for idxs in KNOWN_INDEXES.values())} indexes\n")
        
        # Try Change Streams first (requires replica set)
        print("   💡 Attempting Change Streams for collection monitoring...")
        change_streams_available = watch_collections_with_change_streams(db)
        
        if not change_streams_available:
            # Fallback to polling for both collections and indexes
            print("   💡 Using lightweight polling for collection and index monitoring...")
            print("   💡 Waiting for schema changes... (Press Ctrl+C to stop)\n")
            monitor_indexes_with_polling(db, poll_interval=2)
    
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
