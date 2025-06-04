# routes/integration_routes.py - Complete System Integration Routes

import logging
import asyncio
from datetime import datetime
from flask import Blueprint, request, jsonify
from functools import wraps

logger = logging.getLogger(__name__)

# Create Blueprint
integration_bp = Blueprint('integration', __name__)

# Global service instances
integration_service = None

def async_route(f):
    """Decorator to handle async routes"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(f(*args, **kwargs))
        finally:
            loop.close()
    return wrapper

def get_integration_service():
    """Get or initialize integration service"""
    global integration_service
    if integration_service is None:
        try:
            # Import services
            from services.integration_service import IntegrationService
            from services.azure_openai_service import AzureOpenAIService
            from services.cosmos_service import CosmosVectorService
            from services.document_service import DocumentProcessor
            from services.notion_service import NotionService
            from services.azure_storage_service import AzureStorageService
            
            # Initialize integration service
            integration_service = IntegrationService()
            
            # Initialize individual services
            azure_openai = AzureOpenAIService()
            cosmos_db = CosmosVectorService()
            document_proc = DocumentProcessor()
            
            # Optional services
            try:
                notion = NotionService()
            except Exception:
                notion = None
                logger.warning("⚠️ Notion service not available")
            
            try:
                storage = AzureStorageService()
            except Exception:
                storage = None
                logger.warning("⚠️ Azure Storage service not available")
            
            # Initialize the integration
            asyncio.run(integration_service.initialize_services(
                azure_openai_service=azure_openai,
                cosmos_service=cosmos_db,
                storage_service=storage,
                document_processor=document_proc,
                notion_service=notion
            ))
            
            logger.info("✅ Integration service initialized")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize integration service: {e}")
            raise
    
    return integration_service

# === SYSTEM MANAGEMENT ROUTES ===

@integration_bp.route('/health', methods=['GET'])
@async_route
async def system_health():
    """Get comprehensive system health status"""
    try:
        service = get_integration_service()
        health_status = await service.get_system_status()
        
        return jsonify({
            'success': True,
            'system_health': health_status,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ System health check failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@integration_bp.route('/status', methods=['GET'])
@async_route
async def system_status():
    """Get detailed system status and capabilities"""
    try:
        service = get_integration_service()
        
        status = {
            'integration_service_initialized': service.initialized,
            'last_sync_time': service.last_sync_time,
            'available_endpoints': {
                'system_management': ['/health', '/status', '/sync', '/statistics'],
                'document_processing': ['/upload', '/search', '/sync-storage'],
                'ai_chat': ['/chat', '/search-and-chat'],
                'blob_storage': ['/storage/sync', '/storage/status']
            },
            'capabilities': {
                'blob_storage_processing': True,
                'vector_search': True,
                'ai_enhanced_chat': True,
                'notion_integration': service.notion_service is not None,
                'azure_storage': service.storage_service is not None,
                'document_upload': True
            }
        }
        
        return jsonify({
            'success': True,
            'status': status,
            'message': 'Integration system operational',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Status check failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@integration_bp.route('/statistics', methods=['GET'])
@async_route
async def system_statistics():
    """Get comprehensive system statistics"""
    try:
        service = get_integration_service()
        
        # Get document statistics
        if service.cosmos_service:
            doc_stats = await service.cosmos_service.get_document_stats()
        else:
            doc_stats = {'error': 'Cosmos service not available'}
        
        # Get file statistics if storage available
        file_stats = {}
        if service.storage_service:
            try:
                files = await service.storage_service.list_files()
                file_stats = {
                    'total_files': len(files),
                    'total_size_bytes': sum(f.get('size', 0) for f in files),
                    'file_types': {}
                }
                
                # Count by file type
                for file in files:
                    ext = file.get('name', '').split('.')[-1].lower()
                    file_stats['file_types'][ext] = file_stats['file_types'].get(ext, 0) + 1
                    
            except Exception as e:
                file_stats = {'error': str(e)}
        
        return jsonify({
            'success': True,
            'statistics': {
                'documents': doc_stats,
                'files': file_stats,
                'system': {
                    'last_sync': service.last_sync_time,
                    'services_initialized': service.initialized
                }
            },
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Statistics retrieval failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

# === BLOB STORAGE SYNCHRONIZATION ===

@integration_bp.route('/sync', methods=['POST'])
@async_route
async def sync_blob_storage():
    """Synchronize blob storage to Cosmos DB"""
    try:
        service = get_integration_service()
        
        logger.info("🔄 Starting blob storage synchronization...")
        
        # Run the complete sync process
        sync_result = await service.sync_blob_storage_to_cosmos()
        
        if sync_result.get('success'):
            message = f"Sync completed: {sync_result['metrics']['new_chunks_created']} new chunks created"
            return jsonify({
                'success': True,
                'message': message,
                'sync_result': sync_result,
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({
                'success': False,
                'error': sync_result.get('error', 'Sync failed'),
                'sync_result': sync_result,
                'timestamp': datetime.now().isoformat()
            }), 400
            
    except Exception as e:
        logger.error(f"❌ Blob storage sync failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@integration_bp.route('/storage/status', methods=['GET'])
@async_route
async def storage_status():
    """Get blob storage status and file list"""
    try:
        service = get_integration_service()
        
        if not service.storage_service:
            return jsonify({
                'success': False,
                'error': 'Azure Storage service not configured',
                'timestamp': datetime.now().isoformat()
            }), 503
        
        # Get storage health
        storage_health = await service.storage_service.health_check()
        
        # Get file list
        files = await service.storage_service.list_files()
        
        return jsonify({
            'success': True,
            'storage_health': storage_health,
            'files': {
                'total_count': len(files),
                'files': files[:20],  # Limit to first 20 files
                'total_size_bytes': sum(f.get('size', 0) for f in files)
            },
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Storage status check failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

# === DOCUMENT PROCESSING ===

@integration_bp.route('/upload', methods=['POST'])
@async_route
async def upload_and_process_document():
    """Upload and process a document through the complete pipeline"""
    try:
        service = get_integration_service()
        
        # Check if file is in request
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No file provided',
                'timestamp': datetime.now().isoformat()
            }), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No file selected',
                'timestamp': datetime.now().isoformat()
            }), 400
        
        # Get processing options
        data = request.form
        store_to_blob = data.get('store_to_blob', 'false').lower() == 'true'
        store_to_cosmos = data.get('store_to_cosmos', 'true').lower() == 'true'
        
        # Save file temporarily
        import tempfile
        import os
        from werkzeug.utils import secure_filename
        
        filename = secure_filename(file.filename)
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{filename}") as tmp_file:
            file.save(tmp_file.name)
            temp_file_path = tmp_file.name
        
        try:
            # Process through integration service
            result = await service.process_uploaded_file(
                file_path=temp_file_path,
                file_name=filename,
                store_to_blob=store_to_blob,
                store_to_cosmos=store_to_cosmos
            )
            
            return jsonify({
                'success': result.get('success', False),
                'message': f"File '{filename}' processed successfully" if result.get('success') else 'Processing failed',
                'processing_result': result,
                'timestamp': datetime.now().isoformat()
            })
            
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_file_path)
            except Exception:
                pass
                
    except Exception as e:
        logger.error(f"❌ Document upload processing failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@integration_bp.route('/search', methods=['POST'])
@async_route
async def search_documents():
    """Search documents using vector similarity"""
    try:
        service = get_integration_service()
        
        data = request.get_json()
        if not data or 'query' not in data:
            return jsonify({
                'success': False,
                'error': 'Query is required',
                'required_format': {'query': 'your search query'},
                'timestamp': datetime.now().isoformat()
            }), 400
        
        query = data['query']
        limit = int(data.get('limit', 5))
        similarity_threshold = float(data.get('similarity_threshold', 0.3))
        
        # Search through document processor
        if service.document_processor:
            search_result = await service.document_processor.search_documents(
                query=query,
                limit=limit,
                similarity_threshold=similarity_threshold
            )
        else:
            # Fallback to direct cosmos search
            query_embedding = await service.azure_openai_service.generate_embeddings(query)
            results = await service.cosmos_service.search_similar_chunks(
                query_embedding=query_embedding,
                limit=limit,
                similarity_threshold=similarity_threshold
            )
            search_result = {
                'success': True,
                'query': query,
                'results': results,
                'total_found': len(results)
            }
        
        return jsonify({
            'success': search_result.get('success', False),
            'search_result': search_result,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Document search failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

# === AI CHAT WITH CONTEXT ===

@integration_bp.route('/chat', methods=['POST'])
@async_route
async def enhanced_chat():
    """Enhanced AI chat with document and Notion context"""
    try:
        service = get_integration_service()
        
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({
                'success': False,
                'error': 'Message is required',
                'required_format': {'message': 'your question'},
                'timestamp': datetime.now().isoformat()
            }), 400
        
        user_message = data['message']
        context = data.get('context', [])
        search_limit = int(data.get('search_limit', 5))
        similarity_threshold = float(data.get('similarity_threshold', 0.3))
        include_notion = data.get('include_notion', True)
        
        # Process through integration service
        chat_result = await service.search_and_chat(
            user_message=user_message,
            context=context,
            search_limit=search_limit,
            similarity_threshold=similarity_threshold,
            include_notion=include_notion
        )
        
        return jsonify({
            'success': chat_result.get('success', False),
            'chat_result': chat_result,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Enhanced chat failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'assistant_message': f"I apologize, but I encountered an error: {str(e)}",
            'timestamp': datetime.now().isoformat()
        }), 500

@integration_bp.route('/search-and-chat', methods=['POST'])
@async_route
async def search_and_chat():
    """Combined search and chat endpoint (alias for /chat)"""
    return await enhanced_chat()

# === TESTING AND DIAGNOSTICS ===

@integration_bp.route('/test', methods=['GET'])
@async_route
async def test_integration():
    """Test all integration components"""
    try:
        service = get_integration_service()
        
        test_results = {}
        
        # Test OpenAI service
        if service.azure_openai_service:
            try:
                test_embedding = await service.azure_openai_service.generate_embeddings("test")
                test_results['openai'] = {
                    'status': 'working',
                    'embedding_dimensions': len(test_embedding) if test_embedding else 0
                }
            except Exception as e:
                test_results['openai'] = {'status': 'error', 'error': str(e)}
        
        # Test Cosmos DB
        if service.cosmos_service:
            try:
                cosmos_health = await service.cosmos_service.health_check()
                test_results['cosmos_db'] = cosmos_health
            except Exception as e:
                test_results['cosmos_db'] = {'status': 'error', 'error': str(e)}
        
        # Test Storage if available
        if service.storage_service:
            try:
                storage_health = await service.storage_service.health_check()
                test_results['azure_storage'] = storage_health
            except Exception as e:
                test_results['azure_storage'] = {'status': 'error', 'error': str(e)}
        
        # Test Notion if available
        if service.notion_service:
            try:
                notion_health = await service.notion_service.health_check()
                test_results['notion'] = notion_health
            except Exception as e:
                test_results['notion'] = {'status': 'error', 'error': str(e)}
        
        # Overall test result
        working_services = sum(1 for result in test_results.values() if result.get('status') in ['healthy', 'working'])
        total_services = len(test_results)
        
        return jsonify({
            'success': True,
            'message': f'{working_services}/{total_services} services working correctly',
            'test_results': test_results,
            'overall_status': 'healthy' if working_services == total_services else 'degraded',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Integration test failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

# === ERROR HANDLERS ===

@integration_bp.errorhandler(400)
def bad_request(error):
    return jsonify({
        'success': False,
        'error': 'Bad request - check your request format',
        'timestamp': datetime.now().isoformat()
    }), 400

@integration_bp.errorhandler(500)
def internal_error(error):
    logger.error(f"Integration API internal error: {error}")
    return jsonify({
        'success': False,
        'error': 'Internal server error in integration service',
        'timestamp': datetime.now().isoformat()
    }), 500