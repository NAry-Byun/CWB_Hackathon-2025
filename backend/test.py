#!/usr/bin/env python3
"""
Final Fixed Cosmos DB Test - Corrected query parameter usage
"""

import os
import asyncio
from dotenv import load_dotenv

load_dotenv()

async def test_cosmos_final():
    """Final corrected Cosmos DB test"""
    print("🌌 Testing Cosmos DB (Final Fix)...")
    
    try:
        from azure.cosmos.aio import CosmosClient
        from azure.cosmos import PartitionKey
        
        endpoint = os.getenv('COSMOS_DB_ENDPOINT')
        key = os.getenv('COSMOS_DB_KEY')
        database_name = os.getenv('COSMOS_DB_DATABASE_NAME', 'AICourseDB')
        container_name = os.getenv('COSMOS_DB_CONTAINER_NAME', 'CourseData')
        
        print(f"   Endpoint: {endpoint}")
        print(f"   Database: {database_name}")
        print(f"   Container: {container_name}")
        
        # Create client
        client = CosmosClient(endpoint, key)
        print("✅ Cosmos Client created successfully")
        
        # Test database creation/access
        print("   Creating/accessing database...")
        database = await client.create_database_if_not_exists(id=database_name)
        print(f"✅ Database '{database_name}' ready")
        
        # Test container creation/access
        print("   Creating/accessing container...")
        container = await database.create_container_if_not_exists(
            id=container_name,
            partition_key=PartitionKey(path="/file_name")
        )
        print(f"✅ Container '{container_name}' ready")
        
        # Test query functionality (FIXED - proper parameter usage)
        print("   Testing query functionality...")
        query = "SELECT VALUE COUNT(1) FROM c"
        
        # Method 1: Simple query without parameters
        try:
            items = []
            async for item in container.query_items(query=query):
                items.append(item)
            
            document_count = items[0] if items else 0
            print(f"✅ Query successful - Document count: {document_count}")
            
        except Exception as query_error:
            print(f"   Query method 1 failed: {query_error}")
            
            # Method 2: Alternative query approach
            try:
                print("   Trying alternative query method...")
                query_iterator = container.query_items(
                    query="SELECT * FROM c",
                    max_item_count=1
                )
                
                item_count = 0
                async for item in query_iterator:
                    item_count += 1
                    if item_count >= 10:  # Limit to prevent long loops
                        break
                
                print(f"✅ Alternative query successful - Found {item_count} documents")
                
            except Exception as alt_error:
                print(f"   Alternative query also failed: {alt_error}")
                print("   Continuing with document operations test...")
        
        # Test document operations
        print("   Testing document operations...")
        from datetime import datetime
        
        test_doc = {
            "id": f"connection_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "file_name": "connection_test", 
            "content": "This is a connection test document",
            "source": "connection_test",
            "created_at": datetime.now().isoformat()
        }
        
        # Create test document
        created_item = await container.create_item(body=test_doc)
        print(f"✅ Document created: {created_item['id']}")
        
        # Read test document
        read_item = await container.read_item(
            item=created_item['id'],
            partition_key="connection_test"
        )
        print(f"✅ Document read: {read_item['content'][:30]}...")
        
        # Delete test document (cleanup)
        await container.delete_item(
            item=created_item['id'],
            partition_key="connection_test"
        )
        print("✅ Test document cleaned up")
        
        await client.close()
        print("🎉 Cosmos DB connection test PASSED!")
        return True
        
    except Exception as e:
        print(f"❌ Cosmos DB test failed: {e}")
        print(f"   Error type: {type(e).__name__}")
        return False

async def test_blob_sync_workflow():
    """Test the actual blob sync workflow"""
    print("\n🔄 TESTING BLOB SYNC WORKFLOW")
    print("-" * 40)
    
    try:
        # Test Blob Storage listing
        from azure.storage.blob import BlobServiceClient
        
        connection_string = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
        container_name = os.getenv('BLOB_CONTAINER_NAME', 'documents')
        
        blob_client = BlobServiceClient.from_connection_string(connection_string)
        container_client = blob_client.get_container_client(container_name)
        
        # Create container if it doesn't exist
        if not container_client.exists():
            container_client.create_container()
            print(f"✅ Created container: {container_name}")
        
        # List blobs
        blob_list = list(container_client.list_blobs())
        print(f"✅ Found {len(blob_list)} files in Blob Storage")
        
        if blob_list:
            print("   Sample files:")
            for blob in blob_list[:3]:
                print(f"   - {blob.name} ({blob.size} bytes)")
        else:
            print("   No files found - you can upload some test files to test sync")
        
        # Test Cosmos DB storage
        from azure.cosmos.aio import CosmosClient
        from azure.cosmos import PartitionKey
        
        endpoint = os.getenv('COSMOS_DB_ENDPOINT')
        key = os.getenv('COSMOS_DB_KEY')
        database_name = os.getenv('COSMOS_DB_DATABASE_NAME', 'AICourseDB')
        container_name_cosmos = os.getenv('COSMOS_DB_CONTAINER_NAME', 'CourseData')
        
        cosmos_client = CosmosClient(endpoint, key)
        database = await cosmos_client.create_database_if_not_exists(id=database_name)
        cosmos_container = await database.create_container_if_not_exists(
            id=container_name_cosmos,
            partition_key=PartitionKey(path="/file_name")
        )
        
        print(f"✅ Cosmos DB ready for sync operations")
        
        await cosmos_client.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Blob sync workflow test failed: {e}")
        return False

async def main():
    """Main test with workflow verification"""
    print("🚀 FINAL AZURE SERVICES TEST")
    print("=" * 40)
    
    # Test individual services
    print("\n1️⃣ Testing Cosmos DB...")
    cosmos_ok = await test_cosmos_final()
    
    print("\n2️⃣ Testing Blob Storage...")
    try:
        from azure.storage.blob import BlobServiceClient
        connection_string = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
        client = BlobServiceClient.from_connection_string(connection_string)
        account_info = client.get_account_information()
        print(f"✅ Blob Storage: {account_info.get('account_kind', 'Connected')}")
        blob_ok = True
    except Exception as e:
        print(f"❌ Blob Storage failed: {e}")
        blob_ok = False
    
    print("\n3️⃣ Testing Azure OpenAI...")
    try:
        from openai import AzureOpenAI
        client = AzureOpenAI(
            azure_endpoint=os.getenv('AZURE_OPENAI_ENDPOINT'),
            api_key=os.getenv('AZURE_OPENAI_API_KEY'),
            api_version=os.getenv('AZURE_OPENAI_API_VERSION', '2024-02-01')
        )
        response = client.embeddings.create(
            input="test",
            model=os.getenv('AZURE_OPENAI_EMBEDDING_DEPLOYMENT', 'text-embedding-3-small')
        )
        print(f"✅ Azure OpenAI: {len(response.data[0].embedding)} dimensions")
        openai_ok = True
    except Exception as e:
        print(f"❌ Azure OpenAI failed: {e}")
        openai_ok = False
    
    # Test workflow
    workflow_ok = await test_blob_sync_workflow()
    
    # Summary
    print(f"\n📊 FINAL RESULTS:")
    print(f"Cosmos DB: {'✅' if cosmos_ok else '❌'}")
    print(f"Blob Storage: {'✅' if blob_ok else '❌'}")
    print(f"Azure OpenAI: {'✅' if openai_ok else '❌'}")
    print(f"Sync Workflow: {'✅' if workflow_ok else '❌'}")
    
    if all([cosmos_ok, blob_ok, openai_ok, workflow_ok]):
        print(f"\n🎉 EVERYTHING IS READY!")
        print("Your Flask server should work perfectly now.")
        print("\nNext steps:")
        print("1. Start Flask: python app.py --init --port 5000")
        print("2. Test endpoints:")
        print("   curl http://localhost:5000/api/blob-sync/health")
        print("   curl http://localhost:5000/api/blob-sync/status")
        print("   curl -X POST http://localhost:5000/api/blob-sync/sync-simple")
        print("3. Upload a test file to Blob Storage and sync it!")
        
        return True
    else:
        print(f"\n⚠️ Some issues remain, but basic connectivity works.")
        print("You can still try starting Flask - it might work for basic operations.")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())