"""
PostgreSQL Schema Change Listener
Listens for DDL changes and triggers CodeFlow Catalyst analysis
"""

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import json
import requests
import os
import sys
from typing import Dict

# Configuration
BACKEND_URL = os.getenv("CODEFLOW_BACKEND_URL", "http://localhost:8000")
DB_NAME = os.getenv("POSTGRES_DB", "banking_db")
DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "sabari")
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
REPOSITORY = os.getenv("REPOSITORY_NAME", "banking-app")

def listen_for_schema_changes():
    """Listen for PostgreSQL schema change notifications"""
    print("="*60)
    print("🔍 PostgreSQL Schema Change Listener")
    print("="*60)
    print(f"   Database: {DB_NAME}")
    print(f"   Host: {DB_HOST}:{DB_PORT}")
    print(f"   Backend: {BACKEND_URL}")
    print(f"   Repository: {REPOSITORY}")
    print("\n✅ Listening for schema changes...")
    print("   Make a schema change in PostgreSQL to trigger analysis\n")
    print("   Example: ALTER TABLE transactions ADD COLUMN currency VARCHAR(3);\n")
    
    try:
        # Connect to database
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        
        cursor = conn.cursor()
        cursor.execute("LISTEN schema_change;")
        print("   ✅ Subscribed to 'schema_change' notifications\n")
        print("   💡 Waiting for schema changes... (Press Ctrl+C to stop)\n")
        
        import time
        
        while True:
            # Poll for notifications (this is non-blocking)
            conn.poll()
            
            # Process any notifications that arrived
            # (The notifications are queued in conn.notifies)
            
            # If no notifications, wait a bit before checking again
            # This prevents CPU spinning
            if not conn.notifies:
                time.sleep(0.5)  # Check every 500ms
                continue
            
            while conn.notifies:
                notify = conn.notifies.pop(0)
                print(f"\n   🔔 Received notification on channel: {notify.channel}")
                
                try:
                    payload = json.loads(notify.payload)
                except json.JSONDecodeError as e:
                    print(f"   ⚠️  Failed to parse notification payload: {e}")
                    print(f"   Raw payload: {notify.payload}")
                    continue
                
                print(f"\n{'='*60}")
                print(f"📨 Schema Change Detected!")
                print(f"{'='*60}")
                print(f"   Type: {payload.get('tag', 'UNKNOWN')}")
                print(f"   Object: {payload.get('object_identity', 'UNKNOWN')}")
                print(f"   Schema: {payload.get('schema', 'public')}")
                
                # Extract SQL statement
                sql_statement = payload.get('sql', '')
                if not sql_statement or sql_statement == 'NULL' or (sql_statement.startswith('ALTER TABLE') and len(sql_statement.split()) <= 2):
                    # Try to reconstruct from payload
                    object_type = payload.get('object_type', '')
                    object_identity = payload.get('object_identity', '')
                    tag = payload.get('tag', '')
                    
                    # Reconstruct SQL based on tag
                    if tag == 'ALTER TABLE':
                        # For ALTER TABLE, we need more info - try to get from pg_stat_statements or use a placeholder
                        sql_statement = f"ALTER TABLE {object_identity}"
                        print(f"   ⚠️  SQL statement not fully captured, using reconstructed: {sql_statement}")
                    elif tag == 'CREATE TABLE':
                        sql_statement = f"CREATE TABLE {object_identity}"
                    elif tag == 'DROP TABLE':
                        sql_statement = f"DROP TABLE {object_identity}"
                    elif tag == 'DROP COLUMN':
                        sql_statement = f"ALTER TABLE {object_identity} DROP COLUMN {payload.get('column_name', 'column')}"
                    elif tag == 'ADD COLUMN':
                        sql_statement = f"ALTER TABLE {object_identity} ADD COLUMN {payload.get('column_name', 'column')}"
                    else:
                        sql_statement = f"{tag} {object_identity}"
                
                if sql_statement:
                    print(f"   SQL: {sql_statement[:100]}...")
                    
                    # Call CodeFlow Catalyst API
                    try:
                        print(f"\n   🔄 Triggering analysis...")
                        response = requests.post(
                            f"{BACKEND_URL}/api/v1/schema/webhook",
                            json={
                                "sql_statement": sql_statement,
                                "database_name": DB_NAME,
                                "change_id": f"pg_{payload.get('object_identity', 'unknown').replace('.', '_')}_{int(time.time())}",
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
                else:
                    print(f"   ⚠️  Could not extract SQL statement from notification")
    
    except psycopg2.OperationalError as e:
        print(f"\n❌ Database Connection Error: {e}")
        print(f"\n   Make sure PostgreSQL is running and accessible:")
        print(f"   - Host: {DB_HOST}:{DB_PORT}")
        print(f"   - Database: {DB_NAME}")
        print(f"   - User: {DB_USER}")
        print(f"\n   Test connection: psql -h {DB_HOST} -U {DB_USER} -d {DB_NAME}")
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
    listen_for_schema_changes()

