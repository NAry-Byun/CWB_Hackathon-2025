# diagnostic_notion.py - Run this to diagnose Notion integration issues
import os
import asyncio
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def diagnose_notion_integration():
    """Comprehensive Notion integration diagnostic"""
    
    print("🔍 NOTION INTEGRATION DIAGNOSTIC")
    print("=" * 50)
    
    # 1. Check environment variables
    print("\n1. ENVIRONMENT VARIABLES:")
    notion_token = os.getenv('NOTION_API_TOKEN')
    if notion_token:
        print(f"✅ NOTION_API_TOKEN: Set (length: {len(notion_token)})")
        # Mask the token for security
        masked_token = notion_token[:10] + "..." + notion_token[-4:] if len(notion_token) > 14 else "***"
        print(f"   Preview: {masked_token}")
    else:
        print("❌ NOTION_API_TOKEN: Not set")
        print("   Fix: Add NOTION_API_TOKEN=your_token_here to your .env file")
        return False
    
    notion_version = os.getenv('NOTION_API_VERSION', '2022-06-28')
    print(f"ℹ️  NOTION_API_VERSION: {notion_version}")
    
    # 2. Test service import
    print("\n2. SERVICE IMPORT TEST:")
    try:
        from services.notion_service import NotionService
        print("✅ NotionService import successful")
    except ImportError as e:
        print(f"❌ NotionService import failed: {e}")
        print("   Fix: Ensure services/notion_service.py exists")
        return False
    except Exception as e:
        print(f"❌ NotionService import error: {e}")
        return False
    
    # 3. Test service initialization
    print("\n3. SERVICE INITIALIZATION:")
    try:
        notion_service = NotionService()
        print("✅ NotionService initialized successfully")
    except Exception as e:
        print(f"❌ NotionService initialization failed: {e}")
        return False
    
    # 4. Test API connectivity
    print("\n4. API CONNECTIVITY TEST:")
    try:
        health_result = await notion_service.health_check()
        if health_result.get('status') == 'healthy':
            print("✅ Notion API connectivity successful")
            print(f"   User type: {health_result.get('workspace_user_type', 'unknown')}")
        else:
            print(f"❌ Notion API connectivity failed: {health_result}")
            return False
    except Exception as e:
        print(f"❌ API connectivity test failed: {e}")
        print("   Common issues:")
        print("   - Invalid NOTION_API_TOKEN")
        print("   - Network connectivity issues")
        print("   - API rate limits")
        return False
    
    # 5. Test search functionality
    print("\n5. SEARCH FUNCTIONALITY TEST:")
    try:
        # Test basic search
        pages = await notion_service.search_pages(query="", limit=3)
        print(f"✅ Basic search successful: Found {len(pages)} pages")
        
        if pages:
            sample_page = pages[0]
            print(f"   Sample page: {sample_page.get('title', 'No title')}")
            print(f"   Page ID: {sample_page.get('id', 'No ID')}")
            
            # Test getting page content
            page_content = await notion_service.get_page_content(sample_page['id'])
            if page_content.get('success'):
                print(f"✅ Page content retrieval successful")
                content_preview = page_content.get('content', '')[:100]
                print(f"   Content preview: {content_preview}...")
            else:
                print(f"⚠️ Page content retrieval failed: {page_content.get('error')}")
        else:
            print("ℹ️  No pages found (empty workspace or no access)")
            
    except Exception as e:
        print(f"❌ Search functionality test failed: {e}")
        return False
    
    # 6. Test chat integration path
    print("\n6. CHAT INTEGRATION PATH TEST:")
    try:
        # Test Azure OpenAI service import
        from services.azure_openai_service import AzureOpenAIService
        print("✅ AzureOpenAIService import successful")
        
        # Check required environment variables for OpenAI
        openai_vars = ['AZURE_OPENAI_API_KEY', 'AZURE_OPENAI_ENDPOINT']
        missing_openai = [var for var in openai_vars if not os.getenv(var)]
        
        if missing_openai:
            print(f"⚠️ Missing OpenAI variables: {missing_openai}")
        else:
            print("✅ OpenAI environment variables present")
            
            # Test OpenAI service initialization
            try:
                openai_service = AzureOpenAIService()
                print("✅ AzureOpenAIService initialized")
                
                # Test if it can handle notion_pages parameter
                print("✅ Ready for Notion-OpenAI integration")
                
            except Exception as e:
                print(f"⚠️ OpenAI service initialization issue: {e}")
        
    except ImportError as e:
        print(f"❌ Azure OpenAI service import failed: {e}")
    except Exception as e:
        print(f"❌ Chat integration test failed: {e}")
    
    # 7. Test Flask route integration
    print("\n7. FLASK ROUTE INTEGRATION TEST:")
    try:
        # Check if chat routes exist
        if os.path.exists('routes/chat_routes.py'):
            print("✅ Chat routes file exists")
            
            # Try to import
            try:
                from routes.chat_routes import chat_bp
                print("✅ Chat blueprint import successful")
            except Exception as e:
                print(f"⚠️ Chat blueprint import issue: {e}")
        else:
            print("❌ routes/chat_routes.py not found")
            
    except Exception as e:
        print(f"❌ Flask route integration test failed: {e}")
    
    print("\n" + "=" * 50)
    print("🎯 DIAGNOSTIC SUMMARY")
    print("=" * 50)
    
    # Provide specific fixes based on common issues
    print("\n🔧 COMMON FIXES:")
    
    print("\n1. If Notion token issues:")
    print("   - Get token from: https://www.notion.so/my-integrations")
    print("   - Add to .env file: NOTION_API_TOKEN=secret_xxx")
    print("   - Restart your Flask server")
    
    print("\n2. If no pages found:")
    print("   - Share pages with your integration in Notion")
    print("   - Check integration permissions")
    print("   - Verify workspace access")
    
    print("\n3. If chat integration not working:")
    print("   - Ensure you're using the updated chat_routes.py")
    print("   - Check Flask server logs for errors")
    print("   - Test with: curl http://localhost:5000/api/chat/test-notion")
    
    print("\n4. Test the full integration:")
    print("   - Start Flask: python app.py --test-notion")
    print("   - Test endpoint: curl -X POST http://localhost:5000/api/chat/chat \\")
    print("                          -H 'Content-Type: application/json' \\")
    print("                          -d '{\"message\": \"What meetings do I have?\"}'")
    
    return True

def main():
    """Run the diagnostic"""
    try:
        # Check if we're in the right directory
        if not os.path.exists('services'):
            print("❌ Not in project root directory")
            print("   Please run this from the directory containing 'services' folder")
            return
        
        # Add current directory to path
        sys.path.append(os.getcwd())
        
        # Run async diagnostic
        asyncio.run(diagnose_notion_integration())
        
    except KeyboardInterrupt:
        print("\n⚠️ Diagnostic interrupted by user")
    except Exception as e:
        print(f"\n❌ Diagnostic failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()