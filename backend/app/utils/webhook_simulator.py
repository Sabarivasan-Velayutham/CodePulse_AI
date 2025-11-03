"""
Webhook simulator for demo purposes
Simulates GitHub webhook payloads
"""

import httpx
import asyncio
from typing import Dict

class WebhookSimulator:
    def __init__(self, backend_url: str = "http://localhost:8000"):
        self.backend_url = backend_url
    
    async def simulate_commit(
        self,
        file_path: str,
        diff: str,
        scenario_name: str = "Demo"
    ):
        """Simulate a Git commit webhook"""
        
        payload = {
            "event": "push",
            "repository": "banking-app-demo",
            "commit_sha": f"demo_{scenario_name.lower().replace(' ', '_')}",
            "author": "demo@bank.com",
            "branch": "main",
            "files_changed": [
                {
                    "path": file_path,
                    "status": "modified",
                    "additions": 5,
                    "deletions": 2
                }
            ],
            "diff": diff
        }
        
        print(f"\n🚀 Simulating commit: {scenario_name}")
        print(f"   File: {file_path}")
        print(f"   Diff: {diff[:50]}...")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.backend_url}/api/v1/webhook/github",
                json=payload,
                timeout=60.0
            )
            
            if response.status_code == 202:
                print(f"✅ Webhook accepted")
                return response.json()
            else:
                print(f"❌ Webhook failed: {response.status_code}")
                return None

# Demo scenarios
DEMO_SCENARIOS = {
    "scenario1_fee_change": {
        "file_path": "src/payment/PaymentProcessor.java",
        "diff": """
@@ -55,7 +55,7 @@ public class PaymentProcessor {
     private double calculateFee(double amount, String type) {
         if (type.equals("INTERNATIONAL")) {
-            return amount * 0.03; // 3% fee
+            return amount * 0.025 + 15.0; // 2.5% + $15 flat fee
         }
     }
""",
        "name": "Fee Calculation Change"
    },
    "scenario2_database_change": {
        "file_path": "src/database/TransactionDAO.java",
        "diff": """
@@ -20,7 +20,7 @@ public class TransactionDAO {
     public void save(Payment payment) {
-        String sql = "INSERT INTO transactions (id, amount, status) VALUES (?, ?, ?)";
+        String sql = "INSERT INTO transactions (id, amount, currency, status) VALUES (?, ?, ?, ?)";
     }
""",
        "name": "Database Schema Change"
    },
    "scenario3_breaking_change": {
        "file_path": "src/fraud/FraudDetection.java",
        "diff": """
@@ -15,7 +15,7 @@ public class FraudDetection {
-    public boolean checkTransaction(Payment payment) {
+    public FraudResult checkTransaction(Payment payment, Context context) {
         // Method signature changed
     }
""",
        "name": "Breaking API Change"
    }
}

async def run_demo_scenario(scenario_key: str):
    """Run a specific demo scenario"""
    if scenario_key not in DEMO_SCENARIOS:
        print(f"❌ Unknown scenario: {scenario_key}")
        print(f"Available: {list(DEMO_SCENARIOS.keys())}")
        return
    
    scenario = DEMO_SCENARIOS[scenario_key]
    simulator = WebhookSimulator()
    
    result = await simulator.simulate_commit(
        file_path=scenario["file_path"],
        diff=scenario["diff"],
        scenario_name=scenario["name"]
    )
    
    if result:
        print(f"\n✅ Scenario '{scenario['name']}' triggered successfully")
        print(f"   Wait 10-15 seconds for analysis to complete")
        print(f"   Then check: http://localhost:3000")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        scenario = sys.argv[1]
    else:
        print("Available scenarios:")
        for key, scenario in DEMO_SCENARIOS.items():
            print(f"  - {key}: {scenario['name']}")
        scenario = input("\nEnter scenario key: ")
    
    asyncio.run(run_demo_scenario(scenario))