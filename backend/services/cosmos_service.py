# services/cosmos_service.py - Production Ready Cosmos DB Service with FIXED Vector Search

import os
import asyncio
import logging
from typing import List, Dict, Any, Optional
from azure.cosmos.aio import CosmosClient
from azure.cosmos import PartitionKey
from datetime import datetime
import json
import numpy as np

logger = logging.getLogger(__name__)

class CosmosVectorService:
    """Production-ready Azure Cosmos DB service with proper vector search"""

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
            logger.info(f"✅ Stored blob document: {filename} ({len(content)} chars)")
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
            logger.debug(f"✅ Stored chunk {chunk_index} for {file_name} ({len(chunk_text)} chars)")
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
            query = "SELECT VALUE COUNT(1) FROM c WHERE c.file_name = @filename AND c.source = 'blob_storage'"
            parameters = [{"name": "@filename", "value": filename}]
            
            items = []
            async for item in self.container.query_items(
                query=query,
                parameters=parameters
            ):
                items.append(item)
            
            count = items[0] if items else 0
            exists = count > 0
            
            logger.debug(f"File exists check for {filename}: {exists} (count: {count})")
            return exists
            
        except Exception as e:
            logger.error(f"❌ Error checking file existence for {filename}: {e}")
            return False

    async def search_similar_chunks(
        self,
        query_embedding: List[float],
        limit: int = 5,
        similarity_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """Search for similar chunks using vector similarity (FIXED)"""
        try:
            if not self.container:
                await self.initialize_database()
                
            logger.info(f"🔍 Searching for similar chunks (limit: {limit}, threshold: {similarity_threshold})")
            
            # Get all chunks with embeddings
            query = "SELECT c.id, c.file_name, c.chunk_text, c.chunk_index, c.embedding, c.text_length FROM c WHERE c.source = 'blob_storage' AND c.document_type = 'text_chunk' AND IS_DEFINED(c.embedding)"
            
            all_chunks = []
            async for item in self.container.query_items(query=query):
                all_chunks.append(item)
            
            if not all_chunks:
                logger.warning("⚠️ No chunks with embeddings found in database")
                return []
            
            logger.info(f"📊 Found {len(all_chunks)} chunks to compare")
            
            # Calculate similarities
            similarities = []
            for chunk in all_chunks:
                embedding = chunk.get('embedding')
                if embedding and len(embedding) > 0:
                    # Calculate cosine similarity
                    similarity = self._calculate_cosine_similarity(query_embedding, embedding)
                    
                    if similarity >= similarity_threshold:
                        similarities.append({
                            "id": chunk.get("id"),
                            "file_name": chunk.get("file_name"),
                            "content": chunk.get("chunk_text", ""),
                            "chunk_text": chunk.get("chunk_text", ""),
                            "chunk_index": chunk.get("chunk_index", 0),
                            "similarity": float(similarity),
                            "text_length": chunk.get("text_length", 0)
                        })
            
            # Sort by similarity descending and limit results
            similarities.sort(key=lambda x: x['similarity'], reverse=True)
            results = similarities[:limit]
            
            logger.info(f"✅ Found {len(results)} similar chunks above threshold {similarity_threshold}")
            
            # Log top results for debugging
            for i, result in enumerate(results[:3]):
                logger.info(f"📄 Result {i+1}: {result['file_name']} (similarity: {result['similarity']:.3f})")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Vector search failed: {e}")
            return []

    def _calculate_cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        try:
            # Convert to numpy arrays for efficient calculation
            a = np.array(vec1)
            b = np.array(vec2)
            
            # Calculate cosine similarity
            dot_product = np.dot(a, b)
            norm_a = np.linalg.norm(a)
            norm_b = np.linalg.norm(b)
            
            if norm_a == 0 or norm_b == 0:
                return 0.0
            
            similarity = dot_product / (norm_a * norm_b)
            return float(similarity)
            
        except Exception as e:
            logger.error(f"❌ Similarity calculation failed: {e}")
            return 0.0

    async def search_documents_by_query(
        self,
        user_query: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Search documents using user query (generates embedding and searches)"""
        try:
            if not self.openai_service:
                logger.warning("⚠️ OpenAI service not available for query embedding")
                return []
            
            logger.info(f"🔍 Searching documents for query: '{user_query[:50]}...'")
            
            # Generate embedding for user query
            query_embedding = await self.openai_service.generate_embeddings(user_query)
            
            if not query_embedding:
                logger.error("❌ Failed to generate embedding for user query")
                return []
            
            # Search for similar chunks
            results = await self.search_similar_chunks(query_embedding, limit=limit)
            
            # Format results for chat service
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "id": result["id"],
                    "file_name": result["file_name"],
                    "content": result["content"],
                    "similarity": result["similarity"],
                    "chunk_index": result["chunk_index"]
                })
            
            logger.info(f"✅ Document search completed: {len(formatted_results)} results")
            return formatted_results
            
        except Exception as e:
            logger.error(f"❌ Document search failed: {e}")
            return []

    async def get_blob_sync_stats(self) -> Dict[str, Any]:
        """Get statistics about synced blob documents"""
        try:
            if not self.container:
                await self.initialize_database()
            
            # Count blob documents and chunks separately
            try:
                # Count blob documents
                doc_query = "SELECT VALUE COUNT(1) FROM c WHERE c.source = 'blob_storage' AND c.document_type = 'blob_document'"
                doc_count = 0
                async for item in self.container.query_items(query=doc_query):
                    doc_count = item
                    break
                
                # Count blob chunks
                chunk_query = "SELECT VALUE COUNT(1) FROM c WHERE c.source = 'blob_storage' AND c.document_type = 'text_chunk'"
                chunk_count = 0
                async for item in self.container.query_items(query=chunk_query):
                    chunk_count = item
                    break
                
            except Exception as query_error:
                logger.warning(f"Direct count failed, using fallback: {query_error}")
                # Fallback: manual counting
                doc_count = 0
                chunk_count = 0
                
                async for item in self.container.query_items(query="SELECT * FROM c WHERE c.source = 'blob_storage'"):
                    if item.get('document_type') == 'blob_document':
                        doc_count += 1
                    elif item.get('document_type') == 'text_chunk':
                        chunk_count += 1
            
            return {
                "total_blob_documents": doc_count,
                "total_blob_chunks": chunk_count,
                "sync_status": "active",
                "search_enabled": True,
                "last_check": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting blob sync stats: {e}")
            return {
                "total_blob_documents": 0,
                "total_blob_chunks": 0,
                "sync_status": "error",
                "search_enabled": False,
                "error": str(e),
                "last_check": datetime.now().isoformat()
            }

    async def list_blob_files(self) -> List[Dict[str, Any]]:
        """List all files synced from Blob Storage"""
        try:
            if not self.container:
                await self.initialize_database()
            
            query = "SELECT DISTINCT c.file_name, c.created_at, c.metadata FROM c WHERE c.source = 'blob_storage' AND c.document_type = 'blob_document'"
            
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

    async def health_check(self) -> Dict[str, Any]:
        """Check Cosmos DB health with proper error handling"""
        try:
            if not self.container:
                await self.initialize_database()
            
            # Get blob sync stats
            blob_stats = await self.get_blob_sync_stats()
            
            return {
                "status": "healthy",
                "service": "Cosmos DB with Blob Storage",
                "database": self.database_name,
                "container": self.container_name,
                "connectivity": "successful",
                "blob_integration": "enabled",
                "vector_search": "enabled",
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
                "vector_search_enabled": True,
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