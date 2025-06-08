# routes/document_routes.py - Fixed Document Upload Service

from flask import Blueprint, request, jsonify
import asyncio
import sys
import os
import logging
from datetime import datetime
from typing import Dict, Any, List

# Import the same services from your chat routes
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
logger = logging.getLogger(__name__)

# Import services (same as chat_routes.py)
try:
    from services.azure_openai_service import AzureOpenAIService
    from services.cosmos_service import CosmosVectorService
    from services.azure_ai_search_service import AzureAISearchService
except ImportError as e:
    logger.warning(f"⚠️ Service import failed: {e}")

document_bp = Blueprint('documents', __name__)

# Use the same service instances from chat_routes
try:
    from routes.chat_routes import openai_service, cosmos_service, azure_search_service
except ImportError:
    logger.warning("⚠️ Could not import services from chat_routes, services may not be available")
    openai_service = None
    cosmos_service = None
    azure_search_service = None

def _handle_cors():
    """Handle CORS preflight requests."""
    response = jsonify()
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type, Authorization")
    response.headers.add("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    return response

def _success_response(data: Dict[str, Any], message: str = "Success") -> tuple:
    """Create a standardized success response with nested data structure."""
    response = {
        "success": True,
        "message": message,
        "timestamp": datetime.now().isoformat(),
        "data": data
    }
    return jsonify(response), 200

def _error_response(error_message: str, status_code: int = 400) -> tuple:
    """Create a standardized error response."""
    response = {
        "success": False,
        "error": error_message,
        "timestamp": datetime.now().isoformat(),
        "data": None
    }
    return jsonify(response), status_code

# FIXED: Document processing functions with corrected syntax
def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 100) -> List[str]:
    """Split text into overlapping chunks."""
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        
        # Try to find a good breaking point (sentence or paragraph)
        if end < len(text):
            # Look for sentence endings
            sentence_found = False
            for i in range(end, max(start + chunk_size // 2, end - 200), -1):
                if text[i] in '.!?':
                    end = i + 1
                    sentence_found = True
                    break
            
            # FIXED: If no sentence ending found, look for paragraph breaks
            if not sentence_found and '\n\n' in text[start:end]:
                para_break = text.rfind('\n\n', start, end)
                if para_break > start:
                    end = para_break + 2
        
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        start = end - overlap if end < len(text) else end
    
    return chunks

async def process_document_content(file_content: bytes, file_name: str) -> List[Dict[str, Any]]:
    """Process document content into chunks with embeddings."""
    try:
        # Decode file content
        if file_name.lower().endswith(('.txt', '.md')):
            text_content = file_content.decode('utf-8', errors='ignore')
        elif file_name.lower().endswith('.json'):
            text_content = file_content.decode('utf-8', errors='ignore')
        elif file_name.lower().endswith('.csv'):
            text_content = file_content.decode('utf-8', errors='ignore')
        else:
            # For other file types, you'd need proper document parsing
            # This is a simplified version
            try:
                text_content = file_content.decode('utf-8', errors='ignore')
            except:
                text_content = str(file_content)
        
        # Split into chunks
        text_chunks = chunk_text(text_content, chunk_size=1000, overlap=100)
        
        document_chunks = []
        for i, chunk_text in enumerate(text_chunks):
            if chunk_text.strip():
                chunk = {
                    "chunk_text": chunk_text,
                    "chunk_index": i,
                    "file_name": file_name,
                    "source": "document_upload",
                    "document_type": "text_chunk",
                    "upload_timestamp": datetime.now().isoformat(),
                    "embedding": None
                }
                
                # Generate embedding if OpenAI service is available
                if openai_service:
                    try:
                        embedding = await openai_service.generate_embeddings(chunk_text)
                        chunk["embedding"] = embedding
                        chunk["vector_dimensions"] = len(embedding) if embedding else 0
                    except Exception as e:
                        logger.warning(f"Failed to generate embedding for chunk {i}: {e}")
                
                document_chunks.append(chunk)
        
        return document_chunks
        
    except Exception as e:
        logger.error(f"❌ Document processing failed: {e}")
        raise

async def store_in_cosmos_db(document_chunks: List[Dict[str, Any]], file_name: str) -> bool:
    """Store document chunks in Cosmos DB."""
    try:
        if not cosmos_service:
            logger.warning("Cosmos DB service not available")
            return False
        
        await cosmos_service.initialize_database()
        
        for chunk in document_chunks:
            # Prepare document for Cosmos DB
            cosmos_doc = {
                "id": f"{file_name}_{chunk['chunk_index']}_{int(datetime.now().timestamp())}",
                **chunk
            }
            
            # Store in Cosmos DB
            await cosmos_service.container.create_item(body=cosmos_doc)
        
        logger.info(f"✅ Stored {len(document_chunks)} chunks in Cosmos DB for {file_name}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to store in Cosmos DB: {e}")
        return False

async def store_in_azure_search(document_chunks: List[Dict[str, Any]], file_name: str) -> bool:
    """Store document chunks in Azure AI Search."""
    try:
        if not azure_search_service:
            logger.warning("Azure AI Search service not available")
            return False
        
        search_documents = []
        
        for chunk in document_chunks:
            search_doc = {
                "id": f"{file_name}_{chunk['chunk_index']}_{int(datetime.now().timestamp())}",
                "content": chunk["chunk_text"],
                "file_name": file_name,
                "chunk_index": chunk["chunk_index"],
                "title": file_name.replace('.', ' ').replace('_', ' '),
                "upload_timestamp": chunk["upload_timestamp"],
                "source": "document_upload"
            }
            
            # Add vector field if embeddings are available
            if chunk.get("embedding"):
                search_doc["contentVector"] = chunk["embedding"]
            
            search_documents.append(search_doc)
        
        # Upload to Azure AI Search
        result = await azure_search_service.upload_documents(search_documents)
        
        if result:
            logger.info(f"✅ Stored {len(search_documents)} chunks in Azure AI Search for {file_name}")
            return True
        else:
            logger.error(f"❌ Failed to upload to Azure AI Search for {file_name}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Failed to store in Azure AI Search: {e}")
        return False

@document_bp.route('/upload', methods=['POST', 'OPTIONS'])
def upload_document():
    """Upload document and store in both Cosmos DB and Azure AI Search."""
    if request.method == 'OPTIONS':
        return _handle_cors()
    
    try:
        # Check if file is in request
        if 'file' not in request.files:
            return _error_response("No file provided", 400)
        
        file = request.files['file']
        
        # Check if file was selected
        if file.filename == '':
            return _error_response("No file selected", 400)
        
        # Validate file type
        allowed_extensions = {'.txt', '.md', '.pdf', '.docx', '.csv', '.json'}
        file_extension = os.path.splitext(file.filename)[1].lower()
        
        if file_extension not in allowed_extensions:
            return _error_response(f"File type {file_extension} not supported. Supported: {', '.join(allowed_extensions)}", 400)
        
        # Read file content
        file_content = file.read()
        file_name = file.filename
        
        logger.info(f"📄 Processing uploaded file: {file_name} ({len(file_content)} bytes)")
        
        # Process document in async context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Process document into chunks
            document_chunks = loop.run_until_complete(
                process_document_content(file_content, file_name)
            )
            
            if not document_chunks:
                return _error_response("No content could be extracted from the document", 400)
            
            # Store in both Cosmos DB and Azure AI Search
            cosmos_success = loop.run_until_complete(
                store_in_cosmos_db(document_chunks, file_name)
            )
            
            azure_search_success = loop.run_until_complete(
                store_in_azure_search(document_chunks, file_name)
            )
            
        finally:
            loop.close()
        
        # Prepare response
        result_data = {
            "document_id": f"{file_name}_{int(datetime.now().timestamp())}",
            "file_name": file_name,
            "file_size": len(file_content),
            "chunks_processed": len(document_chunks),
            "storage_results": {
                "cosmos_db": cosmos_success,
                "azure_ai_search": azure_search_success
            },
            "upload_timestamp": datetime.now().isoformat(),
            "embeddings_generated": any(chunk.get("embedding") for chunk in document_chunks),
            "services_used": {
                "cosmos_db_available": cosmos_service is not None,
                "azure_search_available": azure_search_service is not None,
                "openai_available": openai_service is not None
            }
        }
        
        # Determine overall success
        if cosmos_success or azure_search_success:
            message = "Document uploaded successfully"
            if not cosmos_success:
                message += " (Cosmos DB storage failed)"
            elif not azure_search_success:
                message += " (Azure AI Search indexing failed)"
            
            logger.info(f"✅ {message}: {file_name}")
            return _success_response(result_data, message)
        else:
            logger.error(f"❌ Failed to store {file_name} in any storage system")
            return _error_response("Failed to store document in any storage system", 500)
        
    except Exception as e:
        logger.error(f"❌ Document upload failed: {e}")
        return _error_response(f"Upload failed: {str(e)}", 500)

@document_bp.route('/list', methods=['GET', 'OPTIONS'])
def list_documents():
    """List uploaded documents."""
    if request.method == 'OPTIONS':
        return _handle_cors()
    
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            documents = loop.run_until_complete(_get_document_list())
        finally:
            loop.close()
        
        return _success_response({
            "documents": documents,
            "count": len(documents),
            "services_checked": {
                "cosmos_db": cosmos_service is not None,
                "azure_ai_search": azure_search_service is not None
            }
        }, f"Found {len(documents)} documents")
        
    except Exception as e:
        logger.error(f"❌ Failed to list documents: {e}")
        return _error_response(f"Failed to list documents: {str(e)}", 500)

async def _get_document_list():
    """Get list of documents from storage systems."""
    documents = []
    
    # Get from Cosmos DB if available
    if cosmos_service:
        try:
            await cosmos_service.initialize_database()
            
            query = """
                SELECT DISTINCT c.file_name, 
                       MIN(c.upload_timestamp) as upload_timestamp,
                       COUNT(1) as chunk_count
                FROM c 
                WHERE c.source = 'document_upload'
                GROUP BY c.file_name
                ORDER BY MIN(c.upload_timestamp) DESC
            """
            
            items = cosmos_service.container.query_items(
                query=query,
                enable_cross_partition_query=True
            )
            
            async for item in items:
                documents.append({
                    "file_name": item["file_name"],
                    "upload_timestamp": item["upload_timestamp"],
                    "chunk_count": item["chunk_count"],
                    "source": "cosmos_db"
                })
                
        except Exception as e:
            logger.error(f"❌ Failed to get Cosmos DB documents: {e}")
    
    # Get from Azure AI Search if available and no Cosmos results
    if not documents and azure_search_service:
        try:
            search_results = await azure_search_service.search_documents(
                query="*",
                top=1000,
                select=["file_name", "upload_timestamp"]
            )
            
            # Group by file name
            file_groups = {}
            for result in search_results:
                file_name = result.get("file_name", "unknown")
                if file_name not in file_groups:
                    file_groups[file_name] = {
                        "file_name": file_name,
                        "upload_timestamp": result.get("upload_timestamp"),
                        "chunk_count": 0,
                        "source": "azure_ai_search"
                    }
                file_groups[file_name]["chunk_count"] += 1
            
            documents = list(file_groups.values())
            
        except Exception as e:
            logger.error(f"❌ Failed to get Azure AI Search documents: {e}")
    
    return documents

@document_bp.route('/delete/<document_id>', methods=['DELETE', 'OPTIONS'])
def delete_document(document_id):
    """Delete a document and all its chunks."""
    if request.method == 'OPTIONS':
        return _handle_cors()
    
    try:
        # Extract file name from document_id
        file_name = document_id.split('_')[0] if '_' in document_id else document_id
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(_delete_document_chunks(file_name))
        finally:
            loop.close()
        
        return _success_response(result, f"Document {file_name} deletion completed")
        
    except Exception as e:
        logger.error(f"❌ Failed to delete document: {e}")
        return _error_response(f"Failed to delete document: {str(e)}", 500)

async def _delete_document_chunks(file_name: str):
    """Delete all chunks for a document from both storage systems."""
    results = {
        "cosmos_db": {"attempted": False, "success": False, "deleted_count": 0},
        "azure_ai_search": {"attempted": False, "success": False, "deleted_count": 0}
    }
    
    # Delete from Cosmos DB
    if cosmos_service:
        try:
            results["cosmos_db"]["attempted"] = True
            await cosmos_service.initialize_database()
            
            # Find all chunks for this file
            query = f"SELECT * FROM c WHERE c.file_name = '{file_name}'"
            items = cosmos_service.container.query_items(
                query=query,
                enable_cross_partition_query=True
            )
            
            deleted_count = 0
            async for item in items:
                await cosmos_service.container.delete_item(
                    item=item["id"],
                    partition_key=item["id"]
                )
                deleted_count += 1
            
            results["cosmos_db"]["success"] = True
            results["cosmos_db"]["deleted_count"] = deleted_count
            
        except Exception as e:
            logger.error(f"❌ Failed to delete from Cosmos DB: {e}")
    
    # Delete from Azure AI Search
    if azure_search_service:
        try:
            results["azure_ai_search"]["attempted"] = True
            
            # Find all documents for this file
            search_results = await azure_search_service.search_documents(
                query=f'file_name:"{file_name}"',
                top=1000,
                select=["id"]
            )
            
            if search_results:
                # Prepare delete documents
                delete_docs = [{"id": doc["id"], "@search.action": "delete"} for doc in search_results]
                
                # Delete from Azure AI Search
                delete_result = await azure_search_service.upload_documents(delete_docs)
                
                results["azure_ai_search"]["success"] = delete_result
                results["azure_ai_search"]["deleted_count"] = len(delete_docs)
            else:
                results["azure_ai_search"]["success"] = True
                results["azure_ai_search"]["deleted_count"] = 0
                
        except Exception as e:
            logger.error(f"❌ Failed to delete from Azure AI Search: {e}")
    
    return results

@document_bp.route('/health', methods=['GET', 'OPTIONS'])
def documents_health():
    """Health check for document upload service."""
    if request.method == 'OPTIONS':
        return _handle_cors()
    
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "openai": openai_service is not None,
            "cosmos_db": cosmos_service is not None,
            "azure_ai_search": azure_search_service is not None
        },
        "features": [
            "Document upload and processing",
            "Text chunking with overlap", 
            "Automatic embedding generation",
            "Dual storage (Cosmos DB + Azure AI Search)",
            "Document listing and deletion"
        ],
        "supported_formats": [".txt", ".md", ".pdf", ".docx", ".csv", ".json"],
        "endpoints": [
            "/upload", "/list", "/delete/<document_id>", "/health"
        ],
        "syntax_fixed": True,
        "chunking_algorithm": "sentence_boundary_with_paragraph_fallback"
    })