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
    scenarios = {
        1: {
            "name": "Breaking Change: Add Required Parameter",
            "file_path": "backend-api-service/src/main/java/com/backendapi/StockController.java",
            "repository": "backend-api-service",
            "diff": """
-    @PostMapping("/buy")
-    public ResponseEntity<String> buyStock(@RequestParam String symbol, @RequestParam int quantity,@RequestParam String number) {
-        try {
-            transactionService.buyStock(symbol, quantity,number);
-            return ResponseEntity.ok("Stock purchased successfully.");
-        } catch (IllegalArgumentException e) {
-            return ResponseEntity.badRequest().body(e.getMessage());
-        }
-    }
+    @PostMapping("/buy")
+    public ResponseEntity<String> buyStock(@RequestParam String symbol, @RequestParam int quantity, @RequestParam String number, @RequestParam String accountId) {
+        try {
+            transactionService.buyStock(symbol, quantity, number, accountId);
+            return ResponseEntity.ok("Stock purchased successfully.");
+        } catch (IllegalArgumentException e) {
+            return ResponseEntity.badRequest().body(e.getMessage());
+        }
+    }
            """,
            "commit_sha": "test_breaking_change_001",
            "commit_message": "BREAKING: Added required accountId parameter to buyStock endpoint",
            "github_repo_url": "https://github.com/Sabarivasan-Velayutham/backend-api-service"
        },
        2: {
            "name": "Breaking Change: Remove Endpoint",
            "file_path": "backend-api-service/src/main/java/com/backendapi/StockController.java",
            "repository": "backend-api-service",
            "diff": """
-    @PostMapping("/sell")
-    public ResponseEntity<?> sellStock(@RequestBody Map<String, Object> request) {
-        // Processes stock sale
-        // Required fields: stockId, quantity, accountId
-        return ResponseEntity.ok().build();
-    }
-
            """,
            "commit_sha": "test_breaking_change_002",
            "commit_message": "BREAKING: Removed /api/stocks/sell endpoint",
            "github_repo_url": "https://github.com/Sabarivasan-Velayutham/backend-api-service"
        },
        3: {
            "name": "Breaking Change: Change Endpoint Path",
            "file_path": "backend-api-service/src/main/java/com/backendapi/StockController.java",
            "repository": "backend-api-service",
            "diff": """
-    @GetMapping("/{id}/price")
-    public ResponseEntity<?> getStockPrice(@PathVariable String id) {
-        // Returns current stock price
-        return ResponseEntity.ok().build();
-    }
+    @GetMapping("/{id}/current-price")
+    public ResponseEntity<?> getStockPrice(@PathVariable String id) {
+        // Returns current stock price
+        return ResponseEntity.ok().build();
+    }
            """,
            "commit_sha": "test_breaking_change_003",
            "commit_message": "BREAKING: Changed endpoint path from /{id}/price to /{id}/current-price",
            "github_repo_url": "https://github.com/Sabarivasan-Velayutham/backend-api-service"
        },
        4: {
            "name": "Non-Breaking: Add Optional Parameter",
            "file_path": "backend-api-service/src/main/java/com/backendapi/StockController.java",
            "repository": "backend-api-service",
            "diff": """
-    @GetMapping("/{id}")
-    public ResponseEntity<?> getStockById(@PathVariable String id) {
-        // Returns stock details by ID
-        return ResponseEntity.ok().build();
-    }
+    @GetMapping("/{id}")
+    public ResponseEntity<?> getStockById(@PathVariable String id, @RequestParam(required = false) String format) {
+        // Returns stock details by ID
+        // format is optional: 'json' or 'xml'
+        return ResponseEntity.ok().build();
+    }
            """,
            "commit_sha": "test_non_breaking_001",
            "commit_message": "FEATURE: Added optional format parameter to getStockById endpoint",
            "github_repo_url": "https://github.com/Sabarivasan-Velayutham/backend-api-service"
        },
        5: {
            "name": "Breaking Change: Change Response Type",
            "file_path": "backend-api-service/src/main/java/com/backendapi/StockController.java",
            "repository": "backend-api-service",
            "diff": """
-    @GetMapping
-    public ResponseEntity<?> getAllStocks() {
-        // Returns list of all stocks
-        return ResponseEntity.ok().build();
-    }
+    @GetMapping
+    public ResponseEntity<StockListResponse> getAllStocks() {
+        // Returns paginated list of all stocks with metadata
+        return ResponseEntity.ok().build();
+    }
            """,
            "commit_sha": "test_breaking_change_004",
            "commit_message": "BREAKING: Changed response type from generic to StockListResponse",
            "github_repo_url": "https://github.com/Sabarivasan-Velayutham/backend-api-service"
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
    parser.add_argument('--scenario', type=int, default=1, choices=[1, 2, 3, 4, 5],
                        help='Test scenario (1-5). Default: 1')
    parser.add_argument('--all', action='store_true',
                        help='Run all test scenarios')
    
    args = parser.parse_args()
    
    if args.all:
        print("=" * 60)
        print("Running All Test Scenarios")
        print("=" * 60)
        all_success = True
        for i in range(1, 6):
            print(f"\n{'='*60}")
            print(f"SCENARIO {i}/5")
            print(f"{'='*60}")
            success = test_api_contract_change(i)
            if not success:
                all_success = False
            print("\n" + "-" * 60)
        sys.exit(0 if all_success else 1)
    else:
        success = test_api_contract_change(args.scenario)
        sys.exit(0 if success else 1)

