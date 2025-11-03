#!/usr/bin/env python3
"""
Integration test suite for CodeFlow Catalyst
Tests end-to-end flow
"""

import asyncio
import httpx
import time
from typing import Dict, List

class IntegrationTester:
    def __init__(self):
        self.backend_url = "http://localhost:8000"
        self.frontend_url = "http://localhost:3000"
        self.results = []
        self.passed = 0
        self.failed = 0
    
    async def test_full_analysis_flow(self):
        """Test complete analysis flow"""
        print("\n" + "="*60)
        print("🧪 TEST: Full Analysis Flow")
        print("="*60)
        
        test_payload = {
            "file_path": "sample-repo/banking-app/src/payment/PaymentProcessor.java",
            "repository": "banking-app-test",
            "diff": "- return amount * 0.03;\n+ return amount * 0.025 + 15.0;"
        }
        
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                # Step 1: Trigger analysis
                print("\n📤 Step 1: Triggering analysis...")
                response = await client.post(
                    f"{self.backend_url}/api/v1/analyze",
                    json=test_payload
                )
                
                if response.status_code != 200:
                    self.log_failure("Analysis trigger failed", response.status_code)
                    return False
                
                result = response.json()
                analysis_id = result.get("id")
                print(f"✅ Analysis triggered: {analysis_id}")
                
                # Step 2: Verify risk score
                print("\n📊 Step 2: Verifying risk score...")
                risk_score = result.get("risk_score", {})
                
                if not risk_score:
                    self.log_failure("No risk score in response")
                    return False
                
                print(f"✅ Risk Score: {risk_score['score']}/10 - {risk_score['level']}")
                
                # Step 3: Verify dependencies
                print("\n🔗 Step 3: Verifying dependencies...")
                dependencies = result.get("dependencies", {})
                dep_count = dependencies.get("count", {})
                
                print(f"✅ Dependencies found:")
                print(f"   - Direct: {dep_count.get('direct', 0)}")
                print(f"   - Indirect: {dep_count.get('indirect', 0)}")
                
                # Step 4: Verify AI insights
                print("\n🤖 Step 4: Verifying AI insights...")
                ai_insights = result.get("ai_insights", {})
                
                if not ai_insights.get("summary"):
                    self.log_failure("No AI summary generated")
                    return False
                
                print(f"✅ AI Summary: {ai_insights['summary'][:80]}...")
                
                # Step 5: Verify result is in list
                print("\n📋 Step 5: Verifying result in analyses list...")
                list_response = await client.get(
                    f"{self.backend_url}/api/v1/analyses"
                )
                
                analyses = list_response.json()
                found = any(a.get("id") == analysis_id for a in analyses)
                
                if not found:
                    self.log_failure("Analysis not found in list")
                    return False
                
                print(f"✅ Analysis found in list ({len(analyses)} total)")
                
                self.log_success("Full Analysis Flow")
                return True
                
        except Exception as e:
            self.log_failure("Full Analysis Flow", str(e))
            return False
    
    async def test_dependency_graph(self):
        """Test dependency graph endpoint"""
        print("\n" + "="*60)
        print("🧪 TEST: Dependency Graph")
        print("="*60)
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.backend_url}/api/v1/graph/PaymentProcessor.java"
                )
                
                if response.status_code != 200:
                    self.log_failure("Graph endpoint failed", response.status_code)
                    return False
                
                graph_data = response.json()
                nodes = graph_data.get("nodes", [])
                links = graph_data.get("links", [])
                
                print(f"✅ Graph generated:")
                print(f"   - Nodes: {len(nodes)}")
                print(f"   - Links: {len(links)}")
                
                if len(nodes) == 0:
                    self.log_failure("Graph has no nodes")
                    return False
                
                self.log_success("Dependency Graph")
                return True
                
        except Exception as e:
            self.log_failure("Dependency Graph", str(e))
            return False
    
    async def test_webhook_simulation(self):
        """Test webhook handling"""
        print("\n" + "="*60)
        print("🧪 TEST: Webhook Simulation")
        print("="*60)
        
        webhook_payload = {
            "event": "push",
            "repository": "test-repo",
            "commit_sha": "test123abc",
            "author": "test@example.com",
            "branch": "main",
            "files_changed": [
                {
                    "path": "sample-repo/banking-app/src/payment/PaymentProcessor.java",
                    "status": "modified",
                    "additions": 5,
                    "deletions": 2
                }
            ],
            "diff": "- old line\n+ new line"
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.backend_url}/api/v1/webhook/github",
                    json=webhook_payload
                )
                
                if response.status_code != 202:
                    self.log_failure("Webhook not accepted", response.status_code)
                    return False
                
                result = response.json()
                print(f"✅ Webhook accepted: {result.get('message')}")
                
                # Wait for background processing
                print("⏳ Waiting for background analysis (10s)...")
                await asyncio.sleep(10)
                
                # Check if analysis was created
                list_response = await client.get(
                    f"{self.backend_url}/api/v1/analyses"
                )
                analyses = list_response.json()
                
                if len(analyses) == 0:
                    self.log_failure("No analysis created from webhook")
                    return False
                
                print(f"✅ Analysis created from webhook")
                
                self.log_success("Webhook Simulation")
                return True
                
        except Exception as e:
            self.log_failure("Webhook Simulation", str(e))
            return False
    
    async def test_performance(self):
        """Test analysis performance"""
        print("\n" + "="*60)
        print("🧪 TEST: Performance")
        print("="*60)
        
        test_payload = {
            "file_path": "sample-repo/banking-app/src/fraud/FraudDetection.java",
            "repository": "perf-test",
            "diff": "test diff"
        }
        
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                start_time = time.time()
                response = await client.post(
                    f"{self.backend_url}/api/v1/analyze",
                    json=test_payload
                )
            
                duration = time.time() - start_time
                
                if response.status_code != 200:
                    self.log_failure("Performance test failed", response.status_code)
                    return False
                
                print(f"✅ Analysis completed in {duration:.2f}s")
            
                # Check if within acceptable time (< 60 seconds)
                if duration > 60:
                    print(f"⚠️  Warning: Analysis took longer than expected")
                else:
                    print(f"✅ Performance acceptable")
                
                self.log_success("Performance Test")
                return True
            
        except Exception as e:
            self.log_failure("Performance Test", str(e))
            return False

    async def test_frontend_accessibility(self):
        """Test frontend is accessible"""
        print("\n" + "="*60)
        print("🧪 TEST: Frontend Accessibility")
        print("="*60)
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(self.frontend_url)
                
                if response.status_code != 200:
                    self.log_failure("Frontend not accessible", response.status_code)
                    return False
                
                # Check if React app is present
                if "CodeFlow Catalyst" in response.text or "root" in response.text:
                    print("✅ Frontend accessible and serving React app")
                    self.log_success("Frontend Accessibility")
                    return True
                else:
                    self.log_failure("Frontend accessible but content unexpected")
                    return False
                
        except Exception as e:
            self.log_failure("Frontend Accessibility", str(e))
            return False

    async def test_error_handling(self):
        """Test error handling"""
        print("\n" + "="*60)
        print("🧪 TEST: Error Handling")
        print("="*60)
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Test 1: Invalid file path
                print("\n📝 Test 1: Invalid file path...")
                response = await client.post(
                    f"{self.backend_url}/api/v1/analyze",
                    json={
                        "file_path": "nonexistent/file.java",
                        "repository": "test",
                        "diff": "test"
                    }
                )
                
                # Should return error or handle gracefully
                print(f"   Response: {response.status_code}")
                
                # Test 2: Non-existent analysis ID
                print("\n📝 Test 2: Non-existent analysis ID...")
                response = await client.get(
                    f"{self.backend_url}/api/v1/analysis/nonexistent-id"
                )
                
                if response.status_code != 404:
                    self.log_failure("Should return 404 for non-existent ID")
                    return False
                
                print(f"   ✅ Correctly returned 404")
                
                self.log_success("Error Handling")
                return True
                
        except Exception as e:
            self.log_failure("Error Handling", str(e))
            return False

    def log_success(self, test_name: str):
        """Log successful test"""
        self.passed += 1
        self.results.append({
            "test": test_name,
            "status": "PASSED",
            "message": "Success"
        })

    def log_failure(self, test_name: str, message: str = ""):
        """Log failed test"""
        self.failed += 1
        self.results.append({
            "test": test_name,
            "status": "FAILED",
            "message": message
        })
        print(f"❌ FAILED: {message}")

    # --- FIX: Indented this function ---
    async def run_all_tests(self):
        """Run all integration tests"""
        print("\n" + "="*70)
        print("🚀 CODEFLOW CATALYST - INTEGRATION TEST SUITE")
        print("="*70)
        
        tests = [
            self.test_frontend_accessibility(),
            self.test_full_analysis_flow(),
            self.test_dependency_graph(),
            self.test_webhook_simulation(),
            self.test_performance(),
            self.test_error_handling()
        ]
        
        # Run all tests
        results = await asyncio.gather(*tests, return_exceptions=True)
        
        # Print summary
        print("\n" + "="*70)
        print("📊 TEST RESULTS SUMMARY")
        print("="*70)
        
        for result in self.results:
            status_icon = "✅" if result["status"] == "PASSED" else "❌"
            print(f"{status_icon} {result['test']}: {result['status']}")
            if result["message"] and result["status"] == "FAILED":
                print(f"   Error: {result['message']}")
        
        print("\n" + "-"*70)
        print(f"Total Tests: {self.passed + self.failed}")
        print(f"✅ Passed: {self.passed}")
        print(f"❌ Failed: {self.failed}")
        if (self.passed + self.failed) > 0:
            print(f"Success Rate: {(self.passed / (self.passed + self.failed) * 100):.1f}%")
        else:
            print("Success Rate: 0.0%")
        print("="*70)
        
        return self.failed == 0

# --- This function stays outside the class ---
async def main():
    tester = IntegrationTester()
    success = await tester.run_all_tests()
    if success:
        print("\n🎉 All tests passed! System ready for demo.")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please fix before demo.")
        return 1

if __name__ == "__main__":
    import sys 
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
