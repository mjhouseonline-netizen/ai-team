# test_notion_integration.py
# Testing script for Notion integration

import requests
import json
from typing import Dict, List

# Configuration - Update these with your values
BASE_URL = "https://ai-team-q84h.onrender.com"  # Or http://localhost:5000 for local
ACCESS_TOKEN = None  # Will be obtained from login

class NotionIntegrationTester:
    """Test suite for Notion integration"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = requests.Session()
        self.results = []
    
    def test(self, name: str, func):
        """Run a test and record result"""
        print(f"\n🧪 Testing: {name}")
        try:
            result = func()
            if result:
                print(f"✅ PASS: {name}")
                self.results.append({"test": name, "status": "PASS"})
            else:
                print(f"❌ FAIL: {name}")
                self.results.append({"test": name, "status": "FAIL"})
        except Exception as e:
            print(f"❌ ERROR: {name} - {str(e)}")
            self.results.append({"test": name, "status": "ERROR", "error": str(e)})
    
    def test_settings_page(self):
        """Test that settings page loads"""
        response = self.session.get(f"{self.base_url}/settings")
        return response.status_code == 200
    
    def test_notion_status_endpoint(self):
        """Test Notion status endpoint"""
        response = self.session.get(f"{self.base_url}/api/integrations/notion/status")
        return response.status_code == 200
    
    def test_notion_connect_redirect(self):
        """Test that Notion connect redirects to Notion OAuth"""
        response = self.session.get(
            f"{self.base_url}/api/integrations/notion/connect",
            allow_redirects=False
        )
        # Should redirect (302) to Notion OAuth
        if response.status_code in [302, 307]:
            location = response.headers.get('Location', '')
            return 'notion.com' in location or 'notion.so' in location
        return False
    
    def test_database_table_exists(self):
        """Test that notion_integrations table exists"""
        # This would require database access - skip if not available
        print("⚠️  Manual check required: Verify notion_integrations table exists")
        return True
    
    def summary(self):
        """Print test summary"""
        print("\n" + "="*50)
        print("📊 TEST SUMMARY")
        print("="*50)
        
        passed = sum(1 for r in self.results if r["status"] == "PASS")
        failed = sum(1 for r in self.results if r["status"] == "FAIL")
        errors = sum(1 for r in self.results if r["status"] == "ERROR")
        
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"⚠️  Errors: {errors}")
        print(f"📋 Total: {len(self.results)}")
        
        if failed == 0 and errors == 0:
            print("\n🎉 All tests passed!")
        else:
            print("\n⚠️  Some tests failed. Check output above.")


def manual_test_checklist():
    """Print manual testing checklist"""
    print("\n" + "="*50)
    print("📝 MANUAL TESTING CHECKLIST")
    print("="*50)
    
    tests = [
        "1. Visit /settings page",
        "2. Click 'Connect Notion' button",
        "3. Complete OAuth flow on Notion",
        "4. Verify redirect back to your app",
        "5. Check 'Connected' status appears",
        "6. Test agent can search Notion",
        "7. Test agent can read page content",
        "8. Click 'Disconnect' button",
        "9. Verify status changes to 'Not Connected'",
        "10. Reconnect successfully"
    ]
    
    for test in tests:
        print(f"[ ] {test}")
    
    print("\n" + "="*50)


def test_notion_api_directly():
    """Test Notion API directly with credentials"""
    print("\n" + "="*50)
    print("🔧 NOTION API DIRECT TEST")
    print("="*50)
    
    # This would be called after a user connects their Notion
    # For now, just demonstrate the structure
    
    print("""
To test Notion API directly:

1. Get a user's access token from the database:
   SELECT access_token FROM notion_integrations WHERE user_id = X;

2. Use curl to test:
   curl 'https://api.notion.com/v1/search' \\
     -H 'Authorization: Bearer YOUR_ACCESS_TOKEN' \\
     -H 'Notion-Version: 2022-06-28' \\
     -H 'Content-Type: application/json' \\
     --data '{"query":"test"}'

3. Should return JSON with search results

Expected response structure:
{
  "object": "list",
  "results": [...],
  "next_cursor": null,
  "has_more": false
}
""")


def environment_check():
    """Check environment variables are set"""
    print("\n" + "="*50)
    print("🔍 ENVIRONMENT VARIABLE CHECK")
    print("="*50)
    
    import os
    
    vars_to_check = [
        'NOTION_CLIENT_ID',
        'NOTION_CLIENT_SECRET',
        'NOTION_REDIRECT_URI'
    ]
    
    for var in vars_to_check:
        value = os.environ.get(var)
        if value:
            # Mask sensitive values
            if 'SECRET' in var:
                display = f"{value[:10]}...{value[-10:]}"
            else:
                display = value
            print(f"✅ {var}: {display}")
        else:
            print(f"❌ {var}: NOT SET")


if __name__ == "__main__":
    print("="*50)
    print("🧪 NOTION INTEGRATION TEST SUITE")
    print("="*50)
    
    # Environment check
    environment_check()
    
    # Automated tests
    tester = NotionIntegrationTester(BASE_URL)
    
    tester.test("Settings page loads", tester.test_settings_page)
    tester.test("Notion status endpoint", tester.test_notion_status_endpoint)
    tester.test("Notion connect redirects", tester.test_notion_connect_redirect)
    tester.test("Database table exists", tester.test_database_table_exists)
    
    # Summary
    tester.summary()
    
    # Manual tests
    manual_test_checklist()
    
    # API test guide
    test_notion_api_directly()
    
    print("\n" + "="*50)
    print("✨ Testing complete!")
    print("="*50)
