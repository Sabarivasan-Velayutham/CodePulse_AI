# PostgreSQL & MongoDB Setup Guide for Schema Change Analysis

## Overview

This guide sets up PostgreSQL and MongoDB databases with triggers that automatically notify CodeFlow Catalyst when schema changes occur.

## Prerequisites

- PostgreSQL 12+ installed
- MongoDB 6+ installed
- psql command-line tool
- CodeFlow Catalyst backend running

## Step 1: Create PostgreSQL Database

### 1.1 Connect to PostgreSQL

```bash
# Connect as postgres user
psql -U postgres
```

### 1.2 Create Database and User

```sql
-- Create database
CREATE DATABASE banking_db;

-- Create user for application
CREATE USER banking_user WITH PASSWORD 'banking123';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE banking_db TO banking_user;

-- Connect to the new database
\c banking_db
```

### 1.3 Create Sample Tables with Relationships

```sql
-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Customers table
CREATE TABLE customers (
    customer_id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Accounts table (references customers)
CREATE TABLE accounts (
    account_id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    customer_id VARCHAR(36) NOT NULL,
    account_number VARCHAR(20) UNIQUE NOT NULL,
    account_type VARCHAR(50) NOT NULL, -- CHECKING, SAVINGS, BUSINESS
    balance DECIMAL(15, 2) DEFAULT 0.00,
    currency VARCHAR(3) DEFAULT 'USD',
    status VARCHAR(20) DEFAULT 'ACTIVE', -- ACTIVE, CLOSED, FROZEN
    opened_date DATE NOT NULL,
    closed_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE
);

-- Transactions table (references accounts)
CREATE TABLE transactions (
    transaction_id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    customer_id VARCHAR(36) NOT NULL,
    account_id VARCHAR(36) NOT NULL,
    amount DECIMAL(15, 2) NOT NULL,
    fee DECIMAL(10, 2) DEFAULT 0.00,
    type VARCHAR(50) NOT NULL, -- DOMESTIC, INTERNATIONAL, ACH, WIRE
    status VARCHAR(50) NOT NULL, -- PENDING, COMPLETED, FAILED, REVERSED
    processed_at TIMESTAMP NOT NULL,
    device_id VARCHAR(100),
    ip_address VARCHAR(45),
    geo_location VARCHAR(100),
    requires_manual_review BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE RESTRICT,
    FOREIGN KEY (account_id) REFERENCES accounts(account_id) ON DELETE RESTRICT
);

-- Fraud alerts table (references transactions)
CREATE TABLE fraud_alerts (
    alert_id SERIAL PRIMARY KEY,
    customer_id VARCHAR(36) NOT NULL,
    transaction_id VARCHAR(36),
    rule_code VARCHAR(50) NOT NULL,
    reason TEXT NOT NULL,
    severity VARCHAR(20) NOT NULL, -- LOW, MEDIUM, HIGH, CRITICAL
    alert_timestamp TIMESTAMP NOT NULL,
    investigated BOOLEAN DEFAULT FALSE,
    investigation_notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE,
    FOREIGN KEY (transaction_id) REFERENCES transactions(transaction_id) ON DELETE SET NULL
);

-- Balance history table (references accounts and transactions)
CREATE TABLE balance_history (
    history_id SERIAL PRIMARY KEY,
    account_id VARCHAR(36) NOT NULL,
    transaction_id VARCHAR(36),
    old_balance DECIMAL(15, 2) NOT NULL,
    new_balance DECIMAL(15, 2) NOT NULL,
    change_type VARCHAR(50), -- DEBIT, CREDIT
    timestamp TIMESTAMP NOT NULL,
    FOREIGN KEY (account_id) REFERENCES accounts(account_id) ON DELETE CASCADE,
    FOREIGN KEY (transaction_id) REFERENCES transactions(transaction_id) ON DELETE SET NULL
);

-- Create indexes
CREATE INDEX idx_transactions_customer_id ON transactions(customer_id);
CREATE INDEX idx_transactions_account_id ON transactions(account_id);
CREATE INDEX idx_transactions_processed_at ON transactions(processed_at);
CREATE INDEX idx_transactions_status ON transactions(status);
CREATE INDEX idx_accounts_customer_id ON accounts(customer_id);
CREATE INDEX idx_fraud_alerts_customer_id ON fraud_alerts(customer_id);
CREATE INDEX idx_fraud_alerts_transaction_id ON fraud_alerts(transaction_id);
```

### 1.4 Grant Permissions

```sql
-- Grant all privileges on tables
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO banking_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO banking_user;

-- Grant privileges on future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO banking_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO banking_user;
```

## Step 2: Set Up PostgreSQL Event Trigger for Schema Changes

### 2.1 Create Function to Notify Schema Changes

```sql
-- Enable pg_notify extension
CREATE EXTENSION IF NOT EXISTS "pg_notify";

-- Create function to capture DDL changes
CREATE OR REPLACE FUNCTION notify_schema_change()
RETURNS event_trigger AS $$
DECLARE
    r RECORD;
    sql_text TEXT;
    payload JSONB;
BEGIN
    -- Get the command tag and SQL
    FOR r IN SELECT * FROM pg_event_trigger_ddl_commands() LOOP
        -- Get the SQL statement from command
        sql_text := current_query();
        
        -- Build payload
        payload := jsonb_build_object(
            'tag', r.command_tag,
            'object_type', r.object_type,
            'object_identity', r.object_identity,
            'schema', r.schema_name,
            'sql', sql_text
        );
        
        -- Notify via pg_notify
        PERFORM pg_notify('schema_change', payload::text);
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Create event trigger
CREATE EVENT TRIGGER schema_change_trigger
ON ddl_command_end
EXECUTE FUNCTION notify_schema_change();
```

### 2.2 Create Listener Script (Python)

Create `scripts/postgres_schema_listener.py`:

```python
"""
PostgreSQL Schema Change Listener
Listens for DDL changes and triggers CodeFlow Catalyst analysis
"""

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import json
import requests
import os
from typing import Dict

BACKEND_URL = os.getenv("CODEFLOW_BACKEND_URL", "http://localhost:8000")
DB_NAME = os.getenv("POSTGRES_DB", "banking_db")
DB_USER = os.getenv("POSTGRES_USER", "banking_user")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "banking123")
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")

def listen_for_schema_changes():
    """Listen for PostgreSQL schema change notifications"""
    print("🔍 Starting PostgreSQL schema change listener...")
    print(f"   Database: {DB_NAME}")
    print(f"   Backend: {BACKEND_URL}")
    
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
        
        print("✅ Listening for schema changes...")
        print("   Make a schema change in PostgreSQL to trigger analysis\n")
        
        while True:
            if conn.poll():
                while conn.notifies:
                    notify = conn.notifies.pop(0)
                    payload = json.loads(notify.payload)
                    
                    print(f"\n📨 Schema change detected!")
                    print(f"   Type: {payload.get('tag')}")
                    print(f"   Object: {payload.get('object_identity')}")
                    
                    # Extract SQL statement
                    sql_statement = payload.get('sql', '')
                    
                    # Call CodeFlow Catalyst API
                    try:
                        response = requests.post(
                            f"{BACKEND_URL}/api/v1/schema/webhook",
                            json={
                                "sql_statement": sql_statement,
                                "database_name": DB_NAME,
                                "change_id": f"pg_{payload.get('object_identity', 'unknown')}",
                                "repository": "banking-app"
                            },
                            timeout=30
                        )
                        
                        if response.status_code == 202:
                            print(f"   ✅ Analysis triggered successfully")
                        else:
                            print(f"   ⚠️  Analysis request failed: {response.status_code}")
                            print(f"      {response.text[:200]}")
                    
                    except Exception as e:
                        print(f"   ❌ Error calling API: {e}")
    
    except KeyboardInterrupt:
        print("\n👋 Listener stopped")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    listen_for_schema_changes()
```

## Step 3: Set Up MongoDB (Optional - for NoSQL analysis)

### 3.1 Connect to MongoDB

```bash
mongosh
```

### 3.2 Create Database and Collections

```javascript
// Switch to banking database
use banking_db

// Create collections with sample documents
db.customers.insertOne({
    customer_id: "cust_001",
    first_name: "John",
    last_name: "Doe",
    email: "john.doe@example.com",
    accounts: ["acc_001", "acc_002"]
})

db.accounts.insertOne({
    account_id: "acc_001",
    customer_id: "cust_001",
    account_number: "1234567890",
    balance: 10000.00,
    currency: "USD"
})

db.transactions.insertOne({
    transaction_id: "txn_001",
    customer_id: "cust_001",
    account_id: "acc_001",
    amount: 500.00,
    type: "DOMESTIC",
    status: "COMPLETED",
    processed_at: new Date()
})
```

### 3.3 Create Change Stream Listener (Python)

Create `scripts/mongodb_schema_listener.py`:

```python
"""
MongoDB Schema Change Listener
Listens for collection/index changes and triggers CodeFlow Catalyst analysis
"""

from pymongo import MongoClient
from pymongo.change_stream import ChangeStream
import requests
import json
import os

BACKEND_URL = os.getenv("CODEFLOW_BACKEND_URL", "http://localhost:8000")
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = os.getenv("MONGO_DB", "banking_db")

def listen_for_mongodb_changes():
    """Listen for MongoDB schema/index changes"""
    print("🔍 Starting MongoDB schema change listener...")
    print(f"   Database: {DB_NAME}")
    print(f"   Backend: {BACKEND_URL}")
    
    try:
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        
        # Watch for collection and index changes
        with db.watch([{"$match": {"operationType": {"$in": ["create", "drop", "modify"]}}}]) as stream:
            print("✅ Listening for MongoDB schema changes...\n")
            
            for change in stream:
                operation = change.get("operationType")
                collection = change.get("ns", {}).get("coll", "unknown")
                
                print(f"\n📨 MongoDB change detected!")
                print(f"   Operation: {operation}")
                print(f"   Collection: {collection}")
                
                # Build SQL-like statement for MongoDB changes
                if operation == "create":
                    sql_statement = f"CREATE COLLECTION {collection}"
                elif operation == "drop":
                    sql_statement = f"DROP COLLECTION {collection}"
                else:
                    sql_statement = f"MODIFY COLLECTION {collection}"
                
                # Call CodeFlow Catalyst API
                try:
                    response = requests.post(
                        f"{BACKEND_URL}/api/v1/schema/webhook",
                        json={
                            "sql_statement": sql_statement,
                            "database_name": f"mongodb_{DB_NAME}",
                            "change_id": f"mongo_{collection}_{operation}",
                            "repository": "banking-app"
                        },
                        timeout=30
                    )
                    
                    if response.status_code == 202:
                        print(f"   ✅ Analysis triggered successfully")
                    else:
                        print(f"   ⚠️  Analysis request failed: {response.status_code}")
                
                except Exception as e:
                    print(f"   ❌ Error calling API: {e}")
    
    except KeyboardInterrupt:
        print("\n👋 Listener stopped")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    listen_for_mongodb_changes()
```

## Step 4: Test the Setup

### 4.1 Start the Listeners

```bash
# Terminal 1: PostgreSQL listener
python scripts/postgres_schema_listener.py

# Terminal 2: MongoDB listener (optional)
python scripts/mongodb_schema_listener.py
```

### 4.2 Make a Schema Change in PostgreSQL

```sql
-- In psql, make a change
ALTER TABLE transactions ADD COLUMN currency VARCHAR(3) DEFAULT 'USD';
```

You should see the listener detect the change and trigger analysis!

### 4.3 Verify in Dashboard

Check `http://localhost:3000` to see the schema change analysis results.

## Step 5: Integration with Code Analysis

The system now supports bidirectional analysis:

1. **Schema Change → Code**: When you change a table, it finds code files using it
2. **Code Change → Database**: When you commit code, it finds database tables used in that code

Both are automatically analyzed and displayed in the dashboard!

