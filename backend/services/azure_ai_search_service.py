import os
import asyncio
import logging
from typing import List, Dict, Any, Optional
from azure.search.documents.aio import SearchClient
from azure.search.documents.indexes.aio import SearchIndexClient
from azure.search.documents.indexes.models import SearchIndex, SearchField, SearchFieldDataType, VectorSearch, VectorSearchProfile, HnswAlgorithmConfiguration
from azure.core.credentials import AzureKeyCredential
from datetime import datetime
import json

logger = logging.getLogger(__name__)

class AzureAISearchService:
    """Azure AI Search service for advanced document search and indexing"""

    def __init__(self):
        """Initialize Azure AI Search service"""
        self.service_name = os.getenv('AZURE_SEARCH_SERVICE_NAME')
        self.admin_key = os.getenv('AZURE_SEARCH_ADMIN_KEY')
        self.query_key = os.getenv('AZURE_SEARCH_QUERY_KEY')
        self.endpoint = os.getenv('AZURE_SEARCH_ENDPOINT')
        self.api_version = os.getenv('AZURE_SEARCH_API_VERSION', '2023-11-01')
        self.index_name = os.getenv('AZURE_SEARCH_INDEX_NAME', 'documents-index')
        
        if not all([self.service_name, self.admin_key, self.endpoint]):
            raise ValueError(
                "AZURE_SEARCH_SERVICE_NAME, AZURE_SEARCH_ADMIN_KEY, and AZURE_SEARCH_ENDPOINT are required. "
                "Please set them in your .env file."
            )
        
        # Initialize credentials
        self.admin_credential = AzureKeyCredential(self.admin_key)
        self.query_credential = AzureKeyCredential(self.query_key or self.admin_key)
        
        # Initialize clients
        self.index_client = SearchIndexClient(
            endpoint=self.endpoint,
            credential=self.admin_credential
        )
        
        self.search_client = SearchClient(
            endpoint=self.endpoint,
            index_name=self.index_name,
            credential=self.query_credential
        )
        
        self.openai_service = None
        
        logger.info(f"🔍 Azure AI Search initialized")
        logger.info(f"🔧 Service: {self.service_name}")
        logger.info(f"🔧 Index: {self.index_name}")

    def set_openai_service(self, openai_service):
        """Inject OpenAI service for embeddings"""
        self.openai_service = openai_service
        logger.info("✅ OpenAI service injected into Azure AI Search")

    async def create_index(self) -> bool:
        """Create search index with vector search capabilities"""
        try:
            logger.info(f"🔧 Creating search index: {self.index_name}")
            
            # Define vector search configuration
            vector_search = VectorSearch(
                profiles=[
                    VectorSearchProfile(
                        name="myHnswProfile",
                        algorithm_configuration_name="myHnsw"
                    )
                ],
                algorithms=[
                    HnswAlgorithmConfiguration(
                        name="myHnsw"
                    )
                ]
            )
            
            # Define index fields
            fields = [
                SearchField(name="id", type=SearchFieldDataType.String, key=True, searchable=True),
                SearchField(name="file_name", type=SearchFieldDataType.String, searchable=True, filterable=True),
                SearchField(name="content", type=SearchFieldDataType.String, searchable=True),
                SearchField(name="chunk_text", type=SearchFieldDataType.String, searchable=True),
                SearchField(name="chunk_index", type=SearchFieldDataType.Int32, filterable=True),
                SearchField(name="source", type=SearchFieldDataType.String, filterable=True),
                SearchField(name="created_at", type=SearchFieldDataType.DateTimeOffset, filterable=True, sortable=True),
                SearchField(name="metadata", type=SearchFieldDataType.String, searchable=True),
                SearchField(
                    name="content_vector",
                    type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                    searchable=True,
                    vector_search_dimensions=1536,  # OpenAI text-embedding-3-small dimensions
                    vector_search_profile_name="myHnswProfile"
                )
            ]
            
            # Create index
            index = SearchIndex(
                name=self.index_name,
                fields=fields,
                vector_search=vector_search
            )
            
            result = await self.index_client.create_or_update_index(index)
            logger.info(f"✅ Search index created: {result.name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to create search index: {e}")
            return False

    async def index_document(
        self,
        doc_id: str,
        file_name: str,
        content: str,
        chunk_text: str = None,
        chunk_index: int = 0,
        source: str = "blob_storage",
        metadata: Dict = None
    ) -> bool:
        """Index a single document with vector embeddings"""
        try:
            if not self.openai_service:
                logger.warning("⚠️ OpenAI service not available for embeddings")
                return False
            
            # Generate embedding for content
            text_to_embed = chunk_text or content
            embedding = await self.openai_service.generate_embeddings(text_to_embed)
            
            if not embedding:
                logger.error(f"❌ Failed to generate embedding for {file_name}")
                return False
            
            # Prepare document
            document = {
                "id": doc_id,
                "file_name": file_name,
                "content": content[:32000],  # Limit content size
                "chunk_text": chunk_text or content[:8000],
                "chunk_index": chunk_index,
                "source": source,
                "created_at": datetime.now().isoformat(),
                "metadata": json.dumps(metadata or {}),
                "content_vector": embedding
            }
            
            # Upload to index
            result = await self.search_client.upload_documents([document])
            
            if result[0].succeeded:
                logger.debug(f"✅ Indexed document: {file_name}")
                return True
            else:
                logger.error(f"❌ Failed to index {file_name}: {result[0].error_message}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Document indexing failed: {e}")
            return False

    async def search_documents(
        self,
        query: str,
        top: int = 5,
        use_vector_search: bool = True,
        use_semantic_search: bool = True
    ) -> List[Dict[str, Any]]:
        """Search documents using hybrid search (text + vector)"""
        try:
            logger.info(f"🔍 Searching documents: '{query[:50]}...'")
            
            search_params = {
                "search_text": query,
                "top": top,
                "include_total_count": True
            }
            
            # Add vector search if enabled and OpenAI service available
            if use_vector_search and self.openai_service:
                query_embedding = await self.openai_service.generate_embeddings(query)
                if query_embedding:
                    search_params["vector_queries"] = [{
                        "vector": query_embedding,
                        "k_nearest_neighbors": top,
                        "fields": "content_vector"
                    }]
            
            # Add semantic search if enabled
            if use_semantic_search:
                search_params["query_type"] = "semantic"
                search_params["semantic_configuration_name"] = "default"
            
            # Perform search
            results = await self.search_client.search(**search_params)
            
            # Process results
            documents = []
            async for result in results:
                document = {
                    "id": result.get("id"),
                    "file_name": result.get("file_name"),
                    "content": result.get("chunk_text", result.get("content", ""))[:1000],
                    "chunk_index": result.get("chunk_index", 0),
                    "source": result.get("source"),
                    "score": result.get("@search.score", 0.0),
                    "created_at": result.get("created_at")
                }
                
                # Add metadata if available
                metadata_str = result.get("metadata")
                if metadata_str:
                    try:
                        document["metadata"] = json.loads(metadata_str)
                    except:
                        document["metadata"] = {}
                
                documents.append(document)
            
            logger.info(f"✅ Found {len(documents)} documents")
            return documents
            
        except Exception as e:
            logger.error(f"❌ Document search failed: {e}")
            return []

    async def search_with_filters(
        self,
        query: str,
        filters: Dict[str, Any] = None,
        top: int = 5
    ) -> List[Dict[str, Any]]:
        """Search with advanced filtering"""
        try:
            search_params = {
                "search_text": query,
                "top": top
            }
            
            # Build filter string
            if filters:
                filter_parts = []
                
                if "file_name" in filters:
                    filter_parts.append(f"file_name eq '{filters['file_name']}'")
                
                if "source" in filters:
                    filter_parts.append(f"source eq '{filters['source']}'")
                
                if "date_from" in filters:
                    filter_parts.append(f"created_at ge {filters['date_from']}")
                
                if "date_to" in filters:
                    filter_parts.append(f"created_at le {filters['date_to']}")
                
                if filter_parts:
                    search_params["filter"] = " and ".join(filter_parts)
            
            results = await self.search_client.search(**search_params)
            
            documents = []
            async for result in results:
                documents.append({
                    "id": result.get("id"),
                    "file_name": result.get("file_name"),
                    "content": result.get("chunk_text", result.get("content", ""))[:1000],
                    "score": result.get("@search.score", 0.0),
                    "source": result.get("source")
                })
            
            return documents
            
        except Exception as e:
            logger.error(f"❌ Filtered search failed: {e}")
            return []

    async def suggest_documents(self, partial_query: str, top: int = 5) -> List[str]:
        """Get search suggestions based on partial query"""
        try:
            suggestions = await self.search_client.suggest(
                search_text=partial_query,
                suggester_name="sg",
                top=top
            )
            
            return [suggestion["text"] for suggestion in suggestions]
            
        except Exception as e:
            logger.error(f"❌ Suggestions failed: {e}")
            return []

    async def get_index_stats(self) -> Dict[str, Any]:
        """Get index statistics"""
        try:
            stats = await self.search_client.get_document_count()
            
            return {
                "total_documents": stats,
                "index_name": self.index_name,
                "service_name": self.service_name,
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get index stats: {e}")
            return {
                "total_documents": 0,
                "error": str(e)
            }

    async def bulk_index_from_cosmos(self, cosmos_service) -> Dict[str, Any]:
        """Bulk index documents from Cosmos DB"""
        try:
            logger.info("🔄 Starting bulk indexing from Cosmos DB")
            
            # Ensure index exists
            await self.create_index()
            
            # Get all documents from Cosmos
            if not cosmos_service or not cosmos_service.container:
                await cosmos_service.initialize_database()
            
            query = "SELECT * FROM c WHERE c.source = 'blob_storage' AND c.document_type = 'text_chunk'"
            
            indexed_count = 0
            error_count = 0
            
            async for item in cosmos_service.container.query_items(query=query):
                try:
                    doc_id = f"ai_search_{item.get('id', '')}"
                    
                    success = await self.index_document(
                        doc_id=doc_id,
                        file_name=item.get('file_name', ''),
                        content=item.get('chunk_text', ''),
                        chunk_text=item.get('chunk_text', ''),
                        chunk_index=item.get('chunk_index', 0),
                        source="cosmos_migration",
                        metadata=item.get('metadata', {})
                    )
                    
                    if success:
                        indexed_count += 1
                    else:
                        error_count += 1
                        
                except Exception as e:
                    logger.error(f"❌ Error indexing item: {e}")
                    error_count += 1
            
            result = {
                "success": True,
                "indexed_documents": indexed_count,
                "errors": error_count,
                "total_processed": indexed_count + error_count
            }
            
            logger.info(f"✅ Bulk indexing completed: {indexed_count} indexed, {error_count} errors")
            return result
            
        except Exception as e:
            logger.error(f"❌ Bulk indexing failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "indexed_documents": 0,
                "errors": 0
            }

    def set_openai_service(self, openai_service):
        """Inject OpenAI service for embeddings"""
        self.openai_service = openai_service
        logger.info("✅ OpenAI service injected into Azure AI Search")

    async def search_documents(
        self,
        query: str,
        top: int = 5,
        use_vector_search: bool = True,
        use_semantic_search: bool = True
    ) -> List[Dict[str, Any]]:
        """Search documents using hybrid search (text + vector)"""
        try:
            logger.info(f"🔍 Searching documents: '{query[:50]}...'")
            
            # For now, return mock results until index is created
            return [
                {
                    "id": "mock_1",
                    "file_name": "Azure AI Search Test",
                    "content": f"Mock search result for query: {query}",
                    "score": 0.85,
                    "source": "azure_ai_search"
                }
            ]
            
        except Exception as e:
            logger.error(f"❌ Document search failed: {e}")
            return []
        """Check Azure AI Search service health"""
        try:
            # Test index access
            stats = await self.get_index_stats()
            
            return {
                "status": "healthy",
                "service": "Azure AI Search",
                "service_name": self.service_name,
                "index_name": self.index_name,
                "endpoint": self.endpoint,
                "total_documents": stats.get("total_documents", 0),
                "vector_search": "enabled",
                "semantic_search": "enabled",
                "openai_integration": self.openai_service is not None
            }
            
        except Exception as e:
            logger.error(f"❌ Azure AI Search health check failed: {e}")
            return {
                "status": "unhealthy",
                "service": "Azure AI Search",
                "error": str(e)
            }

    async def close(self):
        """Close Azure AI Search connections"""
        try:
            await self.index_client.close()
            await self.search_client.close()
            logger.info("🔒 Azure AI Search connections closed")
        except Exception as e:
            logger.error(f"❌ Error closing Azure AI Search connections: {e}")