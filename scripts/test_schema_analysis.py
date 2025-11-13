"""
Test script for database schema change analysis
"""

import requests
import json
import sys

BACKEND_URL = "http://localhost:8000"

def test_add_column():
    """Test adding a column to transactions table"""
    print("\n" + "="*60)
    print("TEST 1: Add Column to Transactions Table")
    print("="*60)
    
    response = requests.post(
        f"{BACKEND_URL}/api/v1/schema/analyze",
        json={
            "sql_statement": "ALTER TABLE transactions ADD COLUMN currency VARCHAR(3) DEFAULT 'USD'",
            "database_name": "banking_db",
            "change_id": "test_add_column_001",
            "repository": "banking-app"
        },
        timeout=120
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Analysis ID: {result['id']}")
        print(f"✅ Risk Score: {result['risk_score']['score']}/10 - {result['risk_score']['level']}")
        print(f"✅ Affected Files: {len(result['affected_files'])}")
        print(f"✅ Affected Tables: {len(result['affected_tables'])}")
        print(f"\n📋 Summary:")
        print(f"   Code Files: {result['summary']['code_files_affected']}")
        print(f"   Tables: {result['summary']['tables_affected']}")
        print(f"   Total Usages: {result['summary']['total_usages']}")
        return result
    else:
        print(f"❌ Error: {response.status_code}")
        print(response.text)
        return None

def test_drop_column():
    """Test dropping a column (high risk)"""
    print("\n" + "="*60)
    print("TEST 2: Drop Column from Transactions Table")
    print("="*60)
    
    response = requests.post(
        f"{BACKEND_URL}/api/v1/schema/analyze",
        json={
            "sql_statement": "ALTER TABLE transactions DROP COLUMN geo_location",
            "database_name": "banking_db",
            "change_id": "test_drop_column_001",
            "repository": "banking-app"
        },
        timeout=120
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Analysis ID: {result['id']}")
        print(f"✅ Risk Score: {result['risk_score']['score']}/10 - {result['risk_score']['level']}")
        print(f"✅ Affected Files: {len(result['affected_files'])}")
        return result
    else:
        print(f"❌ Error: {response.status_code}")
        print(response.text)
        return None

def test_rename_column():
    """Test renaming a column"""
    print("\n" + "="*60)
    print("TEST 3: Rename Column")
    print("="*60)
    
    response = requests.post(
        f"{BACKEND_URL}/api/v1/schema/analyze",
        json={
            "sql_statement": "ALTER TABLE transactions RENAME COLUMN processed_at TO transaction_timestamp",
            "database_name": "banking_db",
            "change_id": "test_rename_column_001",
            "repository": "banking-app"
        },
        timeout=120
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Analysis ID: {result['id']}")
        print(f"✅ Risk Score: {result['risk_score']['score']}/10 - {result['risk_score']['level']}")
        return result
    else:
        print(f"❌ Error: {response.status_code}")
        print(response.text)
        return None

def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("DATABASE SCHEMA CHANGE ANALYSIS - TEST SUITE")
    print("="*60)
    print(f"\nBackend URL: {BACKEND_URL}")
    print("Make sure backend is running: docker-compose up -d backend\n")
    
    # Check if backend is running
    try:
        health = requests.get(f"{BACKEND_URL}/health", timeout=5)
        if health.status_code != 200:
            print("❌ Backend is not healthy")
            sys.exit(1)
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to backend. Is it running?")
        print("   Run: docker-compose up -d backend")
        sys.exit(1)
    
    results = []
    
    # Run tests
    try:
        results.append(test_add_column())
        results.append(test_drop_column())
        results.append(test_rename_column())
    except KeyboardInterrupt:
        print("\n\n⚠️ Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    successful = sum(1 for r in results if r is not None)
    print(f"✅ Successful: {successful}/{len(results)}")
    print(f"\n🌐 View results at: http://localhost:3000")
    print("\n")

if __name__ == "__main__":
    main()

