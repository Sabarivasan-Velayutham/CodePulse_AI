"""
Demo runner script
Automates demo scenario execution
"""

import asyncio
import httpx
import sys
import time
from datetime import datetime

DEMO_SCENARIOS = {
    "1": {
        "name": "Fee Calculation Change",
        "description": "Modify international transfer fee calculation",
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
        "expected_risk": "HIGH",
        "talking_points": [
            "Notice the risk score - HIGH due to customer impact",
            "See the direct dependencies: FraudDetection, AccountBalance",
            "AI caught the regulatory concern (Regulation E)",
            "Generated test plan includes edge cases"
        ]
    },
    "2": {
        "name": "Database Schema Change",
        "description": "Add currency column to TRANSACTIONS table",
        "file_path": "src/database/TransactionDAO.java",
        "diff": """
@@ -20,7 +20,7 @@ public class TransactionDAO {
     public void save(Payment payment) {
-        String sql = "INSERT INTO transactions (id, amount, status) VALUES (?, ?, ?)";
+        String sql = "INSERT INTO transactions (id, amount, currency, status) VALUES (?, ?, ?, ?)";
     }
""",
        "expected_risk": "CRITICAL",
        "talking_points": [
            "Database changes are HIGH RISK",
            "See how many modules read from this table",
            "AI identified migration complexity (15M rows)",
            "Recommends blue-green deployment"
        ]
    },
    "3": {
        "name": "Breaking API Change",
        "description": "Change method signature in FraudDetection",
        "file_path": "src/fraud/FraudDetection.java",
        "diff": """
@@ -15,7 +15,7 @@ public class FraudDetection {
-    public boolean checkTransaction(Payment payment) {
+    public FraudResult checkTransaction(Payment payment, Context context) {
         // Method signature changed - breaking change
     }
""",
        "expected_risk": "CRITICAL",
        "talking_points": [
            "This is a BREAKING CHANGE",
            "Watch the cascade: FraudDetection → PaymentProcessor → MobileApp",
            "5 million users would be affected",
            "AI recommends backward compatibility approach"
        ]
    },
    "4": {
        "name": "The Saved Disaster",
        "description": "Friday evening deployment with edge case",
        "file_path": "src/payment/PaymentProcessor.java",
        "diff": """
@@ -58,6 +58,11 @@ public class PaymentProcessor {
     private double calculateFee(double amount, String type) {
+        // NEW: Apply month-end surcharge
+        LocalDate today = LocalDate.now();
+        if (today.getDayOfMonth() == 31) {
+            amount = amount * 1.1; // 10% surcharge
+        }
+        
         if (type.equals("INTERNATIONAL")) {
             return amount * 0.03;
         }
""",
        "expected_risk": "CRITICAL",
        "talking_points": [
            "Developer trying to deploy Friday at 5 PM",
            "AI caught the date edge case (what about Feb, Apr, etc.?)",
            "References similar incident from 2023",
            "Recommends delaying until Monday - DISASTER AVERTED!"
        ]
    }
}

class DemoRunner:
    def __init__(self):
        self.backend_url = "http://localhost:8000"
        self.frontend_url = "http://localhost:3000"
    
    async def run_scenario(self, scenario_key: str):
        """Run a specific demo scenario"""
        
        if scenario_key not in DEMO_SCENARIOS:
            print(f"❌ Unknown scenario: {scenario_key}")
            return False
        
        scenario = DEMO_SCENARIOS[scenario_key]
        
        print("\n" + "="*70)
        print(f"🎬 DEMO SCENARIO {scenario_key}: {scenario['name']}")
        print("="*70)
        print(f"\n📝 Description: {scenario['description']}")
        print(f"\n🎯 Expected Risk: {scenario['expected_risk']}")
        
        input("\n⏸️  Press ENTER to trigger analysis...")
        
        # Prepare payload
        payload = {
            "file_path": scenario["file_path"],
            "repository": "banking-app-demo",
            "diff": scenario["diff"]
        }
        
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                print("\n🚀 Triggering analysis...")
                start_time = time.time()
                
                response = await client.post(
                    f"{self.backend_url}/api/v1/analyze",
                    json=payload
                )
                
                duration = time.time() - start_time
                
                if response.status_code != 200:
                    print(f"❌ Analysis failed: {response.status_code}")
                    return False
                
                result = response.json()
                
                print(f"\n✅ Analysis complete in {duration:.1f}s")
                print(f"   Analysis ID: {result['id']}")
                
                # Display results
                self._display_results(result, scenario)
                
                # Show talking points
                print("\n" + "-"*70)
                print("💬 TALKING POINTS FOR JUDGES:")
                print("-"*70)
                for i, point in enumerate(scenario['talking_points'], 1):
                    print(f"{i}. {point}")
                
                print("\n" + "="*70)
                print(f"🌐 View in Dashboard: {self.frontend_url}")
                print("="*70)
                
                return True
                
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
    
    def _display_results(self, result: dict, scenario: dict):
        """Display analysis results"""
        
        risk_score = result.get("risk_score", {})
        dependencies = result.get("dependencies", {})
        ai_insights = result.get("ai_insights", {})
        
        # Risk Score
        print("\n📊 RISK ANALYSIS:")
        print("-"*70)
        print(f"   Score: {risk_score.get('score', 0)}/10")
        print(f"   Level: {risk_score.get('level', 'UNKNOWN')}")
        
        # Check if matches expected
        expected = scenario.get('expected_risk', '')
        actual = risk_score.get('level', '')
        if expected in actual or actual in expected:
            print(f"   ✅ Matches expected risk level")
        else:
            print(f"   ⚠️  Expected {expected}, got {actual}")
        
        # Dependencies
        dep_count = dependencies.get("count", {})
        print(f"\n🔗 DEPENDENCIES:")
        print("-"*70)
        print(f"   Direct: {dep_count.get('direct', 0)}")
        print(f"   Indirect: {dep_count.get('indirect', 0)}")
        print(f"   Total: {dep_count.get('total', 0)}")
        
        # AI Insights
        print(f"\n🤖 AI INSIGHTS:")
        print("-"*70)
        print(f"   Summary: {ai_insights.get('summary', 'N/A')[:150]}...")
        
        risks = ai_insights.get('risks', [])
        if risks:
            print(f"\n   Identified Risks ({len(risks)}):")
            for i, risk in enumerate(risks[:3], 1):
                print(f"   {i}. {risk}")
        
        regulatory = ai_insights.get('regulatory_concerns', '')
        if regulatory and regulatory.lower() not in ['none', 'n/a']:
            print(f"\n   ⚖️  Regulatory: {regulatory}")
    
    def show_menu(self):
        """Show interactive menu"""
        print("\n" + "="*70)
        print("🎬 CODEFLOW CATALYST - DEMO RUNNER")
        print("="*70)
        print("\nAvailable Scenarios:")
        print()
        
        for key, scenario in DEMO_SCENARIOS.items():
            print(f"{key}. {scenario['name']}")
            print(f"   {scenario['description']}")
            print(f"   Expected Risk: {scenario['expected_risk']}")
            print()
        
        print("0. Run all scenarios sequentially")
        print("q. Quit")
        print()
    
    async def run_all_scenarios(self):
        """Run all scenarios sequentially"""
        print("\n🎬 Running all demo scenarios...")
        
        for key in sorted(DEMO_SCENARIOS.keys()):
            success = await self.run_scenario(key)
            
            if not success:
                print(f"\n⚠️  Scenario {key} failed")
                break
            
            if key != list(DEMO_SCENARIOS.keys())[-1]:
                input("\n⏸️  Press ENTER to continue to next scenario...")
        
        print("\n✅ All scenarios complete!")
    
    async def interactive_mode(self):
        """Interactive demo mode"""
        while True:
            self.show_menu()
            choice = input("Select scenario (1-4, 0, or q): ").strip()
            
            if choice.lower() == 'q':
                print("👋 Goodbye!")
                break
            
            if choice == '0':
                await self.run_all_scenarios()
            elif choice in DEMO_SCENARIOS:
                await self.run_scenario(choice)
            else:
                print("❌ Invalid choice. Please try again.")
            
            input("\n⏸️  Press ENTER to return to menu...")

async def main():
    runner = DemoRunner()
    
    if len(sys.argv) > 1:
        # Command-line mode
        scenario_key = sys.argv[1]
        await runner.run_scenario(scenario_key)
    else:
        # Interactive mode
        await runner.interactive_mode()

if __name__ == "__main__":
    asyncio.run(main())