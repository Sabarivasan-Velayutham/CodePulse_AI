"""
Load sample banking data into MongoDB matching the sample repo structure
Based on: sample-repo/banking-app/src/schema/*.sql
"""

from pymongo import MongoClient
from datetime import datetime, date
import os
import sys
import uuid

def date_to_datetime(d):
    """Convert date to datetime (MongoDB requires datetime, not date)"""
    if isinstance(d, date):
        return datetime.combine(d, datetime.min.time())
    return d

# Configuration
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = os.getenv("MONGO_DB", "banking_db")

def load_sample_data():
    """Load sample banking data into MongoDB matching sample repo structure"""
    print("="*60)
    print("📊 MongoDB Sample Data Loader (Sample Repo Structure)")
    print("="*60)
    print(f"   Database: {DB_NAME}")
    print(f"   URI: {MONGO_URI}\n")
    
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        print("   ✅ Connected to MongoDB\n")
        
        db = client[DB_NAME]
        
        # Clear existing data (optional)
        print("   🗑️  Clearing existing collections...")
        for coll_name in ["customers", "customer_devices", "accounts", "balance_history", 
                          "transactions", "fraud_alerts"]:
            db[coll_name].drop()
        print("   ✅ Collections cleared\n")
        
        # Load customers (matching customers.sql)
        print("   📝 Loading customers...")
        customers = [
            {
                "customer_id": str(uuid.uuid4()),
                "email": "john.doe@example.com",
                "first_name": "John",
                "last_name": "Doe",
                "phone": "+1-555-0101",
                "date_of_birth": date_to_datetime(date(1985, 5, 15)),
                "account_created_date": datetime.now(),
                "is_premium_member": False,
                "is_blocked": False,
                "is_suspended": False,
                "average_transaction_amount": 500.00,
                "total_transaction_count": 25,
                "last_transaction_date": datetime.now(),
                "kyc_verified": True,
                "risk_level": "LOW",
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            },
            {
                "customer_id": str(uuid.uuid4()),
                "email": "jane.smith@example.com",
                "first_name": "Jane",
                "last_name": "Smith",
                "phone": "+1-555-0102",
                "date_of_birth": date_to_datetime(date(1990, 8, 22)),
                "account_created_date": datetime.now(),
                "is_premium_member": True,
                "is_blocked": False,
                "is_suspended": False,
                "average_transaction_amount": 1500.00,
                "total_transaction_count": 150,
                "last_transaction_date": datetime.now(),
                "kyc_verified": True,
                "risk_level": "MEDIUM",
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            },
            {
                "customer_id": str(uuid.uuid4()),
                "email": "bob.johnson@example.com",
                "first_name": "Bob",
                "last_name": "Johnson",
                "phone": "+1-555-0103",
                "date_of_birth": date_to_datetime(date(1988, 3, 10)),
                "account_created_date": datetime.now(),
                "is_premium_member": False,
                "is_blocked": False,
                "is_suspended": False,
                "average_transaction_amount": 250.00,
                "total_transaction_count": 10,
                "last_transaction_date": datetime.now(),
                "kyc_verified": False,
                "risk_level": "HIGH",
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            }
        ]
        customer_ids = [c["customer_id"] for c in customers]
        db.customers.insert_many(customers)
        print(f"   ✅ Inserted {len(customers)} customers\n")
        
        # Load customer_devices (matching customers.sql)
        print("   📝 Loading customer_devices...")
        customer_devices = []
        for i, customer_id in enumerate(customer_ids):
            customer_devices.append({
                "device_id": f"device_{i+1}_{customer_id[:8]}",
                "customer_id": customer_id,
                "device_fingerprint": f"fp_{uuid.uuid4()}",
                "first_seen": datetime.now(),
                "last_seen": datetime.now(),
                "is_trusted": i < 2  # First two are trusted
            })
        db.customer_devices.insert_many(customer_devices)
        print(f"   ✅ Inserted {len(customer_devices)} customer devices\n")
        
        # Load accounts (matching accounts.sql)
        print("   📝 Loading accounts...")
        accounts = []
        account_ids = []
        for i, customer_id in enumerate(customer_ids):
            # Each customer gets 1-2 accounts
            account_id = str(uuid.uuid4())
            account_ids.append(account_id)
            accounts.append({
                "account_id": account_id,
                "customer_id": customer_id,
                "account_number": f"123456789{i*2}",
                "account_type": "CHECKING" if i % 2 == 0 else "SAVINGS",
                "balance": 10000.00 + (i * 5000),
                "currency": "USD",
                "overdraft_enabled": i == 0,
                "overdraft_limit": 1000.00 if i == 0 else 0.00,
                "status": "ACTIVE",
                "opened_date": date_to_datetime(date.today()),
                "closed_date": None,
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            })
            # Second account for first customer
            if i == 0:
                account_id2 = str(uuid.uuid4())
                account_ids.append(account_id2)
                accounts.append({
                    "account_id": account_id2,
                    "customer_id": customer_id,
                    "account_number": f"123456789{i*2+1}",
                    "account_type": "SAVINGS",
                    "balance": 50000.00,
                    "currency": "USD",
                    "overdraft_enabled": False,
                    "overdraft_limit": 0.00,
                    "status": "ACTIVE",
                    "opened_date": date_to_datetime(date.today()),
                    "closed_date": None,
                    "created_at": datetime.now(),
                    "updated_at": datetime.now()
                })
        db.accounts.insert_many(accounts)
        print(f"   ✅ Inserted {len(accounts)} accounts\n")
        
        # Load balance_history (matching accounts.sql)
        print("   📝 Loading balance_history...")
        balance_history = []
        for account_id in account_ids[:3]:  # History for first 3 accounts
            balance_history.append({
                "history_id": len(balance_history) + 1,
                "account_id": account_id,
                "old_balance": 0.00,
                "new_balance": 10000.00,
                "transaction_id": None,
                "change_type": "INITIAL",
                "timestamp": datetime.now()
            })
        db.balance_history.insert_many(balance_history)
        print(f"   ✅ Inserted {len(balance_history)} balance history records\n")
        
        # Load transactions (matching transactions.sql)
        print("   📝 Loading transactions...")
        transactions = []
        transaction_ids = []
        for i, account_id in enumerate(account_ids[:4]):  # Transactions for first 4 accounts
            customer_id = accounts[i % len(accounts)]["customer_id"]
            transaction_id = str(uuid.uuid4())
            transaction_ids.append(transaction_id)
            transactions.append({
                "transaction_id": transaction_id,
                "customer_id": customer_id,
                "account_id": account_id,
                "amount": 500.00 + (i * 100),
                "fee": 2.50 + (i * 0.50),
                "type": "DOMESTIC" if i % 2 == 0 else "INTERNATIONAL",
                "status": "COMPLETED" if i < 3 else "PENDING",
                "processed_at": datetime.now(),
                "device_id": customer_devices[i % len(customer_devices)]["device_id"],
                "ip_address": f"192.168.1.{100+i}",
                "geo_location": "US" if i % 2 == 0 else "UK",
                "requires_manual_review": i == 2,
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            })
        db.transactions.insert_many(transactions)
        print(f"   ✅ Inserted {len(transactions)} transactions\n")
        
        # Load fraud_alerts (matching transactions.sql)
        print("   📝 Loading fraud_alerts...")
        fraud_alerts = []
        for i, transaction_id in enumerate(transaction_ids[:2]):  # Alerts for first 2 transactions
            customer_id = transactions[i]["customer_id"]
            fraud_alerts.append({
                "alert_id": len(fraud_alerts) + 1,
                "customer_id": customer_id,
                "payment_id": transaction_id,
                "rule_code": f"RULE_{i+1}",
                "reason": "Unusual transaction pattern detected" if i == 0 else "Large international transfer",
                "severity": "HIGH" if i == 0 else "MEDIUM",
                "alert_timestamp": datetime.now(),
                "investigated": False,
                "investigation_notes": None,
                "created_at": datetime.now()
            })
        db.fraud_alerts.insert_many(fraud_alerts)
        print(f"   ✅ Inserted {len(fraud_alerts)} fraud alerts\n")
        
        # Create indexes (matching SQL schema indexes)
        print("   📝 Creating indexes...")
        
        # customers indexes
        db.customers.create_index("customer_id", unique=True, name="idx_customer_id")
        db.customers.create_index("email", unique=True, name="idx_email")
        db.customers.create_index("is_blocked", name="idx_is_blocked")
        db.customers.create_index("risk_level", name="idx_risk_level")
        
        # customer_devices indexes
        db.customer_devices.create_index("device_id", unique=True)
        db.customer_devices.create_index("customer_id", name="idx_customer_id")
        
        # accounts indexes
        db.accounts.create_index("account_id", unique=True, name="idx_account_id")
        db.accounts.create_index("customer_id", name="idx_customer_id")
        db.accounts.create_index("account_number", unique=True, name="idx_account_number")
        db.accounts.create_index("status", name="idx_status")
        
        # balance_history indexes
        db.balance_history.create_index("history_id", unique=True)
        db.balance_history.create_index("account_id", name="idx_account_id")
        db.balance_history.create_index("transaction_id", name="idx_transaction_id")
        
        # transactions indexes
        db.transactions.create_index("transaction_id", unique=True, name="idx_transaction_id")
        db.transactions.create_index("customer_id", name="idx_customer_id")
        db.transactions.create_index("account_id", name="idx_account_id")
        db.transactions.create_index("processed_at", name="idx_processed_at")
        db.transactions.create_index("status", name="idx_status")
        
        # fraud_alerts indexes
        db.fraud_alerts.create_index("alert_id", unique=True)
        db.fraud_alerts.create_index("customer_id", name="idx_customer_id")
        db.fraud_alerts.create_index("payment_id", name="idx_payment_id")
        db.fraud_alerts.create_index("alert_timestamp", name="idx_alert_timestamp")
        db.fraud_alerts.create_index("investigated", name="idx_investigated")
        
        print("   ✅ Indexes created\n")
        
        # Summary
        print("="*60)
        print("✅ Sample Data Loaded Successfully!")
        print("="*60)
        print(f"   Collections:")
        print(f"      - customers: {db.customers.count_documents({})} documents")
        print(f"      - customer_devices: {db.customer_devices.count_documents({})} documents")
        print(f"      - accounts: {db.accounts.count_documents({})} documents")
        print(f"      - balance_history: {db.balance_history.count_documents({})} documents")
        print(f"      - transactions: {db.transactions.count_documents({})} documents")
        print(f"      - fraud_alerts: {db.fraud_alerts.count_documents({})} documents")
        print(f"\n   💡 Test schema changes:")
        print(f"      - Create collection: db.payments.insertOne({{}})")
        print(f"      - Create index: db.transactions.createIndex({{amount: 1}})")
        print(f"      - Drop index: db.transactions.dropIndex('amount_1')")
        print("="*60)
        
        client.close()
        
    except Exception as e:
        print(f"\n❌ Error loading data: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    load_sample_data()
