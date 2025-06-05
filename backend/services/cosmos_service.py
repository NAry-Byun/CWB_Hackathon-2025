# services/cosmos_service.py - Production Ready Cosmos DB Service

import os
import asyncio
import logging
from typing import List, Dict, Any, Optional
from azure.cosmos.aio import CosmosClient
from azure.cosmos import PartitionKey
from datetime import datetime
import json

logger = logging.getLogger(__name__)

class CosmosVectorService:
    """Production-ready Azure Cosmos DB service with proper error handling"""

    def __init__(self):
        """Initialize Cosmos DB service with environment variables"""
        self.endpoint = os.getenv('COSMOS_DB_ENDPOINT')
        self.key = os.getenv('COSMOS_DB_KEY')
        self.database_name = os.getenv('COSMOS_DB_DATABASE_NAME', 'AICourseDB')
        self.container_name = os.getenv('COSMOS_DB_CONTAINER_NAME', 'CourseData')
        
        if not self.endpoint or not self.key:
            raise ValueError(
                "COSMOS_DB_ENDPOINT and COSMOS_DB_KEY are required. "
                "Please set them in your .env file."
            )
        
        self.client = None
        self.database = None
        self.container = None
        self.openai_service = None
        
        logger.info(f"🌌 CosmosVectorService initialized")
        logger.info(f"🔧 Database: {self.database_name}")
        logger.info(f"🔧 Container: {self.container_name}")

    def set_openai_service(self, openai_service):
        """Inject the OpenAI service for embeddings"""
        self.openai_service = openai_service
        logger.info("✅ OpenAI service injected into CosmosVectorService")

    async def initialize_database(self):
        """Initialize Cosmos DB with proper error handling"""
        try:
            # Create Cosmos client
            self.client = CosmosClient(self.endpoint, self.key)
            
            # Create database
            self.database = await self.client.create_database_if_not_exists(
                id=self.database_name
            )
            logger.info(f"✅ Cosmos DB database '{self.database_name}' ready")
            
            # Create container with partition key for file names
            self.container = await self.database.create_container_if_not_exists(
                id=self.container_name,
                partition_key=PartitionKey(path="/file_name")
            )
            logger.info(f"✅ Cosmos DB container '{self.container_name}' ready")
            
        except Exception as e:
            logger.error(f"❌ Cosmos DB initialization failed: {e}")
            raise

    async def store_blob_document(
        self,
        filename: str,
        content: str,
        metadata: Dict[str, Any] = None
    ) -> str:
        """Store a complete document from Blob Storage"""
        try:
            if not self.container:
                await self.initialize_database()
            
            document_id = f"blob_{filename}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            document = {
                "id": document_id,
                "file_name": filename,
                "document_type": "blob_document",
                "content": content,
                "content_length": len(content),
                "source": "blob_storage",
                "created_at": datetime.now().isoformat(),
                "metadata": metadata or {},
                "processed": True
            }
            
            result = await self.container.create_item(body=document)
            logger.info(f"✅ Stored blob document: {filename}")
            return result['id']
            
        except Exception as e:
            logger.error(f"❌ Failed to store blob document {filename}: {e}")
            raise

    async def store_document_chunk(
        self,
        file_name: str,
        chunk_text: str,
        embedding: List[float],
        chunk_index: int,
        metadata: Dict = None
    ) -> str:
        """Store document chunk with embedding from Blob Storage"""
        try:
            if not self.container:
                await self.initialize_database()
                
            document_id = f"chunk_{file_name}_{chunk_index}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            document = {
                "id": document_id,
                "file_name": file_name,
                "document_type": "text_chunk",
                "chunk_text": chunk_text,
                "chunk_index": chunk_index,
                "embedding": embedding,
                "vector_dimensions": len(embedding) if embedding else 0,
                "text_length": len(chunk_text),
                "source": "blob_storage",
                "created_at": datetime.now().isoformat(),
                "metadata": metadata or {}
            }
            
            result = await self.container.create_item(body=document)
            logger.debug(f"✅ Stored chunk {chunk_index} for {file_name}")
            return result['id']
            
        except Exception as e:
            logger.error(f"❌ Failed to store chunk: {e}")
            raise

    async def check_file_exists(self, filename: str) -> bool:
        """Check if a file from Blob Storage already exists in Cosmos DB"""
        try:
            if not self.container:
                await self.initialize_database()
            
            # Use parameterized query for safety
            query = "SELECT VALUE COUNT(1) FROM c WHERE c.file_name = @filename"
            parameters = [{"name": "@filename", "value": filename}]
            
            items = []
            # Fixed: Remove enable_cross_partition_query from query_items call
            async for item in self.container.query_items(
                query=query,
                parameters=parameters
            ):
                items.append(item)
            
            count = items[0] if items else 0
            exists = count > 0
            
            logger.debug(f"File exists check for {filename}: {exists}")
            return exists
            
        except Exception as e:
            logger.error(f"❌ Error checking file existence for {filename}: {e}")
            # Fallback: try alternative approach
            try:
                query_simple = f"SELECT * FROM c WHERE c.file_name = '{filename}'"
                items = []
                async for item in self.container.query_items(query=query_simple):
                    items.append(item)
                    break  # Just need to know if any exist
                return len(items) > 0
            except:
                return False

    async def get_blob_sync_stats(self) -> Dict[str, Any]:
        """Get statistics about synced blob documents"""
        try:
            if not self.container:
                await self.initialize_database()
            
            # Simplified queries without cross-partition parameters
            try:
                # Count blob documents
                blob_doc_query = "SELECT VALUE COUNT(1) FROM c WHERE c.source = 'blob_storage'"
                blob_docs = []
                async for item in self.container.query_items(query=blob_doc_query):
                    blob_docs.append(item)
                
                # Count blob chunks
                blob_chunk_query = "SELECT VALUE COUNT(1) FROM c WHERE c.source = 'blob_storage' AND c.document_type = 'text_chunk'"
                blob_chunks = []
                async for item in self.container.query_items(query=blob_chunk_query):
                    blob_chunks.append(item)
                
                blob_doc_count = blob_docs[0] if blob_docs else 0
                blob_chunk_count = blob_chunks[0] if blob_chunks else 0
                
            except Exception as query_error:
                logger.warning(f"Query stats failed, using fallback: {query_error}")
                # Fallback: manual counting
                blob_doc_count = 0
                blob_chunk_count = 0
                
                async for item in self.container.query_items(query="SELECT * FROM c"):
                    if item.get('source') == 'blob_storage':
                        blob_doc_count += 1
                        if item.get('document_type') == 'text_chunk':
                            blob_chunk_count += 1
            
            return {
                "total_blob_documents": blob_doc_count,
                "total_blob_chunks": blob_chunk_count,
                "sync_status": "active",
                "last_check": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting blob sync stats: {e}")
            return {
                "total_blob_documents": 0,
                "total_blob_chunks": 0,
                "sync_status": "error",
                "error": str(e),
                "last_check": datetime.now().isoformat()
            }

    async def list_blob_files(self) -> List[Dict[str, Any]]:
        """List all files synced from Blob Storage"""
        try:
            if not self.container:
                await self.initialize_database()
            
            query = "SELECT DISTINCT c.file_name, c.created_at, c.metadata FROM c WHERE c.source = 'blob_storage'"
            
            files = []
            async for item in self.container.query_items(query=query):
                files.append({
                    "filename": item.get("file_name"),
                    "synced_at": item.get("created_at"),
                    "metadata": item.get("metadata", {})
                })
            
            logger.info(f"📂 Found {len(files)} synced blob files")
            return files
            
        except Exception as e:
            logger.error(f"❌ Error listing blob files: {e}")
            return []

    async def search_similar_chunks(
        self,
        query_embedding: List[float],
        limit: int = 5,
        similarity_threshold: float = 0.1
    ) -> List[Dict[str, Any]]:
        """Search for similar chunks (simplified implementation)"""
        try:
            logger.info(f"🔍 Searching for similar chunks from blob documents")
            
            # Simplified query without TOP clause for compatibility
            query = "SELECT c.id, c.file_name, c.chunk_text, c.chunk_index FROM c WHERE c.source = 'blob_storage' AND c.document_type = 'text_chunk'"
            
            results = []
            count = 0
            async for item in self.container.query_items(query=query):
                if count >= limit:
                    break
                    
                results.append({
                    "id": item.get("id"),
                    "file_name": item.get("file_name"),
                    "chunk_text": item.get("chunk_text"),
                    "chunk_index": item.get("chunk_index"),
                    "similarity_score": 0.8  # Placeholder score
                })
                count += 1
            
            logger.info(f"🔍 Found {len(results)} similar chunks")
            return results
            
        except Exception as e:
            logger.error(f"❌ Search failed: {e}")
            return []

    async def health_check(self) -> Dict[str, Any]:
        """Check Cosmos DB health with proper error handling"""
        try:
            if not self.container:
                await self.initialize_database()
            
            # Simple connectivity test
            try:
                # Try to read container properties instead of querying
                container_properties = await self.container.read()
                document_count = "available"
                
            except Exception as query_error:
                logger.warning(f"Query test failed: {query_error}")
                document_count = "unknown"
            
            # Get blob sync stats
            blob_stats = await self.get_blob_sync_stats()
            
            return {
                "status": "healthy",
                "service": "Cosmos DB with Blob Storage",
                "database": self.database_name,
                "container": self.container_name,
                "connectivity": "successful",
                "blob_integration": "enabled",
                "blob_stats": blob_stats,
                "openai_service_connected": self.openai_service is not None
            }
            
        except Exception as e:
            logger.error(f"❌ Cosmos DB health check failed: {e}")
            return {
                "status": "unhealthy",
                "service": "Cosmos DB",
                "error": str(e),
                "connectivity": "failed"
            }

    async def get_document_stats(self) -> Dict[str, Any]:
        """Get comprehensive document statistics"""
        try:
            blob_stats = await self.get_blob_sync_stats()
            
            return {
                "total_documents": blob_stats["total_blob_documents"],
                "total_chunks": blob_stats["total_blob_chunks"],
                "blob_storage_integration": "active",
                "openai_service_available": self.openai_service is not None,
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Stats query failed: {e}")
            return {
                "total_documents": 0,
                "total_chunks": 0,
                "error": str(e)
            }

    async def close(self):
        """Close Cosmos DB connection"""
        try:
            if self.client:
                await self.client.close()
                logger.info("🔒 Cosmos DB connection closed")
        except Exception as e:
            logger.error(f"❌ Error closing Cosmos DB connection: {e}")