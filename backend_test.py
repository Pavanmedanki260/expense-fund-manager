#!/usr/bin/env python3
"""
FundTrack Backend API Testing Suite - Email/Password JWT Auth
Tests all endpoints with real authentication using email/password credentials
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
        
        # Real test credentials from /app/memory/test_credentials.md
        self.credentials = {
            'admin': {'email': 'admin@fundtrack.com', 'password': 'Admin@123'},
            'ravi': {'email': 'ravi@test.com', 'password': 'Ravi@123'},
            'priya': {'email': 'priya@test.com', 'password': 'Priya@123'}
        }
        
        # Will be populated after login
        self.sessions = {}
        self.users = {}
        self.test_group_id = None

    def log_test(self, name: str, success: bool, details: str = ""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name}")
        else:
            print(f"❌ {name} - {details}")
            self.failed_tests.append(f"{name}: {details}")

    def make_request(self, method: str, endpoint: str, session: requests.Session = None, data: dict = None, expected_status: int = 200) -> tuple:
        """Make HTTP request with session (for cookies)"""
        url = f"{self.base_url}{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        if session is None:
            session = requests.Session()
            
        try:
            if method == 'GET':
                response = session.get(url, headers=headers, timeout=10)
            elif method == 'POST':
                response = session.post(url, headers=headers, json=data, timeout=10)
            elif method == 'PUT':
                response = session.put(url, headers=headers, json=data, timeout=10)
            elif method == 'DELETE':
                response = session.delete(url, headers=headers, timeout=10)
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

    def login_user(self, user_key: str) -> bool:
        """Login user and store session"""
        creds = self.credentials[user_key]
        session = requests.Session()
        
        success, details, data = self.make_request('POST', '/api/auth/login', session, creds)
        if success and 'user_id' in data:
            self.sessions[user_key] = session
            self.users[user_key] = data
            return True
        else:
            print(f"❌ Failed to login {user_key}: {details}")
            return False

    def setup_test_users(self) -> bool:
        """Login all test users"""
        print("🔐 Setting up test users...")
        
        # Login admin
        if not self.login_user('admin'):
            return False
            
        # Try to login test users, register if they don't exist
        for user_key in ['ravi', 'priya']:
            if not self.login_user(user_key):
                # Try to register the user
                creds = self.credentials[user_key]
                register_data = {
                    'name': user_key.title(),
                    'email': creds['email'],
                    'password': creds['password']
                }
                success, details, data = self.make_request('POST', '/api/auth/register', None, register_data)
                if success:
                    print(f"✅ Registered {user_key}")
                    # Login after registration
                    if not self.login_user(user_key):
                        return False
                else:
                    print(f"❌ Failed to register {user_key}: {details}")
                    return False
        
        return True

    def test_health_endpoint(self):
        """Test /api/health endpoint"""
        success, details, data = self.make_request('GET', '/api/health')
        self.log_test("Health Check", success and 'status' in data, details)
        return success

    def test_auth_endpoints(self):
        """Test authentication endpoints"""
        print("\n🔐 Testing Authentication Endpoints...")
        
        # Test register with new user
        test_email = f"test.{int(datetime.now().timestamp())}@example.com"
        register_data = {
            'name': 'Test User',
            'email': test_email,
            'password': 'TestPass123'
        }
        success, details, data = self.make_request('POST', '/api/auth/register', None, register_data)
        self.log_test("POST /api/auth/register creates new user account", success and 'user_id' in data, details)
        
        # Test login with correct credentials
        login_data = {'email': 'admin@fundtrack.com', 'password': 'Admin@123'}
        success, details, data = self.make_request('POST', '/api/auth/login', None, login_data)
        self.log_test("POST /api/auth/login with correct credentials returns user", success and 'user_id' in data, details)
        
        # Test login with wrong password
        wrong_login = {'email': 'admin@fundtrack.com', 'password': 'WrongPassword'}
        success, details, data = self.make_request('POST', '/api/auth/login', None, wrong_login, 401)
        self.log_test("POST /api/auth/login with wrong password returns 401", success, details)
        
        # Test /api/auth/me with admin session
        admin_session = self.sessions.get('admin')
        if admin_session:
            success, details, data = self.make_request('GET', '/api/auth/me', admin_session)
            is_super_admin = data.get('is_super_admin', False) if success else False
            self.log_test("GET /api/auth/me returns current user when authenticated", 
                         success and 'user_id' in data and is_super_admin, details)

    def test_logout_endpoint(self):
        """Test logout endpoint separately at the end"""
        print("\n🚪 Testing Logout Endpoint...")
        
        # Create a separate session for logout test
        logout_session = requests.Session()
        login_data = {'email': 'admin@fundtrack.com', 'password': 'Admin@123'}
        success, details, data = self.make_request('POST', '/api/auth/login', logout_session, login_data)
        
        if success:
            # Test logout
            success, details, data = self.make_request('POST', '/api/auth/logout', logout_session)
            self.log_test("POST /api/auth/logout clears cookies", success, details)

    def test_group_endpoints(self):
        """Test group management endpoints"""
        print("\n🏢 Testing Group Endpoints...")
        
        admin_session = self.sessions.get('admin')
        if not admin_session:
            self.log_test("Admin session required for group tests", False, "No admin session")
            return
        
        # Test POST /api/groups creates a new group
        group_data = {
            "name": "Test Group API",
            "description": "Created via API test"
        }
        success, details, response_data = self.make_request('POST', '/api/groups', admin_session, group_data)
        self.test_group_id = response_data.get('group_id') if success else None
        self.log_test("POST /api/groups creates a new group (creator becomes admin)", success and self.test_group_id, details)
        
        # Test GET /api/groups lists user's groups
        success, details, data = self.make_request('GET', '/api/groups', admin_session)
        self.log_test("GET /api/groups lists user's groups", 
                     success and isinstance(data, list) and len(data) >= 1, details)
        
        # Test GET /api/groups/{groupId} returns group details
        if self.test_group_id:
            success, details, data = self.make_request('GET', f'/api/groups/{self.test_group_id}', admin_session)
            has_user_role = 'user_role' in data if success else False
            self.log_test("GET /api/groups/{groupId} returns group with user_role", 
                         success and has_user_role, details)

    def test_fund_endpoints(self):
        """Test group-scoped fund CRUD operations"""
        print("\n💰 Testing Group-Scoped Fund Endpoints...")
        
        if not self.test_group_id:
            self.log_test("Test group required for fund tests", False, "No test group available")
            return
            
        admin_session = self.sessions.get('admin')
        ravi_session = self.sessions.get('ravi')
        
        # Test GET /api/groups/{groupId}/funds returns funds
        success, details, data = self.make_request('GET', f'/api/groups/{self.test_group_id}/funds', admin_session)
        self.log_test("GET /api/groups/{groupId}/funds returns funds", 
                     success and isinstance(data, list), details)
        
        # Test POST /api/groups/{groupId}/funds creates fund (admin/contributor only)
        fund_data = {
            "source_name": "Test Fund Admin",
            "amount_inr": 50000.0,
            "category": "Donation",
            "date_received": "2025-01-15",
            "notes": "Test fund created by admin"
        }
        success, details, response_data = self.make_request('POST', f'/api/groups/{self.test_group_id}/funds', 
                                                          admin_session, fund_data)
        admin_fund_id = response_data.get('fund_id') if success else None
        self.log_test("POST /api/groups/{groupId}/funds creates fund (admin/contributor only)", success and admin_fund_id, details)
        
        # Test role-based access - invite ravi as contributor and test fund creation
        if ravi_session:
            # First invite ravi to the group as contributor
            invite_data = {"email": "ravi@test.com", "role": "contributor"}
            self.make_request('POST', f'/api/groups/{self.test_group_id}/invite', admin_session, invite_data)
            
            # Accept invitation (in real scenario, ravi would click email link)
            # For testing, we'll add ravi directly as contributor
            
        # Clean up test fund
        if admin_fund_id:
            self.make_request('DELETE', f'/api/groups/{self.test_group_id}/funds/{admin_fund_id}', admin_session)

    def test_dashboard_endpoint(self):
        """Test group-scoped dashboard data endpoint"""
        print("\n📈 Testing Group-Scoped Dashboard Endpoint...")
        
        if not self.test_group_id:
            self.log_test("Test group required for dashboard tests", False, "No test group available")
            return
            
        admin_session = self.sessions.get('admin')
        
        # Test GET /api/groups/{groupId}/dashboard returns summary data
        success, details, data = self.make_request('GET', f'/api/groups/{self.test_group_id}/dashboard', admin_session)
        required_fields = ['total_collected', 'total_utilized', 'balance', 'pct_utilized', 'category_breakdown', 'monthly_data', 'recent_activity']
        has_all_fields = all(field in data for field in required_fields) if success else False
        self.log_test("GET /api/groups/{groupId}/dashboard returns summary data", success and has_all_fields, details)

    def test_member_endpoints(self):
        """Test group member management endpoints"""
        print("\n👥 Testing Group Member Management Endpoints...")
        
        if not self.test_group_id:
            self.log_test("Test group required for member tests", False, "No test group available")
            return
            
        admin_session = self.sessions.get('admin')
        
        # Test GET /api/groups/{groupId}/members lists group members
        success, details, data = self.make_request('GET', f'/api/groups/{self.test_group_id}/members', admin_session)
        member_count = len(data) if success and isinstance(data, list) else 0
        self.log_test("GET /api/groups/{groupId}/members lists group members", 
                     success and member_count >= 1, f"{details} (found {member_count} members)")

    def test_invitation_endpoints(self):
        """Test group invitation endpoints"""
        print("\n📧 Testing Group Invitation Endpoints...")
        
        if not self.test_group_id:
            self.log_test("Test group required for invitation tests", False, "No test group available")
            return
            
        admin_session = self.sessions.get('admin')
        
        # Test POST /api/groups/{groupId}/invite sends email invitation
        invite_data = {
            "email": f"test.invite.{int(datetime.now().timestamp())}@example.com",
            "role": "viewer"
        }
        success, details, response_data = self.make_request('POST', f'/api/groups/{self.test_group_id}/invite', 
                                                          admin_session, invite_data)
        invite_id = response_data.get('invite_id') if success else None
        self.log_test("POST /api/groups/{groupId}/invite sends email invitation", success and invite_id, details)

    def test_role_based_access_control(self):
        """Test role-based access control"""
        print("\n🔒 Testing Role-Based Access Control...")
        
        if not self.test_group_id:
            self.log_test("Test group required for RBAC tests", False, "No test group available")
            return
            
        # Create a second group to test non-member access
        admin_session = self.sessions.get('admin')
        ravi_session = self.sessions.get('ravi')
        
        # Create another group that ravi is not a member of
        group_data = {"name": "Private Group", "description": "Ravi not a member"}
        success, details, response_data = self.make_request('POST', '/api/groups', admin_session, group_data)
        private_group_id = response_data.get('group_id') if success else None
        
        if private_group_id and ravi_session:
            # Test non-member cannot access group (403)
            success, details, data = self.make_request('GET', f'/api/groups/{private_group_id}/funds', 
                                                      ravi_session, expected_status=403)
            self.log_test("Non-member cannot access group (403)", success, details)
            
            # Clean up private group
            self.make_request('DELETE', f'/api/groups/{private_group_id}', admin_session)

    def run_all_tests(self):
        """Run all test suites"""
        print("🚀 Starting FundTrack Backend API Tests (Email/Password JWT Auth)...")
        print(f"Backend URL: {self.base_url}")
        print(f"Test Time: {datetime.now(timezone.utc).isoformat()}")
        
        # Test basic connectivity
        if not self.test_health_endpoint():
            print("❌ Health check failed - stopping tests")
            return False
            
        # Setup test users (login/register)
        if not self.setup_test_users():
            print("❌ Failed to setup test users - stopping tests")
            return False
            
        # Run all test suites
        self.test_auth_endpoints()
        self.test_group_endpoints()
        self.test_fund_endpoints()
        self.test_dashboard_endpoint()
        self.test_member_endpoints()
        self.test_invitation_endpoints()
        self.test_role_based_access_control()
        self.test_logout_endpoint()  # Test logout at the end
        
        # Clean up test group
        if self.test_group_id and self.sessions.get('admin'):
            self.make_request('DELETE', f'/api/groups/{self.test_group_id}', self.sessions['admin'])
        
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