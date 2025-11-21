"""
Test script to simulate API change in backend-api-service
and trigger cross-repo consumer discovery
"""

import requests
import json
import sys
import os

# Fix Windows console encoding for emojis
if sys.platform == 'win32':
    os.system('chcp 65001 >nul 2>&1')  # Set UTF-8 encoding

# Backend API URL
API_URL = "http://localhost:8000/api/v1/api/contract/analyze"

def test_api_contract_change(scenario=1):
    """Test API contract change detection with cross-repo consumer discovery"""
    
    print("=" * 60)
    print("Testing Backend API Service Change")
    print("=" * 60)
    
    # Multiple test scenarios
    # Scenario 1: WITH consumer impact (used by consumer repos)
    # Scenarios 2-4: WITHOUT consumer impact (not used by any repo)
    scenarios = {
        # ============================================================
        # SCENARIOS WITH CONSUMER IMPACT (Used by consumer repos)
        # ============================================================
        
        1: {
            "name": "[WITH IMPACT] Breaking Change: Add Required Parameter to POST /api/auctions/{id}/bid",
            "file_path": "backend-api-service/src/main/java/com/backendapi/AuctionController.java",
            "repository": "backend-api-service",
            "diff": """
-    @PostMapping("/{id}/bid")
-    public ResponseEntity<?> placeBid(
-        @PathVariable String id,
-        @RequestBody Map<String, Object> request
-    ) {
-        // Places a bid on an auction
-        // Required fields: bidAmount, bidderId
-        return ResponseEntity.ok().build();
-    }
+    @PostMapping("/{id}/bid")
+    public ResponseEntity<?> placeBid(
+        @PathVariable String id,
+        @RequestBody Map<String, Object> request,
+        @RequestParam String paymentMethod
+    ) {
+        // Places a bid on an auction
+        // Required fields: bidAmount, bidderId, paymentMethod
+        return ResponseEntity.ok().build();
+    }
            """,
            "commit_sha": "test_with_impact_002",
            "commit_message": "Added required paymentMethod parameter to placeBid endpoint",
            "github_repo_url": "https://github.com/Sabarivasan-Velayutham/backend-api-service",
            "expected_consumers": "auctioneer (uses this endpoint for bidding)"
        },       
        # ============================================================
        # SCENARIOS WITHOUT CONSUMER IMPACT (Not used by any repo)
        # ============================================================
        2: {
            "name": "[NO IMPACT] Breaking Change: Add Required Parameter to POST /api/stocks/buy",
            "file_path": "backend-api-service/src/main/java/com/backendapi/StockController.java",
            "repository": "backend-api-service",
            "diff": """
-    @PostMapping("/buy")
-    public ResponseEntity<?> buyStock(@RequestBody Map<String, Object> request) {
-        // Processes stock purchase
-        // Required fields: stockId, quantity, accountId
-        return ResponseEntity.ok().build();
-    }
+    @PostMapping("/buy")
+    public ResponseEntity<?> buyStock(
+        @RequestBody Map<String, Object> request,
+        @RequestParam String verificationCode
+    ) {
+        // Processes stock purchase
+        // Required fields: stockId, quantity, accountId, verificationCode (NEW - BREAKING)
+        return ResponseEntity.ok().build();
+    }
            """,
            "commit_sha": "test_no_impact_001",
            "commit_message": "Added required verificationCode parameter to buyStock endpoint",
            "github_repo_url": "https://github.com/Sabarivasan-Velayutham/backend-api-service",
            "expected_consumers": "None (endpoint not used by any consumer repo)"
        },
        3: {
            "name": "[NO IMPACT] Breaking Change: Change GET /api/transactions/account/{accountId} Path",
            "file_path": "backend-api-service/src/main/java/com/backendapi/TransactionController.java",
            "repository": "backend-api-service",
            "diff": """
-    @GetMapping("/account/{accountId}")
-    public ResponseEntity<?> getTransactionsByAccount(@PathVariable String accountId) {
-        // Returns all transactions for a specific account
-        return ResponseEntity.ok().build();
-    }
+    @GetMapping("/by-account/{accountId}")
+    public ResponseEntity<?> getTransactionsByAccount(@PathVariable String accountId) {
+        // Returns all transactions for a specific account
+        // BREAKING: Path changed from /account/{accountId} to /by-account/{accountId}
+        return ResponseEntity.ok().build();
+    }
            """,
            "commit_sha": "test_no_impact_002",
            "commit_message": "Changed endpoint path from /account/{accountId} to /by-account/{accountId}",
            "github_repo_url": "https://github.com/Sabarivasan-Velayutham/backend-api-service",
            "expected_consumers": "None (endpoint not used by any consumer repo)"
        },
        4: {
            "name": "[NO IMPACT] Breaking Change: Remove Required Field from PUT /api/accounts/{id}",
            "file_path": "backend-api-service/src/main/java/com/backendapi/AccountController.java",
            "repository": "backend-api-service",
            "diff": """
-    @PutMapping("/{id}")
-    public ResponseEntity<?> updateAccount(
-        @PathVariable String id,
-        @RequestBody Map<String, Object> request
-    ) {
-        // Updates account details
-        return ResponseEntity.ok().build();
-    }
+    @PutMapping("/{id}")
+    public ResponseEntity<?> updateAccount(
+        @PathVariable String id,
+        @RequestBody Map<String, Object> request
+    ) {
+        // Updates account details
+        // BREAKING: Removed 'email' field requirement - now optional
+        // Previously required: name, email
+        // Now required: name only
+        return ResponseEntity.ok().build();
+    }
            """,
            "commit_sha": "test_no_impact_003",
            "commit_message": "Made email field optional in updateAccount endpoint (previously required)",
            "github_repo_url": "https://github.com/Sabarivasan-Velayutham/backend-api-service",
            "expected_consumers": "None (endpoint not used by any consumer repo)"
        }
    }
    
    # Get selected scenario
    if scenario not in scenarios:
        scenario = 1
    
    test_data = scenarios[scenario]
    scenario_name = test_data.pop("name")
    
    print(f"\n[SCENARIO] {scenario_name}")
    print(f"   File: {test_data['file_path']}")
    print(f"   Expected: System should search all 3 consumer repos")
    if 'expected_consumers' in test_data:
        print(f"   Expected Consumers: {test_data.get('expected_consumers', 'N/A')}")
    
    
    try:
        response = requests.post(API_URL, json=test_data, timeout=120)
        
        if response.status_code == 200:
            result = response.json()
            
            print("\n[OK] Analysis Complete!")
            print(f"   Analysis ID: {result.get('id', 'N/A')}")
            print(f"   Type: {result.get('type', 'N/A')}")
            
            # Show API changes
            api_changes = result.get('api_changes', [])
            print(f"\n[*] API Changes Detected: {len(api_changes)}")
            for change in api_changes:
                print(f"   - {change.get('method')} {change.get('endpoint')}: {change.get('change_type')}")
                if change.get('change_type') == 'BREAKING':
                    print(f"     [WARNING] BREAKING CHANGE!")
            
            # Show consumers
            consumers = result.get('consumers', {})
            total_consumers = sum(len(cons) for cons in consumers.values())
            print(f"\n[*] Consumers Found: {total_consumers}")
            
            for api_key, consumer_list in consumers.items():
                if consumer_list:
                    print(f"\n   {api_key}:")
                    # Group by source repository
                    by_repo = {}
                    for consumer in consumer_list:
                        repo = consumer.get('source_repo', 'unknown')
                        if repo not in by_repo:
                            by_repo[repo] = []
                        by_repo[repo].append(consumer)
                    
                    for repo, repo_consumers in by_repo.items():
                        print(f"      [REPO] {repo} ({len(repo_consumers)} files):")
                        for consumer in repo_consumers[:3]:  # Show first 3
                            print(f"         - {consumer.get('file_path', 'N/A')} (line {consumer.get('line_number', 0)})")
            
            # Show risk score
            risk_score = result.get('risk_score', {})
            print(f"\n[*] Risk Score: {risk_score.get('score', 'N/A')}/10 - {risk_score.get('level', 'N/A')}")
            
            # Show summary
            summary = result.get('summary', {})
            print(f"\n[*] Summary:")
            print(f"   Total Changes: {summary.get('total_changes', 0)}")
            print(f"   Breaking Changes: {summary.get('breaking_changes', 0)}")
            print(f"   Total Consumers: {summary.get('total_consumers', 0)}")
            print(f"   Affected Endpoints: {summary.get('affected_endpoints', 0)}")
            
            print("\n" + "=" * 60)
            print("[OK] Test completed successfully!")
            print("=" * 60)
            
            return True
            
        else:
            print(f"\n[ERROR] Error: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("\n[ERROR] Cannot connect to backend API")
        print("   Make sure the backend is running on http://localhost:8000")
        return False
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Test API contract change detection')
    parser.add_argument('--scenario', type=int, default=1, choices=[1, 2, 3, 4],
                        help='Test scenario (1-4). Default: 1')
    parser.add_argument('--all', action='store_true',
                        help='Run all test scenarios')
    
    args = parser.parse_args()
    
    if args.all:
        print("=" * 60)
        print("Running All Test Scenarios")
        print("=" * 60)
        all_success = True
        for i in range(1, 5):
            print(f"\n{'='*60}")
            print(f"SCENARIO {i}/4")
            print(f"{'='*60}")
            success = test_api_contract_change(i)
            if not success:
                all_success = False
            print("\n" + "-" * 60)
        sys.exit(0 if all_success else 1)
    else:
        success = test_api_contract_change(args.scenario)
        sys.exit(0 if success else 1)
