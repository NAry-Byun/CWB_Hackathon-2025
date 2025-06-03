# services/cosmos_service.py - Complete Cosmos DB Vector Service with Storage Integration

import os
import asyncio
import logging
from typing import List, Dict, Any, Optional
from azure.cosmos.aio import CosmosClient
from azure.cosmos.partition_key import PartitionKey
from azure.storage.blob import BlobServiceClient
import openai

logger = logging.getLogger(__name__)

class CosmosVectorService:
    """Complete Azure Cosmos DB Vector Service with Storage Integration"""

    def __init__(self):
        """Initialize Cosmos DB service with environment variables"""
        self.endpoint = os.getenv('COSMOS_DB_ENDPOINT')
        self.key = os.getenv('COSMOS_DB_KEY')
        self.database_name = os.getenv('COSMOS_DB_DATABASE', 'AICourseDB')
        self.container_name = os.getenv('COSMOS_DB_CONTAINER', 'CourseData')
        
        if not self.endpoint or not self.key:
            raise ValueError(
                "COSMOS_DB_ENDPOINT and COSMOS_DB_KEY are required. "
                "Please set them in your .env file."
            )
        
        self.client = None
        self.database = None
        self.container = None
        
        # OpenAI setup for embeddings
        openai.api_key = os.getenv('AZURE_OPENAI_API_KEY')
        openai.api_base = os.getenv('AZURE_OPENAI_ENDPOINT')
        openai.api_type = "azure"
        openai.api_version = "2023-12-01-preview"
        
        logger.info(f"🌌 CosmosVectorService initialized")
        logger.info(f"🔧 Database: {self.database_name}")
        logger.info(f"🔧 Container: {self.container_name}")

    async def initialize_database(self):
        """Initialize Cosmos DB with proper vector configuration"""
        try:
            # Create Cosmos client
            self.client = CosmosClient(self.endpoint, self.key)
            
            # Create database
            self.database = await self.client.create_database_if_not_exists(
                id=self.database_name
            )
            logger.info(f"✅ Cosmos DB database '{self.database_name}' ready")
            
            # Define vector policy for embeddings
            vector_policy = {
                "vectorEmbeddings": [
                    {
                        "path": "/embedding",
                        "dataType": "float32",
                        "distanceFunction": "cosine",
                        "dimensions": 1536  # Standard for text-embedding-ada-002
                    }
                ]
            }
            
            # Define indexing policy with vector index
            indexing_policy = {
                "vectorIndexes": [
                    {
                        "path": "/embedding",
                        "type": "quantizedFlat"  # Efficient for most use cases
                    }
                ]
            }
            
            # Create container with vector support
            self.container = await self.database.create_container_if_not_exists(
                id=self.container_name,
                partition_key=PartitionKey(path="/file_name"),
                vector_embedding_policy=vector_policy,
                indexing_policy=indexing_policy
            )
            logger.info(f"✅ Cosmos DB container '{self.container_name}' ready with vector support")
            
        except Exception as e:
            logger.error(f"❌ Cosmos DB initialization failed: {e}")
            raise

    async def process_storage_files(self):
        """Simple method to process files from Azure Storage and store in Cosmos DB"""
        try:
            # Get storage connection
            connection_string = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
            container_name = os.getenv('AZURE_STORAGE_CONTAINER_NAME', 'rahul')
            
            if not connection_string:
                logger.warning("No storage connection string found - skipping storage processing")
                return {
                    'success': False,
                    'error': 'AZURE_STORAGE_CONNECTION_STRING not set'
                }
            
            blob_service = BlobServiceClient.from_connection_string(connection_string)
            container_client = blob_service.get_container_client(container_name)
            
            logger.info(f"🔍 Processing files from Azure Storage container: {container_name}")
            
            processed_files = []
            failed_files = []
            
            # List and process each file
            for blob in container_client.list_blobs():
                file_name = blob.name
                logger.info(f"📄 Processing: {file_name}")
                
                try:
                    # Skip image files
                    if any(file_name.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.bmp']):
                        logger.info(f"⏭️ Skipping {file_name} (image file)")
                        continue
                    
                    # Download file
                    blob_client = container_client.get_blob_client(file_name)
                    file_content = blob_client.download_blob().readall()
                    
                    # Extract text (simple version)
                    text_content = self._extract_simple_text(file_content, file_name)
                    
                    if text_content and len(text_content.strip()) > 10:
                        # Create embedding
                        embedding = await self._create_embedding(text_content[:2000])  # First 2000 chars for embedding
                        
                        # Store in Cosmos DB
                        await self.store_document_chunk(
                            file_name=file_name,
                            chunk_text=text_content[:1000],  # First 1000 chars as summary
                            embedding=embedding,
                            chunk_index=0,
                            metadata={
                                'source': 'azure_storage', 
                                'full_content': text_content[:5000],  # Store more content in metadata
                                'file_size': len(file_content),
                                'processed_at': '2025-06-03T12:00:00Z'
                            }
                        )
                        
                        processed_files.append(file_name)
                        logger.info(f"✅ Stored {file_name} in Cosmos DB")
                    else:
                        logger.warning(f"⚠️ No text content found in {file_name}")
                        failed_files.append(file_name)
                        
                except Exception as e:
                    logger.error(f"❌ Failed to process {file_name}: {e}")
                    failed_files.append(file_name)
            
            return {
                'success': True,
                'processed_files': processed_files,
                'failed_files': failed_files,
                'total_processed': len(processed_files),
                'container': container_name
            }
            
        except Exception as e:
            logger.error(f"❌ Storage processing failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _extract_simple_text(self, file_content: bytes, file_name: str) -> str:
        """Simple text extraction"""
        try:
            if file_name.lower().endswith(('.txt', '.rtf')):
                return file_content.decode('utf-8', errors='ignore')
            elif file_name.lower().endswith(('.doc', '.docx')):
                # Try to extract basic text from Word documents
                try:
                    # First try to decode as plain text (works for some .doc files)
                    text = file_content.decode('utf-8', errors='ignore')
                    # Clean up control characters
                    import re
                    text = re.sub(r'[\x00-\x1f\x7f-\x9f]', ' ', text)
                    return text
                except:
                    return ""
            return ""
        except Exception as e:
            logger.error(f"Text extraction error for {file_name}: {e}")
            return ""
    
    async def _create_embedding(self, text: str) -> List[float]:
        """Create embedding using Azure OpenAI"""
        try:
            if not text.strip():
                return [0.0] * 1536
                
            response = await openai.Embedding.acreate(
                engine="text-embedding-ada-002",
                input=text
            )
            return response['data'][0]['embedding']
            
        except Exception as e:
            logger.error(f"❌ Failed to create embedding: {e}")
            # Return dummy embedding as fallback
            return [0.1] * 1536

    async def store_document_chunk(
        self,
        file_name: str,
        chunk_text: str,
        embedding: List[float],
        chunk_index: int,
        metadata: Dict = None
    ) -> str:
        """
        Store document chunk with embedding in Cosmos DB
        
        Args:
            file_name: Name of the source file
            chunk_text: Text content of the chunk
            embedding: Vector embedding for the chunk
            chunk_index: Index of the chunk in the document
            metadata: Additional metadata
            
        Returns:
            Document ID of the stored chunk
        """
        try:
            document = {
                "id": f"{file_name}_{chunk_index}",
                "file_name": file_name,
                "chunk_text": chunk_text,
                "chunk_index": chunk_index,
                "embedding": embedding,
                "metadata": metadata or {},
                "created_at": "2025-06-03T12:00:00Z",
                "document_type": "text_chunk",
                "vector_dimensions": len(embedding)
            }
            
            result = await self.container.create_item(body=document)
            logger.info(f"✅ Stored chunk {chunk_index} for {file_name}")
            return result['id']
            
        except Exception as e:
            logger.error(f"❌ Failed to store chunk: {e}")
            raise

    async def search_similar_chunks(
        self,
        query_embedding: List[float],
        limit: int = 5,
        similarity_threshold: float = 0.3
    ) -> List[Dict[str, Any]]:
        """
        Search for similar chunks using VectorDistance function
        
        Args:
            query_embedding: Vector embedding of the search query
            limit: Maximum number of results to return
            similarity_threshold: Minimum similarity score
            
        Returns:
            List of similar document chunks with similarity scores
        """
        try:
            if not query_embedding or len(query_embedding) == 0:
                logger.warning("⚠️ Empty query embedding provided")
                return []

            # Use VectorDistance with proper syntax for Cosmos DB
            query = f"""
            SELECT TOP {limit}
                c.file_name,
                c.chunk_text,
                c.chunk_index,
                c.metadata,
                c.created_at,
                VectorDistance(c.embedding, @embedding) AS similarity
            FROM c
            WHERE VectorDistance(c.embedding, @embedding) > {similarity_threshold}
            ORDER BY VectorDistance(c.embedding, @embedding)
            """
            
            # Parameters for the query
            parameters = [{"name": "@embedding", "value": query_embedding}]
            
            logger.info(f"🔍 Searching for similar chunks (threshold: {similarity_threshold})")
            
            # Execute query
            results = []
            query_iterable = self.container.query_items(
                query=query,
                parameters=parameters
            )
            
            async for item in query_iterable:
                results.append(item)
            
            logger.info(f"✅ Found {len(results)} similar chunks")
            
            # Log top results for debugging
            for i, result in enumerate(results[:3]):
                file_name = result.get("file_name", "unknown")
                similarity = result.get("similarity", 0.0)
                logger.info(f"  {i+1}. {file_name} (similarity: {similarity:.3f})")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Vector search failed: {e}")
            return []

    async def get_all_documents(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get all documents in the container (for debugging/admin)
        
        Args:
            limit: Maximum number of documents to return
            
        Returns:
            List of all documents
        """
        try:
            query = f"SELECT TOP {limit} * FROM c"
            
            results = []
            query_iterable = self.container.query_items(query=query)
            
            async for item in query_iterable:
                results.append(item)
            
            logger.info(f"📋 Retrieved {len(results)} documents")
            return results
            
        except Exception as e:
            logger.error(f"❌ Failed to get documents: {e}")
            return []

    async def delete_document(self, document_id: str, partition_key: str) -> bool:
        """
        Delete a document from Cosmos DB
        
        Args:
            document_id: ID of the document to delete
            partition_key: Partition key value
            
        Returns:
            True if successful, False otherwise
        """
        try:
            await self.container.delete_item(
                item=document_id,
                partition_key=partition_key
            )
            logger.info(f"🗑️ Deleted document: {document_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to delete document {document_id}: {e}")
            return False

    async def health_check(self) -> Dict[str, Any]:
        """
        Check Cosmos DB health and connectivity
        
        Returns:
            Dict with health status and service information
        """
        try:
            if not self.container:
                return {
                    "status": "not_initialized",
                    "error": "Container not initialized"
                }
            
            # Simple query to test connectivity
            query = "SELECT TOP 1 c.id FROM c"
            query_iterable = self.container.query_items(query=query)
            
            count = 0
            async for _ in query_iterable:
                count += 1
                break  # Just check if we can query
            
            return {
                "status": "healthy",
                "service": "Cosmos DB",
                "database": self.database_name,
                "container": self.container_name,
                "can_query": True,
                "connectivity": "successful"
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
        """
        Get statistics about documents in the container
        
        Returns:
            Dict with document statistics
        """
        try:
            # Count total documents
            count_query = "SELECT VALUE COUNT(1) FROM c"
            count_iterable = self.container.query_items(query=count_query)
            
            total_count = 0
            async for count in count_iterable:
                total_count = count
                break
            
            # Count by file type
            file_count_query = "SELECT c.file_name, COUNT(1) as chunk_count FROM c GROUP BY c.file_name"
            file_iterable = self.container.query_items(query=file_count_query)
            
            files = []
            async for file_info in file_iterable:
                files.append(file_info)
            
            return {
                "total_chunks": total_count,
                "unique_files": len(files),
                "files": files[:10],  # Limit to first 10 files
                "has_vector_data": total_count > 0
            }
            
        except Exception as e:
            logger.error(f"❌ Stats query failed: {e}")
            return {
                "total_chunks": 0,
                "unique_files": 0,
                "files": [],
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