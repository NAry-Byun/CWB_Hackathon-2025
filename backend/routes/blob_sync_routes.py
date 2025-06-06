# routes/blob_sync_routes.py - COMPLETE Flask Backend for Blob Storage Sync

from flask import Blueprint, request, jsonify
import asyncio
import logging
from datetime import datetime
from functools import wraps

logger = logging.getLogger(__name__)

# Blueprint creation
blob_sync_bp = Blueprint('blob_sync', __name__)

def async_route(f):
    """Decorator to convert Flask route to async function"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(f(*args, **kwargs))
        finally:
            loop.close()
    return wrapper

@blob_sync_bp.route('/sync-all', methods=['POST'])
@async_route
async def sync_all_blobs():
    """Sync all Blob Storage files to Cosmos DB"""
    try:
        logger.info("🚀 Starting bulk blob sync process...")
        
        # Service initialization
        from services.azure_storage_service import AzureStorageService
        from services.cosmos_service import CosmosVectorService
        from services.azure_openai_service import AzureOpenAIService
        from services.document_processor import DocumentProcessor
        
        storage_service = AzureStorageService()
        cosmos_service = CosmosVectorService()
        openai_service = AzureOpenAIService()
        doc_processor = DocumentProcessor()
        
        cosmos_service.set_openai_service(openai_service)
        await cosmos_service.initialize_database()
        
        # Get all files from Blob Storage
        logger.info("🔍 Fetching files from Blob Storage...")
        files = await storage_service.list_files()
        
        results = {
            "processed_files": [],
            "failed_files": [],
            "skipped_files": [],
            "total_found": len(files),
            "total_chunks_created": 0
        }
        
        for file_info in files:
            try:
                filename = file_info['name']
                logger.info(f"📄 Processing: {filename}")
                
                # Check if file format is supported
                if not doc_processor.validate_file_format(filename):
                    logger.info(f"⏭️ Skipping unsupported format: {filename}")
                    results["skipped_files"].append({
                        "filename": filename,
                        "reason": "unsupported_format"
                    })
                    continue
                
                # Check if already exists in Cosmos DB
                existing = await cosmos_service.check_file_exists(filename)
                if existing:
                    logger.info(f"⏭️ Skipping existing file: {filename}")
                    results["skipped_files"].append({
                        "filename": filename,
                        "reason": "already_exists"
                    })
                    continue
                
                # Process file
                chunk_count = await process_single_file_with_chunks(
                    storage_service, cosmos_service, openai_service, 
                    doc_processor, filename, file_info
                )
                
                if chunk_count > 0:
                    results["processed_files"].append({
                        "filename": filename,
                        "chunks_created": chunk_count,
                        "file_size": file_info.get('size', 0)
                    })
                    results["total_chunks_created"] += chunk_count
                    logger.info(f"✅ Successfully processed: {filename} ({chunk_count} chunks)")
                else:
                    results["failed_files"].append({
                        "filename": filename,
                        "error": "no_chunks_created"
                    })
                
            except Exception as e:
                logger.error(f"❌ Failed to process {filename}: {str(e)}")
                results["failed_files"].append({
                    "filename": filename,
                    "error": str(e)
                })
        
        return jsonify({
            "success": True,
            "message": f"{len(results['processed_files'])} 파일 동기화 완료",
            "results": results,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Bulk sync failed: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@blob_sync_bp.route('/sync-file', methods=['POST'])
@async_route
async def sync_single_file():
    """Sync specific file"""
    try:
        data = request.get_json()
        filename = data.get('filename')
        
        if not filename:
            return jsonify({"error": "filename required"}), 400
        
        logger.info(f"🎯 Processing single file: {filename}")
        
        # Service initialization
        from services.azure_storage_service import AzureStorageService
        from services.cosmos_service import CosmosVectorService
        from services.azure_openai_service import AzureOpenAIService
        from services.document_processor import DocumentProcessor
        
        storage_service = AzureStorageService()
        cosmos_service = CosmosVectorService()
        openai_service = AzureOpenAIService()
        doc_processor = DocumentProcessor()
        
        cosmos_service.set_openai_service(openai_service)
        await cosmos_service.initialize_database()
        
        # Check if file already exists
        existing = await cosmos_service.check_file_exists(filename)
        if existing:
            return jsonify({
                "success": True,
                "status": "already_synced",
                "message": f"파일이 이미 동기화되어 있습니다: {filename}",
                "timestamp": datetime.now().isoformat()
            })
        
        # Get file info
        file_info = await storage_service.get_file_info(filename)
        if not file_info:
            return jsonify({"error": f"파일을 찾을 수 없습니다: {filename}"}), 404
        
        # Process file
        chunk_count = await process_single_file_with_chunks(
            storage_service, cosmos_service, openai_service, 
            doc_processor, filename, file_info
        )
        
        if chunk_count > 0:
            return jsonify({
                "success": True,
                "message": f"파일 '{filename}' 동기화 완료",
                "document_id": f"blob_{filename}",
                "chunks_created": chunk_count,
                "content_length": file_info.get('size', 0),
                "timestamp": datetime.now().isoformat()
            })
        else:
            return jsonify({
                "success": False,
                "error": "텍스트 추출 또는 청킹 실패",
                "filename": filename,
                "timestamp": datetime.now().isoformat()
            }), 500
        
    except Exception as e:
        logger.error(f"❌ Single file sync failed: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@blob_sync_bp.route('/force-sync-file', methods=['POST'])
@async_route
async def force_sync_single_file():
    """Force re-sync specific file, ignoring 'already exists' check"""
    try:
        data = request.get_json()
        filename = data.get('filename')
        
        if not filename:
            return jsonify({"error": "filename required"}), 400
        
        logger.info(f"🎯 FORCE Processing single file: {filename}")
        
        from services.azure_storage_service import AzureStorageService
        from services.cosmos_service import CosmosVectorService
        from services.azure_openai_service import AzureOpenAIService
        from services.document_processor import DocumentProcessor
        
        storage_service = AzureStorageService()
        cosmos_service = CosmosVectorService()
        openai_service = AzureOpenAIService()
        doc_processor = DocumentProcessor()
        
        cosmos_service.set_openai_service(openai_service)
        await cosmos_service.initialize_database()
        
        # Get file info
        file_info = await storage_service.get_file_info(filename)
        if not file_info:
            return jsonify({"error": f"File not found: {filename}"}), 404
        
        # FORCE process file (ignore existing check)
        chunk_count = await process_single_file_with_chunks(
            storage_service, cosmos_service, openai_service, 
            doc_processor, filename, file_info
        )
        
        return jsonify({
            "success": True,
            "message": f"FORCE synced '{filename}'",
            "chunks_created": chunk_count,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ FORCE single file sync failed: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@blob_sync_bp.route('/force-sync-all', methods=['POST'])
@async_route
async def force_sync_all_blobs():
    """Force re-sync all files, ignoring 'already exists' check"""
    try:
        logger.info("🚀 Starting FORCE bulk blob sync (ignoring existing files)...")
        
        from services.azure_storage_service import AzureStorageService
        from services.cosmos_service import CosmosVectorService
        from services.azure_openai_service import AzureOpenAIService
        from services.document_processor import DocumentProcessor
        
        storage_service = AzureStorageService()
        cosmos_service = CosmosVectorService()
        openai_service = AzureOpenAIService()
        doc_processor = DocumentProcessor()
        
        cosmos_service.set_openai_service(openai_service)
        await cosmos_service.initialize_database()
        
        files = await storage_service.list_files()
        
        results = {
            "processed_files": [],
            "failed_files": [],
            "skipped_files": [],
            "total_found": len(files),
            "total_chunks_created": 0
        }
        
        for file_info in files:
            try:
                filename = file_info['name']
                logger.info(f"📄 FORCE Processing: {filename}")
                
                if not doc_processor.validate_file_format(filename):
                    logger.info(f"⏭️ Skipping unsupported format: {filename}")
                    results["skipped_files"].append({
                        "filename": filename,
                        "reason": "unsupported_format"
                    })
                    continue
                
                # FORCE process file (ignore existing check)
                chunk_count = await process_single_file_with_chunks(
                    storage_service, cosmos_service, openai_service, 
                    doc_processor, filename, file_info
                )
                
                if chunk_count > 0:
                    results["processed_files"].append({
                        "filename": filename,
                        "chunks_created": chunk_count,
                        "file_size": file_info.get('size', 0)
                    })
                    results["total_chunks_created"] += chunk_count
                    logger.info(f"✅ FORCE processed: {filename} ({chunk_count} chunks)")
                else:
                    results["failed_files"].append({
                        "filename": filename,
                        "error": "no_chunks_created"
                    })
                
            except Exception as e:
                logger.error(f"❌ Failed to FORCE process {filename}: {str(e)}")
                results["failed_files"].append({
                    "filename": filename,
                    "error": str(e)
                })
        
        return jsonify({
            "success": True,
            "message": f"FORCE synced {len(results['processed_files'])} files",
            "results": results,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ FORCE bulk sync failed: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@blob_sync_bp.route('/status', methods=['GET'])
@async_route
async def sync_status():
    """Check sync status"""
    try:
        from services.azure_storage_service import AzureStorageService
        from services.cosmos_service import CosmosVectorService
        
        storage_service = AzureStorageService()
        cosmos_service = CosmosVectorService()
        
        await cosmos_service.initialize_database()
        
        # Blob Storage file count
        blob_files = await storage_service.list_files()
        blob_count = len(blob_files)
        
        # Cosmos DB stats
        cosmos_stats = await cosmos_service.get_blob_sync_stats()
        
        # Find unsynced files
        not_synced = []
        for file_info in blob_files:
            filename = file_info['name']
            exists = await cosmos_service.check_file_exists(filename)
            if not exists:
                not_synced.append(filename)
        
        # Sample file list
        sample_files = [f['name'] for f in blob_files[:4]]
        
        return jsonify({
            "success": True,
            "status": {
                "blob_storage_files": blob_count,
                "cosmos_synced_documents": cosmos_stats.get('total_blob_documents', 0),
                "cosmos_chunks": cosmos_stats.get('total_blob_chunks', 0),
                "not_synced_count": len(not_synced),
                "sync_percentage": ((blob_count - len(not_synced)) / blob_count * 100) if blob_count > 0 else 0
            },
            "blob_files_sample": sample_files,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Status check failed: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@blob_sync_bp.route('/health', methods=['GET'])
def health_check():
    """Blob sync service health check"""
    return jsonify({
        "status": "healthy",
        "service": "blob_sync",
        "description": "Blob Storage to Cosmos DB synchronization",
        "endpoints": [
            "/health",
            "/status", 
            "/sync-all",
            "/sync-file",
            "/force-sync-file",
            "/force-sync-all",
            "/test-connection"
        ],
        "timestamp": datetime.now().isoformat()
    })

@blob_sync_bp.route('/test-connection', methods=['GET'])
@async_route
async def test_connection():
    """Test connections"""
    try:
        from services.azure_storage_service import AzureStorageService
        from services.cosmos_service import CosmosVectorService
        
        storage_service = AzureStorageService()
        cosmos_service = CosmosVectorService()
        
        # Test storage
        storage_health = await storage_service.health_check()
        
        # Test cosmos
        cosmos_health = await cosmos_service.health_check()
        
        return jsonify({
            "success": True,
            "storage_service": storage_health,
            "cosmos_service": cosmos_health,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

# Helper functions
async def process_single_file_with_chunks(
    storage_service, cosmos_service, openai_service, 
    doc_processor, filename, file_info
) -> int:
    """Process single file and create chunks"""
    try:
        # 1. Download file from Blob
        logger.info(f"📥 Downloading {filename}...")
        file_content = await storage_service.download_file(filename)
        
        # 2. Extract text
        logger.info(f"📝 Extracting text from {filename}...")
        text_content = await doc_processor.extract_text_from_file(file_content, filename)
        
        if len(text_content.strip()) < 20:
            logger.warning(f"⚠️ Very little text extracted from {filename}: {len(text_content)} chars")
            logger.warning(f"Text preview: {text_content[:100]}...")
            
        # 3. Store full document first
        await cosmos_service.store_blob_document(
            filename=filename,
            content=text_content,
            metadata={
                "file_size": file_info.get('size', 0),
                "last_modified": file_info.get('last_modified'),
                "content_type": file_info.get('content_type'),
                "source": "blob_storage",
                "text_length": len(text_content)
            }
        )
        
        # 4. Create text chunks
        logger.info(f"✂️ Creating chunks for {filename}...")
        chunks = split_text_into_chunks(text_content, max_chunk_size=800, overlap=100)
        
        if not chunks:
            logger.warning(f"⚠️ No chunks created for {filename}")
            return 0
        
        # 5. Process each chunk with embeddings
        chunk_count = 0
        for i, chunk in enumerate(chunks):
            if len(chunk.strip()) < 10:  # Skip very small chunks
                continue
                
            # Generate embedding
            logger.debug(f"🔢 Generating embedding for chunk {i} of {filename}")
            embedding = await openai_service.generate_embeddings(chunk)
            
            if embedding:
                # Store chunk in Cosmos DB
                await cosmos_service.store_document_chunk(
                    file_name=filename,
                    chunk_text=chunk,
                    embedding=embedding,
                    chunk_index=i,
                    metadata={
                        "file_size": file_info.get('size', 0),
                        "last_modified": file_info.get('last_modified'),
                        "content_type": file_info.get('content_type'),
                        "source": "blob_storage",
                        "chunk_length": len(chunk)
                    }
                )
                chunk_count += 1
                logger.debug(f"✅ Stored chunk {i} for {filename}")
            else:
                logger.warning(f"⚠️ Failed to generate embedding for chunk {i} of {filename}")
        
        logger.info(f"✅ Created {chunk_count} chunks for {filename}")
        return chunk_count
        
    except Exception as e:
        logger.error(f"❌ Failed to process {filename}: {str(e)}")
        raise

def split_text_into_chunks(text: str, max_chunk_size: int = 800, overlap: int = 100) -> list:
    """Split text into chunks"""
    if not text or len(text.strip()) < 20:
        return []
    
    chunks = []
    
    # Split by paragraphs first
    paragraphs = text.split('\n\n')
    
    current_chunk = []
    current_length = 0
    
    for paragraph in paragraphs:
        paragraph = paragraph.strip()
        if not paragraph:
            continue
            
        # If paragraph is too large, split by sentences
        if len(paragraph) > max_chunk_size:
            sentences = paragraph.split('. ')
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue
                    
                if current_length + len(sentence) + 2 <= max_chunk_size:
                    current_chunk.append(sentence)
                    current_length += len(sentence) + 2
                else:
                    # Save current chunk
                    if current_chunk:
                        chunks.append('. '.join(current_chunk))
                        
                        # Keep last sentence for overlap
                        if len(current_chunk) > 1:
                            current_chunk = [current_chunk[-1]]
                            current_length = len(current_chunk[0]) + 2
                        else:
                            current_chunk = []
                            current_length = 0
                    
                    current_chunk.append(sentence)
                    current_length = len(sentence) + 2
        else:
            # Paragraph is small enough, add directly
            if current_length + len(paragraph) + 2 <= max_chunk_size:
                current_chunk.append(paragraph)
                current_length += len(paragraph) + 2
            else:
                # Save current chunk and start new
                if current_chunk:
                    chunks.append('\n\n'.join(current_chunk))
                
                current_chunk = [paragraph]
                current_length = len(paragraph)
    
    # Save last chunk
    if current_chunk:
        chunks.append('\n\n'.join(current_chunk))
    
    # Filter out very short chunks
    filtered_chunks = [chunk for chunk in chunks if len(chunk.strip()) > 50]
    
    logger.info(f"📝 Text split into {len(filtered_chunks)} chunks")
    return filtered_chunks