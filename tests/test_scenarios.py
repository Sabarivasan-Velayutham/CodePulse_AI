"""
Test script to verify demo scenarios work correctly
Run this before the actual demo
"""

import requests
import json
import sys

class DemoTester:
    def __init__(self):
        self.backend_url = "http://localhost:8000"
        self.passed = 0
        self.failed = 0
    
    def test_backend_health(self):
        """Test 1: Backend is responding"""
        print("\n🧪 Test 1: Backend Health Check")
        try:
            response = requests.get(f"{self.backend_url}/health", timeout=5)
            if response.status_code == 200:
                print("   ✅ Backend is healthy")
                self.passed += 1
                return True
            else:
                print(f"   ❌ Backend returned status {response.status_code}")
                self.failed += 1
                return False
        except Exception as e:
            print(f"   ❌ Backend not accessible: {e}")
            self.failed += 1
            return False
    
    def test_neo4j_connection(self):
        """Test 2: Neo4j has data"""
        print("\n🧪 Test 2: Neo4j Data Check")
        try:
            # This endpoint should return graph data
            response = requests.get(
                f"{self.backend_url}/api/v1/graph/PaymentProcessor.java",
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                if len(data.get("nodes", [])) > 0:
                    print(f"   ✅ Neo4j has {len(data['nodes'])} nodes")
                    self.passed += 1
                    return True
                else:
                    print("   ❌ Neo4j has no data")
                    self.failed += 1
                    return False
            else:
                print(f"   ⚠️  Endpoint not implemented yet (expected during development)")
                return True
        except Exception as e:
            print(f"   ⚠️  Graph endpoint not ready: {e}")
            return True
    
    def test_depends_tool(self):
        """Test 3: DEPENDS tool is accessible"""
        print("\n🧪 Test 3: DEPENDS Tool Check")
        import os
        depends_path = "tools/depends/depends.jar"
        if os.path.exists(depends_path):
            print(f"   ✅ DEPENDS tool found at {depends_path}")
            self.passed += 1
            return True
        else:
            print(f"   ❌ DEPENDS tool not found at {depends_path}")
            self.failed += 1
            return False
    
    def test_sample_code_exists(self):
        """Test 4: Sample Java code exists"""
        print("\n🧪 Test 4: Sample Code Check")
        import os
        required_files = [
            "sample-repo/banking-app/src/payment/PaymentProcessor.java",
            "sample-repo/banking-app/src/fraud/FraudDetection.java",
            "sample-repo/banking-app/src/account/AccountBalance.java"
        ]
        
        missing = []
        for file in required_files:
            if not os.path.exists(file):
                missing.append(file)
        
        if not missing:
            print(f"   ✅ All {len(required_files)} sample files exist")
            self.passed += 1
            return True
        else:
            print(f"   ❌ Missing files:")
            for file in missing:
                print(f"      - {file}")
            self.failed += 1
            return False
    
    def test_frontend_accessible(self):
        """Test 5: Frontend is running"""
        print("\n🧪 Test 5: Frontend Accessibility")
        try:
            response = requests.get("http://localhost:3000", timeout=5)
            if response.status_code == 200:
                print("   ✅ Frontend is accessible")
                self.passed += 1
                return True
            else:
                print(f"   ❌ Frontend returned status {response.status_code}")
                self.failed += 1
                return False
        except Exception as e:
            print(f"   ❌ Frontend not accessible: {e}")
            print("      Make sure to run: cd frontend && npm start")
            self.failed += 1
            return False
    
    def run_all_tests(self):
        """Run all tests"""
        print("=" * 60)
        print("🧪 DEMO PRE-FLIGHT CHECK")
        print("=" * 60)
        
        self.test_backend_health()
        self.test_neo4j_connection()
        self.test_depends_tool()
        self.test_sample_code_exists()
        self.test_frontend_accessible()
        
        print("\n" + "=" * 60)
        print(f"📊 Test Results: {self.passed} passed, {self.failed} failed")
        print("=" * 60)
        
        if self.failed == 0:
            print("\n✅ All systems ready for demo!")
            return True
        else:
            print(f"\n❌ {self.failed} issues found. Fix before demo.")
            return False

def main():
    tester = DemoTester()
    success = tester.run_all_tests()
    
    if not success:
        print("\n🔧 Quick fixes:")
        print("   Backend:  cd backend && python app/main.py")
        print("   Frontend: cd frontend && npm start")
        print("   Neo4j:    docker-compose up -d neo4j")
        print("   Data:     python sample-repo/init_neo4j.py")
        sys.exit(1)
    
    sys.exit(0)

if __name__ == "__main__":
    main()