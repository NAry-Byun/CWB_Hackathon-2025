# services/integration_service.py - Complete Blob Storage → Cosmos DB → Vector Search → OpenAI Integration

import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class IntegrationService:
    """
    Main integration service that orchestrates:
    1. Azure Blob Storage → Text Extraction → Chunking
    2. Azure OpenAI → Embedding Generation
    3. Cosmos DB → Vector Storage
    4. Vector Search → Context Retrieval
    5. Azure OpenAI → Enhanced Chat Responses
    """

    def __init__(self):
        # Service instances
        self.azure_openai_service = None
        self.cosmos_service = None
        self.storage_service = None
        self.document_processor = None
        self.notion_service = None
        
        # Status tracking
        self.initialized = False
        self.last_sync_time = None
        
        logger.info("🔧 IntegrationService initialized")

    async def initialize_services(
        self,
        azure_openai_service=None,
        cosmos_service=None,
        storage_service=None,
        document_processor=None,
        notion_service=None
    ):
        """
        Initialize all services and establish connections
        
        Args:
            azure_openai_service: Azure OpenAI service instance
            cosmos_service: Cosmos DB service instance
            storage_service: Azure Storage service instance
            document_processor: Document processing service instance
            notion_service: Notion service instance (optional)
        """
        try:
            logger.info("🚀 Initializing integration services...")
            
            # Store service references
            self.azure_openai_service = azure_openai_service
            self.cosmos_service = cosmos_service
            self.storage_service = storage_service
            self.document_processor = document_processor
            self.notion_service = notion_service
            
            # Validate required services
            if not self.azure_openai_service:
                raise ValueError("Azure OpenAI service is required")
            
            if not self.cosmos_service:
                raise ValueError("Cosmos DB service is required")
            
            # Initialize Cosmos DB
            await self.cosmos_service.initialize_database()
            logger.info("✅ Cosmos DB initialized")
            
            # Inject dependencies
            if self.document_processor:
                self.document_processor.set_services(
                    cosmos_service=self.cosmos_service,
                    openai_service=self.azure_openai_service,
                    storage_service=self.storage_service
                )
                logger.info("✅ Document processor configured")
            
            # Configure Cosmos service with OpenAI
            self.cosmos_service.set_openai_service(self.azure_openai_service)
            logger.info("✅ Cosmos service configured with OpenAI")
            
            self.initialized = True
            logger.info("🎉 Integration services fully initialized!")
            
            return {
                'success': True,
                'message': 'All services initialized successfully',
                'services': {
                    'azure_openai': self.azure_openai_service is not None,
                    'cosmos_db': self.cosmos_service is not None,
                    'storage': self.storage_service is not None,
                    'document_processor': self.document_processor is not None,
                    'notion': self.notion_service is not None
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Service initialization failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    async def sync_blob_storage_to_cosmos(self) -> Dict[str, Any]:
        """
        Complete workflow: Blob Storage → Text Extraction → Embedding → Cosmos DB
        
        Returns:
            Sync results with detailed statistics
        """
        try:
            if not self.initialized:
                return {
                    'success': False,
                    'error': 'Services not initialized. Call initialize_services() first.'
                }
            
            logger.info("🔄 Starting blob storage to Cosmos DB sync...")
            start_time = datetime.now()
            
            # Step 1: Get current Cosmos DB state
            initial_stats = await self.cosmos_service.get_document_stats()
            initial_chunks = initial_stats.get('total_chunks', 0)
            
            # Step 2: Process blob storage files
            if self.document_processor:
                sync_result = await self.document_processor.process_blob_storage_files()
            else:
                # Fallback to direct Cosmos processing
                sync_result = await self.cosmos_service.process_storage_files()
            
            # Step 3: Get final state
            final_stats = await self.cosmos_service.get_document_stats()
            final_chunks = final_stats.get('total_chunks', 0)
            
            # Calculate metrics
            processing_time = (datetime.now() - start_time).total_seconds()
            new_chunks = final_chunks - initial_chunks
            
            self.last_sync_time = datetime.now().isoformat()
            
            result = {
                'success': sync_result.get('success', False),
                'sync_time': self.last_sync_time,
                'processing_time_seconds': round(processing_time, 2),
                'metrics': {
                    'initial_chunks': initial_chunks,
                    'final_chunks': final_chunks,
                    'new_chunks_created': new_chunks,
                    'files_processed': len(sync_result.get('processed_files', [])),
                    'files_failed': len(sync_result.get('failed_files', []))
                },
                'details': sync_result
            }
            
            if sync_result.get('success'):
                logger.info(f"✅ Sync completed: {new_chunks} new chunks created in {processing_time:.1f}s")
            else:
                logger.error(f"❌ Sync failed: {sync_result.get('error', 'Unknown error')}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Blob storage sync failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'sync_time': datetime.now().isoformat()
            }

    async def search_and_chat(
        self,
        user_message: str,
        context: List[Dict] = None,
        search_limit: int = 5,
        similarity_threshold: float = 0.3,
        include_notion: bool = True
    ) -> Dict[str, Any]:
        """
        Complete workflow: User Query → Vector Search → Context Retrieval → Enhanced AI Response
        
        Args:
            user_message: User's question/message
            context: Previous conversation context
            search_limit: Maximum search results
            similarity_threshold: Minimum similarity for search
            include_notion: Whether to include Notion search
            
        Returns:
            Enhanced AI response with sources
        """
        try:
            if not self.initialized:
                return {
                    'success': False,
                    'error': 'Services not initialized'
                }
            
            logger.info(f"💬 Processing search and chat for: '{user_message[:100]}...'")
            start_time = datetime.now()
            
            # Step 1: Generate embedding for user query
            query_embedding = await self.azure_openai_service.generate_embeddings(user_message)
            
            if not query_embedding:
                return {
                    'success': False,
                    'error': 'Failed to generate embedding for query'
                }
            
            # Step 2: Search Cosmos DB for relevant documents
            document_chunks = []
            try:
                search_results = await self.cosmos_service.search_similar_chunks(
                    query_embedding=query_embedding,
                    limit=search_limit,
                    similarity_threshold=similarity_threshold
                )
                
                # Format document chunks for AI prompt
                document_chunks = [
                    {
                        "file_name": result.get("file_name", "unknown"),
                        "content": result.get("chunk_text", "")[:1000],  # Limit content
                        "similarity": result.get("similarity", 0.0),
                        "chunk_index": result.get("chunk_index", 0)
                    }
                    for result in search_results
                ]
                
                logger.info(f"📊 Found {len(document_chunks)} relevant document chunks")
                
            except Exception as e:
                logger.warning(f"⚠️ Document search failed: {e}")
                document_chunks = []
            
            # Step 3: Search Notion if available and requested
            notion_pages = []
            if include_notion and self.notion_service:
                try:
                    # Check for meeting-related keywords
                    meeting_keywords = ["meeting", "agenda", "schedule", "call", "conference"]
                    if any(kw in user_message.lower() for kw in meeting_keywords):
                        notion_results = await self.notion_service.search_meeting_pages(user_message)
                    else:
                        notion_results = await self.notion_service.search_pages(user_message, limit=3)
                    
                    # Format Notion pages
                    for page in notion_results[:3]:  # Limit to top 3
                        if isinstance(page, dict):
                            notion_pages.append({
                                "id": page.get("id", ""),
                                "title": page.get("title", "Untitled"),
                                "url": page.get("url", ""),
                                "content": page.get("content", "")[:1500],  # Limit content
                                "last_edited_time": page.get("last_edited_time", ""),
                                "created_time": page.get("created_time", "")
                            })
                    
                    logger.info(f"📝 Found {len(notion_pages)} relevant Notion pages")
                    
                except Exception as e:
                    logger.warning(f"⚠️ Notion search failed: {e}")
                    notion_pages = []
            
            # Step 4: Generate enhanced AI response
            ai_response = await self.azure_openai_service.generate_response(
                user_message=user_message,
                context=context or [],
                document_chunks=document_chunks,
                notion_pages=notion_pages,
                max_tokens=1500,
                temperature=0.7
            )
            
            # Step 5: Calculate processing metrics
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Step 6: Format complete response
            result = {
                'success': True,
                'assistant_message': ai_response.get('assistant_message', ''),
                'content': ai_response.get('assistant_message', ''),  # Frontend compatibility
                'processing_time_seconds': round(processing_time, 2),
                'sources': {
                    'document_chunks': len(document_chunks),
                    'notion_pages': len(notion_pages),
                    'total_sources': len(document_chunks) + len(notion_pages)
                },
                'search_results': {
                    'documents': document_chunks,
                    'notion': notion_pages
                },
                'ai_metadata': {
                    'model_used': ai_response.get('model_used'),
                    'token_usage': ai_response.get('usage', {}),
                    'has_context': ai_response.get('has_context', False),
                    'has_documents': len(document_chunks) > 0,
                    'has_notion': len(notion_pages) > 0
                },
                'query_info': {
                    'original_query': user_message,
                    'search_limit': search_limit,
                    'similarity_threshold': similarity_threshold,
                    'include_notion': include_notion
                }
            }
            
            logger.info(f"✅ Search and chat completed in {processing_time:.2f}s with {len(document_chunks)} docs + {len(notion_pages)} notion pages")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Search and chat failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'assistant_message': f"I apologize, but I encountered an error: {str(e)}",
                'content': f"I apologize, but I encountered an error: {str(e)}"
            }

    async def process_uploaded_file(
        self,
        file_path: str,
        file_name: str,
        store_to_blob: bool = False,
        store_to_cosmos: bool = True
    ) -> Dict[str, Any]:
        """
        Process an uploaded file through the complete pipeline
        
        Args:
            file_path: Local path to uploaded file
            file_name: Name of the file
            store_to_blob: Whether to upload to blob storage
            store_to_cosmos: Whether to process and store in Cosmos DB
            
        Returns:
            Processing results
        """
        try:
            if not self.initialized:
                return {
                    'success': False,
                    'error': 'Services not initialized'
                }
            
            logger.info(f"📤 Processing uploaded file: {file_name}")
            
            result = {'success': True, 'file_name': file_name}
            
            # Step 1: Store in blob storage if requested
            if store_to_blob and self.storage_service:
                try:
                    with open(file_path, 'rb') as f:
                        file_content = f.read()
                    
                    blob_url = await self.storage_service.upload_file(
                        file_name=file_name,
                        file_content=file_content
                    )
                    
                    result['blob_storage'] = {
                        'uploaded': blob_url is not None,
                        'url': blob_url
                    }
                    
                except Exception as e:
                    logger.warning(f"⚠️ Blob storage upload failed: {e}")
                    result['blob_storage'] = {
                        'uploaded': False,
                        'error': str(e)
                    }
            
            # Step 2: Process and store in Cosmos DB
            if store_to_cosmos and self.document_processor:
                try:
                    processing_result = await self.document_processor.process_uploaded_file(
                        file_path=file_path,
                        file_name=file_name,
                        store_to_cosmos=True
                    )
                    
                    result['document_processing'] = processing_result
                    
                except Exception as e:
                    logger.error(f"❌ Document processing failed: {e}")
                    result['document_processing'] = {
                        'success': False,
                        'error': str(e)
                    }
                    result['success'] = False
            
            return result
            
        except Exception as e:
            logger.error(f"❌ File upload processing failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'file_name': file_name
            }

    async def get_system_status(self) -> Dict[str, Any]:
        """
        Get comprehensive system status
        
        Returns:
            Complete system health and statistics
        """
        try:
            status = {
                'integration_service': {
                    'initialized': self.initialized,
                    'last_sync_time': self.last_sync_time
                },
                'services': {},
                'statistics': {},
                'overall_health': 'unknown'
            }
            
            # Check each service
            if self.azure_openai_service:
                try:
                    openai_health = await self.azure_openai_service.health_check()
                    status['services']['azure_openai'] = openai_health
                except Exception as e:
                    status['services']['azure_openai'] = {'status': 'error', 'error': str(e)}
            
            if self.cosmos_service:
                try:
                    cosmos_health = await self.cosmos_service.health_check()
                    status['services']['cosmos_db'] = cosmos_health
                    
                    # Get document statistics
                    stats = await self.cosmos_service.get_document_stats()
                    status['statistics']['cosmos_db'] = stats
                except Exception as e:
                    status['services']['cosmos_db'] = {'status': 'error', 'error': str(e)}
            
            if self.storage_service:
                try:
                    storage_health = await self.storage_service.health_check()
                    status['services']['azure_storage'] = storage_health
                except Exception as e:
                    status['services']['azure_storage'] = {'status': 'error', 'error': str(e)}
            
            if self.document_processor:
                try:
                    doc_health = await self.document_processor.health_check()
                    status['services']['document_processor'] = doc_health
                except Exception as e:
                    status['services']['document_processor'] = {'status': 'error', 'error': str(e)}
            
            if self.notion_service:
                try:
                    notion_health = await self.notion_service.health_check()
                    status['services']['notion'] = notion_health
                except Exception as e:
                    status['services']['notion'] = {'status': 'error', 'error': str(e)}
            
            # Determine overall health
            healthy_services = sum(1 for s in status['services'].values() if s.get('status') == 'healthy')
            total_services = len(status['services'])
            
            if healthy_services == total_services and self.initialized:
                status['overall_health'] = 'healthy'
            elif healthy_services >= total_services * 0.7:
                status['overall_health'] = 'degraded'
            else:
                status['overall_health'] = 'unhealthy'
            
            status['health_summary'] = {
                'healthy_services': healthy_services,
                'total_services': total_services,
                'health_percentage': round((healthy_services / max(total_services, 1)) * 100, 1)
            }
            
            return status
            
        except Exception as e:
            logger.error(f"❌ System status check failed: {e}")
            return {
                'integration_service': {
                    'initialized': self.initialized,
                    'error': str(e)
                },
                'overall_health': 'error'
            }

    async def cleanup_resources(self):
        """
        Clean up all service resources
        """
        try:
            logger.info("🧹 Cleaning up integration service resources...")
            
            if self.azure_openai_service and hasattr(self.azure_openai_service, 'close'):
                await self.azure_openai_service.close()
            
            if self.cosmos_service and hasattr(self.cosmos_service, 'close'):
                await self.cosmos_service.close()
            
            logger.info("✅ Integration service cleanup completed")
            
        except Exception as e:
            logger.error(f"❌ Cleanup failed: {e}")

# Global integration service instance
integration_service = IntegrationService()