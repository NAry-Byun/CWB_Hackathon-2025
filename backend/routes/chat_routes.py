# routes/chat_routes.py - COMPLETE MERGED Enhanced Chat Routes with Full Notion Integration

from flask import Blueprint, request, jsonify
import asyncio
import sys
import os
import logging
import re
from datetime import datetime
from typing import Dict, Any
from services.notion_service import NotionService

# ─── Allow importing from project root ────────────────────────────────────────
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
logger = logging.getLogger(__name__)

# ─── Import services with graceful fallbacks ──────────────────────────────────
try:
    from services.azure_openai_service import AzureOpenAIService
    logger.info("✅ AzureOpenAIService imported successfully")
except ImportError as e:
    logger.warning(f"⚠️ AzureOpenAIService not available: {e}")
    AzureOpenAIService = None

try:
    from services.cosmos_service import CosmosVectorService
    logger.info("✅ CosmosVectorService imported successfully")
except ImportError as e:
    logger.warning(f"⚠️ CosmosVectorService not available: {e}")
    CosmosVectorService = None

try:
    from services.notion_service import NotionService
    logger.info("✅ NotionService imported successfully")
except ImportError as e:
    logger.warning(f"⚠️ NotionService not available: {e}")
    NotionService = None

try:
    from services.web_scraper_service import EnhancedWebScraperService
    logger.info("✅ EnhancedWebScraperService imported successfully")
except ImportError as e:
    logger.warning(f"⚠️ EnhancedWebScraperService not available: {e}")
    EnhancedWebScraperService = None

# ─── Blueprint Definition ─────────────────────────────────────────────────────
chat_bp = Blueprint('chat', __name__)

# ─── Global service instances ─────────────────────────────────────────────────
openai_service = None
cosmos_service = None
notion_service = None
web_scraper_service = None

def initialize_services():
    """Initialize all available services."""
    global openai_service, cosmos_service, notion_service, web_scraper_service

    # Initialize OpenAI Service
    if AzureOpenAIService:
        try:
            openai_service = AzureOpenAIService()
            logger.info("✅ AzureOpenAIService initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize AzureOpenAIService: {e}")
            openai_service = None

    # Initialize Cosmos Service
    if CosmosVectorService:
        try:
            cosmos_service = CosmosVectorService()
            logger.info("✅ CosmosVectorService initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize CosmosVectorService: {e}")
            cosmos_service = None

    # Initialize Notion Service
    if NotionService:
        try:
            notion_service = NotionService()
            logger.info("✅ NotionService initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize NotionService: {e}")
            notion_service = None

    # Initialize Web Scraper Service
    if EnhancedWebScraperService:
        try:
            web_scraper_service = EnhancedWebScraperService(
                cosmos_service=cosmos_service,
                openai_service=openai_service
            )
            logger.info("🕷️ EnhancedWebScraperService initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize EnhancedWebScraperService: {e}")
            web_scraper_service = None

# Initialize services on import
initialize_services()

# ─── CORS Helper Function ─────────────────────────────────────────────────────
def _handle_cors():
    """Handle CORS preflight requests."""
    response = jsonify()
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type, Authorization")
    response.headers.add("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    return response

# ─── Enhanced Notion Integration Functions ────────────────────────────────────

def detect_notion_write_request(user_message: str) -> Dict[str, Any]:
    """Detect if user wants to write to Notion and extract details (AUTO-WRITE)"""
    
    write_patterns = [
        r"write.*?(?:to|in|on)\s+(?:notion|page)",
        r"add.*?(?:to|in|on)\s+(?:notion|page)", 
        r"save.*?(?:to|in|on)\s+(?:notion|page)",
        r"append.*?(?:to|in|on)\s+(?:notion|page)",
        r"put.*?(?:in|on)\s+(?:notion|page)",
        r"write.*?(?:this|that|summary|response).*?(?:to|in|on)\s+(?:notion|page)",
        r"save.*?(?:this|that|summary|response).*?(?:to|in|on)\s+(?:notion|page)"
    ]
    
    is_write_request = any(re.search(pattern, user_message.lower()) for pattern in write_patterns)
    
    if not is_write_request:
        return {"is_write_request": False}
    
    # Extract page title with enhanced patterns
    page_patterns = [
        r"(?:Meeting\s+Calendar\s*\([^)]+\))",      # Meeting Calendar (July 2025)
        r"([A-Z][A-Za-z\s]+\s*\([^)]+\))",         # Any Title (Something)
        r"page\s+['\"]([^'\"]+)['\"]",              # page "Title"
        r"notion\s+['\"]([^'\"]+)['\"]",            # notion "Title"
        r"(?:to|in|on)\s+([A-Z][A-Za-z\s]{5,30})",  # Generic title after "to/in/on"
        r"(?:to|in|on)\s+(?:my\s+)?([A-Za-z\s]{5,30})\s+(?:notion\s+)?page" # "to my calendar page"
    ]
    
    target_page = None
    for pattern in page_patterns:
        match = re.search(pattern, user_message, re.IGNORECASE)
        if match:
            if match.groups():
                target_page = match.group(1).strip()
            else:
                target_page = match.group(0).strip()
            
            # Clean up common prefixes
            target_page = target_page.replace('my ', '').replace('the ', '').strip()
            break
    
    return {
        "is_write_request": True,
        "target_page": target_page,
        "original_message": user_message,
        "write_type": "auto_write"
    }

def _parse_notion_edit_request(user_message: str) -> dict:
    """Parse user message to detect direct Notion edit requests (DIRECT EDIT)."""
    patterns = [
        r'add\s+(?:text\s+)?["\'](.+?)["\'] to (?:my\s+)?(.+?)\s+notion\s+page',
        r'add\s+["\'](.+?)["\'] to (?:my\s+)?(.+?)\s+page',
        r'add\s+(.+?) to (?:my\s+)?(.+?)\s+notion\s+page',
        r'add\s+(.+?) to (?:my\s+)?(.+?)\s+page',
        r'write\s+["\'](.+?)["\'] in (?:my\s+)?(.+?)\s+(?:notion\s+)?page',
        r'put\s+["\'](.+?)["\'] in (?:my\s+)?(.+?)\s+(?:notion\s+)?page'
    ]
    
    user_lower = user_message.lower().strip()
    
    for pattern in patterns:
        match = re.search(pattern, user_lower, re.IGNORECASE)
        if match:
            content = match.group(1).strip()
            page_title = match.group(2).strip()
            
            page_title = page_title.replace('my ', '').replace('the ', '')
            
            formatting = 'paragraph'
            if content.startswith('#'):
                if content.startswith('### '):
                    formatting = 'heading_3'
                elif content.startswith('## '):
                    formatting = 'heading_2'
                elif content.startswith('# '):
                    formatting = 'heading_1'
            elif content.startswith(('• ', '- ', '* ')):
                formatting = 'bulleted_list'
            
            return {
                'is_notion_edit': True,
                'content': content,
                'page_title': page_title,
                'formatting': formatting,
                'original_message': user_message,
                'edit_type': 'direct_edit'
            }
    
    return {'is_notion_edit': False}

async def handle_notion_write_request(user_message: str, ai_response: str, notion_request: Dict[str, Any]) -> Dict[str, Any]:
    """Handle automatic writing of AI response to Notion"""
    try:
        if not notion_service:
            return {
                "success": False,
                "error": "Notion service not available"
            }
        
        target_page = notion_request.get("target_page")
        
        if not target_page:
            return {
                "success": False,
                "error": "Could not identify target Notion page",
                "suggestion": "Please specify a page like 'Meeting Calendar (July 2025)'"
            }
        
        logger.info(f"🤖 Auto-writing AI response to Notion page: '{target_page}'")
        
        # Use the enhanced write method if available
        if hasattr(notion_service, 'write_chatbot_response_to_page'):
            result = await notion_service.write_chatbot_response_to_page(
                page_title=target_page,
                chatbot_response=ai_response,
                user_question=user_message
            )
        else:
            # Fallback to basic method
            result = notion_service.add_text_by_page_title(
                page_title=target_page,
                text=f"**User Question:** {user_message}\n\n**AI Response:**\n{ai_response}",
                formatting='paragraph'
            )
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Auto-write to Notion failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }

# ─── Main Chat Endpoints ──────────────────────────────────────────────────────

@chat_bp.route('/chat', methods=['POST', 'OPTIONS'])
def chat():
    """Enhanced full chat with integrated Notion auto-write + direct edit detection."""
    if request.method == 'OPTIONS':
        return _handle_cors()

    if not openai_service:
        return _error_response("OpenAI service not available", 503)

    data = request.get_json()
    if not data or 'message' not in data:
        return _error_response("Field 'message' is required", 400)

    user_message = data['message']
    context = data.get('context', [])

    logger.info(f"💬 Full chat: {user_message}")

    try:
        # 🟣 PRIORITY 1: Check for direct Notion edit requests first
        notion_edit_check = _parse_notion_edit_request(user_message)
        
        if notion_edit_check['is_notion_edit'] and notion_service:
            logger.info(f"🟣 DIRECT NOTION EDIT detected: '{notion_edit_check['content']}' -> '{notion_edit_check['page_title']}'")
            
            try:
                result = notion_service.add_text_by_page_title(
                    notion_edit_check['page_title'], 
                    notion_edit_check['content'], 
                    notion_edit_check['formatting']
                )
                
                if result['success']:
                    response_text = f"""✅ **Content Added Successfully!**

**Page**: {result.get('page_title', notion_edit_check['page_title'])}
**Added**: "{notion_edit_check['content']}"
**Time**: {datetime.now().strftime('%Y-%m-%d %H:%M')}

The text has been added to your Notion page.
{f"🔗 View page: {result.get('page_url', '')}" if result.get('page_url') else ""}"""
                    
                    result_data = {
                        "assistant_message": response_text,
                        "content": response_text,
                        "type": "notion_direct_edit",
                        "success": True,
                        "notion_result": result,
                        "azure_services_used": {
                            "openai": False,
                            "cosmos_db": False,
                            "vector_search": False,
                            "notion_edit": True
                        }
                    }
                    
                    logger.info(f"✅ Notion direct edit successful: {result.get('page_title')}")
                    return _success_response(result_data, "Notion page updated successfully")
                
                else:
                    error_text = f"""❌ **Failed to Add Content**

**Error**: {result.get('error', 'Unknown error')}
**Page**: {notion_edit_check['page_title']}
**Content**: "{notion_edit_check['content']}"

**Suggestions**:
{result.get('suggestion', '• Check that the page exists and you have edit permissions')}
• Make sure the page is shared with your Notion integration
• Verify the page title is correct"""

                    result_data = {
                        "assistant_message": error_text,
                        "content": error_text,
                        "type": "notion_direct_edit",
                        "success": False,
                        "notion_result": result,
                        "azure_services_used": {
                            "openai": False,
                            "cosmos_db": False,
                            "vector_search": False,
                            "notion_edit": True
                        }
                    }
                    
                    logger.warning(f"❌ Notion direct edit failed: {result.get('error')}")
                    return _success_response(result_data, "Notion edit attempted but failed")
                
            except Exception as e:
                logger.error(f"❌ Notion direct edit exception: {e}", exc_info=True)
                error_text = f"""❌ **Notion Integration Error**

I encountered an error while trying to add text to your Notion page:
{str(e)}

Please try again or check your Notion integration settings."""

                result_data = {
                    "assistant_message": error_text,
                    "content": error_text,
                    "type": "notion_direct_edit",
                    "success": False,
                    "error": str(e),
                    "azure_services_used": {
                        "openai": False,
                        "cosmos_db": False,
                        "vector_search": False,
                        "notion_edit": False
                    }
                }
                
                return _success_response(result_data, "Notion edit failed due to error")

        # 🟣 PRIORITY 2: Check for auto-write requests (AI response to Notion)
        notion_auto_write_check = detect_notion_write_request(user_message)
        
        if notion_auto_write_check['is_write_request']:
            logger.info(f"🤖 AUTO-WRITE REQUEST detected: Write response to '{notion_auto_write_check.get('target_page')}'")
            
            # Generate AI response first
            result_data = asyncio.run(_process_full_chat(user_message, context))
            ai_response = result_data.get("assistant_message", "")
            
            # Then write it to Notion automatically
            notion_result = asyncio.run(handle_notion_write_request(user_message, ai_response, notion_auto_write_check))
            
            # Enhance response with Notion confirmation
            if notion_result.get("success"):
                page_url = notion_result.get("page_url", "")
                page_title = notion_auto_write_check.get("target_page", "")
                
                result_data["assistant_message"] += f"\n\n✅ **Your response has been automatically saved to your Notion page: '{page_title}'**"
                if page_url:
                    result_data["assistant_message"] += f"\n🔗 [View in Notion]({page_url})"
                
                result_data["notion_integration"] = {
                    "requested": True,
                    "success": True,
                    "target_page": page_title,
                    "result": notion_result,
                    "type": "auto_write"
                }
            else:
                error_msg = notion_result.get("error", "Unknown error")
                result_data["assistant_message"] += f"\n\n❌ **Failed to save to Notion:** {error_msg}"
                
                result_data["notion_integration"] = {
                    "requested": True,
                    "success": False,
                    "target_page": notion_auto_write_check.get("target_page"),
                    "error": error_msg,
                    "type": "auto_write"
                }
            
            result_data["content"] = result_data["assistant_message"]
            logger.info(f"✅ Auto-write chat completed: Notion {'success' if notion_result.get('success') else 'failed'}")
            return _success_response(result_data, "Chat response with auto-write completed")

        # If neither direct edit nor auto-write, continue with normal chat pipeline
        logger.info(f"🔄 Proceeding with normal chat pipeline")
        result_data = asyncio.run(_process_full_chat(user_message, context))
        return _success_response(result_data, "Chat response generated")

    except Exception as e:
        logger.error(f"❌ Full chat error: {e}", exc_info=True)
        return _error_response(f"Chat failed: {str(e)}", 500)

@chat_bp.route('/simple', methods=['POST', 'OPTIONS'])
def simple_chat():
    """Simple chat without vector search - just return OpenAI response."""
    if request.method == 'OPTIONS':
        return _handle_cors()

    if not openai_service:
        return _error_response("OpenAI service not available", 503)

    data = request.get_json()
    if not data or 'message' not in data:
        return _error_response("Field 'message' is required", 400)

    user_message = data['message']
    logger.info(f"💬 Simple chat: {user_message[:100]}")

    try:
        response = asyncio.run(_simple_openai_call(user_message))

        result_data = {
            "assistant_message": response,
            "content": response,
            "mode": "simple",
            "azure_services_used": {
                "openai": True,
                "cosmos_db": False,
                "vector_search": False
            }
        }

        return _success_response(result_data, "Simple chat response generated")

    except Exception as e:
        logger.error(f"❌ Simple chat error: {e}", exc_info=True)
        return _error_response(f"Chat failed: {str(e)}", 500)

# ─── Notion Endpoints ────────────────────────────────────────────────────────
@chat_bp.route('/notion/add-text', methods=['POST', 'OPTIONS'])
def notion_add_text():
    """Direct endpoint for adding text to Notion pages."""
    if request.method == 'OPTIONS':
        return _handle_cors()

    if not notion_service:
        return _error_response("Notion service not available", 503)

    data = request.get_json()
    if not data or 'page_title' not in data or 'content' not in data:
        return _error_response("Fields 'page_title' and 'content' are required", 400)

    page_title = data['page_title']
    content = data['content']
    formatting = data.get('formatting', 'paragraph')

    try:
        logger.info(f"🟣 Direct Notion API call: Adding '{content}' to '{page_title}'")
        
        result = notion_service.add_text_by_page_title(page_title, content, formatting)
        
        if result['success']:
            logger.info(f"✅ Direct Notion add successful: {result.get('page_title')}")
        else:
            logger.warning(f"❌ Direct Notion add failed: {result.get('error')}")
        
        return _success_response(result, "Notion operation completed")

    except Exception as e:
        logger.error(f"❌ Direct Notion add error: {e}", exc_info=True)
        return _error_response(f"Notion operation failed: {str(e)}", 500)

@chat_bp.route('/notion/search', methods=['POST', 'OPTIONS'])
def notion_search():
    """Search Notion pages."""
    if request.method == 'OPTIONS':
        return _handle_cors()

    if not notion_service:
        return _error_response("Notion service not available", 503)

    data = request.get_json()
    if not data or 'query' not in data:
        return _error_response("Field 'query' is required", 400)

    query = data['query']

    try:
        pages = notion_service.search_pages(query)
        
        result = {
            "pages": pages,
            "count": len(pages),
            "query": query
        }
        
        logger.info(f"🔍 Notion search for '{query}': {len(pages)} results")
        return _success_response(result, f"Found {len(pages)} Notion pages")

    except Exception as e:
        logger.error(f"❌ Notion search error: {e}", exc_info=True)
        return _error_response(f"Notion search failed: {str(e)}", 500)

@chat_bp.route('/notion/write-response', methods=['POST', 'OPTIONS'])
def notion_write_response():
    """Enhanced endpoint for writing chatbot responses to Notion."""
    if request.method == 'OPTIONS':
        return _handle_cors()

    if not notion_service:
        return _error_response("Notion service not available", 503)

    data = request.get_json()
    if not data or 'page_title' not in data or 'response' not in data:
        return _error_response("Fields 'page_title' and 'response' are required", 400)

    page_title = data['page_title']
    response_text = data['response']
    user_question = data.get('user_question', '')

    try:
        logger.info(f"🤖 Writing chatbot response to '{page_title}': {len(response_text)} chars")
        
        if hasattr(notion_service, 'write_chatbot_response_to_page'):
            result = asyncio.run(notion_service.write_chatbot_response_to_page(
                page_title, response_text, user_question
            ))
        else:
            # Fallback to basic method
            content = f"**User Question:** {user_question}\n\n**AI Response:**\n{response_text}" if user_question else response_text
            result = notion_service.add_text_by_page_title(page_title, content, 'paragraph')
        
        if result['success']:
            logger.info(f"✅ Chatbot response written to Notion: {result.get('page_title')}")
        else:
            logger.warning(f"❌ Failed to write chatbot response: {result.get('error')}")
        
        return _success_response(result, "Chatbot response write completed")

    except Exception as e:
        logger.error(f"❌ Chatbot response write error: {e}", exc_info=True)
        return _error_response(f"Chatbot response write failed: {str(e)}", 500)

# ─── Health and Test Endpoints ────────────────────────────────────────────────

@chat_bp.route('/health', methods=['GET', 'OPTIONS'])
def chat_health():
    """Health check for chat services."""
    if request.method == 'OPTIONS':
        return _handle_cors()

    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "openai": openai_service is not None,
            "cosmos": cosmos_service is not None,
            "notion": notion_service is not None,
            "web_scraper": web_scraper_service is not None
        },
        "notion_features": {
            "direct_edit": True,
            "auto_write": True,
            "enhanced_search": hasattr(notion_service, 'search_pages_and_content') if notion_service else False,
            "long_text_writing": hasattr(notion_service, 'write_long_text_to_page') if notion_service else False
        },
        "endpoints": [
            "/chat", "/simple", "/health", "/test", "/fix-embeddings",
            "/scrape-url", "/scrape-multiple", "/scrape-test",
            "/notion/add-text", "/notion/search", "/notion/write-response"
        ]
    })

@chat_bp.route('/test', methods=['GET', 'OPTIONS'])
def test_endpoint():
    """Simple test endpoint to confirm that chat routes are working."""
    if request.method == 'OPTIONS':
        return _handle_cors()

    return jsonify({
        "status": "Enhanced Chat routes working",
        "message": "Test endpoint successful with full Notion integration",
        "timestamp": datetime.now().isoformat(),
        "backend_url": "http://localhost:5000",
        "features": [
            "Direct Notion Edit",
            "Auto-write AI responses to Notion", 
            "Enhanced content search",
            "Vector similarity search",
            "Full document integration"
        ]
    })

# ─── Other Endpoints ──────────────────────────────────────────────────────────

@chat_bp.route('/fix-embeddings', methods=['POST', 'OPTIONS'])
def fix_embeddings():
    """Fix missing embeddings for stored documents in Cosmos DB."""
    if request.method == 'OPTIONS':
        return _handle_cors()

    if not openai_service or not cosmos_service:
        return _error_response("Services not available", 503)

    try:
        result = asyncio.run(_fix_embeddings_async())
        return _success_response(result, "임베딩 수정 완료")
    except Exception as e:
        logger.error(f"❌ 임베딩 수정 오류: {e}", exc_info=True)
        return _error_response(f"임베딩 수정 실패: {str(e)}", 500)

# ─── Async Helper Functions ───────────────────────────────────────────────────

async def _simple_openai_call(user_message: str) -> str:
    """Simple OpenAI call without any context."""
    try:
        if openai_service and hasattr(openai_service, 'generate_response'):
            response = await openai_service.generate_response(
                user_message=user_message,
                context=[],
                document_chunks=[],
                notion_pages=[]
            )
            if isinstance(response, dict):
                return response.get("assistant_message", str(response))
            return str(response)
        elif openai_service and hasattr(openai_service, 'chat_completion'):
            return await openai_service.chat_completion(user_message)
        else:
            return "OpenAI service is not properly configured."
    except Exception as e:
        logger.error(f"❌ OpenAI call failed: {e}", exc_info=True)
        return f"I apologize, but I encountered an error: {str(e)}"

async def _process_full_chat(user_message: str, context: list) -> dict:
    """Process chat with full pipeline: Notion search, embedding 생성, Cosmos 검색, then OpenAI."""
    result_data = {
        "assistant_message": "",
        "content": "",
        "sources": [],
        "azure_services_used": {
            "openai": False,
            "openai_embedding": False,
            "cosmos_db": False,
            "vector_search": False,
            "notion_search": False,
            "document_chunks": 0
        },
        "notion_pages": [],
        "document_chunks": []
    }

    try:
        # 1. Notion 검색 (예약어 기반)
        notion_pages = []
        if notion_service and any(
            kw in user_message.lower()
            for kw in ["notion", "meeting", "agenda", "schedule", "calendar", "june", "july"]
        ):
            try:
                notion_pages = await _search_notion(user_message)
                result_data["notion_pages"] = notion_pages
                result_data["azure_services_used"]["notion_search"] = len(notion_pages) > 0
                logger.info(f"🔍 Found {len(notion_pages)} Notion pages")

                if notion_pages:
                    for i, page in enumerate(notion_pages[:3]):
                        logger.info(f"📄 Notion page {i+1}: {page.get('title', 'No title')}")

            except Exception as e:
                logger.error(f"❌ Notion search failed: {e}", exc_info=True)

        # 2. Cosmos DB 벡터 검색
        document_chunks = []
        if cosmos_service:
            try:
                await cosmos_service.initialize_database()
                result_data["azure_services_used"]["cosmos_db"] = True

                # embedding 생성
                embedding = await openai_service.generate_embeddings(user_message)
                if embedding:
                    result_data["azure_services_used"]["openai_embedding"] = True

                    search_results = await cosmos_service.search_similar_chunks(
                        embedding, limit=5, similarity_threshold=0.1
                    )
                    if search_results:
                        result_data["azure_services_used"]["vector_search"] = True

                        document_chunks = [
                            {
                                "file_name": r.get("file_name", "unknown"),
                                "content": r.get("chunk_text", "")[:1000],
                                "similarity": r.get("similarity", 0.0)
                            }
                            for r in search_results
                        ]
                        result_data["sources"] = [
                            f"{r.get('file_name', '?')} ({int(r.get('similarity', 0.0)*100)}%)"
                            for r in search_results
                        ]

                    logger.info(f"🔍 Found {len(document_chunks)} document chunks")

            except Exception as e:
                logger.error(f"❌ Cosmos search failed: {e}", exc_info=True)

        result_data["document_chunks"] = document_chunks
        result_data["azure_services_used"]["document_chunks"] = len(document_chunks)

        # 3. Debug logs before sending to AI
        logger.info(f"🔍 Sending to AI - Notion pages: {len(notion_pages)}")
        logger.info(f"🔍 Sending to AI - Document chunks: {len(document_chunks)}")
        logger.info(f"🔍 User message: {user_message}")

        # 4. OpenAI 최종 응답 생성
        ai_response = await openai_service.generate_response(
            user_message=user_message,
            context=context,
            document_chunks=document_chunks,
            notion_pages=notion_pages,
            max_tokens=1500,
            temperature=0.7
        )

        if isinstance(ai_response, dict):
            response_text = ai_response.get("assistant_message", str(ai_response))
        else:
            response_text = str(ai_response)

        # 5. 응답이 너무 짧으면 Notion 데이터로 보강
        if len(response_text) < 100 and notion_pages:
            logger.warning(f"⚠️ AI response too short ({len(response_text)} chars), enhancing with Notion data")
            enhanced_response = response_text + "\n\n📝 **Notion에서 찾은 정보:**\n"
            for i, page in enumerate(notion_pages[:3]):
                title = page.get('title', 'Untitled')
                content_preview = page.get('content_preview', page.get('content', ''))[:200]
                url = page.get('url', '')
                
                enhanced_response += f"\n{i+1}. **{title}**"
                if content_preview and content_preview != 'Unable to load content':
                    enhanced_response += f"\n   📝 {content_preview}..."
                if url:
                    enhanced_response += f"\n   🔗 {url}"
                enhanced_response += "\n"
            response_text = enhanced_response
            logger.info(f"✅ Enhanced response with Notion data: {len(response_text)} characters")

        if not response_text.strip():
            response_text = "죄송합니다. 응답을 생성하는 데 문제가 발생했습니다. 다시 시도해주세요."

        result_data["assistant_message"] = response_text
        result_data["content"] = response_text
        result_data["azure_services_used"]["openai"] = True

        logger.info(f"✅ Generated response: {len(response_text)} characters")

    except Exception as e:
        logger.error(f"❌ Full chat processing failed: {e}", exc_info=True)
        error_msg = f"I apologize, but I encountered an error: {str(e)}"
        result_data["assistant_message"] = error_msg
        result_data["content"] = error_msg

    return result_data

async def _search_notion(query: str) -> list:
    """Enhanced Notion search with content reading capabilities."""
    if not notion_service:
        return []

    try:
        # Check if this is a meeting-related query
        meeting_keywords = ['meeting', 'meetings', '회의', '미팅', 'calendar', 'schedule']
        is_meeting_query = any(keyword in query.lower() for keyword in meeting_keywords)
        
        if is_meeting_query:
            logger.info(f"🗓️ Detected meeting-related query: {query}")
            
            # Check for month-specific queries
            month_match = re.search(r'(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)', query.lower())
            
            if month_match:
                month = month_match.group(1)
                logger.info(f"🗓️ Detected month-specific query: {month}")
                
                try:
                    meetings = notion_service.get_meetings_for_month(month)
                    
                    detailed_pages = []
                    for meeting in meetings:
                        page_data = {
                            "id": f"meeting_{len(detailed_pages)}",
                            "title": meeting.get('title', 'Untitled Meeting'),
                            "url": meeting.get('page_url', ''),
                            "last_edited_time": '',
                            "created_time": '',
                            "content": f"""Meeting: {meeting.get('title', 'No title')}
{meeting.get('datetime', 'No date/time specified')}
{meeting.get('location', '')}
{meeting.get('participants', '')}
Source: {meeting.get('source_page', 'Unknown')}""",
                            "content_preview": f"Meeting: {meeting.get('title', 'No title')} - {meeting.get('datetime', 'No date/time specified')}",
                            "meeting_info": meeting
                        }
                        detailed_pages.append(page_data)
                    
                    logger.info(f"✅ Found {len(meetings)} meetings for {month}")
                    return detailed_pages
                    
                except Exception as e:
                    logger.error(f"❌ Month-specific meeting search failed: {e}")
        
        # For non-month-specific queries or fallback, use enhanced search
        try:
            # Use enhanced search if available
            if hasattr(notion_service, 'search_pages_and_content'):
                pages = notion_service.search_pages_and_content(query, limit=10)
            elif hasattr(notion_service, 'search_meeting_pages'):
                pages = notion_service.search_meeting_pages(query)
            else:
                pages = notion_service.search_pages(query)
                
                # Enhance with content if basic search
                enhanced_pages = []
                for page in pages:
                    try:
                        page_id = page.get('id', '')
                        if page_id and hasattr(notion_service, 'get_page_content'):
                            content = notion_service.get_page_content(page_id)
                            page['content'] = content
                            page['content_preview'] = content[:500] + "..." if len(content) > 500 else content
                        enhanced_pages.append(page)
                    except Exception as e:
                        logger.error(f"❌ Error getting content for page {page.get('id', 'unknown')}: {e}")
                        enhanced_pages.append(page)
                
                pages = enhanced_pages

        except Exception as e:
            logger.error(f"❌ Enhanced search failed, falling back to basic search: {e}")
            pages = notion_service.search_pages(query) if hasattr(notion_service, 'search_pages') else []

        detailed_pages = []
        for p in pages:
            if isinstance(p, dict):
                # Extract proper title
                title = p.get("title", "Untitled")
                if title == "Untitled" or not title:
                    title = notion_service._extract_page_title(p) if hasattr(notion_service, '_extract_page_title') else "Untitled"
                
                page_data = {
                    "id": p.get("id", ""),
                    "title": title,
                    "url": p.get("url", ""),
                    "last_edited_time": p.get("last_edited_time", ""),
                    "created_time": p.get("created_time", ""),
                    "content": p.get("content", "")[:2000] if p.get("content") else "",
                    "content_preview": p.get("content_preview", "")
                }
                detailed_pages.append(page_data)

        logger.info(f"✅ Enhanced Notion search completed: {len(detailed_pages)} pages found")
        return detailed_pages

    except Exception as e:
        logger.error(f"❌ Notion search error: {e}", exc_info=True)
        return []

async def _fix_embeddings_async():
    """Fix missing embeddings for all documents in Cosmos DB asynchronously."""
    base_result = {
        "total_documents": 0,
        "fixed_count": 0,
        "error_count": 0,
        "status": "완료"
    }

    try:
        if not cosmos_service:
            base_result["status"] = "Cosmos service not available"
            return base_result
            
        await cosmos_service.initialize_database()
        
        # Use the new fix method if available
        if hasattr(cosmos_service, 'fix_missing_embeddings'):
            return await cosmos_service.fix_missing_embeddings()
        
        # Fallback to basic fix
        base_result["status"] = "Basic fix completed"
        return base_result

    except Exception as e:
        logger.error(f"❌ _fix_embeddings_async 전체 오류: {e}", exc_info=True)
        base_result["status"] = "오류 발생"
        base_result["error"] = str(e)

    return base_result

# ─── Response Helpers ─────────────────────────────────────────────────────────

def _success_response(data, message="Success"):
    """Create standardized success response with CORS headers."""
    response = jsonify({
        "success": True,
        "message": message,
        "data": data,
        "timestamp": datetime.now().isoformat()
    })
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response

def _error_response(message, status_code=400):
    """Create standardized error response with CORS headers."""
    response = jsonify({
        "success": False,
        "error": message,
        "timestamp": datetime.now().isoformat()
    })
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response, status_code