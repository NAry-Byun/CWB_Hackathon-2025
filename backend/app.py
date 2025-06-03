import os
import asyncio
import logging
import argparse
import sys
from datetime import datetime

from services.cosmos_service import CosmosVectorService
from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv

# ─── SIMPLE LOGGING SETUP ───
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ─── LOAD ENVIRONMENT VARIABLES ───
load_dotenv()

# ─── ENSURE SERVICES AND ROUTES CAN BE FOUND ───
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# ─── GLOBAL BACKEND INSTANCE ───
backend_instance = None

def create_app():
    """Create and configure the Flask app."""
    app = Flask(__name__)

    # Enable CORS for local front-end origins
    CORS(app, origins=[
        'http://localhost:3000',
        'http://localhost:8080',
        'http://127.0.0.1:3000',
        'http://127.0.0.1:8080',
        'http://172.21.112.1:8080',
        'http://192.168.10.152:8080',
        'http://192.168.10.75:8080'
    ])

    # Flask config
    app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50 MB uploads
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
    app.config['JSON_AS_ASCII'] = False

    # Register Blueprints
    register_blueprints(app)

    # Main routes
    @app.route('/', methods=['GET'])
    def root():
        return jsonify({
            "message": "🤖 AI Personal Assistant Backend",
            "version": "2.1",
            "description": "Azure OpenAI + Cosmos DB + Notion + Web Scraper Integrated AI Assistant",
            "status": "running",
            "endpoints": {
                "chat": "/api/chat/chat",
                "simple_chat": "/api/chat/simple",
                "chat_health": "/api/chat/health",
                "upload": "/api/documents/upload",
                "documents": "/api/documents/list",
                "scraper_health": "/api/scraper/health",
                "scraper_scrape": "/api/scraper/scrape",
                "scraper_test": "/api/scraper/test",
                "notion_health": "/api/notion/health",
                "notion_pages": "/api/notion/pages",
                "notion_meetings": "/api/notion/meetings",
                "notion_page_content": "/api/notion/page/<page_id>",
                "notion_append": "/api/notion/page/<page_id>/append",
                "health": "/health"
            },
            "frontend_url": "http://localhost:8080",
            "cors_enabled": True,
            "features": [
                "Azure OpenAI Chat",
                "Document Upload & Processing",
                "Cosmos DB Vector Storage",
                "Notion Integration",
                "Professional Web Scraping",
                "AI-Optimized Content Extraction"
            ]
        })

    @app.route('/health', methods=['GET'])
    def health_check():
        # Check Notion service health
        notion_status = False
        notion_token_available = bool(os.getenv('NOTION_API_TOKEN'))
        
        try:
            if notion_token_available:
                from services.notion_service import NotionService
                notion_service = NotionService()
                notion_status = True
        except Exception as e:
            logger.warning(f"Notion service check failed: {e}")
            notion_status = False

        return jsonify({
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "message": "Flask server is running",
            "services": {
                "flask": True,
                "cors": True,
                "routes": True,
                "upload_folder": os.path.exists('./data/uploads'),
                "web_scraper": True,
                "notion": notion_status
            },
            "python_version": sys.version,
            "backend_initialized": backend_instance is not None,
            "environment_variables": {
                "COSMOS_DB_ENDPOINT": bool(os.getenv('COSMOS_DB_ENDPOINT')),
                "COSMOS_DB_KEY": bool(os.getenv('COSMOS_DB_KEY')),
                "AZURE_OPENAI_ENDPOINT": bool(os.getenv('AZURE_OPENAI_ENDPOINT')),
                "AZURE_OPENAI_API_KEY": bool(os.getenv('AZURE_OPENAI_API_KEY')),
                "NOTION_API_TOKEN": notion_token_available
            }
        })

    @app.route('/api/status', methods=['GET'])
    def api_status():
        """전체 API 상태 확인"""
        return jsonify({
            "api_status": "operational",
            "available_endpoints": {
                "chat_api": {
                    "base_url": "/api/chat",
                    "endpoints": ["/chat", "/simple", "/health"]
                },
                "document_api": {
                    "base_url": "/api/documents", 
                    "endpoints": ["/upload", "/list", "/delete"]
                },
                "web_scraper_api": {
                    "base_url": "/api/scraper",
                    "endpoints": ["/health", "/scrape", "/test"]
                },
                "notion_api": {
                    "base_url": "/api/notion",
                    "endpoints": ["/health", "/pages", "/meetings", "/page/<page_id>", "/page/<page_id>/append"]
                }
            },
            "usage_examples": {
                "web_scraping": {
                    "method": "POST",
                    "url": "/api/scraper/scrape",
                    "body": {"url": "https://example.com/ai-article"},
                    "description": "AI-optimized web scraping for clean responses"
                },
                "chat": {
                    "method": "POST", 
                    "url": "/api/chat/chat",
                    "body": {"message": "What is machine learning?"},
                    "description": "Chat with AI using scraped content knowledge"
                },
                "notion_pages": {
                    "method": "GET",
                    "url": "/api/notion/pages", 
                    "description": "Get all accessible Notion pages"
                },
                "notion_meetings": {
                    "method": "GET",
                    "url": "/api/notion/meetings",
                    "description": "Get meeting notes from Notion"
                }
            },
            "timestamp": datetime.now().isoformat()
        })

    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            'success': False,
            'error': 'Endpoint not found',
            'path': request.path,
            'available_endpoints': [
                '/api/chat/chat',
                '/api/chat/simple', 
                '/api/chat/health',
                '/api/documents/upload',
                '/api/documents/list',
                '/api/scraper/health',
                '/api/scraper/scrape',
                '/api/scraper/test',
                '/api/notion/health',
                '/api/notion/pages',
                '/api/notion/meetings',
                '/api/status',
                '/health'
            ],
            'suggestion': f"Did you mean one of the available endpoints above?",
            'timestamp': datetime.now().isoformat()
        }), 404

    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal server error: {error}")
        return jsonify({
            'success': False,
            'error': 'Internal server error occurred',
            'timestamp': datetime.now().isoformat(),
            'support': 'Check server logs for details'
        }), 500

    @app.errorhandler(413)
    def file_too_large(error):
        return jsonify({
            'success': False,
            'error': 'File too large. Maximum size is 50MB.',
            'timestamp': datetime.now().isoformat()
        }), 413

    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({
            'success': False,
            'error': 'Bad request. Please check your request format.',
            'timestamp': datetime.now().isoformat()
        }), 400

    return app

def register_blueprints(app):
    """Import and register all route Blueprints."""
    
    # Register Chat Routes
    try:
        from routes.chat_routes import chat_bp
        app.register_blueprint(chat_bp, url_prefix='/api/chat')
        logger.info("✅ Chat routes registered at /api/chat")
    except Exception as e:
        logger.error(f"❌ Failed to register chat routes: {e}")

    # Register Document Routes
    try:
        from routes.document_routes import document_bp
        app.register_blueprint(document_bp, url_prefix='/api/documents')
        logger.info("✅ Document routes registered at /api/documents")
    except Exception as e:
        logger.error(f"❌ Failed to register document routes: {e}")

    # Register Web Scraper Routes (NEW!)
    try:
        from routes.web_scraper_routes import web_scraper_bp
        app.register_blueprint(web_scraper_bp, url_prefix='/api/scraper')
        logger.info("✅ Web Scraper routes registered at /api/scraper")
    except Exception as e:
        logger.error(f"❌ Failed to register web scraper routes: {e}")
        logger.warning("⚠️ Web scraper functionality will not be available")

    # Register Notion Routes - CORRECTED IMPORT PATH
    try:
        from routes.notion_routes import notion_bp
        app.register_blueprint(notion_bp, url_prefix='/api/notion')
        logger.info("✅ Notion routes registered at /api/notion")
    except Exception as e:
        logger.warning(f"⚠️ Notion routes not available: {e}")
        logger.info("💡 Make sure you have:")
        logger.info("   - routes/notion_routes.py file")
        logger.info("   - services/notion_service.py file") 
        logger.info("   - NOTION_API_TOKEN environment variable set")

    # Register Training Routes (optional)
    try:
        from routes.training_routes import training_bp
        app.register_blueprint(training_bp, url_prefix='/api/training')
        logger.info("✅ Training routes registered at /api/training")
    except Exception as e:
        logger.warning(f"⚠️ Training routes not available: {e}")

def run_cli():
    """Handle CLI commands (e.g., --init to initialize services)."""
    parser = argparse.ArgumentParser(description='AI Personal Assistant Backend')
    parser.add_argument('--init', action='store_true', help='Initialize backend services')
    parser.add_argument('--port', type=int, default=5000, help='Port to run Flask server on')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='Host to bind Flask server to')
    parser.add_argument('--debug', action='store_true', help='Run in debug mode')
    parser.add_argument('--test', action='store_true', help='Run in test mode (no service initialization)')
    parser.add_argument('--scraper-only', action='store_true', help='Run with web scraper functionality only')

    args = parser.parse_args()

    # Create necessary directories
    os.makedirs('./data/uploads', exist_ok=True)
    os.makedirs('./data/documents', exist_ok=True)

    print("🚀 AI Personal Assistant Backend Starting...")
    print("=" * 60)
    
    # Check environment variables
    required_vars = ['COSMOS_DB_ENDPOINT', 'COSMOS_DB_KEY', 'AZURE_OPENAI_ENDPOINT', 'AZURE_OPENAI_API_KEY']
    optional_vars = ['NOTION_API_TOKEN']
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    missing_optional = [var for var in optional_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"⚠️ Missing required environment variables: {', '.join(missing_vars)}")
        print("📝 Some features may not work properly")
    else:
        print("✅ All required environment variables are set")
        
    if missing_optional:
        print(f"💡 Optional environment variables not set: {', '.join(missing_optional)}")
        print("   - NOTION_API_TOKEN: Notion integration will be disabled")

    if args.init and not args.test:
        print("🔧 Initializing AI Personal Assistant Backend services…")
        try:
            from main_training import AITrainingBackend

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                global backend_instance
                backend_instance = AITrainingBackend()
                loop.run_until_complete(backend_instance.initialize_services())
                print("✅ Backend initialization completed successfully!")
                print(f"🔧 Available services: {list(backend_instance.services.keys())}")
            finally:
                loop.close()

        except Exception as e:
            print(f"❌ Backend initialization failed: {e}")
            print("⚠️ Continuing without full backend services...")
            print("🕷️ Web scraper will still be available in basic mode")

    elif args.test:
        print("🧪 Running in test mode - no service initialization")
        print("🕷️ Web scraper available in standalone mode")

    elif args.scraper_only:
        print("🕷️ Running with web scraper functionality only")
        print("📝 Other services will be available but may not be fully initialized")

    # Display startup information
    print("\n" + "=" * 60)
    print("🌐 Flask Server Configuration:")
    print(f"   Host: {args.host}")
    print(f"   Port: {args.port}")
    print(f"   Debug Mode: {args.debug}")
    print(f"   Frontend URL: http://localhost:{args.port}")
    print(f"   Upload Folder: ./data/uploads")
    
    print("\n🔗 Available API Endpoints:")
    print(f"   Health Check: http://localhost:{args.port}/health")
    print(f"   API Status: http://localhost:{args.port}/api/status")
    print(f"   Chat API: http://localhost:{args.port}/api/chat/")
    print(f"   Document API: http://localhost:{args.port}/api/documents/")
    print(f"   Web Scraper API: http://localhost:{args.port}/api/scraper/")
    print(f"   Notion API: http://localhost:{args.port}/api/notion/")
    
    print("\n🕷️ Web Scraper Quick Test:")
    print(f"   curl http://localhost:{args.port}/api/scraper/health")
    print(f"   curl http://localhost:{args.port}/api/scraper/test")
    
    print("\n📝 Notion API Quick Test:")
    print(f"   curl http://localhost:{args.port}/api/notion/health")
    print(f"   curl http://localhost:{args.port}/api/notion/pages")
    
    print("\n🚀 Starting Flask server...")
    print("=" * 60)
    
    # Start Flask server
    app = create_app()
    
    try:
        app.run(host=args.host, port=args.port, debug=args.debug)
    except KeyboardInterrupt:
        print("\n⚠️ Server stopped by user")
    except Exception as e:
        print(f"\n❌ Server error: {e}")
    finally:
        print("🔚 AI Personal Assistant Backend stopped")

if __name__ == '__main__':
    run_cli()
else:
    # When imported (e.g. by WSGI), create the app
    app = create_app()
    
    # Additional configuration for production deployment
    if os.getenv('FLASK_ENV') == 'production':
        # Production-specific settings
        app.config['DEBUG'] = False
        app.config['TESTING'] = False
        
        # Add security headers
        @app.after_request
        def after_request(response):
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['X-Frame-Options'] = 'DENY'
            response.headers['X-XSS-Protection'] = '1; mode=block'
            return response