# routes/notion_routes.py - Notion API Routes
import logging
import asyncio
from datetime import datetime
from flask import Blueprint, jsonify, request
from services.notion_service import NotionService

# ─── LOGGING SETUP ───
logger = logging.getLogger(__name__)

# ─── CREATE BLUEPRINT ───
notion_bp = Blueprint('notion', __name__)

# ─── GLOBAL SERVICE INSTANCE ───
notion_service = None

def get_notion_service():
    """Initialize NotionService if not already done."""
    global notion_service
    if notion_service is None:
        try:
            notion_service = NotionService()
            logger.info("✅ NotionService initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize NotionService: {e}")
            raise
    return notion_service

# ─── HEALTH CHECK ROUTE ───
@notion_bp.route('/health', methods=['GET'])
def health_check():
    """Check Notion service health."""
    try:
        service = get_notion_service()
        
        # Run async health check
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            health_result = loop.run_until_complete(service.health_check())
        finally:
            loop.close()
        
        if health_result.get('status') == 'healthy':
            return jsonify({
                'success': True,
                'service': 'notion',
                'status': 'healthy',
                'message': 'Notion API is accessible',
                'workspace_user_type': health_result.get('workspace_user_type', 'unknown'),
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({
                'success': False,
                'service': 'notion',
                'status': 'unhealthy',
                'error': health_result.get('error', 'Unknown error'),
                'timestamp': datetime.now().isoformat()
            }), 503
            
    except Exception as e:
        logger.error(f"❌ Notion health check failed: {e}")
        return jsonify({
            'success': False,
            'service': 'notion',
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

# ─── GET ALL PAGES ROUTE ───
@notion_bp.route('/pages', methods=['GET'])
def get_pages():
    """Get all accessible Notion pages."""
    try:
        service = get_notion_service()
        query = request.args.get('query', '')
        limit = int(request.args.get('limit', 10))
        
        # Run async search
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            pages = loop.run_until_complete(service.search_pages(query=query, limit=limit))
        finally:
            loop.close()
        
        return jsonify({
            'success': True,
            'pages': pages,
            'count': len(pages),
            'query': query,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Error getting pages: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

# ─── GET MEETING PAGES ROUTE ───
@notion_bp.route('/meetings', methods=['GET'])
def get_meeting_pages():
    """Get meeting-related pages from Notion."""
    try:
        service = get_notion_service()
        query = request.args.get('query', 'meeting')
        
        # Run async search for meetings
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            meetings = loop.run_until_complete(service.search_meeting_pages(query=query))
        finally:
            loop.close()
        
        return jsonify({
            'success': True,
            'meetings': meetings,
            'count': len(meetings),
            'query': query,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Error getting meeting pages: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

# ─── GET SPECIFIC PAGE CONTENT ROUTE ───
@notion_bp.route('/page/<string:page_id>', methods=['GET'])
def get_page_content(page_id: str):
    """Get content of a specific Notion page."""
    try:
        service = get_notion_service()
        
        # Run async page content retrieval
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            content = loop.run_until_complete(service.get_page_content(page_id))
        finally:
            loop.close()
        
        if content.get('success'):
            return jsonify({
                'success': True,
                'page': content,
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({
                'success': False,
                'error': content.get('error', 'Failed to get page content'),
                'timestamp': datetime.now().isoformat()
            }), 404
            
    except Exception as e:
        logger.error(f"❌ Error getting page content: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

# ─── APPEND TEXT TO PAGE ROUTE ───
@notion_bp.route('/page/<string:page_id>/append', methods=['POST'])
def append_to_page(page_id: str):
    """Append text to a specific Notion page."""
    try:
        service = get_notion_service()
        
        # Get text from request
        data = request.get_json()
        if not data or 'text' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing required field: text',
                'timestamp': datetime.now().isoformat()
            }), 400
        
        text = data['text']
        
        # Run async append operation
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(service.append_text_to_page(page_id, text))
        finally:
            loop.close()
        
        if result.get('success'):
            return jsonify({
                'success': True,
                'message': 'Text appended successfully',
                'page_id': page_id,
                'appended_text': text,
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

# ─── GET DATABASES ROUTE ───
@notion_bp.route('/databases', methods=['GET'])
def get_databases():
    """Get all accessible Notion databases."""
    try:
        service = get_notion_service()
        query = request.args.get('query', '')
        
        # Run async database search
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            databases = loop.run_until_complete(service.search_databases(query=query))
        finally:
            loop.close()
        
        return jsonify({
            'success': True,
            'databases': databases,
            'count': len(databases),
            'query': query,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Error getting databases: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

# ─── QUERY DATABASE ROUTE ───
@notion_bp.route('/database/<string:database_id>/query', methods=['POST'])
def query_database(database_id: str):
    """Query a specific Notion database."""
    try:
        service = get_notion_service()
        
        # Get filter conditions from request (optional)
        data = request.get_json() or {}
        filter_conditions = data.get('filter')
        
        # Run async database query
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            results = loop.run_until_complete(service.query_database(database_id, filter_conditions))
        finally:
            loop.close()
        
        return jsonify({
            'success': True,
            'results': results,
            'count': len(results),
            'database_id': database_id,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Error querying database: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

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
    logger.error(f"Internal error in Notion routes: {error}")
    return jsonify({
        'success': False,
        'error': 'Internal server error in Notion service',
        'timestamp': datetime.now().isoformat()
    }), 500
