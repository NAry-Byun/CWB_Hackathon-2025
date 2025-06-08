from flask import Blueprint, request, jsonify
import asyncio
import sys
import os
import logging
import re
from datetime import datetime
from typing import Dict, Any, List, Optional

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
    from services.azure_ai_search_service import AzureAISearchService
    logger.info("✅ AzureAISearchService imported successfully")
except ImportError as e:
    logger.warning(f"⚠️ AzureAISearchService not available: {e}")
    AzureAISearchService = None

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
azure_search_service = None
web_scraper_service = None
services_initialized = False

def initialize_services():
    """Initialize all available services safely."""
    global openai_service, cosmos_service, notion_service, azure_search_service, web_scraper_service, services_initialized

    if services_initialized:
        return

    # Initialize OpenAI Service (Required)
    if AzureOpenAIService:
        try:
            openai_service = AzureOpenAIService()
            logger.info("✅ AzureOpenAIService initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize AzureOpenAIService: {e}")
            openai_service = None

    # Initialize Cosmos Service (Optional)
    if CosmosVectorService and openai_service:
        try:
            cosmos_service = CosmosVectorService()
            cosmos_service.set_openai_service(openai_service)
            logger.info("✅ CosmosVectorService initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize CosmosVectorService: {e}")
            cosmos_service = None

    # Initialize Azure AI Search Service (Optional)
    if AzureAISearchService and openai_service:
        try:
            azure_search_service = AzureAISearchService()
            azure_search_service.set_openai_service(openai_service)
            logger.info("✅ AzureAISearchService initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize AzureAISearchService: {e}")
            azure_search_service = None

    # Initialize Notion Service (Optional)
    if NotionService:
        try:
            notion_service = NotionService()
            logger.info("✅ NotionService initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize NotionService: {e}")
            notion_service = None

    # Initialize Web Scraper Service (Optional)
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

    services_initialized = True
    logger.info("🚀 All services initialization completed")

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

# ─── Response Helper Functions ────────────────────────────────────────────────
def _success_response(data: Dict[str, Any], message: str = "Success") -> tuple:
    """Create a standardized success response."""
    response = {
        "success": True,
        "message": message,
        "timestamp": datetime.now().isoformat(),
        **data
    }
    return jsonify(response), 200

def _error_response(error_message: str, status_code: int = 400) -> tuple:
    """Create a standardized error response."""
    response = {
        "success": False,
        "error": error_message,
        "timestamp": datetime.now().isoformat()
    }
    return jsonify(response), status_code

# ─── FIXED: Page Title Normalization ─────────────────────────────────────────

def _normalize_page_title(title_raw: str) -> str:
    """Normalize and match page titles to handle variations"""
    # Remove common prefixes
    title = title_raw.replace('my ', '').replace('the ', '').strip()
    
    # Common page title patterns and their normalized forms
    title_mappings = {
        'meeting calendar july 2025': 'Meeting Calendar (July 2025)',
        'meeting calendar (july 2025)': 'Meeting Calendar (July 2025)',
        'meeting calendar': 'Meeting Calendar (July 2025)',  # Default to current month
        'calendar july 2025': 'Meeting Calendar (July 2025)',
        'july 2025 calendar': 'Meeting Calendar (July 2025)',
        'july calendar': 'Meeting Calendar (July 2025)',
        'meeting calendar july': 'Meeting Calendar (July 2025)'
    }
    
    # Check direct mappings first
    title_lower = title.lower()
    if title_lower in title_mappings:
        return title_mappings[title_lower]
    
    # Try to construct proper format for meeting calendar patterns
    if 'meeting' in title_lower and 'calendar' in title_lower:
        if 'july' in title_lower or '2025' in title_lower:
            return 'Meeting Calendar (July 2025)'
        else:
            return 'Meeting Calendar (July 2025)'  # Default
    
    # For other titles, try to maintain proper capitalization
    if '(' in title and ')' in title:
        return title.title()
    
    return title

# ─── Enhanced Notion Integration Functions ────────────────────────────────────

def detect_notion_write_request(user_message: str) -> Dict[str, Any]:
    """Detect if user wants to write to Notion and extract details (AUTO-WRITE) - FIXED"""
    
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
    
    # Enhanced page title extraction patterns
    page_patterns = [
        r"(?:Meeting\s+Calendar\s*\([^)]+\))",              # Meeting Calendar (July 2025)
        r"(?:meeting\s+calendar\s+july\s+2025)",            # meeting calendar july 2025
        r"(?:meeting\s+calendar\s+\([^)]+\))",             # meeting calendar (july 2025)
        r"([A-Z][A-Za-z\s]+\s*\([^)]+\))",                 # Any Title (Something)
        r"page\s+['\"]([^'\"]+)['\"]",                      # page "Title"
        r"notion\s+['\"]([^'\"]+)['\"]",                    # notion "Title"
        r"(?:to|in|on)\s+(?:my\s+)?([A-Za-z\s]{5,50})\s+(?:notion\s+)?page"  # to my calendar page
    ]
    
    target_page = None
    for pattern in page_patterns:
        match = re.search(pattern, user_message, re.IGNORECASE)
        if match:
            # Handle different group scenarios
            if match.groups():
                if len(match.groups()) >= 1 and match.group(1):
                    target_page = match.group(1).strip()
                else:
                    target_page = match.group(0).strip()
            else:
                target_page = match.group(0).strip()
            
            if target_page:
                # Normalize the extracted title
                target_page = _normalize_page_title(target_page)
                break
    
    return {
        "is_write_request": True,
        "target_page": target_page,
        "original_message": user_message,
        "write_type": "auto_write"
    }

def _parse_notion_edit_request(user_message: str) -> dict:
    """Parse user message to detect direct Notion edit requests (DIRECT EDIT) - FIXED"""
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
            page_title_raw = match.group(2).strip()
            
            # Clean up page title and try to match known patterns
            page_title = _normalize_page_title(page_title_raw)
            
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

def handle_notion_write_request_sync(user_message: str, ai_response: str, notion_request: Dict[str, Any]) -> Dict[str, Any]:
    """Handle automatic writing of AI response to Notion - synchronous version"""
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
        
        # Try enhanced async method first
        if hasattr(notion_service, 'write_chatbot_response_to_page'):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(
                    notion_service.write_chatbot_response_to_page(target_page, ai_response, user_message)
                )
            finally:
                loop.close()
        else:
            # Fallback to basic method
            page = notion_service.get_page_by_title(target_page)
            if page:
                page_id = page['id']
                content = f"**User Question:** {user_message}\n\n**AI Response:**\n{ai_response}"
                success = notion_service.add_text_to_page(page_id, content, 'paragraph')
                result = {
                    "success": success,
                    "page_title": target_page,
                    "page_id": page_id,
                    "page_url": page.get('url', '')
                }
            else:
                result = {
                    "success": False,
                    "error": f"Page '{target_page}' not found"
                }
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Auto-write to Notion failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }

async def handle_notion_write_request(user_message: str, ai_response: str, notion_request: Dict[str, Any]) -> Dict[str, Any]:
    """Handle automatic writing of AI response to Notion - async wrapper"""
    return handle_notion_write_request_sync(user_message, ai_response, notion_request)

# ─── FIXED: Notion Search Function ───────────────────────────────────────────

async def _search_notion(user_message: str) -> List[Dict[str, Any]]:
    """Search Notion pages based on user message - FIXED nested event loop"""
    try:
        if not notion_service:
            return []
        
        # Enhanced keyword extraction
        keywords = user_message.lower().split()
        relevant_keywords = [kw for kw in keywords if len(kw) > 2 and kw not in [
            'what', 'when', 'where', 'how', 'why', 'the', 'and', 'or', 'do', 'have', 'my', 'in'
        ]]
        
        # Add specific search terms for known patterns
        search_terms = []
        if any(term in user_message.lower() for term in ['july', '2025', 'meeting', 'calendar']):
            search_terms.extend(['meeting', 'calendar', 'july', '2025'])
        
        # Combine relevant keywords with specific terms
        all_search_terms = list(set(relevant_keywords + search_terms))
        search_query = ' '.join(all_search_terms[:5])  # Use top 5 terms
        
        logger.info(f"🔍 Searching Notion with enhanced query: '{search_query}'")
        
        # Search for pages with enhanced method if available
        if hasattr(notion_service, 'search_pages_and_content'):
            # FIX: Since we're already in an async context, just await directly
            # NO event loop creation needed - we're already inside one
            pages = await notion_service.search_pages_and_content(search_query, limit=10)
            logger.info(f"✅ Enhanced Notion search found {len(pages)} results")
        else:
            # Fallback to basic search with multiple queries
            all_pages = []
            for term in ['meeting calendar', 'july 2025', search_query]:
                if term.strip():
                    pages = notion_service.search_pages(term.strip())
                    all_pages.extend(pages)
            
            # Remove duplicates based on page ID
            seen_ids = set()
            unique_pages = []
            for page in all_pages:
                page_id = page.get('id')
                if page_id and page_id not in seen_ids:
                    seen_ids.add(page_id)
                    unique_pages.append(page)
            
            pages = unique_pages[:10]
            logger.info(f"✅ Basic Notion search found {len(pages)} results")
        
        return pages[:3]  # Return top 3 matches
        
    except Exception as e:
        logger.error(f"❌ Notion search failed: {e}")
        return []

# ─── Main Chat Endpoints ──────────────────────────────────────────────────────

@chat_bp.route('/chat', methods=['POST', 'OPTIONS'])
def chat():
    """Enhanced full chat with Azure AI Search + Notion + Cosmos DB integration."""
    if request.method == 'OPTIONS':
        return _handle_cors()

    if not openai_service:
        return _error_response("OpenAI service not available", 503)

    data = request.get_json()
    if not data or 'message' not in data:
        return _error_response("Field 'message' is required", 400)

    user_message = data['message']
    context = data.get('context', [])

    logger.info(f"💬 Enhanced chat with Azure AI Search: {user_message}")

    try:
        # 🟣 PRIORITY 1: Check for direct Notion edit requests first
        notion_edit_check = _parse_notion_edit_request(user_message)
        
        if notion_edit_check['is_notion_edit'] and notion_service:
            logger.info(f"🟣 DIRECT NOTION EDIT detected: '{notion_edit_check['content']}' -> '{notion_edit_check['page_title']}'")
            
            try:
                # Check if the enhanced method exists
                if hasattr(notion_service, 'add_text_by_page_title'):
                    result = notion_service.add_text_by_page_title(
                        notion_edit_check['page_title'], 
                        notion_edit_check['content'], 
                        notion_edit_check['formatting']
                    )
                else:
                    # Fallback to basic add_text_to_page method
                    page = notion_service.get_page_by_title(notion_edit_check['page_title'])
                    if page:
                        page_id = page['id']
                        success = notion_service.add_text_to_page(
                            page_id, 
                            notion_edit_check['content'], 
                            notion_edit_check['formatting']
                        )
                        result = {
                            "success": success,
                            "page_title": notion_edit_check['page_title'],
                            "page_id": page_id
                        }
                    else:
                        result = {
                            "success": False,
                            "error": f"Page '{notion_edit_check['page_title']}' not found"
                        }
                
                if result.get('success'):
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
                            "azure_ai_search": False,
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
                            "azure_ai_search": False,
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
                        "azure_ai_search": False,
                        "vector_search": False,
                        "notion_edit": False
                    }
                }
                
                return _success_response(result_data, "Notion edit failed due to error")

        # 🟣 PRIORITY 2: Check for auto-write requests (AI response to Notion)
        notion_auto_write_check = detect_notion_write_request(user_message)
        
        if notion_auto_write_check['is_write_request']:
            logger.info(f"🤖 AUTO-WRITE REQUEST detected: Write response to '{notion_auto_write_check.get('target_page')}'")
            
            # Generate AI response first using event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result_data = loop.run_until_complete(_process_enhanced_chat(user_message, context))
                ai_response = result_data.get("assistant_message", "")
                
                # Then write it to Notion automatically - use sync version to avoid nested loops
                notion_result = handle_notion_write_request_sync(user_message, ai_response, notion_auto_write_check)
            finally:
                loop.close()
            
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

        # If neither direct edit nor auto-write, continue with enhanced chat pipeline
        logger.info(f"🔄 Proceeding with enhanced chat pipeline (Azure AI Search + Cosmos + Notion)")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result_data = loop.run_until_complete(_process_enhanced_chat(user_message, context))
        finally:
            loop.close()
        return _success_response(result_data, "Enhanced chat response generated")

    except Exception as e:
        logger.error(f"❌ Enhanced chat error: {e}", exc_info=True)
        return _error_response(f"Chat failed: {str(e)}", 500)

@chat_bp.route('/simple', methods=['POST', 'OPTIONS'])
def simple_chat():
    """Simple chat without any search - just return OpenAI response."""
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
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            response = loop.run_until_complete(_simple_openai_call(user_message))
        finally:
            loop.close()

        result_data = {
            "assistant_message": response,
            "content": response,
            "mode": "simple",
            "azure_services_used": {
                "openai": True,
                "cosmos_db": False,
                "azure_ai_search": False,
                "vector_search": False
            }
        }

        return _success_response(result_data, "Simple chat response generated")

    except Exception as e:
        logger.error(f"❌ Simple chat error: {e}", exc_info=True)
        return _error_response(f"Chat failed: {str(e)}", 500)

# ─── Health and Test Endpoints ────────────────────────────────────────────────

@chat_bp.route('/health', methods=['GET', 'OPTIONS'])
def chat_health():
    """Health check for enhanced chat services."""
    if request.method == 'OPTIONS':
        return _handle_cors()

    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "openai": openai_service is not None,
            "cosmos": cosmos_service is not None,
            "azure_ai_search": azure_search_service is not None,
            "notion": notion_service is not None,
            "web_scraper": web_scraper_service is not None
        },
        "search_capabilities": {
            "azure_ai_search": azure_search_service is not None,
            "cosmos_vector_search": cosmos_service is not None,
            "notion_search": notion_service is not None,
            "hybrid_search": azure_search_service is not None and cosmos_service is not None
        },
        "notion_features": {
            "direct_edit": True,
            "auto_write": True,
            "enhanced_search": hasattr(notion_service, 'search_pages_and_content') if notion_service else False,
            "long_text_writing": hasattr(notion_service, 'write_long_text_to_page') if notion_service else False
        },
        "endpoints": [
            "/chat", "/simple", "/health", "/test", "/fix-embeddings",
            "/notion/add-text", "/notion/search", "/notion/write-response"
        ]
    })

@chat_bp.route('/test', methods=['GET', 'OPTIONS'])
def test_endpoint():
    """Simple test endpoint to confirm that enhanced chat routes are working."""
    if request.method == 'OPTIONS':
        return _handle_cors()

    return jsonify({
        "status": "Enhanced Chat routes working",
        "message": "Test endpoint successful with Azure AI Search + Cosmos DB + Notion integration",
        "timestamp": datetime.now().isoformat(),
        "backend_url": "http://localhost:5000",
        "features": [
            "Azure AI Search Integration",
            "Cosmos DB Vector Search", 
            "Notion Integration",
            "Direct Notion Edit",
            "Auto-write AI responses to Notion", 
            "Hybrid Search Capabilities",
            "Advanced Document Retrieval"
        ]
    })

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
        else:
            return "OpenAI service is not properly configured."
    except Exception as e:
        logger.error(f"❌ OpenAI call failed: {e}", exc_info=True)
        return f"I apologize, but I encountered an error: {str(e)}"

async def _process_enhanced_chat(user_message: str, context: list) -> dict:
    """Process chat with enhanced search: Azure AI Search + Cosmos DB + Notion."""
    result_data = {
        "assistant_message": "",
        "content": "",
        "sources": [],
        "azure_services_used": {
            "openai": False,
            "openai_embedding": False,
            "cosmos_db": False,
            "azure_ai_search": False,
            "vector_search": False,
            "notion_search": False,
            "document_chunks": 0
        },
        "search_results": {
            "azure_ai_search": [],
            "cosmos_db": [],
            "notion_pages": []
        }
    }

    try:
        # 1. Azure AI Search (if available)
        azure_search_results = []
        if azure_search_service:
            try:
                azure_search_results = await azure_search_service.search_documents(
                    query=user_message,
                    top=3,
                    use_vector_search=True,
                    use_semantic_search=True
                )
                result_data["azure_services_used"]["azure_ai_search"] = len(azure_search_results) > 0
                result_data["search_results"]["azure_ai_search"] = azure_search_results
                logger.info(f"🔍 Azure AI Search found {len(azure_search_results)} results")
            except Exception as e:
                logger.error(f"❌ Azure AI Search failed: {e}")

        # 2. Cosmos DB Vector Search (if available)
        cosmos_results = []
        if cosmos_service:
            try:
                await cosmos_service.initialize_database()
                result_data["azure_services_used"]["cosmos_db"] = True

                # Generate embedding
                embedding = await openai_service.generate_embeddings(user_message)
                if embedding:
                    result_data["azure_services_used"]["openai_embedding"] = True

                    search_results = await cosmos_service.search_similar_chunks(
                        embedding, limit=3, similarity_threshold=0.1
                    )
                    if search_results:
                        result_data["azure_services_used"]["vector_search"] = True
                        cosmos_results = search_results
                        result_data["search_results"]["cosmos_db"] = cosmos_results

                    logger.info(f"🔍 Cosmos DB found {len(cosmos_results)} results")

            except Exception as e:
                logger.error(f"❌ Cosmos search failed: {e}")

        # 3. Notion Search (if available) - FIXED
        notion_pages = []
        if notion_service and any(
            kw in user_message.lower()
            for kw in ["notion", "meeting", "agenda", "schedule", "calendar", "june", "july"]
        ):
            try:
                notion_pages = await _search_notion(user_message)
                result_data["azure_services_used"]["notion_search"] = len(notion_pages) > 0
                result_data["search_results"]["notion_pages"] = notion_pages
                logger.info(f"🔍 Notion found {len(notion_pages)} pages")
            except Exception as e:
                logger.error(f"❌ Notion search failed: {e}")

        # 4. Combine all search results for AI context
        all_document_chunks = []
        
        # Add Azure AI Search results
        for result in azure_search_results:
            all_document_chunks.append({
                "file_name": result.get("file_name", "Azure AI Search"),
                "content": result.get("content", ""),
                "similarity": result.get("score", 0.0),
                "source": "azure_ai_search"
            })
        
        # Add Cosmos DB results
        for result in cosmos_results:
            all_document_chunks.append({
                "file_name": result.get("file_name", "Cosmos DB"),
                "content": result.get("content", ""),
                "similarity": result.get("similarity", 0.0),
                "source": "cosmos_db"
            })

        result_data["azure_services_used"]["document_chunks"] = len(all_document_chunks)
        
        # Build sources list
        result_data["sources"] = [
            f"{chunk.get('file_name', '?')} ({chunk.get('source', 'unknown')})"
            for chunk in all_document_chunks
        ]

        # 5. Generate AI response with all context
        ai_response = await openai_service.generate_response(
            user_message=user_message,
            context=context,
            document_chunks=all_document_chunks,
            notion_pages=notion_pages,
            max_tokens=1500,
            temperature=0.7
        )

        if isinstance(ai_response, dict):
            result_data["assistant_message"] = ai_response.get("assistant_message", str(ai_response))
        else:
            result_data["assistant_message"] = str(ai_response)

        result_data["azure_services_used"]["openai"] = True
        result_data["content"] = result_data["assistant_message"]

        # Add search information to response if we found results
        if all_document_chunks or notion_pages:
            search_info = []
            if azure_search_results:
                search_info.append(f"🔍 Found {len(azure_search_results)} results from Azure AI Search")
            if cosmos_results:
                search_info.append(f"🔍 Found {len(cosmos_results)} results from Cosmos DB")
            if notion_pages:
                search_info.append(f"📄 Found {len(notion_pages)} Notion pages")
            
            if search_info:
                result_data["assistant_message"] += f"\n\n---\n**Sources used:** {'; '.join(search_info)}"

        logger.info(f"✅ Enhanced chat completed with {len(all_document_chunks)} document chunks and {len(notion_pages)} Notion pages")
        return result_data

    except Exception as e:
        logger.error(f"❌ Enhanced chat processing failed: {e}", exc_info=True)
        # Return error response but still try to provide basic OpenAI response
        try:
            fallback_response = await _simple_openai_call(user_message)
            result_data["assistant_message"] = fallback_response
            result_data["content"] = fallback_response
            result_data["azure_services_used"]["openai"] = True
            result_data["error"] = f"Enhanced search failed: {str(e)}"
            return result_data
        except Exception as fallback_error:
            logger.error(f"❌ Fallback OpenAI call also failed: {fallback_error}")
            result_data["assistant_message"] = f"I apologize, but I encountered an error processing your request: {str(e)}"
            result_data["content"] = result_data["assistant_message"]
            result_data["error"] = str(e)
            return result_data

# ─── Additional Notion Endpoints ──────────────────────────────────────────────

@chat_bp.route('/notion/add-text', methods=['POST', 'OPTIONS'])
def add_text_to_notion():
    """Add text directly to a Notion page"""
    if request.method == 'OPTIONS':
        return _handle_cors()

    if not notion_service:
        return _error_response("Notion service not available", 503)

    data = request.get_json()
    if not data or not all(k in data for k in ['page_title', 'text']):
        return _error_response("Fields 'page_title' and 'text' are required", 400)

    try:
        result = notion_service.add_text_by_page_title(
            page_title=data['page_title'],
            text=data['text'],
            formatting=data.get('formatting', 'paragraph')
        )

        if result.get('success'):
            return _success_response({
                "notion_result": result,
                "page_title": data['page_title'],
                "text_added": data['text']
            }, "Text added to Notion page successfully")
        else:
            return _error_response(result.get('error', 'Failed to add text to Notion page'))

    except Exception as e:
        logger.error(f"❌ Notion add text failed: {e}")
        return _error_response(f"Notion integration error: {str(e)}", 500)

@chat_bp.route('/notion/search', methods=['POST', 'OPTIONS'])
def search_notion_endpoint():
    """Search Notion pages - FIXED VERSION"""
    if request.method == 'OPTIONS':
        return _handle_cors()

    if not notion_service:
        return _error_response("Notion service not available", 503)

    data = request.get_json()
    if not data or 'query' not in data:
        return _error_response("Field 'query' is required", 400)

    try:
        # Use event loop to handle the async search properly
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            pages = loop.run_until_complete(_search_notion(data['query']))
        finally:
            loop.close()

        return _success_response({
            "pages": pages,
            "count": len(pages),
            "query": data['query']
        }, f"Found {len(pages)} Notion pages")

    except Exception as e:
        logger.error(f"❌ Notion search failed: {e}")
        return _error_response(f"Notion search error: {str(e)}", 500)

@chat_bp.route('/notion/write-response', methods=['POST', 'OPTIONS'])
def write_response_to_notion():
    """Write an AI response to a specific Notion page"""
    if request.method == 'OPTIONS':
        return _handle_cors()

    if not notion_service:
        return _error_response("Notion service not available", 503)

    data = request.get_json()
    if not data or not all(k in data for k in ['page_title', 'user_message', 'ai_response']):
        return _error_response("Fields 'page_title', 'user_message', and 'ai_response' are required", 400)

    try:
        notion_request = {
            "target_page": data['page_title'],
            "is_write_request": True,
            "write_type": "manual_write"
        }

        result = handle_notion_write_request_sync(
            data['user_message'],
            data['ai_response'],
            notion_request
        )

        if result.get('success'):
            return _success_response({
                "notion_result": result,
                "page_title": data['page_title']
            }, "Response written to Notion page successfully")
        else:
            return _error_response(result.get('error', 'Failed to write response to Notion page'))

    except Exception as e:
        logger.error(f"❌ Notion write response failed: {e}")
        return _error_response(f"Notion integration error: {str(e)}", 500)

# ─── Embedding Fix Endpoint ───────────────────────────────────────────────────

@chat_bp.route('/fix-embeddings', methods=['POST', 'OPTIONS'])
def fix_embeddings():
    """Fix missing embeddings in Cosmos DB"""
    if request.method == 'OPTIONS':
        return _handle_cors()

    if not cosmos_service or not openai_service:
        return _error_response("Cosmos DB or OpenAI service not available", 503)

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(_fix_missing_embeddings())
        finally:
            loop.close()

        return _success_response(result, "Embeddings fix completed")

    except Exception as e:
        logger.error(f"❌ Fix embeddings failed: {e}")
        return _error_response(f"Fix embeddings error: {str(e)}", 500)

async def _fix_missing_embeddings() -> Dict[str, Any]:
    """Fix missing embeddings in existing documents"""
    try:
        await cosmos_service.initialize_database()
        
        # Find documents without embeddings
        query = "SELECT * FROM c WHERE c.source = 'blob_storage' AND c.document_type = 'text_chunk' AND NOT IS_DEFINED(c.embedding)"
        
        fixed_count = 0
        error_count = 0
        
        async for item in cosmos_service.container.query_items(query=query):
            try:
                chunk_text = item.get('chunk_text', '')
                if chunk_text:
                    # Generate embedding
                    embedding = await openai_service.generate_embeddings(chunk_text)
                    
                    if embedding:
                        # Update document with embedding
                        item['embedding'] = embedding
                        item['vector_dimensions'] = len(embedding)
                        item['updated_at'] = datetime.now().isoformat()
                        
                        await cosmos_service.container.replace_item(item=item, body=item)
                        fixed_count += 1
                        logger.debug(f"✅ Fixed embedding for {item.get('file_name')} chunk {item.get('chunk_index')}")
                    else:
                        error_count += 1
                        logger.warning(f"❌ Failed to generate embedding for {item.get('file_name')}")
                        
            except Exception as e:
                error_count += 1
                logger.error(f"❌ Error fixing embedding for document: {e}")
        
        return {
            "fixed_embeddings": fixed_count,
            "errors": error_count,
            "total_processed": fixed_count + error_count,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Fix embeddings process failed: {e}")
        return {
            "fixed_embeddings": 0,
            "errors": 1,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }