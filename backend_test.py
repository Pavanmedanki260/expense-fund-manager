#!/usr/bin/env python3
"""
FundTrack Backend API Testing Suite
Tests all endpoints with different user roles and validates responses
"""

import requests
import json
import sys
from datetime import datetime, timezone
from typing import Dict, List, Optional

class FundTrackAPITester:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []
        
        # Test credentials from /app/memory/test_credentials.md
        self.tokens = {
            'admin': 'test_session_admin_001',
            'contributor': 'test_session_contrib_001', 
            'viewer': 'test_session_viewer_001'
        }
        
        self.users = {
            'admin': 'user_testadmin001',
            'contributor': 'user_testcontrib01',
            'viewer': 'user_testviewer001'
        }

    def log_test(self, name: str, success: bool, details: str = ""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name}")
        else:
            print(f"❌ {name} - {details}")
            self.failed_tests.append(f"{name}: {details}")

    def make_request(self, method: str, endpoint: str, token: str = None, data: dict = None, expected_status: int = 200) -> tuple:
        """Make HTTP request with optional auth"""
        url = f"{self.base_url}{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        if token:
            headers['Authorization'] = f'Bearer {token}'
            
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, headers=headers, json=data, timeout=10)
            elif method == 'PUT':
                response = requests.put(url, headers=headers, json=data, timeout=10)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=10)
            else:
                return False, f"Unsupported method: {method}", {}
                
            success = response.status_code == expected_status
            response_data = {}
            
            try:
                response_data = response.json()
            except:
                response_data = {"raw_response": response.text}
                
            return success, f"Status: {response.status_code}", response_data
            
        except Exception as e:
            return False, f"Request failed: {str(e)}", {}

    def test_health_endpoint(self):
        """Test /api/health endpoint"""
        success, details, data = self.make_request('GET', '/api/health')
        self.log_test("Health Check", success and 'status' in data, details)
        return success

    def test_auth_endpoints(self):
        """Test authentication endpoints"""
        print("\n🔐 Testing Authentication Endpoints...")
        
        # Test /api/auth/me with valid token
        success, details, data = self.make_request('GET', '/api/auth/me', self.tokens['admin'])
        self.log_test("Auth /api/auth/me with admin token", success and 'user_id' in data, details)
        
        # Test /api/auth/me with contributor token
        success, details, data = self.make_request('GET', '/api/auth/me', self.tokens['contributor'])
        self.log_test("Auth /api/auth/me with contributor token", success and 'user_id' in data, details)
        
        # Test /api/auth/me with viewer token
        success, details, data = self.make_request('GET', '/api/auth/me', self.tokens['viewer'])
        self.log_test("Auth /api/auth/me with viewer token", success and 'user_id' in data, details)
        
        # Test /api/auth/me without token (should return 401)
        success, details, data = self.make_request('GET', '/api/auth/me', expected_status=401)
        self.log_test("Auth /api/auth/me without token returns 401", success, details)

    def test_fund_endpoints(self):
        """Test fund CRUD operations"""
        print("\n💰 Testing Fund Endpoints...")
        
        # Test GET /api/funds with auth
        success, details, data = self.make_request('GET', '/api/funds', self.tokens['admin'])
        self.log_test("GET /api/funds with auth", success and isinstance(data, list), details)
        
        # Test POST /api/funds (admin)
        fund_data = {
            "source_name": "Test Fund Admin",
            "amount_inr": 50000.0,
            "category": "Donation",
            "date_received": "2025-01-15",
            "notes": "Test fund created by admin"
        }
        success, details, response_data = self.make_request('POST', '/api/funds', self.tokens['admin'], fund_data, 200)
        admin_fund_id = response_data.get('fund_id') if success else None
        self.log_test("POST /api/funds (admin)", success and admin_fund_id, details)
        
        # Test POST /api/funds (contributor)
        fund_data_contrib = {
            "source_name": "Test Fund Contributor", 
            "amount_inr": 25000.0,
            "category": "Grant",
            "date_received": "2025-01-15",
            "notes": "Test fund created by contributor"
        }
        success, details, response_data = self.make_request('POST', '/api/funds', self.tokens['contributor'], fund_data_contrib, 200)
        contrib_fund_id = response_data.get('fund_id') if success else None
        self.log_test("POST /api/funds (contributor)", success and contrib_fund_id, details)
        
        # Test POST /api/funds (viewer - should fail with 403)
        success, details, data = self.make_request('POST', '/api/funds', self.tokens['viewer'], fund_data, 403)
        self.log_test("POST /api/funds (viewer) returns 403", success, details)
        
        # Test PUT /api/funds/{fund_id} (admin updating own fund)
        if admin_fund_id:
            update_data = {**fund_data, "amount_inr": 60000.0, "notes": "Updated by admin"}
            success, details, data = self.make_request('PUT', f'/api/funds/{admin_fund_id}', self.tokens['admin'], update_data)
            self.log_test("PUT /api/funds/{fund_id} (admin)", success, details)
        
        # Test DELETE /api/funds/{fund_id} (admin)
        if admin_fund_id:
            success, details, data = self.make_request('DELETE', f'/api/funds/{admin_fund_id}', self.tokens['admin'])
            self.log_test("DELETE /api/funds/{fund_id} (admin)", success, details)
            
        # Test DELETE /api/funds/{fund_id} (contributor deleting own fund)
        if contrib_fund_id:
            success, details, data = self.make_request('DELETE', f'/api/funds/{contrib_fund_id}', self.tokens['contributor'])
            self.log_test("DELETE /api/funds/{fund_id} (contributor own fund)", success, details)

    def test_utilization_endpoints(self):
        """Test utilization CRUD operations"""
        print("\n📊 Testing Utilization Endpoints...")
        
        # First create a fund to link utilizations to
        fund_data = {
            "source_name": "Test Fund for Utilization",
            "amount_inr": 100000.0,
            "category": "Donation", 
            "date_received": "2025-01-15",
            "notes": "Fund for testing utilizations"
        }
        success, details, response_data = self.make_request('POST', '/api/funds', self.tokens['admin'], fund_data, 200)
        test_fund_id = response_data.get('fund_id') if success else None
        
        if not test_fund_id:
            self.log_test("Create test fund for utilizations", False, "Failed to create test fund")
            return
            
        # Test GET /api/utilizations
        success, details, data = self.make_request('GET', '/api/utilizations', self.tokens['admin'])
        self.log_test("GET /api/utilizations", success and isinstance(data, list), details)
        
        # Test POST /api/utilizations (admin)
        util_data = {
            "purpose": "Test Utilization Admin",
            "amount_inr": 15000.0,
            "date_spent": "2025-01-16",
            "linked_fund_id": test_fund_id,
            "notes": "Test utilization by admin"
        }
        success, details, response_data = self.make_request('POST', '/api/utilizations', self.tokens['admin'], util_data, 200)
        admin_util_id = response_data.get('util_id') if success else None
        self.log_test("POST /api/utilizations (admin)", success and admin_util_id, details)
        
        # Test POST /api/utilizations (contributor)
        util_data_contrib = {
            "purpose": "Test Utilization Contributor",
            "amount_inr": 10000.0,
            "date_spent": "2025-01-16", 
            "linked_fund_id": test_fund_id,
            "notes": "Test utilization by contributor"
        }
        success, details, response_data = self.make_request('POST', '/api/utilizations', self.tokens['contributor'], util_data_contrib, 200)
        contrib_util_id = response_data.get('util_id') if success else None
        self.log_test("POST /api/utilizations (contributor)", success and contrib_util_id, details)
        
        # Test POST /api/utilizations (viewer - should fail)
        success, details, data = self.make_request('POST', '/api/utilizations', self.tokens['viewer'], util_data, 403)
        self.log_test("POST /api/utilizations (viewer) returns 403", success, details)
        
        # Test PUT /api/utilizations/{util_id}
        if admin_util_id:
            update_data = {**util_data, "amount_inr": 20000.0, "notes": "Updated by admin"}
            success, details, data = self.make_request('PUT', f'/api/utilizations/{admin_util_id}', self.tokens['admin'], update_data)
            self.log_test("PUT /api/utilizations/{util_id} (admin)", success, details)
        
        # Test DELETE /api/utilizations/{util_id}
        if admin_util_id:
            success, details, data = self.make_request('DELETE', f'/api/utilizations/{admin_util_id}', self.tokens['admin'])
            self.log_test("DELETE /api/utilizations/{util_id} (admin)", success, details)
            
        if contrib_util_id:
            success, details, data = self.make_request('DELETE', f'/api/utilizations/{contrib_util_id}', self.tokens['contributor'])
            self.log_test("DELETE /api/utilizations/{util_id} (contributor own)", success, details)
        
        # Clean up test fund
        success, details, data = self.make_request('DELETE', f'/api/funds/{test_fund_id}', self.tokens['admin'])

    def test_dashboard_endpoint(self):
        """Test dashboard data endpoint"""
        print("\n📈 Testing Dashboard Endpoint...")
        
        success, details, data = self.make_request('GET', '/api/dashboard', self.tokens['admin'])
        required_fields = ['total_collected', 'total_utilized', 'balance', 'pct_utilized', 'category_breakdown', 'monthly_data', 'recent_activity']
        has_all_fields = all(field in data for field in required_fields) if success else False
        self.log_test("GET /api/dashboard returns summary data", success and has_all_fields, details)

    def test_user_management_endpoints(self):
        """Test user management endpoints (admin only)"""
        print("\n👥 Testing User Management Endpoints...")
        
        # Test GET /api/users (admin)
        success, details, data = self.make_request('GET', '/api/users', self.tokens['admin'])
        self.log_test("GET /api/users (admin)", success and isinstance(data, list), details)
        
        # Test GET /api/users (contributor - should fail)
        success, details, data = self.make_request('GET', '/api/users', self.tokens['contributor'], expected_status=403)
        self.log_test("GET /api/users (contributor) returns 403", success, details)
        
        # Test GET /api/users (viewer - should fail)
        success, details, data = self.make_request('GET', '/api/users', self.tokens['viewer'], expected_status=403)
        self.log_test("GET /api/users (viewer) returns 403", success, details)
        
        # Test PUT /api/users/{user_id}/role (admin changing contributor role)
        role_data = {"role": "viewer"}
        success, details, data = self.make_request('PUT', f'/api/users/{self.users["contributor"]}/role', self.tokens['admin'], role_data)
        self.log_test("PUT /api/users/{user_id}/role (admin)", success, details)
        
        # Revert role change
        role_data = {"role": "contributor"}
        self.make_request('PUT', f'/api/users/{self.users["contributor"]}/role', self.tokens['admin'], role_data)
        
        # Test PUT /api/users/{user_id}/status (admin)
        status_data = {"is_active": False}
        success, details, data = self.make_request('PUT', f'/api/users/{self.users["viewer"]}/status', self.tokens['admin'], status_data)
        self.log_test("PUT /api/users/{user_id}/status (admin)", success, details)
        
        # Revert status change
        status_data = {"is_active": True}
        self.make_request('PUT', f'/api/users/{self.users["viewer"]}/status', self.tokens['admin'], status_data)

    def test_export_endpoint(self):
        """Test Excel export endpoint"""
        print("\n📄 Testing Export Endpoint...")
        
        try:
            url = f"{self.base_url}/api/export/excel"
            headers = {'Authorization': f'Bearer {self.tokens["admin"]}'}
            response = requests.get(url, headers=headers, timeout=15)
            
            success = response.status_code == 200
            is_excel = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' in response.headers.get('content-type', '')
            has_filename = 'attachment' in response.headers.get('content-disposition', '')
            
            self.log_test("GET /api/export/excel returns .xlsx file", success and is_excel and has_filename, 
                         f"Status: {response.status_code}, Content-Type: {response.headers.get('content-type', 'N/A')}")
                         
        except Exception as e:
            self.log_test("GET /api/export/excel returns .xlsx file", False, f"Request failed: {str(e)}")

    def test_role_based_access_control(self):
        """Test role-based access control"""
        print("\n🔒 Testing Role-Based Access Control...")
        
        # Viewer cannot create funds
        fund_data = {"source_name": "Viewer Test", "amount_inr": 1000, "category": "Donation", "date_received": "2025-01-15"}
        success, details, data = self.make_request('POST', '/api/funds', self.tokens['viewer'], fund_data, 403)
        self.log_test("Viewer cannot create funds (403)", success, details)
        
        # Viewer cannot create utilizations  
        util_data = {"purpose": "Viewer Test", "amount_inr": 500, "date_spent": "2025-01-15", "linked_fund_id": "fund_seed001"}
        success, details, data = self.make_request('POST', '/api/utilizations', self.tokens['viewer'], util_data, 403)
        self.log_test("Viewer cannot create utilizations (403)", success, details)
        
        # Contributor cannot access user management
        success, details, data = self.make_request('GET', '/api/users', self.tokens['contributor'], expected_status=403)
        self.log_test("Contributor cannot access user management (403)", success, details)

    def run_all_tests(self):
        """Run all test suites"""
        print("🚀 Starting FundTrack Backend API Tests...")
        print(f"Backend URL: {self.base_url}")
        print(f"Test Time: {datetime.now(timezone.utc).isoformat()}")
        
        # Test basic connectivity
        if not self.test_health_endpoint():
            print("❌ Health check failed - stopping tests")
            return False
            
        # Run all test suites
        self.test_auth_endpoints()
        self.test_fund_endpoints()
        self.test_utilization_endpoints()
        self.test_dashboard_endpoint()
        self.test_user_management_endpoints()
        self.test_export_endpoint()
        self.test_role_based_access_control()
        
        # Print summary
        print(f"\n📊 Test Summary:")
        print(f"Tests Run: {self.tests_run}")
        print(f"Tests Passed: {self.tests_passed}")
        print(f"Tests Failed: {self.tests_run - self.tests_passed}")
        print(f"Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%")
        
        if self.failed_tests:
            print(f"\n❌ Failed Tests:")
            for failure in self.failed_tests:
                print(f"  - {failure}")
        
        return self.tests_passed == self.tests_run

def main():
    # Use the backend URL from environment
    backend_url = "https://b844d7d4-15d5-4ca4-8fbd-5ff90237ce2f.preview.emergentagent.com"
    
    tester = FundTrackAPITester(backend_url)
    success = tester.run_all_tests()
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())