#!/usr/bin/env python3
"""
FundTrack Backend API Testing Suite - Multi-Group Architecture
Tests all group-scoped endpoints with different user roles and validates responses
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
        
        # Test groups from credentials
        self.groups = {
            'education': 'grp_education01',  # All users are members
            'csr': 'grp_csrfund0001'        # Viewer is NOT a member
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
        
        # Test /api/auth/me with admin token (should be super admin)
        success, details, data = self.make_request('GET', '/api/auth/me', self.tokens['admin'])
        is_super_admin = data.get('is_super_admin', False) if success else False
        self.log_test("GET /api/auth/me with admin token returns super admin user", 
                     success and 'user_id' in data and is_super_admin, details)
        
        # Test /api/auth/me with contributor token
        success, details, data = self.make_request('GET', '/api/auth/me', self.tokens['contributor'])
        self.log_test("GET /api/auth/me with contributor token", success and 'user_id' in data, details)
        
        # Test /api/auth/me with viewer token
        success, details, data = self.make_request('GET', '/api/auth/me', self.tokens['viewer'])
        self.log_test("GET /api/auth/me with viewer token", success and 'user_id' in data, details)
        
        # Test /api/auth/me without token (should return 401)
        success, details, data = self.make_request('GET', '/api/auth/me', expected_status=401)
        self.log_test("GET /api/auth/me without token returns 401", success, details)

    def test_group_endpoints(self):
        """Test group management endpoints"""
        print("\n🏢 Testing Group Endpoints...")
        
        # Test GET /api/groups (super admin sees all)
        success, details, data = self.make_request('GET', '/api/groups', self.tokens['admin'])
        self.log_test("GET /api/groups lists groups (super admin sees all)", 
                     success and isinstance(data, list) and len(data) >= 2, details)
        
        # Test GET /api/groups with contributor token (sees only their groups)
        success, details, data = self.make_request('GET', '/api/groups', self.tokens['contributor'])
        self.log_test("GET /api/groups with contributor token sees only their groups", 
                     success and isinstance(data, list), details)
        
        # Test POST /api/groups creates new group
        group_data = {
            "name": "Test Group API",
            "description": "Created via API test"
        }
        success, details, response_data = self.make_request('POST', '/api/groups', self.tokens['admin'], group_data, 200)
        test_group_id = response_data.get('group_id') if success else None
        self.log_test("POST /api/groups creates new group", success and test_group_id, details)
        
        # Test GET /api/groups/{groupId} returns group with user_role
        success, details, data = self.make_request('GET', f'/api/groups/{self.groups["education"]}', self.tokens['admin'])
        has_user_role = 'user_role' in data if success else False
        self.log_test("GET /api/groups/{groupId} returns group with user_role", 
                     success and has_user_role, details)
        
        # Clean up test group
        if test_group_id:
            self.make_request('DELETE', f'/api/groups/{test_group_id}', self.tokens['admin'])

    def test_fund_endpoints(self):
        """Test group-scoped fund CRUD operations"""
        print("\n💰 Testing Group-Scoped Fund Endpoints...")
        
        # Test GET /api/groups/grp_education01/funds returns funds
        success, details, data = self.make_request('GET', f'/api/groups/{self.groups["education"]}/funds', self.tokens['admin'])
        self.log_test("GET /api/groups/grp_education01/funds returns funds", 
                     success and isinstance(data, list), details)
        
        # Test POST /api/groups/grp_education01/funds creates fund (admin)
        fund_data = {
            "source_name": "Test Fund Admin",
            "amount_inr": 50000.0,
            "category": "Donation",
            "date_received": "2025-01-15",
            "notes": "Test fund created by admin"
        }
        success, details, response_data = self.make_request('POST', f'/api/groups/{self.groups["education"]}/funds', 
                                                          self.tokens['admin'], fund_data, 200)
        admin_fund_id = response_data.get('fund_id') if success else None
        self.log_test("POST /api/groups/grp_education01/funds creates fund (admin)", success and admin_fund_id, details)
        
        # Test POST /api/groups/grp_education01/funds creates fund (contributor)
        fund_data_contrib = {
            "source_name": "Test Fund Contributor", 
            "amount_inr": 25000.0,
            "category": "Grant",
            "date_received": "2025-01-15",
            "notes": "Test fund created by contributor"
        }
        success, details, response_data = self.make_request('POST', f'/api/groups/{self.groups["education"]}/funds', 
                                                          self.tokens['contributor'], fund_data_contrib, 200)
        contrib_fund_id = response_data.get('fund_id') if success else None
        self.log_test("POST /api/groups/grp_education01/funds creates fund (contributor)", success and contrib_fund_id, details)
        
        # Test POST /api/groups/grp_education01/funds denied for viewer (403)
        success, details, data = self.make_request('POST', f'/api/groups/{self.groups["education"]}/funds', 
                                                  self.tokens['viewer'], fund_data, 403)
        self.log_test("POST /api/groups/grp_education01/funds denied for viewer (403)", success, details)
        
        # Test GET /api/groups/grp_csrfund0001/funds with viewer token returns 403 (not a member)
        success, details, data = self.make_request('GET', f'/api/groups/{self.groups["csr"]}/funds', 
                                                  self.tokens['viewer'], expected_status=403)
        self.log_test("GET /api/groups/grp_csrfund0001/funds with viewer token returns 403 (not a member)", success, details)
        
        # Clean up test funds
        if admin_fund_id:
            self.make_request('DELETE', f'/api/groups/{self.groups["education"]}/funds/{admin_fund_id}', self.tokens['admin'])
        if contrib_fund_id:
            self.make_request('DELETE', f'/api/groups/{self.groups["education"]}/funds/{contrib_fund_id}', self.tokens['contributor'])

    def test_utilization_endpoints(self):
        """Test group-scoped utilization CRUD operations"""
        print("\n📊 Testing Group-Scoped Utilization Endpoints...")
        
        # First create a fund to link utilizations to
        fund_data = {
            "source_name": "Test Fund for Utilization",
            "amount_inr": 100000.0,
            "category": "Donation", 
            "date_received": "2025-01-15",
            "notes": "Fund for testing utilizations"
        }
        success, details, response_data = self.make_request('POST', f'/api/groups/{self.groups["education"]}/funds', 
                                                          self.tokens['admin'], fund_data, 200)
        test_fund_id = response_data.get('fund_id') if success else None
        
        if not test_fund_id:
            self.log_test("Create test fund for utilizations", False, "Failed to create test fund")
            return
            
        # Test GET /api/groups/grp_education01/utilizations returns utilizations
        success, details, data = self.make_request('GET', f'/api/groups/{self.groups["education"]}/utilizations', self.tokens['admin'])
        self.log_test("GET /api/groups/grp_education01/utilizations returns utilizations", 
                     success and isinstance(data, list), details)
        
        # Test POST /api/groups/grp_education01/utilizations creates utilization
        util_data = {
            "purpose": "Test Utilization Admin",
            "amount_inr": 15000.0,
            "date_spent": "2025-01-16",
            "linked_fund_id": test_fund_id,
            "notes": "Test utilization by admin"
        }
        success, details, response_data = self.make_request('POST', f'/api/groups/{self.groups["education"]}/utilizations', 
                                                          self.tokens['admin'], util_data, 200)
        admin_util_id = response_data.get('util_id') if success else None
        self.log_test("POST /api/groups/grp_education01/utilizations creates utilization", success and admin_util_id, details)
        
        # Clean up
        if admin_util_id:
            self.make_request('DELETE', f'/api/groups/{self.groups["education"]}/utilizations/{admin_util_id}', self.tokens['admin'])
        self.make_request('DELETE', f'/api/groups/{self.groups["education"]}/funds/{test_fund_id}', self.tokens['admin'])

    def test_dashboard_endpoint(self):
        """Test group-scoped dashboard data endpoint"""
        print("\n📈 Testing Group-Scoped Dashboard Endpoint...")
        
        # Test GET /api/groups/grp_education01/dashboard returns dashboard data
        success, details, data = self.make_request('GET', f'/api/groups/{self.groups["education"]}/dashboard', self.tokens['admin'])
        required_fields = ['total_collected', 'total_utilized', 'balance', 'pct_utilized', 'category_breakdown', 'monthly_data', 'recent_activity']
        has_all_fields = all(field in data for field in required_fields) if success else False
        self.log_test("GET /api/groups/grp_education01/dashboard returns dashboard data", success and has_all_fields, details)

    def test_member_endpoints(self):
        """Test group member management endpoints"""
        print("\n👥 Testing Group Member Management Endpoints...")
        
        # Test GET /api/groups/grp_education01/members lists 3 members
        success, details, data = self.make_request('GET', f'/api/groups/{self.groups["education"]}/members', self.tokens['admin'])
        member_count = len(data) if success and isinstance(data, list) else 0
        self.log_test("GET /api/groups/grp_education01/members lists 3 members", 
                     success and member_count >= 3, f"{details} (found {member_count} members)")
        
        # Test PUT /api/groups/grp_education01/members/{userId}/role changes role
        if success and data:
            test_member = next((m for m in data if m['user_id'] == self.users['contributor']), None)
            if test_member:
                original_role = test_member['role']
                new_role = 'viewer' if original_role != 'viewer' else 'contributor'
                
                role_success, role_details, role_data = self.make_request('PUT', 
                    f'/api/groups/{self.groups["education"]}/members/{self.users["contributor"]}/role', 
                    self.tokens['admin'], {"role": new_role})
                self.log_test("PUT /api/groups/grp_education01/members/{userId}/role changes role", role_success, role_details)
                
                # Revert role change
                self.make_request('PUT', f'/api/groups/{self.groups["education"]}/members/{self.users["contributor"]}/role', 
                                self.tokens['admin'], {"role": original_role})

    def test_invitation_endpoints(self):
        """Test group invitation endpoints"""
        print("\n📧 Testing Group Invitation Endpoints...")
        
        # Test POST /api/groups/grp_education01/invite sends invitation
        invite_data = {
            "email": f"test.invite.{int(datetime.now().timestamp())}@example.com",
            "role": "viewer"
        }
        success, details, response_data = self.make_request('POST', f'/api/groups/{self.groups["education"]}/invite', 
                                                          self.tokens['admin'], invite_data, 200)
        invite_id = response_data.get('invite_id') if success else None
        self.log_test("POST /api/groups/grp_education01/invite sends invitation", success and invite_id, details)

    def test_export_endpoint(self):
        """Test group-scoped Excel export endpoint"""
        print("\n📄 Testing Group-Scoped Export Endpoint...")
        
        try:
            url = f"{self.base_url}/api/groups/{self.groups['education']}/export/excel"
            headers = {'Authorization': f'Bearer {self.tokens["admin"]}'}
            response = requests.get(url, headers=headers, timeout=15)
            
            success = response.status_code == 200
            is_excel = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' in response.headers.get('content-type', '')
            has_filename = 'attachment' in response.headers.get('content-disposition', '')
            
            self.log_test("GET /api/groups/grp_education01/export/excel returns xlsx file", success and is_excel and has_filename, 
                         f"Status: {response.status_code}, Content-Type: {response.headers.get('content-type', 'N/A')}")
                         
        except Exception as e:
            self.log_test("GET /api/groups/grp_education01/export/excel returns xlsx file", False, f"Request failed: {str(e)}")

    def test_role_based_access_control(self):
        """Test role-based access control"""
        print("\n🔒 Testing Role-Based Access Control...")
        
        # Viewer cannot create funds in their group
        fund_data = {"source_name": "Viewer Test", "amount_inr": 1000, "category": "Donation", "date_received": "2025-01-15"}
        success, details, data = self.make_request('POST', f'/api/groups/{self.groups["education"]}/funds', 
                                                  self.tokens['viewer'], fund_data, 403)
        self.log_test("Viewer cannot create funds in their group (403)", success, details)
        
        # Viewer cannot access group they're not a member of
        success, details, data = self.make_request('GET', f'/api/groups/{self.groups["csr"]}/funds', 
                                                  self.tokens['viewer'], expected_status=403)
        self.log_test("Viewer cannot access group they're not a member of (403)", success, details)

    def run_all_tests(self):
        """Run all test suites"""
        print("🚀 Starting FundTrack Backend API Tests (Multi-Group Architecture)...")
        print(f"Backend URL: {self.base_url}")
        print(f"Test Time: {datetime.now(timezone.utc).isoformat()}")
        
        # Test basic connectivity
        if not self.test_health_endpoint():
            print("❌ Health check failed - stopping tests")
            return False
            
        # Run all test suites
        self.test_auth_endpoints()
        self.test_group_endpoints()
        self.test_fund_endpoints()
        self.test_utilization_endpoints()
        self.test_dashboard_endpoint()
        self.test_member_endpoints()
        self.test_invitation_endpoints()
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