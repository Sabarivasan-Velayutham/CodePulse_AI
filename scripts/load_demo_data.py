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

# --- NEW DEMO DATA ---
# This data is designed to trigger a real analysis based on the
# sample-repo code, creating interesting and varied risk scores.
DEMO_DATA = [
    {
        "scenario_name": "Scenario 1: High-Risk Fee Change (PaymentProcessor)",
        "file_path": "sample-repo/banking-app/src/payment/PaymentProcessor.java",
        "commit_sha": "demo_fee_change_high_risk",
        "repository": "banking-app-demo",
        "diff": """
--- a/src/payment/PaymentProcessor.java
+++ b/src/payment/PaymentProcessor.java
@@ -60,10 +60,8 @@
     */
    private double calculateFee(double amount, String type) {
        if (type.equals("DOMESTIC")) {
-           return 10.0;
        } else if (type.equals("INTERNATIONAL")) {
-           return amount * 0.03; // 3% fee
+           return amount * 0.025 + 15.0; // 2.5% + $15 flat fee
        }
        return 0.0;
    }
"""
    },
    {
        "scenario_name": "Scenario 2: Critical Fraud Logic Change (FraudDetection)",
        "file_path": "sample-repo/banking-app/src/fraud/FraudDetection.java",
        "commit_sha": "demo_fraud_logic_critical",
        "repository": "banking-app-demo",
        "diff": """
--- a/src/fraud/FraudDetection.java
+++ b/src/fraud/FraudDetection.java
@@ -21,7 +21,7 @@
    public boolean checkTransaction(Payment payment) {
        // Rule 1: Check amount threshold
-       if (payment.getAmount() > 50000) {
+       if (payment.getAmount() > 10000) { // CRITICAL: Threshold lowered from 50k to 10k
            logSuspiciousActivity(payment, "High amount");
            return true;
        }
"""
    },
    {
        "scenario_name": "Scenario 3: Low-Risk Logging Change (AccountBalance)",
        "file_path": "sample-repo/banking-app/src/account/AccountBalance.java",
        "commit_sha": "demo_logging_change_low_risk",
        "repository": "banking-app-demo",
        "diff": """
--- a/src/account/AccountBalance.java
+++ b/src/account/AccountBalance.java
@@ -32,6 +32,8 @@
     * @param amount Amount to deduct (including fees)
     */
    public void updateBalance(String accountId, double amount) {
+        // LOW RISK: Add logging
+        System.out.println("Updating balance for account: " + accountId);
        Transaction debitTxn = new Transaction();
        debitTxn.setAccountId(accountId);
        debitTxn.setAmount(amount);
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

