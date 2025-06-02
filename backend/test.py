#!/usr/bin/env python3
"""
Test your Flask Notion API endpoints
"""
import requests
import json
import sys
from typing import Dict, Any

class NotionAPITester:
    def __init__(self, base_url: str = "http://localhost:5000"):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
    
    def test_list_pages(self, query: str = "meeting") -> Dict[str, Any]:
        """Test the /pages endpoint"""
        print(f"🔍 Testing GET /pages?query={query}")
        try:
            response = self.session.get(
                f"{self.base_url}/pages",
                params={"query": query},
                timeout=30
            )
            
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Success: {data.get('message', 'OK')}")
                pages = data.get('data', [])
                print(f"Found {len(pages)} pages:")
                
                for i, page in enumerate(pages[:5], 1):
                    print(f"  {i}. {page.get('title', 'Untitled')} (ID: {page.get('id', '')[:8]}...)")
                    if page.get('content'):
                        content_preview = page['content'][:100] + '...' if len(page['content']) > 100 else page['content']
                        print(f"     Content: {content_preview}")
                
                return {"success": True, "data": pages}
            else:
                error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {"error": response.text}
                print(f"❌ Error: {error_data.get('error', 'Unknown error')}")
                return {"success": False, "error": error_data}
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed: {e}")
            return {"success": False, "error": str(e)}
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            return {"success": False, "error": str(e)}
    
    def test_get_page_content(self, page_id: str) -> Dict[str, Any]:
        """Test the /page/<page_id> endpoint"""
        print(f"📄 Testing GET /page/{page_id[:8]}...")
        try:
            response = self.session.get(
                f"{self.base_url}/page/{page_id}",
                timeout=30
            )
            
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    print(f"✅ Success: Retrieved page '{data.get('title', 'Untitled')}'")
                    content = data.get('content', '')
                    print(f"Content length: {len(content)} characters")
                    if content:
                        print(f"Content preview:\n{content[:200]}{'...' if len(content) > 200 else ''}")
                else:
                    print(f"❌ API Error: {data.get('error', 'Unknown error')}")
                
                return data
            else:
                error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {"error": response.text}
                print(f"❌ HTTP Error: {error_data.get('error', 'Unknown error')}")
                return {"success": False, "error": error_data}
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed: {e}")
            return {"success": False, "error": str(e)}
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            return {"success": False, "error": str(e)}
    
    def test_append_to_page(self, page_id: str, text: str) -> Dict[str, Any]:
        """Test the /page/<page_id>/append endpoint"""
        print(f"✏️ Testing POST /page/{page_id[:8]}.../append")
        try:
            payload = {"text": text}
            response = self.session.post(
                f"{self.base_url}/page/{page_id}/append",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Success: {data.get('message', 'Text appended')}")
                return data
            else:
                error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {"error": response.text}
                print(f"❌ Error: {error_data.get('error', 'Unknown error')}")
                return {"success": False, "error": error_data}
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed: {e}")
            return {"success": False, "error": str(e)}
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            return {"success": False, "error": str(e)}
    
    def run_full_test(self):
        """Run a complete test suite"""
        print("🚀 Running Full Notion API Test Suite")
        print("=" * 60)
        
        # Test 1: List pages
        print("\n1. Testing page listing...")
        pages_result = self.test_list_pages("meeting")
        
        if not pages_result.get('success'):
            print("❌ Cannot continue tests without page listing working")
            return False
        
        pages = pages_result.get('data', [])
        if not pages:
            print("⚠️ No pages found. Make sure you have shared some pages with your Notion integration.")
            return False
        
        # Test 2: Get page content
        print("\n2. Testing page content retrieval...")
        test_page = pages[0]
        page_id = test_page['id']
        content_result = self.test_get_page_content(page_id)
        
        if not content_result.get('success'):
            print("❌ Page content retrieval failed")
            return False
        
        # Test 3: Append to page (optional - ask user)
        print("\n3. Testing page append...")
        user_consent = input("⚠️ This will add text to a Notion page. Continue? (y/N): ").strip().lower()
        
        if user_consent in ['y', 'yes']:
            test_text = f"Test note added by API at {self._get_timestamp()}"
            append_result = self.test_append_to_page(page_id, test_text)
            
            if append_result.get('success'):
                print("✅ All tests passed!")
            else:
                print("❌ Append test failed, but other functionality works")
        else:
            print("⏭️ Skipping append test")
            print("✅ Read operations working correctly!")
        
        return True
    
    def _get_timestamp(self):
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def main():
    print("🔧 Flask Notion API Tester")
    print("=" * 40)
    
    # Get base URL
    base_url = input("Enter Flask app URL (default: http://localhost:5000): ").strip()
    if not base_url:
        base_url = "http://localhost:5000"
    
    # Test connection
    print(f"\n🔗 Testing connection to {base_url}...")
    try:
        response = requests.get(f"{base_url}/", timeout=5)
        print(f"✅ Server is running (Status: {response.status_code})")
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot connect to server: {e}")
        print("\n💡 Make sure your Flask app is running:")
        print("   python app.py")
        sys.exit(1)
    
    # Run tests
    tester = NotionAPITester(base_url)
    
    while True:
        print("\n" + "=" * 40)
        print("🧪 Test Menu")
        print("=" * 40)
        print("1. Run full test suite")
        print("2. Test list pages")
        print("3. Test get page content")
        print("4. Test append to page")
        print("5. Exit")
        
        choice = input("\nEnter choice (1-5): ").strip()
        
        if choice == '1':
            print()
            tester.run_full_test()
        
        elif choice == '2':
            query = input("Enter search query (default: 'meeting'): ").strip() or "meeting"
            print()
            tester.test_list_pages(query)
        
        elif choice == '3':
            page_id = input("Enter page ID: ").strip()
            if page_id:
                print()
                tester.test_get_page_content(page_id)
            else:
                print("❌ Page ID required")
        
        elif choice == '4':
            page_id = input("Enter page ID: ").strip()
            text = input("Enter text to append: ").strip()
            if page_id and text:
                print()
                tester.test_append_to_page(page_id, text)
            else:
                print("❌ Both page ID and text required")
        
        elif choice == '5':
            print("👋 Goodbye!")
            break
        
        else:
            print("❌ Invalid choice")

if __name__ == "__main__":
    main()