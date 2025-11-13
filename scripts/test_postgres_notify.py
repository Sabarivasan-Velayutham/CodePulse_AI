"""
Test script to verify PostgreSQL NOTIFY/LISTEN is working
Run this to test if notifications are being sent and received correctly
"""

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import json
import time
import sys

# Configuration
DB_NAME = "banking_db"
DB_USER = "postgres"
DB_PASSWORD = "sabari"  # Update with your password
DB_HOST = "localhost"
DB_PORT = "5432"

def test_notify_listen():
    """Test NOTIFY/LISTEN functionality"""
    print("="*60)
    print("🧪 Testing PostgreSQL NOTIFY/LISTEN")
    print("="*60)
    
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
        
        # Step 1: Listen for notifications
        print("\n1️⃣ Setting up LISTEN...")
        cursor.execute("LISTEN test_channel;")
        print("   ✅ Listening on channel 'test_channel'")
        
        # Step 2: Send a test notification
        print("\n2️⃣ Sending test notification...")
        test_payload = json.dumps({
            "test": "data",
            "message": "This is a test notification",
            "timestamp": time.time()
        })
        cursor.execute(f"SELECT pg_notify('test_channel', %s);", (test_payload,))
        print("   ✅ Notification sent")
        
        # Step 3: Wait and check for notification
        print("\n3️⃣ Checking for notification...")
        time.sleep(0.5)  # Give it a moment
        
        conn.poll()
        
        if conn.notifies:
            notify = conn.notifies.pop(0)
            print(f"   ✅ Notification received!")
            print(f"      Channel: {notify.channel}")
            print(f"      Payload: {notify.payload}")
            
            try:
                payload = json.loads(notify.payload)
                print(f"      Parsed: {payload}")
            except:
                print(f"      (Could not parse as JSON)")
            
            print("\n✅ NOTIFY/LISTEN is working correctly!")
            return True
        else:
            print("   ❌ No notification received")
            print("   ⚠️  This might indicate a connection issue")
            return False
            
    except psycopg2.OperationalError as e:
        print(f"\n❌ Database Connection Error: {e}")
        print(f"\n   Make sure PostgreSQL is running and accessible:")
        print(f"   - Host: {DB_HOST}:{DB_PORT}")
        print(f"   - Database: {DB_NAME}")
        print(f"   - User: {DB_USER}")
        return False
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if 'conn' in locals():
            conn.close()

def test_event_trigger():
    """Test if event trigger is set up correctly"""
    print("\n" + "="*60)
    print("🧪 Testing Event Trigger Setup")
    print("="*60)
    
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Check if event trigger exists
        print("\n1️⃣ Checking for event trigger...")
        cursor.execute("""
            SELECT evtname, evtevent, evtenabled 
            FROM pg_event_trigger 
            WHERE evtname = 'schema_change_trigger';
        """)
        
        result = cursor.fetchone()
        if result:
            print(f"   ✅ Event trigger found: {result[0]}")
            print(f"      Event: {result[1]}")
            print(f"      Enabled: {result[2]}")
        else:
            print("   ❌ Event trigger not found!")
            print("   Run: psql -U postgres -d banking_db -f docs/postgres-trigger-setup.sql")
            return False
        
        # Check if function exists
        print("\n2️⃣ Checking for notify function...")
        cursor.execute("""
            SELECT proname, prosrc 
            FROM pg_proc 
            WHERE proname = 'notify_schema_change';
        """)
        
        result = cursor.fetchone()
        if result:
            print(f"   ✅ Function found: {result[0]}")
        else:
            print("   ❌ Function not found!")
            return False
        
        print("\n✅ Event trigger setup looks correct!")
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    print("\n")
    
    # Test 1: Basic NOTIFY/LISTEN
    notify_works = test_notify_listen()
    
    # Test 2: Event trigger setup
    trigger_works = test_event_trigger()
    
    print("\n" + "="*60)
    print("📊 Test Results")
    print("="*60)
    print(f"   NOTIFY/LISTEN: {'✅ Working' if notify_works else '❌ Failed'}")
    print(f"   Event Trigger: {'✅ Set up' if trigger_works else '❌ Not set up'}")
    print("="*60)
    
    if notify_works and trigger_works:
        print("\n✅ All tests passed! The listener should work correctly.")
        print("   Start the listener: python scripts/postgres_schema_listener.py")
    else:
        print("\n⚠️  Some tests failed. Fix the issues above before using the listener.")
        sys.exit(1)

