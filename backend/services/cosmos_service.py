# services/cosmos_service.py - Fixed Cosmos DB Vector Service with Proper Azure OpenAI Integration

import os
import asyncio
import logging
from typing import List, Dict, Any, Optional
from azure.cosmos.aio import CosmosClient
from azure.cosmos.partition_key import PartitionKey
from azure.storage.blob import BlobServiceClient
from datetime import datetime

logger = logging.getLogger(__name__)

class CosmosVectorService:
    """Complete Azure Cosmos DB Vector Service with Storage Integration"""

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
        
        # Will be injected by the service that calls this
        self.openai_service = None
        
        logger.info(f"🌌 CosmosVectorService initialized")
        logger.info(f"🔧 Database: {self.database_name}")
        logger.info(f"🔧 Container: {self.container_name}")

    def set_openai_service(self, openai_service):
        """Inject the OpenAI service for embeddings"""
        self.openai_service = openai_service
        logger.info("✅ OpenAI service injected into CosmosVectorService")

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
            
            # Define vector policy for embeddings (updated for latest models)
            vector_policy = {
                "vectorEmbeddings": [
                    {
                        "path": "/embedding",
                        "dataType": "float32",
                        "distanceFunction": "cosine",
                        "dimensions": 1536  # Standard for text-embedding-ada-002 and 3-small
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
        """Process files from Azure Storage and store in Cosmos DB with proper embeddings"""
        try:
            # Ensure OpenAI service is available
            if not self.openai_service:
                return {
                    'success': False,
                    'error': 'OpenAI service not configured. Call set_openai_service() first.'
                }

            # Get storage connection
            connection_string = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
            container_name = os.getenv('AZURE_STORAGE_CONTAINER_NAME', 'documents')
            
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
            total_chunks = 0
            
            # List and process each file
            try:
                blobs = list(container_client.list_blobs())
                logger.info(f"📁 Found {len(blobs)} files in storage container")
            except Exception as e:
                logger.error(f"❌ Failed to list blobs: {e}")
                return {
                    'success': False,
                    'error': f'Failed to access storage container: {str(e)}'
                }

            for blob in blobs:
                file_name = blob.name
                logger.info(f"📄 Processing: {file_name}")
                
                try:
                    # Skip image files
                    if any(file_name.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.ico']):
                        logger.info(f"⏭️ Skipping {file_name} (image file)")
                        continue
                    
                    # Download file
                    blob_client = container_client.get_blob_client(file_name)
                    file_content = blob_client.download_blob().readall()
                    
                    # Extract text (enhanced version)
                    text_content = await self._extract_text_advanced(file_content, file_name)
                    
                    if text_content and len(text_content.strip()) > 50:  # Minimum content threshold
                        # Split into chunks for better processing
                        chunks = self._split_text_into_chunks(text_content, chunk_size=1000, overlap=200)
                        
                        file_chunk_count = 0
                        for i, chunk in enumerate(chunks):
                            if len(chunk.strip()) > 20:  # Skip very short chunks
                                # Create embedding using our OpenAI service
                                embedding = await self.openai_service.generate_embeddings(chunk)
                                
                                if embedding and len(embedding) > 0:
                                    # Store in Cosmos DB
                                    await self.store_document_chunk(
                                        file_name=file_name,
                                        chunk_text=chunk,
                                        embedding=embedding,
                                        chunk_index=i,
                                        metadata={
                                            'source': 'azure_storage',
                                            'file_size': len(file_content),
                                            'processed_at': datetime.now().isoformat(),
                                            'total_chunks': len(chunks),
                                            'original_content_length': len(text_content)
                                        }
                                    )
                                    file_chunk_count += 1
                                    total_chunks += 1
                                else:
                                    logger.warning(f"⚠️ Failed to create embedding for chunk {i} of {file_name}")
                        
                        if file_chunk_count > 0:
                            processed_files.append({
                                'file_name': file_name,
                                'chunks_created': file_chunk_count,
                                'total_text_length': len(text_content)
                            })
                            logger.info(f"✅ Stored {file_name} with {file_chunk_count} chunks in Cosmos DB")
                        else:
                            failed_files.append({
                                'file_name': file_name,
                                'error': 'No embeddings could be created'
                            })
                    else:
                        logger.warning(f"⚠️ No sufficient text content found in {file_name}")
                        failed_files.append({
                            'file_name': file_name,
                            'error': 'Insufficient text content'
                        })
                        
                except Exception as e:
                    logger.error(f"❌ Failed to process {file_name}: {e}")
                    failed_files.append({
                        'file_name': file_name,
                        'error': str(e)
                    })
            
            return {
                'success': True,
                'processed_files': processed_files,
                'failed_files': failed_files,
                'total_processed': len(processed_files),
                'total_chunks_created': total_chunks,
                'container': container_name,
                'summary': f"Successfully processed {len(processed_files)} files, created {total_chunks} searchable chunks"
            }
            
        except Exception as e:
            logger.error(f"❌ Storage processing failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def _split_text_into_chunks(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """Split text into overlapping chunks for better context preservation"""
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            
            # Try to break at word boundaries
            if end < len(text):
                # Look back for a good breaking point
                for i in range(min(100, end - start)):
                    if text[end - i] in ['.', '!', '?', '\n']:
                        end = end - i + 1
                        break
                    elif text[end - i] in [' ', '\t']:
                        end = end - i
                        break
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            # Move start forward with overlap
            start = end - overlap
            if start >= len(text):
                break
        
        return chunks

    async def _extract_text_advanced(self, file_content: bytes, file_name: str) -> str:
        """Enhanced text extraction with better error handling"""
        try:
            file_ext = file_name.lower().split('.')[-1] if '.' in file_name else ''
            
            if file_ext in ['txt', 'md', 'rtf']:
                # Try multiple encodings
                for encoding in ['utf-8', 'utf-16', 'latin-1', 'cp1252']:
                    try:
                        return file_content.decode(encoding, errors='ignore')
                    except UnicodeDecodeError:
                        continue
                
            elif file_ext in ['doc', 'docx']:
                # Basic Word document text extraction
                try:
                    # Try to decode as UTF-8 first (works for some simple .doc files)
                    text = file_content.decode('utf-8', errors='ignore')
                    # Clean up control characters and binary noise
                    import re
                    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', ' ', text)
                    text = re.sub(r'\s+', ' ', text)
                    # Filter out mostly non-text content
                    if len([c for c in text if c.isalnum()]) / max(len(text), 1) > 0.3:
                        return text
                except:
                    pass
                
            elif file_ext == 'pdf':
                # Note: For production, you'd want to use PyPDF2 or pdfplumber
                logger.warning(f"⚠️ PDF processing not implemented for {file_name}")
                return ""
                
            # Fallback: try to extract any readable text
            try:
                text = file_content.decode('utf-8', errors='ignore')
                # Remove control characters
                import re
                text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', ' ', text)
                return text
            except:
                return ""
                
        except Exception as e:
            logger.error(f"Text extraction error for {file_name}: {e}")
            return ""

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
            document_id = f"{file_name}_{chunk_index}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            document = {
                "id": document_id,
                "file_name": file_name,
                "chunk_text": chunk_text,
                "chunk_index": chunk_index,
                "embedding": embedding,
                "metadata": metadata or {},
                "created_at": datetime.now().isoformat(),
                "document_type": "text_chunk",
                "vector_dimensions": len(embedding),
                "text_length": len(chunk_text)
            }
            
            result = await self.container.create_item(body=document)
            logger.debug(f"✅ Stored chunk {chunk_index} for {file_name}")
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

            # Ensure we have a container
            if not self.container:
                await self.initialize_database()

            # Use VectorDistance with proper syntax for Cosmos DB
            query = f"""
            SELECT TOP {limit}
                c.id,
                c.file_name,
                c.chunk_text,
                c.chunk_index,
                c.metadata,
                c.created_at,
                c.text_length,
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
                parameters=parameters,
                enable_cross_partition_query=True
            )
            
            async for item in query_iterable:
                results.append(item)
            
            logger.info(f"✅ Found {len(results)} similar chunks")
            
            # Log top results for debugging
            for i, result in enumerate(results[:3]):
                file_name = result.get("file_name", "unknown")
                similarity = result.get("similarity", 0.0)
                text_preview = result.get("chunk_text", "")[:100] + "..."
                logger.info(f"  {i+1}. {file_name} (similarity: {similarity:.3f}) - {text_preview}")
            
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
            if not self.container:
                await self.initialize_database()
                
            query = f"SELECT TOP {limit} * FROM c ORDER BY c.created_at DESC"
            
            results = []
            query_iterable = self.container.query_items(
                query=query,
                enable_cross_partition_query=True
            )
            
            async for item in query_iterable:
                # Remove embedding from results to save bandwidth
                if 'embedding' in item:
                    item['has_embedding'] = True
                    item['embedding_dimensions'] = len(item['embedding'])
                    del item['embedding']
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
                await self.initialize_database()
            
            # Simple query to test connectivity
            query = "SELECT TOP 1 c.id, c.file_name FROM c"
            query_iterable = self.container.query_items(
                query=query,
                enable_cross_partition_query=True
            )
            
            count = 0
            sample_doc = None
            async for item in query_iterable:
                count += 1
                sample_doc = item
                break  # Just check if we can query
            
            return {
                "status": "healthy",
                "service": "Cosmos DB",
                "database": self.database_name,
                "container": self.container_name,
                "can_query": True,
                "sample_document": sample_doc,
                "openai_service_connected": self.openai_service is not None,
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
            if not self.container:
                await self.initialize_database()
                
            # Count total documents
            count_query = "SELECT VALUE COUNT(1) FROM c"
            count_iterable = self.container.query_items(
                query=count_query,
                enable_cross_partition_query=True
            )
            
            total_count = 0
            async for count in count_iterable:
                total_count = count
                break
            
            # Count by file type
            file_count_query = """
            SELECT c.file_name, 
                   COUNT(1) as chunk_count,
                   SUM(c.text_length) as total_text_length
            FROM c 
            GROUP BY c.file_name
            """
            file_iterable = self.container.query_items(
                query=file_count_query,
                enable_cross_partition_query=True
            )
            
            files = []
            async for file_info in file_iterable:
                files.append(file_info)
            
            return {
                "total_chunks": total_count,
                "unique_files": len(files),
                "files": files[:20],  # Limit to first 20 files
                "has_vector_data": total_count > 0,
                "openai_service_available": self.openai_service is not None
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