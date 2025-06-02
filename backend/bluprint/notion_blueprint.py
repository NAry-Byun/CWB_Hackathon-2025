# blueprints/notion_blueprint.py
from flask import Blueprint, jsonify, request
import logging
import os

# Create logger
logger = logging.getLogger(__name__)

# Create Blueprint
notion_bp = Blueprint('notion', __name__)

@notion_bp.route('/health', methods=['GET'])
def notion_health():
    """Check if Notion service is healthy and accessible."""
    try:
        # Check if token is available
        token_available = bool(os.getenv('NOTION_API_TOKEN'))
        
        if not token_available:
            return jsonify({
                'status': 'unhealthy',
                'error': 'NOTION_API_TOKEN not found',
                'message': 'Please set your Notion API token in environment variables',
                'setup_instructions': [
                    '1. Go to https://www.notion.so/my-integrations',
                    '2. Create a new integration',
                    '3. Copy the Internal Integration Token',
                    '4. Set it as NOTION_API_TOKEN environment variable',
                    '5. Share your Notion pages with the integration'
                ]
            }), 503
        
        # Try to import and initialize the Notion service
        try:
            from services.notion_service import NotionService
            notion_service = NotionService()
            
            return jsonify({
                'status': 'healthy',
                'message': 'Notion API service is accessible',
                'token_configured': True,
                'api_version': '2022-06-28',
                'available_endpoints': {
                    'health': '/api/notion/health',
                    'pages': '/api/notion/pages',
                    'meetings': '/api/notion/meetings',
                    'page_content': '/api/notion/page/<page_id>',
                    'append_content': '/api/notion/page/<page_id>/append'
                }
            })
            
        except Exception as service_error:
            logger.error(f"Notion service initialization failed: {service_error}")
            return jsonify({
                'status': 'unhealthy',
                'error': 'Service initialization failed',
                'message': str(service_error),
                'token_configured': True,
                'suggestions': [
                    'Check if services/notion_service.py exists',
                    'Verify your NOTION_API_TOKEN is valid',
                    'Ensure your Notion pages are shared with the integration'
                ]
            }), 503
            
    except Exception as e:
        logger.error(f"Notion health check failed: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e),
            'message': 'Health check failed'
        }), 500

@notion_bp.route('/pages', methods=['GET'])
def get_notion_pages():
    """Get all accessible Notion pages."""
    try:
        from services.notion_service import NotionService
        notion_service = NotionService()
        
        # Get all pages
        pages = notion_service.search_pages("")
        
        if not pages:
            return jsonify({
                'success': True,
                'message': 'No pages found',
                'pages': [],
                'total_count': 0,
                'suggestions': [
                    'Make sure your Notion pages are shared with the integration',
                    'Check if you have any pages in your Notion workspace',
                    'Verify your integration has the correct permissions'
                ]
            })
        
        # Format pages for response
        formatted_pages = []
        for page in pages:
            formatted_pages.append({
                'id': page.get('id'),
                'title': notion_service._extract_title(page),
                'url': page.get('url'),
                'created_time': page.get('created_time'),
                'last_edited_time': page.get('last_edited_time'),
                'object_type': page.get('object')
            })
        
        return jsonify({
            'success': True,
            'message': f'Found {len(formatted_pages)} pages',
            'pages': formatted_pages,
            'total_count': len(formatted_pages)
        })
        
    except Exception as e:
        logger.error(f"Failed to get Notion pages: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Failed to retrieve Notion pages'
        }), 500

@notion_bp.route('/meetings', methods=['GET'])
def get_notion_meetings():
    """Get meeting-related pages from Notion."""
    try:
        from services.notion_service import NotionService
        notion_service = NotionService()
        
        # Search for meeting-related content
        meeting_keywords = ['meeting', 'meetings', 'agenda', 'notes', 'standup', 'sync']
        all_meetings = []
        
        for keyword in meeting_keywords:
            try:
                results = notion_service.search_pages(keyword)
                for result in results:
                    # Avoid duplicates
                    if not any(m.get('id') == result.get('id') for m in all_meetings):
                        all_meetings.append(result)
            except Exception as search_error:
                logger.warning(f"Search for '{keyword}' failed: {search_error}")
                continue
        
        if not all_meetings:
            return jsonify({
                'success': True,
                'message': 'No meeting-related pages found',
                'meetings': [],
                'total_count': 0,
                'searched_keywords': meeting_keywords,
                'suggestions': [
                    'Create pages with titles containing "meeting", "agenda", or "notes"',
                    'Make sure meeting pages are shared with your integration'
                ]
            })
        
        # Get content for each meeting page
        meeting_details = []
        for meeting in all_meetings:
            try:
                content = notion_service.get_page_content(meeting['id'])
                meeting_details.append({
                    'id': meeting.get('id'),
                    'title': notion_service._extract_title(meeting),
                    'url': meeting.get('url'),
                    'content_preview': content[:200] + '...' if len(content) > 200 else content,
                    'full_content': content,
                    'created_time': meeting.get('created_time'),
                    'last_edited_time': meeting.get('last_edited_time')
                })
            except Exception as content_error:
                logger.warning(f"Failed to get content for meeting {meeting.get('id')}: {content_error}")
                meeting_details.append({
                    'id': meeting.get('id'),
                    'title': notion_service._extract_title(meeting),
                    'url': meeting.get('url'),
                    'content_preview': 'Content could not be retrieved',
                    'error': str(content_error)
                })
        
        return jsonify({
            'success': True,
            'message': f'Found {len(meeting_details)} meeting-related pages',
            'meetings': meeting_details,
            'total_count': len(meeting_details),
            'searched_keywords': meeting_keywords
        })
        
    except Exception as e:
        logger.error(f"Failed to get meeting pages: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Failed to retrieve meeting pages'
        }), 500

@notion_bp.route('/page/<page_id>', methods=['GET'])
def get_page_content(page_id):
    """Get content of a specific Notion page."""
    try:
        from services.notion_service import NotionService
        notion_service = NotionService()
        
        # Get page content
        content = notion_service.get_page_content(page_id)
        
        if not content:
            return jsonify({
                'success': False,
                'error': 'Page not found or empty',
                'page_id': page_id,
                'message': 'The page might not exist or you might not have access to it'
            }), 404
        
        return jsonify({
            'success': True,
            'page_id': page_id,
            'content': content,
            'content_length': len(content)
        })
        
    except Exception as e:
        logger.error(f"Failed to get page content for {page_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'page_id': page_id,
            'message': 'Failed to retrieve page content'
        }), 500

@notion_bp.route('/page/<page_id>/append', methods=['POST'])
def append_to_page(page_id):
    """Append content to a Notion page."""
    try:
        data = request.get_json()
        if not data or 'content' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing content',
                'message': 'Please provide content in the request body'
            }), 400
        
        from services.notion_service import NotionService
        notion_service = NotionService()
        
        # Append content to page
        result = notion_service.append_to_page(page_id, data['content'])
        
        return jsonify({
            'success': True,
            'page_id': page_id,
            'message': 'Content appended successfully',
            'appended_content': data['content'],
            'result': result
        })
        
    except Exception as e:
        logger.error(f"Failed to append to page {page_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'page_id': page_id,
            'message': 'Failed to append content to page'
        }), 500

# Error handlers for the blueprint
@notion_bp.errorhandler(404)
def notion_not_found(error):
    return jsonify({
        'success': False,
        'error': 'Notion endpoint not found',
        'available_endpoints': [
            '/api/notion/health',
            '/api/notion/pages',
            '/api/notion/meetings',
            '/api/notion/page/<page_id>',
            '/api/notion/page/<page_id>/append'
        ],
        'message': 'Check the available endpoints above'
    }), 404

@notion_bp.errorhandler(500)
def notion_internal_error(error):
    return jsonify({
        'success': False,
        'error': 'Internal Notion service error',
        'message': 'Something went wrong with the Notion service'
    }), 500