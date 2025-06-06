# routes/notion_routes.py - ENHANCED Notion Routes with Full Content Search & Writing

import logging
import asyncio
import re
from datetime import datetime
from flask import Blueprint, jsonify, request
from services.notion_service import NotionService

logger = logging.getLogger(__name__)

# Create Blueprint
notion_bp = Blueprint('notion', __name__)

# Global service instance
notion_service = None

def get_notion_service():
    """Initialize NotionService if not already done."""
    global notion_service
    if notion_service is None:
        try:
            notion_service = NotionService()
            logger.info("✅ Enhanced NotionService initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize NotionService: {e}")
            raise
    return notion_service

# ─── ENHANCED SEARCH ROUTE ───
@notion_bp.route('/search-all', methods=['GET'])
def enhanced_search():
    """Search BOTH titles AND content in Notion pages"""
    try:
        service = get_notion_service()
        query = request.args.get('query', '')
        limit = int(request.args.get('limit', 20))
        
        if not query:
            return jsonify({
                'success': False,
                'error': 'Query parameter is required',
                'timestamp': datetime.now().isoformat()
            }), 400
        
        logger.info(f"🔍 Enhanced search request: '{query}'")
        
        # Run enhanced async search
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            results = loop.run_until_complete(service.search_pages_and_content(query, limit))
        finally:
            loop.close()
        
        return jsonify({
            'success': True,
            'query': query,
            'results': results,
            'count': len(results),
            'search_type': 'title_and_content',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Enhanced search failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

# ─── WRITE CHATBOT RESPONSE ROUTE ───
@notion_bp.route('/write-chatbot-response', methods=['POST'])
def write_chatbot_response():
    """Write chatbot response to a Notion page"""
    try:
        service = get_notion_service()
        
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'JSON data required',
                'timestamp': datetime.now().isoformat()
            }), 400
        
        page_title = data.get('page_title')
        chatbot_response = data.get('chatbot_response')
        user_question = data.get('user_question')  # Optional
        
        if not page_title or not chatbot_response:
            return jsonify({
                'success': False,
                'error': 'page_title and chatbot_response are required',
                'timestamp': datetime.now().isoformat()
            }), 400
        
        logger.info(f"🤖 Writing chatbot response to '{page_title}': {len(chatbot_response)} chars")
        
        # Run async write operation
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                service.write_chatbot_response_to_page(page_title, chatbot_response, user_question)
            )
        finally:
            loop.close()
        
        if result['success']:
            return jsonify({
                'success': True,
                'message': 'Chatbot response written successfully',
                'result': result,
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Failed to write response'),
                'suggestion': result.get('suggestion', 'Try again or check page permissions'),
                'timestamp': datetime.now().isoformat()
            }), 400
            
    except Exception as e:
        logger.error(f"❌ Error writing chatbot response: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

# ─── WRITE LONG TEXT ROUTE ───
@notion_bp.route('/write-long-text', methods=['POST'])
def write_long_text():
    """Write long text content to a Notion page"""
    try:
        service = get_notion_service()
        
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'JSON data required',
                'timestamp': datetime.now().isoformat()
            }), 400
        
        page_id = data.get('page_id')
        text = data.get('text')
        add_timestamp = data.get('add_timestamp', True)
        
        if not page_id or not text:
            return jsonify({
                'success': False,
                'error': 'page_id and text are required',
                'timestamp': datetime.now().isoformat()
            }), 400
        
        logger.info(f"📝 Writing long text to page {page_id}: {len(text)} chars")
        
        # Run async write operation
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                service.write_long_text_to_page(page_id, text, add_timestamp)
            )
        finally:
            loop.close()
        
        if result['success']:
            return jsonify({
                'success': True,
                'message': 'Long text written successfully',
                'result': result,
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Failed to write text'),
                'result': result,
                'timestamp': datetime.now().isoformat()
            }), 400
            
    except Exception as e:
        logger.error(f"❌ Error writing long text: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

# ─── SMART WRITE ROUTE (Auto-detect what to write) ───
@notion_bp.route('/smart-write', methods=['POST'])
def smart_write():
    """Smart write - automatically detect and write content to appropriate page"""
    try:
        service = get_notion_service()
        
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'JSON data required',
                'timestamp': datetime.now().isoformat()
            }), 400
        
        # Extract information from request
        content = data.get('content', '')
        target_info = data.get('target', '')  # Could be page title or instruction
        content_type = data.get('type', 'auto')  # 'chatbot_response', 'summary', 'auto'
        user_context = data.get('user_context', '')  # Original user question
        
        if not content or not target_info:
            return jsonify({
                'success': False,
                'error': 'content and target are required',
                'timestamp': datetime.now().isoformat()
            }), 400
        
        logger.info(f"🧠 Smart write request: {len(content)} chars to '{target_info}'")
        
        # Parse target to find page
        page_title = extract_page_title_from_target(target_info)
        
        if not page_title:
            return jsonify({
                'success': False,
                'error': f"Could not identify target page from: '{target_info}'",
                'suggestion': "Please specify a clear page title like 'Meeting Calendar (July 2025)'",
                'timestamp': datetime.now().isoformat()
            }), 400
        
        # Run async write operation
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            if content_type == 'chatbot_response' or 'chatbot' in target_info.lower():
                result = loop.run_until_complete(
                    service.write_chatbot_response_to_page(page_title, content, user_context)
                )
            else:
                # Find page first
                page = service.get_page_by_title(page_title)
                if page:
                    page_id = page['id']
                    result = loop.run_until_complete(
                        service.write_long_text_to_page(page_id, content, add_timestamp=True)
                    )
                else:
                    result = {
                        "success": False,
                        "error": f"Page '{page_title}' not found"
                    }
        finally:
            loop.close()
        
        if result['success']:
            return jsonify({
                'success': True,
                'message': f"Content written to '{page_title}' successfully",
                'detected_page': page_title,
                'content_type': content_type,
                'result': result,
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Failed to write content'),
                'detected_page': page_title,
                'result': result,
                'timestamp': datetime.now().isoformat()
            }), 400
            
    except Exception as e:
        logger.error(f"❌ Smart write error: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

# ─── EXISTING ROUTES (Enhanced) ───
@notion_bp.route('/health', methods=['GET'])
def health_check():
    """Enhanced health check"""
    try:
        service = get_notion_service()
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            health_result = loop.run_until_complete(service.health_check())
        finally:
            loop.close()
        
        if health_result.get('status') == 'healthy':
            return jsonify({
                'success': True,
                'service': 'Enhanced Notion',
                'status': 'healthy',
                'features': health_result.get('enhanced_features', []),
                'message': 'Enhanced Notion API is accessible',
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({
                'success': False,
                'service': 'Enhanced Notion',
                'status': 'unhealthy',
                'error': health_result.get('error', 'Unknown error'),
                'timestamp': datetime.now().isoformat()
            }), 503
            
    except Exception as e:
        logger.error(f"❌ Enhanced Notion health check failed: {e}")
        return jsonify({
            'success': False,
            'service': 'Enhanced Notion',
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@notion_bp.route('/pages', methods=['GET'])
def get_pages():
    """Get pages with optional enhanced search"""
    try:
        service = get_notion_service()
        query = request.args.get('query', '')
        enhanced = request.args.get('enhanced', 'false').lower() == 'true'
        limit = int(request.args.get('limit', 10))
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            if enhanced and query:
                # Use enhanced search
                pages = loop.run_until_complete(service.search_pages_and_content(query, limit))
                search_type = 'enhanced_content_search'
            else:
                # Use basic search
                pages = service.search_pages(query) if query else []
                search_type = 'basic_title_search'
        finally:
            loop.close()
        
        return jsonify({
            'success': True,
            'pages': pages,
            'count': len(pages),
            'query': query,
            'search_type': search_type,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Error getting pages: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@notion_bp.route('/page/<string:page_id>/append', methods=['POST'])
def append_to_page(page_id: str):
    """Enhanced append text to page"""
    try:
        service = get_notion_service()
        
        data = request.get_json()
        if not data or 'text' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing required field: text',
                'timestamp': datetime.now().isoformat()
            }), 400
        
        text = data['text']
        use_long_text = data.get('use_long_text', len(text) > 1500)
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            if use_long_text:
                # Use enhanced long text writing
                result = loop.run_until_complete(service.write_long_text_to_page(page_id, text))
            else:
                # Use basic append
                result = loop.run_until_complete(service.append_text_to_page(page_id, text))
        finally:
            loop.close()
        
        if result.get('success'):
            return jsonify({
                'success': True,
                'message': 'Text appended successfully',
                'page_id': page_id,
                'method_used': 'long_text' if use_long_text else 'basic_append',
                'result': result,
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Failed to append text'),
                'timestamp': datetime.now().isoformat()
            }), 400
            
    except Exception as e:
        logger.error(f"❌ Error appending to page: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

# ─── HELPER FUNCTIONS ───
def extract_page_title_from_target(target_text: str) -> str:
    """Extract page title from target instruction"""
    # Common patterns for page references
    patterns = [
        r"(?:page|notion)\s+['\"]([^'\"]+)['\"]",  # "page 'Meeting Calendar'"
        r"(?:Meeting\s+Calendar\s*\([^)]+\))",      # Meeting Calendar (July 2025)
        r"([A-Z][A-Za-z\s]+\s*\([^)]+\))",         # Any Title (Something)
        r"([A-Z][A-Za-z\s]{5,30})",                # Generic title pattern
    ]
    
    for pattern in patterns:
        match = re.search(pattern, target_text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    
    # Fallback: use the whole target if it looks like a title
    if len(target_text) < 100 and any(c.isupper() for c in target_text):
        return target_text.strip()
    
    return ""

# ─── ERROR HANDLERS ───
@notion_bp.errorhandler(400)
def bad_request(error):
    return jsonify({
        'success': False,
        'error': 'Bad request - check your request format',
        'timestamp': datetime.now().isoformat()
    }), 400

@notion_bp.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'error': 'Notion resource not found',
        'timestamp': datetime.now().isoformat()
    }), 404

@notion_bp.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal error in Enhanced Notion routes: {error}")
    return jsonify({
        'success': False,
        'error': 'Internal server error in Enhanced Notion service',
        'timestamp': datetime.now().isoformat()
    }), 500