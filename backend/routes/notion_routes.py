# routes/notion_routes.py - Fixed Notion Routes (No Circular Imports)

from flask import Blueprint, request, jsonify
import asyncio
import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)

# Create blueprint FIRST before any other imports
notion_bp = Blueprint('notion', __name__)

@notion_bp.route('/health', methods=['GET'])
def notion_health():
    """Check Notion service health"""
    try:
        # Import NotionService inside the function to avoid circular imports
        from services.notion_service import NotionService
        
        # Check if token is available
        notion_token = os.getenv('NOTION_API_TOKEN')
        if not notion_token:
            return jsonify({
                'status': 'unhealthy',
                'error': 'NOTION_API_TOKEN not found in environment variables',
                'timestamp': datetime.now().isoformat()
            }), 500
        
        # Run health check
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            notion_service = NotionService()
            health_result = loop.run_until_complete(notion_service.health_check())
            
            return jsonify({
                'status': health_result.get('status', 'unknown'),
                'service': 'Notion API',
                'token_available': True,
                'workspace_info': health_result,
                'timestamp': datetime.now().isoformat()
            })
        finally:
            loop.close()
        
    except Exception as e:
        logger.error(f"❌ Notion health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@notion_bp.route('/pages', methods=['GET'])
def get_notion_pages():
    """Get all accessible Notion pages"""
    try:
        from services.notion_service import NotionService
        
        query = request.args.get('query', '')
        limit = request.args.get('limit', 10, type=int)
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            notion_service = NotionService()
            pages = loop.run_until_complete(notion_service.search_pages(query=query, limit=limit))
            
            return jsonify({
                'success': True,
                'pages': pages,
                'count': len(pages),
                'query': query if query else 'all pages',
                'timestamp': datetime.now().isoformat()
            })
        finally:
            loop.close()
        
    except Exception as e:
        logger.error(f"❌ Failed to get Notion pages: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@notion_bp.route('/meetings', methods=['GET'])
def get_notion_meetings():
    """Get meeting notes from Notion"""
    try:
        from services.notion_service import NotionService
        
        query = request.args.get('query', 'meeting')
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            notion_service = NotionService()
            meetings = loop.run_until_complete(notion_service.search_meeting_pages(query=query))
            
            return jsonify({
                'success': True,
                'meetings': meetings,
                'count': len(meetings),
                'query': query,
                'timestamp': datetime.now().isoformat()
            })
        finally:
            loop.close()
        
    except Exception as e:
        logger.error(f"❌ Failed to get Notion meetings: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@notion_bp.route('/page/<page_id>', methods=['GET'])
def get_notion_page_content(page_id):
    """Get content of a specific Notion page"""
    try:
        from services.notion_service import NotionService
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            notion_service = NotionService()
            content = loop.run_until_complete(notion_service.get_page_content(page_id))
            
            if content.get('success'):
                return jsonify({
                    'success': True,
                    'page_id': page_id,
                    'page_data': content,
                    'timestamp': datetime.now().isoformat()
                })
            else:
                return jsonify({
                    'success': False,
                    'error': content.get('error', 'Page not found'),
                    'page_id': page_id,
                    'timestamp': datetime.now().isoformat()
                }), 404
        finally:
            loop.close()
        
    except Exception as e:
        logger.error(f"❌ Failed to get Notion page content: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@notion_bp.route('/page/<page_id>/append', methods=['POST'])
def append_to_notion_page(page_id):
    """Append content to a Notion page"""
    try:
        from services.notion_service import NotionService
        
        data = request.get_json()
        if not data or 'content' not in data:
            return jsonify({
                'success': False,
                'error': 'content is required in request body',
                'example': {'content': 'Text to append to the page'},
                'timestamp': datetime.now().isoformat()
            }), 400
        
        content = data['content']
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            notion_service = NotionService()
            result = loop.run_until_complete(notion_service.append_text_to_page(page_id, content))
            
            if result.get('success'):
                return jsonify({
                    'success': True,
                    'message': f'Content appended to page {page_id}',
                    'page_id': page_id,
                    'appended_content': content,
                    'timestamp': datetime.now().isoformat()
                })
            else:
                return jsonify({
                    'success': False,
                    'error': result.get('error', 'Failed to append content'),
                    'page_id': page_id,
                    'timestamp': datetime.now().isoformat()
                }), 500
        finally:
            loop.close()
        
    except Exception as e:
        logger.error(f"❌ Failed to append to Notion page: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@notion_bp.route('/databases', methods=['GET'])
def get_notion_databases():
    """Get all accessible Notion databases"""
    try:
        from services.notion_service import NotionService
        
        query = request.args.get('query', '')
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            notion_service = NotionService()
            databases = loop.run_until_complete(notion_service.search_databases(query=query))
            
            return jsonify({
                'success': True,
                'databases': databases,
                'count': len(databases),
                'query': query if query else 'all databases',
                'timestamp': datetime.now().isoformat()
            })
        finally:
            loop.close()
        
    except Exception as e:
        logger.error(f"❌ Failed to get Notion databases: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@notion_bp.route('/test', methods=['GET'])
def test_notion_connection():
    """Test Notion API connection"""
    try:
        from services.notion_service import NotionService
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            notion_service = NotionService()
            health_result = loop.run_until_complete(notion_service.health_check())
            
            return jsonify({
                'success': True,
                'test_result': 'passed' if health_result.get('status') == 'healthy' else 'failed',
                'message': 'Notion API connection working',
                'health_data': health_result,
                'timestamp': datetime.now().isoformat()
            })
        finally:
            loop.close()
        
    except Exception as e:
        logger.error(f"❌ Notion connection test failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'test_result': 'failed',
            'timestamp': datetime.now().isoformat()
        }), 500