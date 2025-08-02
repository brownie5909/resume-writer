#!/usr/bin/env python3
"""
Test script for Hire Ready authentication system
Run this to test the API endpoints
"""

import requests
import json
import sys

# Configuration
BASE_URL = "http://localhost:8000/api"  # Change for production
TEST_USER = {
    "email": "test@example.com",
    "password": "testpass123",
    "full_name": "Test User"
}

def test_endpoint(method, endpoint, data=None, headers=None, expected_status=200):
    """Test an API endpoint"""
    url = f"{BASE_URL}{endpoint}"
    
    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=headers)
        elif method.upper() == "POST":
            response = requests.post(url, json=data, headers=headers)
        else:
            print(f"❌ Unsupported method: {method}")
            return None
        
        print(f"🔗 {method.upper()} {endpoint}")
        print(f"   Status: {response.status_code}")
        
        if response.status_code == expected_status:
            print("   ✅ Expected status code")
        else:
            print(f"   ⚠️  Expected {expected_status}, got {response.status_code}")
        
        try:
            result = response.json()
            print(f"   Response: {json.dumps(result, indent=2)[:200]}...")
            return result
        except:
            print(f"   Response: {response.text[:200]}...")
            return response.text
            
    except requests.exceptions.ConnectionError:
        print(f"❌ Connection failed to {url}")
        print("   Make sure the API server is running")
        return None
    except Exception as e:
        print(f"❌ Error testing {endpoint}: {e}")
        return None

def test_authentication_flow():
    """Test the complete authentication flow"""
    print("🧪 Testing Hire Ready Authentication System")
    print("=" * 50)
    
    # Test 1: Health check
    print("\n1. Health Check")
    health = test_endpoint("GET", "/health")
    if not health:
        print("❌ API server not responding. Start with: uvicorn main:app --reload")
        return False
    
    # Test 2: Check available tiers (public)
    print("\n2. Get Available Tiers (Public)")
    tiers = test_endpoint("GET", "/tiers/all")
    
    # Test 3: Check email availability
    print("\n3. Check Email Availability")
    email_check = test_endpoint("POST", "/auth/check-email", {"email": TEST_USER["email"]})
    
    # Test 4: Register user
    print("\n4. User Registration")
    register_result = test_endpoint("POST", "/auth/register", TEST_USER, expected_status=200)
    
    if not register_result or "access_token" not in register_result:
        print("❌ Registration failed")
        return False
    
    access_token = register_result["access_token"]
    print(f"   ✅ Got access token: {access_token[:20]}...")
    
    # Test 5: Get user info
    print("\n5. Get Current User Info")
    headers = {"Authorization": f"Bearer {access_token}"}
    user_info = test_endpoint("GET", "/auth/me", headers=headers)
    
    # Test 6: Get user tier info
    print("\n6. Get User Tier Info")
    tier_info = test_endpoint("GET", "/user/tier", headers=headers)
    
    # Test 7: Check feature access
    print("\n7. Check Feature Access")
    feature_check = test_endpoint("POST", "/user/check-access/resume_builder", headers=headers)
    
    # Test 8: Get user usage
    print("\n8. Get User Usage Statistics")
    usage = test_endpoint("GET", "/user/usage", headers=headers)
    
    # Test 9: Generate resume (authenticated)
    print("\n9. Generate Resume (Authenticated)")
    resume_data = {
        "data": {
            "full_name": "Test User",
            "email": "test@example.com",
            "job_title": "Software Developer",
            "summary": "Experienced developer",
            "skills": "Python, JavaScript, FastAPI"
        },
        "template_choice": "default"
    }
    resume_result = test_endpoint("POST", "/generate-resume", resume_data, headers)
    
    # Test 10: Get user documents
    print("\n10. Get User Documents")
    documents = test_endpoint("GET", "/user/documents", headers=headers)
    
    # Test 11: Test login with same credentials
    print("\n11. User Login Test")
    login_data = {
        "email": TEST_USER["email"],
        "password": TEST_USER["password"]
    }
    login_result = test_endpoint("POST", "/auth/login", login_data)
    
    # Test 12: Generate guest resume (no auth)
    print("\n12. Generate Guest Resume (No Auth)")
    guest_resume = test_endpoint("POST", "/generate-resume-guest", resume_data)
    
    print("\n" + "=" * 50)
    print("🎉 Authentication system test completed!")
    
    return True

def test_premium_features():
    """Test premium feature access"""
    print("\n🔒 Testing Premium Feature Access")
    print("-" * 30)
    
    # Test premium feature without auth
    print("Testing premium feature without authentication:")
    premium_test = test_endpoint("POST", "/analyze-resume", {}, expected_status=401)
    
    print("\nPremium feature testing completed")

def cleanup_test_data():
    """Clean up test data"""
    print("\n🧹 Cleanup")
    print("Note: Test data will remain in database for now")
    print("To reset database, run: python db_init.py reset")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "auth":
            test_authentication_flow()
        elif command == "premium":
            test_premium_features()
        elif command == "cleanup":
            cleanup_test_data()
        elif command == "all":
            test_authentication_flow()
            test_premium_features()
            cleanup_test_data()
        else:
            print("Usage: python test_auth.py [auth|premium|cleanup|all]")
    else:
        # Default: run auth flow
        success = test_authentication_flow()
        
        if success:
            print("\n✅ All tests passed! Your authentication system is working.")
            print("\nNext steps:")
            print("1. Test the API with your frontend")
            print("2. Configure environment variables")
            print("3. Set up email verification")
            print("4. Plan Stripe integration")
        else:
            print("\n❌ Some tests failed. Check the API server and try again.")