# app.py - Complete AI Personal Assistant Backend with Blob Storage Sync

import os
import sys
import asyncio
import logging
import argparse
from datetime import datetime
from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv

# ─── LOAD ENVIRONMENT VARIABLES ───
load_dotenv()

# ─── LOGGING SETUP ───
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ─── GLOBAL BACKEND INSTANCE ───
backend_instance = None

# ─── APP FACTORY ───
def create_app():
    app = Flask(__name__)
    CORS(app, origins=[
        'http://localhost:3000', 'http://localhost:8080',
        'http://127.0.0.1:3000', 'http://127.0.0.1:8080',
        'http://172.21.112.1:8080', 'http://192.168.10.152:8080',
        'http://192.168.10.75:8080'
    ])
    app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
    app.config['JSON_AS_ASCII'] = False

    register_blueprints(app)

    @app.route('/', methods=['GET'])
    def root():
        return jsonify({
            "message": "🤖 AI Personal Assistant Backend",
            "version": "2.4",
            "description": "Azure OpenAI + Cosmos DB + Blob Storage Sync + Educational Content Generator",
            "status": "running",
            "endpoints": {
                # Core Chat & Document endpoints
                "chat": "/api/chat/chat",
                "simple_chat": "/api/chat/simple",
                "chat_health": "/api/chat/health",
                "upload": "/api/documents/upload",
                "documents": "/api/documents/list",
                
                # Educational Content endpoints
                "education_process": "/api/education/process",
                "education_documents": "/api/education/documents",
                "education_health": "/api/education/health",
                "education_stats": "/api/education/stats",
                
                # Blob Storage Sync endpoints (NEW)
                "blob_sync_health": "/api/blob-sync/health",
                "blob_sync_status": "/api/blob-sync/status",
                "blob_sync_all": "/api/blob-sync/sync-all",
                "blob_sync_file": "/api/blob-sync/sync-file",
                
                # Web Scraper endpoints
                "scraper_health": "/api/scraper/health",
                "scraper_scrape": "/api/scraper/scrape",
                "scraper_test": "/api/scraper/test",
                
                # Notion Integration endpoints
                "notion_health": "/api/notion/health",
                "notion_pages": "/api/notion/pages",
                "notion_meetings": "/api/notion/meetings",
                "notion_page_content": "/api/notion/page/<page_id>",
                "notion_append": "/api/notion/page/<page_id>/append",
                
                # System endpoints
                "health": "/health",
                "api_status": "/api/status"
            },
            "frontend_url": "http://localhost:8080",
            "cors_enabled": True,
            "features": [
                "Azure OpenAI Chat",
                "Document Upload & Processing",
                "Educational Content Generation",
                "AI-Powered Flashcards",
                "Automated Quiz Generation",
                "Blob Storage to Cosmos DB Sync",  # NEW
                "Vector Search & Similarity",      # NEW
                "Automated Text Chunking",         # NEW
                "Cosmos DB Vector Storage",
                "Notion Integration",
                "Professional Web Scraping",
                "AI-Optimized Content Extraction"
            ],
            "integrations": {
                "azure_openai": "GPT-4 & Embeddings",
                "cosmos_db": "Vector Database",
                "blob_storage": "Document Storage",
                "notion": "Knowledge Management",
                "web_scraping": "Content Extraction"
            }
        })

    @app.route('/health', methods=['GET'])
    def health_check():
        # Check various service statuses
        notion_status = False
        storage_status = False
        
        try:
            if os.getenv('NOTION_API_TOKEN'):
                from services.notion_service import NotionService
                notion_service = NotionService()
                notion_status = True
        except Exception as e:
            logger.warning(f"Notion service check failed: {e}")
        
        try:
            if os.getenv('AZURE_STORAGE_CONNECTION_STRING'):
                from services.azure_storage_service import AzureStorageService
                storage_service = AzureStorageService()
                storage_status = True
        except Exception as e:
            logger.warning(f"Azure Storage service check failed: {e}")

        return jsonify({
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "message": "AI Personal Assistant Backend is operational",
            "services": {
                "flask": True,
                "cors": True,
                "routes": True,
                "upload_folder": os.path.exists('./data/uploads'),
                "notion": notion_status,
                "azure_storage": storage_status,
                "educational_content": True,
                "web_scraper": True
            },
            "python_version": sys.version,
            "backend_initialized": backend_instance is not None,
            "environment_variables": {
                "COSMOS_DB_ENDPOINT": bool(os.getenv('COSMOS_DB_ENDPOINT')),
                "COSMOS_DB_KEY": bool(os.getenv('COSMOS_DB_KEY')),
                "AZURE_OPENAI_ENDPOINT": bool(os.getenv('AZURE_OPENAI_ENDPOINT')),
                "AZURE_OPENAI_API_KEY": bool(os.getenv('AZURE_OPENAI_API_KEY')),
                "AZURE_STORAGE_CONNECTION_STRING": bool(os.getenv('AZURE_STORAGE_CONNECTION_STRING')),
                "BLOB_CONTAINER_NAME": bool(os.getenv('BLOB_CONTAINER_NAME')),
                "NOTION_API_TOKEN": bool(os.getenv('NOTION_API_TOKEN'))
            }
        })

    @app.route('/api/status', methods=['GET'])
    def api_status():
        """전체 API 상태 및 사용 가이드"""
        return jsonify({
            "api_status": "operational",
            "available_endpoints": {
                "chat_api": {
                    "base_url": "/api/chat",
                    "endpoints": ["/chat", "/simple", "/health"],
                    "description": "AI Chat with OpenAI GPT-4"
                },
                "document_api": {
                    "base_url": "/api/documents", 
                    "endpoints": ["/upload", "/list", "/delete"],
                    "description": "Document upload and management"
                },
                "education_api": {
                    "base_url": "/api/education",
                    "endpoints": ["/process", "/documents", "/documents/<id>", "/health", "/stats"],
                    "description": "Educational content generation (flashcards, quizzes, summaries)"
                },
                "blob_sync_api": {
                    "base_url": "/api/blob-sync",
                    "endpoints": ["/health", "/status", "/sync-all", "/sync-file"],
                    "description": "Blob Storage to Cosmos DB synchronization"
                },
                "web_scraper_api": {
                    "base_url": "/api/scraper",
                    "endpoints": ["/health", "/scrape", "/test"],
                    "description": "AI-optimized web content extraction"
                },
                "notion_api": {
                    "base_url": "/api/notion",
                    "endpoints": ["/health", "/pages", "/meetings", "/page/<page_id>", "/page/<page_id>/append"],
                    "description": "Notion workspace integration"
                }
            },
            "usage_examples": {
                "educational_content": {
                    "method": "POST",
                    "url": "/api/education/process",
                    "body": "multipart/form-data with 'file' field",
                    "description": "Upload document and generate flashcards, quizzes, and summaries"
                },
                "blob_sync": {
                    "method": "POST",
                    "url": "/api/blob-sync/sync-all",
                    "description": "Sync all Blob Storage files to Cosmos DB with vector embeddings"
                },
                "blob_sync_single": {
                    "method": "POST",
                    "url": "/api/blob-sync/sync-file",
                    "body": {"filename": "document.pdf"},
                    "description": "Sync specific file from Blob Storage"
                },
                "web_scraping": {
                    "method": "POST",
                    "url": "/api/scraper/scrape",
                    "body": {"url": "https://example.com/article"},
                    "description": "AI-optimized web scraping for clean responses"
                },
                "chat": {
                    "method": "POST", 
                    "url": "/api/chat/chat",
                    "body": {"message": "What is machine learning?"},
                    "description": "Chat with AI using document knowledge base"
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
                '/api/documents/upload',
                '/api/education/process',
                '/api/blob-sync/health',
                '/api/blob-sync/sync-all',
                '/api/scraper/scrape',
                '/api/notion/pages',
                '/api/status',
                '/health'
            ],
            'suggestion': f"Check /api/status for complete endpoint documentation",
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

# ─── REGISTER BLUEPRINTS ───
def register_blueprints(app):
    """Import and register all route Blueprints."""
    
    # Core Chat Routes
    try:
        from routes.chat_routes import chat_bp
        app.register_blueprint(chat_bp, url_prefix='/api/chat')
        logger.info("✅ Chat routes registered at /api/chat")
    except Exception as e:
        logger.error(f"❌ Failed to register chat routes: {e}")

    # Document Management Routes
    try:
        from routes.document_routes import document_bp
        app.register_blueprint(document_bp, url_prefix='/api/documents')
        logger.info("✅ Document routes registered at /api/documents")
    except Exception as e:
        logger.error(f"❌ Failed to register document routes: {e}")

    # Educational Content Routes
    try:
        from routes.education_routes import education_bp
        app.register_blueprint(education_bp, url_prefix='/api/education')
        logger.info("✅ Education routes registered at /api/education")
    except Exception as e:
        logger.error(f"❌ Failed to register education routes: {e}")

    # Blob Storage Sync Routes (NEW)
    try:
        from routes.blob_sync_routes import blob_sync_bp
        app.register_blueprint(blob_sync_bp, url_prefix='/api/blob-sync')
        logger.info("✅ Blob Sync routes registered at /api/blob-sync")
    except Exception as e:
        logger.error(f"❌ Failed to register blob sync routes: {e}")

    # Web Scraper Routes
    try:
        from routes.web_scraper_routes import web_scraper_bp
        app.register_blueprint(web_scraper_bp, url_prefix='/api/scraper')
        logger.info("✅ Web Scraper routes registered at /api/scraper")
    except Exception as e:
        logger.error(f"❌ Failed to register web scraper routes: {e}")

    # Notion Integration Routes
    try:
        from routes.notion_routes import notion_bp
        app.register_blueprint(notion_bp, url_prefix='/api/notion')
        logger.info("✅ Notion routes registered at /api/notion")
    except Exception as e:
        logger.warning(f"⚠️ Notion routes not available: {e}")

    # Training Routes (optional)
    try:
        from routes.training_routes import training_bp
        app.register_blueprint(training_bp, url_prefix='/api/training')
        logger.info("✅ Training routes registered at /api/training")
    except Exception as e:
        logger.warning(f"⚠️ Training routes not available: {e}")

# ─── RUN CLI ───
def run_cli():
    parser = argparse.ArgumentParser(description='AI Personal Assistant Backend with Blob Storage Sync')
    parser.add_argument('--init', action='store_true', help='Initialize backend services')
    parser.add_argument('--port', type=int, default=5000, help='Port to run Flask server on')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='Host to bind Flask server to')
    parser.add_argument('--debug', action='store_true', help='Run in debug mode')
    parser.add_argument('--test', action='store_true', help='Run in test mode')
    args = parser.parse_args()

    # Create necessary directories
    os.makedirs('./data/uploads', exist_ok=True)
    os.makedirs('./data/documents', exist_ok=True)

    print("🚀 AI Personal Assistant Backend Starting...")
    print("=" * 60)
    
    # Check environment variables
    required_vars = ['COSMOS_DB_ENDPOINT', 'COSMOS_DB_KEY', 'AZURE_OPENAI_ENDPOINT', 'AZURE_OPENAI_API_KEY']
    optional_vars = ['AZURE_STORAGE_CONNECTION_STRING', 'BLOB_CONTAINER_NAME', 'NOTION_API_TOKEN']
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    missing_optional = [var for var in optional_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"⚠️ Missing required environment variables: {', '.join(missing_vars)}")
        print("📝 Some features may not work properly")
    else:
        print("✅ All required environment variables are set")
        
    if missing_optional:
        print(f"💡 Optional environment variables not set: {', '.join(missing_optional)}")
        print("   - AZURE_STORAGE_CONNECTION_STRING: Blob sync will be disabled")
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
            print("🕷️ Web scraper, blob sync, and educational content will still be available")

    elif args.test:
        print("🧪 Running in test mode - no service initialization")
        print("🕷️ All services available in standalone mode")

    # Display startup information
    print("\n" + "=" * 60)
    print("🌐 Flask Server Configuration:")
    print(f"   Host: {args.host}")
    print(f"   Port: {args.port}")
    print(f"   Debug Mode: {args.debug}")
    print(f"   Frontend URL: http://localhost:{args.port}")
    
    print("\n🔗 Available API Endpoints:")
    print(f"   Health Check: http://localhost:{args.port}/health")
    print(f"   API Status: http://localhost:{args.port}/api/status")
    print(f"   Chat API: http://localhost:{args.port}/api/chat/")
    print(f"   Document API: http://localhost:{args.port}/api/documents/")
    print(f"   Education API: http://localhost:{args.port}/api/education/")
    print(f"   Blob Sync API: http://localhost:{args.port}/api/blob-sync/")
    print(f"   Web Scraper API: http://localhost:{args.port}/api/scraper/")
    print(f"   Notion API: http://localhost:{args.port}/api/notion/")
    
    print("\n📊 Blob Storage Sync Quick Test:")
    print(f"   curl http://localhost:{args.port}/api/blob-sync/health")
    print(f"   curl http://localhost:{args.port}/api/blob-sync/status")
    print(f"   curl -X POST http://localhost:{args.port}/api/blob-sync/sync-all")
    
    print("\n📚 Educational Content Quick Test:")
    print(f"   curl http://localhost:{args.port}/api/education/health")
    print(f"   curl -X POST -F 'file=@document.pdf' http://localhost:{args.port}/api/education/process")
    
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