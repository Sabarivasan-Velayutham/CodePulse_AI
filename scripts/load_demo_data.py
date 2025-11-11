"""
Load demo data by triggering LIVE analysis.
This script creates complex, high-risk scenarios based on the sample repo
to populate the dashboard with interesting data.
"""

import json
import httpx
import asyncio
import sys
import time

# --- DEMO DATA ---
# This data is designed to trigger a real analysis based on the
# sample-repo code, creating interesting and varied dependency graphs.
DEMO_DATA = [
    {
        "scenario_name": "Scenario 1: PaymentProcessor Core Logic - Fee Calculation Integration",
        "file_path": "sample-repo/banking-app/src/payment/PaymentProcessor.java",
        "commit_sha": "demo_payment_processor_fee_change",
        "repository": "banking-app-demo",
        "diff": """
--- a/src/payment/PaymentProcessor.java
+++ b/src/payment/PaymentProcessor.java
@@ -105,8 +105,12 @@ public class PaymentProcessor {
             }
             
             // Step 7: Calculate fees
-            double fee = feeCalculator.calculate(payment);
+            // CHANGED: Added fee calculation with customer tier check
+            double fee = feeCalculator.calculate(payment);
+            if (customer.isPremiumMember()) {
+                fee = fee * 0.5; // Additional 50% discount for premium
+            }
             payment.setFee(fee);
             
             // Step 8: Process through payment gateway
"""
    },
    {
        "scenario_name": "Scenario 2: FeeCalculator International Fee Structure Change",
        "file_path": "sample-repo/banking-app/src/payment/FeeCalculator.java",
        "commit_sha": "demo_fee_calculator_international",
        "repository": "banking-app-demo",
        "diff": """
--- a/src/payment/FeeCalculator.java
+++ b/src/payment/FeeCalculator.java
@@ -41,9 +41,15 @@ public class FeeCalculator {
         // International wire transfers
         else if (paymentType.equals("INTERNATIONAL")) {
-            // Percentage-based fee
-            baseFee = amount * 0.03; // 3% fee
+            // CHANGED: New tiered fee structure for international transfers
+            if (amount < 10000) {
+                baseFee = amount * 0.025 + 15.0; // 2.5% + $15 flat
+            } else if (amount < 50000) {
+                baseFee = amount * 0.02 + 50.0; // 2% + $50 flat
+            } else {
+                baseFee = amount * 0.015 + 100.0; // 1.5% + $100 flat
+            }
             
             // Minimum fee
             if (baseFee < 35.0) {
"""
    },
    {
        "scenario_name": "Scenario 3: FraudDetection Threshold Change - Security Impact",
        "file_path": "sample-repo/banking-app/src/fraud/FraudDetection.java",
        "commit_sha": "demo_fraud_detection_threshold",
        "repository": "banking-app-demo",
        "diff": """
--- a/src/fraud/FraudDetection.java
+++ b/src/fraud/FraudDetection.java
@@ -40,7 +40,7 @@ public class FraudDetection {
         auditLogger.log("FRAUD_CHECK_STARTED", payment.getCustomerId(), payment);
         
         // Rule 1: Amount threshold
-        if (payment.getAmount() > 50000) {
+        if (payment.getAmount() > 10000) { // CHANGED: Lowered threshold from $50k to $10k
             logSuspiciousActivity(payment, "HIGH_AMOUNT", "Amount exceeds $50,000");
             return true;
         }
@@ -122,7 +122,7 @@ public class FraudDetection {
         // Rule 8: ML-based fraud detection
         double mlFraudScore = mlModel.predictFraudProbability(payment, customer);
-        if (mlFraudScore > 0.85) {
+        if (mlFraudScore > 0.75) { // CHANGED: Lowered ML threshold from 0.85 to 0.75
             logSuspiciousActivity(payment, "ML_HIGH_FRAUD_SCORE", 
                 "ML model fraud score: " + mlFraudScore);
             return true;
"""
    },
    {
        "scenario_name": "Scenario 4: TransactionDAO Schema Change - Add Currency Column",
        "file_path": "sample-repo/banking-app/src/database/TransactionDAO.java",
        "commit_sha": "demo_transaction_dao_schema",
        "repository": "banking-app-demo",
        "diff": """
--- a/src/database/TransactionDAO.java
+++ b/src/database/TransactionDAO.java
@@ -27,9 +27,11 @@ public class TransactionDAO {
     public void save(Payment payment) {
         String sql = "INSERT INTO transactions (" +
                      "transaction_id, customer_id, account_id, " +
-                     "amount, fee, type, status, " +
+                     "amount, fee, currency, type, status, " + // CHANGED: Added currency column
                      "processed_at, device_id, ip_address, " +
                      "geo_location, requires_manual_review) " +
-                     "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)";
+                     "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"; // 13 params now
         
         try (Connection conn = dbConnection.getConnection();
              PreparedStatement stmt = conn.prepareStatement(sql)) {
@@ -40,6 +42,7 @@ public class TransactionDAO {
             stmt.setDouble(4, payment.getAmount());
             stmt.setDouble(5, payment.getFee());
-            stmt.setString(6, payment.getType());
+            stmt.setString(6, payment.getCurrency()); // NEW: Currency parameter
+            stmt.setString(7, payment.getType());
             stmt.setString(7, payment.getStatus());
"""
    },
    {
        "scenario_name": "Scenario 5: AccountBalance Calculation - Include Pending Transactions",
        "file_path": "sample-repo/banking-app/src/account/AccountBalance.java",
        "commit_sha": "demo_account_balance_pending",
        "repository": "banking-app-demo",
        "diff": """
--- a/src/account/AccountBalance.java
+++ b/src/account/AccountBalance.java
@@ -22,8 +22,15 @@ public class AccountBalance {
     public double getBalance(String accountId) {
         List<Transaction> transactions = 
             transactionDAO.findByAccountId(accountId);
+        // CHANGED: Now include pending transactions in balance calculation
+        List<Transaction> pendingTransactions = 
+            transactionDAO.findPendingByAccountId(accountId);
         
         double balance = 0.0;
         for (Transaction txn : transactions) {
             if (txn.getType().equals("CREDIT")) {
                 balance += txn.getAmount();
             } else if (txn.getType().equals("DEBIT")) {
                 balance -= txn.getAmount();
             }
         }
+        
+        // NEW: Subtract pending debits from available balance
+        for (Transaction pending : pendingTransactions) {
+            if (pending.getType().equals("DEBIT") && pending.getStatus().equals("PENDING")) {
+                balance -= pending.getAmount();
+            }
+        }
         
         return balance;
     }
"""
    }
]


async def load_demo_data():
    """Trigger live analysis for each demo scenario"""

    print("\n" + "="*60)
    print("📦 TRIGGERING LIVE DEMO DATA ANALYSIS")
    print("="*60)
    print("\nThis will populate the system by triggering a")
    print("live analysis for each demo scenario.\n")

    backend_url = "http://localhost:8000"
    start_time = time.time()

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Check if backend is running
            try:
                await client.get(f"{backend_url}/health")
            except httpx.ConnectError:
                print("❌ Backend not running. Please start backend first.")
                print("   Run: docker-compose up -d backend")
                return False

            print(f"✅ Backend is running\n")

            # Load each demo analysis
            for i, data in enumerate(DEMO_DATA, 1):
                print(
                    f"📝 Triggering scenario {i}/{len(DEMO_DATA)}: {data['scenario_name']}")

                request_data = {
                    "file_path": data["file_path"],
                    "repository": data["repository"],
                    "diff": data["diff"]
                }

                try:
                    # Give each analysis a long timeout
                    response = await client.post(
                        f"{backend_url}/api/v1/analyze",
                        json=request_data,
                        timeout=120.0 
                    )

                    if response.status_code == 200:
                        result = response.json()
                        risk = result.get('risk_score', {})
                        print(f"   ✅ Loaded: {data['commit_sha']}")
                        print(f"   📊 Risk: {risk.get('score')}/10 - {risk.get('level')}")
                    else:
                        print(
                            f"   ⚠️  Failed to load (status {response.status_code})")
                        print(f"      Response: {response.text[:200]}...")

                except httpx.ReadTimeout:
                     print(f"   ⚠️  Error: Analysis request timed out ( > 120s )")
                except Exception as e:
                    print(f"   ⚠️  Error: {e}")

                # Small delay between requests to not overwhelm the API
                await asyncio.sleep(1)
            
            duration = time.time() - start_time
            print(f"\n✅ Demo data analysis triggered successfully in {duration:.1f}s!")
            print(f"🌐 View at: http://localhost:3000")

            return True

    except Exception as e:
        print(f"❌ Error loading demo data: {e}")
        return False


async def export_current_data():
    """Export current analyses for backup"""
    print("\n" + "="*60)
    print("💾 EXPORTING CURRENT DATA")
    print("="*60)
    print()

    backend_url = "http://localhost:8000"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{backend_url}/api/v1/analyses")

            if response.status_code == 200:
                analyses = response.json()

                # Save to file
                with open('backup_analyses.json', 'w') as f:
                    json.dump(analyses, f, indent=2)

                print(
                    f"✅ Exported {len(analyses)} analyses to backup_analyses.json")
                return True
            else:
                print(f"❌ Failed to export data")
                return False

    except Exception as e:
        print(f"❌ Error exporting data: {e}")
        return False


def show_menu():
    """Show interactive menu"""
    print("\n" + "="*60)
    print("📦 DEMO DATA MANAGER")
    print("="*60)
    print("\n1. Trigger demo data analysis (live)")
    print("2. Export current data to file")
    print("q. Quit")
    print()

async def main():
    """Main function"""
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "load":
            await load_demo_data()
        elif command == "export":
            await export_current_data()
        else:
            print(f"Unknown command: {command}")
            print("Usage: python scripts/load_demo_data.py [load|export]")
    else:
        # Interactive mode
        while True:
            show_menu()
            choice = input("Select option: ").strip()

            if choice == '1':
                await load_demo_data()
            elif choice == '2':
                await export_current_data()
            elif choice.lower() == 'q':
                print("👋 Goodbye!")
                break
            else:
                print("❌ Invalid choice")
            
            print("\nPress ENTER to continue...")
            try:
                # Wait for user input, handle Ctrl+C
                input()
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break

if __name__ == "__main__":
    asyncio.run(main())
