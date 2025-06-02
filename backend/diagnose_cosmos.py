"""
Cosmos DB Diagnostic Script
Check if scraping data is being saved properly
"""

import asyncio
import os
import sys
from datetime import datetime

# Add path for services
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def diagnose_cosmos_db():
    """Diagnose Cosmos DB storage and retrieval"""
    print("🔍 Cosmos DB Diagnostic Script")
    print("=" * 50)
    
    # 1. Check environment variables
    print("\n1. 🔧 Environment Variables:")
    required_vars = ['COSMOS_DB_ENDPOINT', 'COSMOS_DB_KEY', 'COSMOS_DB_DATABASE_NAME', 'COSMOS_DB_CONTAINER_NAME']
    
    for var in required_vars:
        value = os.environ.get(var)
        if value:
            if 'KEY' in var:
                print(f"   ✅ {var}: {'*' * 10}...{value[-10:]}")
            else:
                print(f"   ✅ {var}: {value}")
        else:
            print(f"   ❌ {var}: NOT SET")
    
    # 2. Test Cosmos DB connection
    print("\n2. 🗄️ Cosmos DB Connection Test:")
    try:
        from services.cosmos_service import CosmosVectorService
        cosmos_service = CosmosVectorService()
        await cosmos_service.initialize_database()
        print("   ✅ Cosmos DB connection successful")
        
        # 3. Check if database/container exists
        print("\n3. 📦 Database Structure Check:")
        try:
            # Get container reference
            container = cosmos_service.container
            print(f"   ✅ Container accessed: {container.id}")
            
            # 4. Count existing documents
            print("\n4. 📄 Document Count Check:")
            query = "SELECT VALUE COUNT(1) FROM c"
            items = list(container.query_items(query=query, enable_cross_partition_query=True))
            total_docs = items[0] if items else 0
            print(f"   📊 Total documents in container: {total_docs}")
            
            # 5. Check for AI-related documents
            print("\n5. 🤖 AI-Related Document Check:")
            ai_query = """
            SELECT c.id, c.file_name, c.metadata.document_title, c.metadata.quality_level 
            FROM c 
            WHERE CONTAINS(LOWER(c.metadata.document_title || ''), 'artificial intelligence')
            OR CONTAINS(LOWER(c.file_name || ''), 'artificial')
            """
            ai_docs = list(container.query_items(query=ai_query, enable_cross_partition_query=True))
            print(f"   🔍 AI-related documents found: {len(ai_docs)}")
            
            for doc in ai_docs[:5]:  # Show first 5
                title = doc.get('metadata', {}).get('document_title', 'No title')
                quality = doc.get('metadata', {}).get('quality_level', 'Unknown')
                print(f"      📝 {title[:50]}... (Quality: {quality})")
            
            # 6. Check for professional vs basic scraping
            print("\n6. 🎯 Scraping Quality Check:")
            professional_query = """
            SELECT c.id, c.metadata.extraction_method, c.metadata.optimized_for_professional_responses
            FROM c 
            WHERE c.metadata.optimized_for_professional_responses = true
            """
            prof_docs = list(container.query_items(query=professional_query, enable_cross_partition_query=True))
            print(f"   ✨ Professional scraped documents: {len(prof_docs)}")
            
            basic_query = """
            SELECT c.id, c.metadata.extraction_method
            FROM c 
            WHERE c.metadata.optimized_for_professional_responses != true
            OR NOT IS_DEFINED(c.metadata.optimized_for_professional_responses)
            """
            basic_docs = list(container.query_items(query=basic_query, enable_cross_partition_query=True))
            print(f"   📝 Basic/old scraped documents: {len(basic_docs)}")
            
            # 7. Check specific URL
            print("\n7. 🔗 Specific URL Check:")
            url_to_check = "https://www.artificial-intelligence.blog/terminology/artificial-intelligence"
            url_query = f"""
            SELECT c.id, c.metadata.source_url, c.metadata.document_title, 
                   c.metadata.optimized_for_professional_responses, c.metadata.quality_level
            FROM c 
            WHERE c.metadata.source_url = '{url_to_check}'
            """
            url_docs = list(container.query_items(query=url_query, enable_cross_partition_query=True))
            print(f"   🎯 Documents from target URL: {len(url_docs)}")
            
            for doc in url_docs:
                professional = doc.get('metadata', {}).get('optimized_for_professional_responses', False)
                quality = doc.get('metadata', {}).get('quality_level', 'Unknown')
                title = doc.get('metadata', {}).get('document_title', 'No title')
                print(f"      📄 {title[:40]}... (Professional: {professional}, Quality: {quality})")
            
            # 8. Sample document structure
            print("\n8. 📋 Sample Document Structure:")
            sample_query = "SELECT TOP 1 * FROM c"
            sample_docs = list(container.query_items(query=sample_query, enable_cross_partition_query=True))
            
            if sample_docs:
                sample = sample_docs[0]
                print("   📄 Sample document keys:")
                print(f"      🔑 Top level: {list(sample.keys())}")
                if 'metadata' in sample:
                    print(f"      🔑 Metadata keys: {list(sample['metadata'].keys())[:10]}...")
            
        except Exception as e:
            print(f"   ❌ Container access failed: {e}")
            
    except Exception as e:
        print(f"   ❌ Cosmos DB connection failed: {e}")
        print(f"      Make sure services/cosmos_service.py exists")
    
    # 9. Test web scraper
    print("\n9. 🕷️ Web Scraper Test:")
    try:
        from services.web_scraper_service import get_scraper
        scraper = get_scraper(use_professional=True)
        scraper_type = type(scraper).__name__
        print(f"   ✅ Scraper loaded: {scraper_type}")
        
        # Test if it has professional capabilities
        has_professional = hasattr(scraper, 'scrape_and_store_professionally')
        has_cosmos = hasattr(scraper, 'cosmos_service')
        print(f"   🎯 Professional scraping: {has_professional}")
        print(f"   🗄️ Cosmos DB integration: {has_cosmos}")
        
    except Exception as e:
        print(f"   ❌ Web scraper test failed: {e}")
    
    # 10. Test AI chat system
    print("\n10. 🤖 AI Chat System Test:")
    try:
        from services.openai_service import OpenAIService
        from services.cosmos_service import CosmosVectorService
        
        # Test if services can be imported
        print("   ✅ AI services can be imported")
        
        # Check if AI service can query Cosmos DB
        cosmos = CosmosVectorService()
        await cosmos.initialize_database()
        
        # Test a search query
        test_query = "artificial intelligence definition"
        results = await cosmos.search_similar_documents(test_query, top_k=3)
        print(f"   🔍 Search test results: {len(results)} documents found")
        
        for i, result in enumerate(results[:2]):
            score = result.get('score', 0)
            title = result.get('metadata', {}).get('document_title', 'No title')
            print(f"      {i+1}. {title[:40]}... (Score: {score:.3f})")
            
    except Exception as e:
        print(f"   ❌ AI chat system test failed: {e}")

async def test_scraping_and_storage():
    """Test the complete scraping and storage pipeline"""
    print("\n" + "=" * 50)
    print("🔄 Testing Complete Scraping Pipeline")
    print("=" * 50)
    
    try:
        from services.web_scraper_service import get_scraper
        
        scraper = get_scraper(use_professional=True)
        test_url = "https://httpbin.org/html"  # Simple test URL
        
        print(f"\n📄 Testing with URL: {test_url}")
        
        if hasattr(scraper, 'scrape_and_store_professionally'):
            print("🎯 Running professional scraping...")
            result = await scraper.scrape_and_store_professionally(test_url)
            
            if result['success']:
                print("✅ Professional scraping successful!")
                print(f"   📝 Chunks created: {result['chunks']['total_created']}")
                print(f"   💾 Chunks stored: {result['chunks']['stored_successfully']}")
                print(f"   ✨ Success rate: {result['chunks']['success_rate']}%")
            else:
                print(f"❌ Professional scraping failed: {result['error']}")
        else:
            print("⚠️ Only basic scraping available")
            result = scraper.scrape_url(test_url)
            print(f"📊 Result: {result['success']}")
            
    except Exception as e:
        print(f"❌ Scraping pipeline test failed: {e}")

def check_chat_routing():
    """Check if chat system is configured to use scraped data"""
    print("\n" + "=" * 50)
    print("💬 Chat System Configuration Check")
    print("=" * 50)
    
    try:
        # Check if chat routes exist and are configured
        from routes.chat_routes import chat_bp
        print("✅ Chat routes found")
        
        # Check if they import the right services
        print("🔍 Checking chat service imports...")
        
        # Look for cosmos service usage in chat
        import inspect
        import routes.chat_routes as chat_module
        
        source = inspect.getsource(chat_module)
        
        has_cosmos = 'cosmos' in source.lower()
        has_vector_search = 'search_similar' in source.lower() or 'vector' in source.lower()
        has_embeddings = 'embedding' in source.lower()
        
        print(f"   🗄️ Uses Cosmos DB: {has_cosmos}")
        print(f"   🔍 Uses vector search: {has_vector_search}")
        print(f"   🧠 Uses embeddings: {has_embeddings}")
        
        if not (has_cosmos and has_vector_search):
            print("\n⚠️ WARNING: Chat system may not be using scraped data!")
            print("   💡 Check routes/chat_routes.py for Cosmos DB integration")
        
    except Exception as e:
        print(f"❌ Chat system check failed: {e}")

async def main():
    """Run all diagnostics"""
    print("🚀 Starting Complete AI Assistant Diagnostics")
    print(f"⏰ Time: {datetime.now().isoformat()}")
    
    await diagnose_cosmos_db()
    await test_scraping_and_storage()
    check_chat_routing()
    
    print("\n" + "=" * 50)
    print("🎯 DIAGNOSIS COMPLETE")
    print("=" * 50)
    print("💡 Next Steps:")
    print("   1. If no documents found → Run web scraper on target URL")
    print("   2. If only basic docs found → Use professional scraper")
    print("   3. If chat system not using Cosmos → Update chat routes")
    print("   4. If embeddings not working → Check OpenAI service")

if __name__ == "__main__":
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️ Diagnostic interrupted by user")
    except Exception as e:
        print(f"\n❌ Diagnostic failed: {e}")
        import traceback
        traceback.print_exc()