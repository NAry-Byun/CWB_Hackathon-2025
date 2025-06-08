# app.py - Complete AI Personal Assistant Backend (Updated with FlashCard Integration)

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
        'http://localhost:3000', 'http://localhost:8080', 'http://localhost:5000',
        'http://127.0.0.1:3000', 'http://127.0.0.1:8080', 'http://127.0.0.1:5000',
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
            "message": "🤖 AI Personal Assistant Backend with FlashCards",
            "version": "3.1",
            "description": "Complete AI System with Azure OpenAI + AI Search + Cosmos DB + Blob Storage + Notion + FlashCards",
            "status": "running",
            "endpoints": {
                # Core Chat & Document endpoints
                "chat": "/api/chat/chat",
                "simple_chat": "/api/chat/simple",
                "chat_health": "/api/chat/health",
                "debug_azure_search": "/api/chat/debug/azure-search",
                "debug_upload_test": "/api/chat/debug/upload-test",
                "upload": "/api/documents/upload",
                "documents": "/api/documents/list",
                
                # NEW: FlashCard endpoints
                "flashcard_create_from_chat": "/api/flashcards/from-chat",
                "flashcard_create_manual": "/api/flashcards/create-manual",
                "flashcard_review_due": "/api/flashcards/review/due",
                "flashcard_review_submit": "/api/flashcards/review/submit",
                "flashcard_list": "/api/flashcards/list",
                "flashcard_stats": "/api/flashcards/stats",
                "flashcard_delete": "/api/flashcards/delete/<id>",
                "flashcard_health": "/api/flashcards/health",
                
                # Educational Content endpoints (if available)
                "education_process": "/api/education/process",
                "education_documents": "/api/education/documents",
                "education_health": "/api/education/health",
                "education_stats": "/api/education/stats",
                
                # Blob Storage Sync endpoints (if available)
                "blob_sync_health": "/api/blob-sync/health",
                "blob_sync_status": "/api/blob-sync/status",
                "blob_sync_all": "/api/blob-sync/sync-all",
                "blob_sync_file": "/api/blob-sync/sync-file",
                
                # Web Scraper endpoints (if available)
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
            "frontend_url": "http://localhost:5000",
            "cors_enabled": True,
            "features": [
                "Azure OpenAI GPT-4 Chat",
                "Azure AI Search Integration",
                "Cosmos DB Vector Search",
                "Document Upload & Processing", 
                "Speech-to-Text Support",
                "Real-time Chat Interface",
                "Debug Tools & Diagnostics",
                "Educational Content Generation",
                "AI-Powered Flashcards with Spaced Repetition",  # NEW
                "Intelligent Flashcard Enhancement",             # NEW
                "Automated Quiz Generation",
                "Blob Storage to Cosmos DB Sync",
                "Vector Search & Similarity",
                "Automated Text Chunking",
                "Notion Integration",
                "Professional Web Scraping",
                "AI-Optimized Content Extraction"
            ],
            "integrations": {
                "azure_openai": "GPT-4 & Embeddings",
                "azure_ai_search": "Document Indexing & Search",
                "cosmos_db": "Vector Database + FlashCard Storage",  # UPDATED
                "blob_storage": "Document Storage",
                "notion": "Knowledge Management",
                "web_scraping": "Content Extraction",
                "flashcards": "Spaced Repetition Learning System"    # NEW
            },
            "new_flashcard_features": [  # NEW
                "Create flashcards from any chat conversation",
                "AI-enhanced with automatic tags and difficulty",
                "Spaced repetition algorithm (SM-2)",
                "Mnemonic generation for better memory",
                "Progress tracking and statistics",
                "Seamless integration with existing chat"
            ]
        })

    @app.route('/health', methods=['GET'])
    def health_check():
        # Check various service statuses
        notion_status = False
        storage_status = False
        search_status = False
        flashcard_status = False  # NEW
        
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

        try:
            if os.getenv('AZURE_SEARCH_ENDPOINT'):
                from services.azure_ai_search_service import AzureAISearchService
                search_service = AzureAISearchService()
                search_status = True
        except Exception as e:
            logger.warning(f"Azure AI Search service check failed: {e}")

        # NEW: Check FlashCard service
        try:
            if os.getenv('COSMOS_DB_ENDPOINT') and os.getenv('AZURE_OPENAI_ENDPOINT'):
                from services.flashcard_service import FlashCardService
                flashcard_service = FlashCardService()
                flashcard_status = True
        except Exception as e:
            logger.warning(f"FlashCard service check failed: {e}")

        return jsonify({
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "message": "AI Personal Assistant Backend with FlashCards is operational",
            "services": {
                "flask": True,
                "cors": True,
                "routes": True,
                "upload_folder": os.path.exists('./data/uploads'),
                "azure_openai": bool(os.getenv('AZURE_OPENAI_ENDPOINT')),
                "azure_ai_search": search_status,
                "cosmos_db": bool(os.getenv('COSMOS_DB_ENDPOINT')),
                "notion": notion_status,
                "azure_storage": storage_status,
                "educational_content": True,
                "web_scraper": True,
                "flashcard_system": flashcard_status  # NEW
            },
            "python_version": sys.version,
            "backend_initialized": backend_instance is not None,
            "environment_variables": {
                "COSMOS_DB_ENDPOINT": bool(os.getenv('COSMOS_DB_ENDPOINT')),
                "COSMOS_DB_KEY": bool(os.getenv('COSMOS_DB_KEY')),
                "AZURE_OPENAI_ENDPOINT": bool(os.getenv('AZURE_OPENAI_ENDPOINT')),
                "AZURE_OPENAI_API_KEY": bool(os.getenv('AZURE_OPENAI_API_KEY')),
                "AZURE_SEARCH_ENDPOINT": bool(os.getenv('AZURE_SEARCH_ENDPOINT')),
                "AZURE_SEARCH_API_KEY": bool(os.getenv('AZURE_SEARCH_API_KEY')),
                "AZURE_STORAGE_CONNECTION_STRING": bool(os.getenv('AZURE_STORAGE_CONNECTION_STRING')),
                "BLOB_CONTAINER_NAME": bool(os.getenv('BLOB_CONTAINER_NAME')),
                "NOTION_API_TOKEN": bool(os.getenv('NOTION_API_TOKEN'))
            }
        })

    @app.route('/api/status', methods=['GET'])
    def api_status():
        """Complete API status and usage guide"""
        return jsonify({
            "api_status": "operational",
            "available_endpoints": {
                "chat_api": {
                    "base_url": "/api/chat",
                    "endpoints": ["/chat", "/simple", "/health", "/debug/azure-search", "/debug/upload-test"],
                    "description": "AI Chat with OpenAI GPT-4, Azure AI Search, and Cosmos DB"
                },
                "document_api": {
                    "base_url": "/api/documents", 
                    "endpoints": ["/upload", "/list", "/delete/<id>"],
                    "description": "Document upload and management with dual storage"
                },
                # NEW: FlashCard API
                "flashcard_api": {
                    "base_url": "/api/flashcards",
                    "endpoints": [
                        "/from-chat", "/create-manual", "/review/due", "/review/submit", 
                        "/list", "/stats", "/delete/<id>", "/health"
                    ],
                    "description": "AI-enhanced flashcards with spaced repetition learning"
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
            "core_features": {
                "azure_ai_search_integration": {
                    "description": "Full Azure AI Search integration with document indexing",
                    "test_endpoint": "/api/chat/debug/azure-search",
                    "upload_test": "/api/chat/debug/upload-test"
                },
                "dual_storage_system": {
                    "description": "Documents stored in both Cosmos DB and Azure AI Search",
                    "cosmos_db": "Vector embeddings and similarity search",
                    "azure_search": "Full-text and semantic search"
                },
                "intelligent_chat": {
                    "description": "AI chat using multiple data sources",
                    "sources": ["Azure AI Search", "Cosmos DB", "Notion pages"],
                    "endpoint": "/api/chat/chat"
                },
                # NEW: FlashCard system
                "flashcard_system": {
                    "description": "AI-enhanced flashcards with spaced repetition",
                    "features": ["Create from conversations", "Auto-enhancement", "SM-2 algorithm", "Progress tracking"],
                    "workflow": [
                        "Chat with AI", 
                        "Say 'create flashcard'", 
                        "AI enhances with tags/difficulty", 
                        "Review with spaced repetition"
                    ]
                }
            },
            "usage_examples": {
                "test_azure_search": {
                    "method": "GET",
                    "url": "/api/chat/debug/azure-search",
                    "description": "Check what documents are in Azure AI Search index"
                },
                "upload_document": {
                    "method": "POST",
                    "url": "/api/documents/upload",
                    "description": "Upload document to both Cosmos DB and Azure AI Search"
                },
                "intelligent_chat": {
                    "method": "POST", 
                    "url": "/api/chat/chat",
                    "body": {"message": "What were the key decisions from last month's planning meetings?", "user_id": "user123"},
                    "description": "Chat with AI using your document knowledge base"
                },
                # NEW: FlashCard examples
                "create_flashcard_from_chat": {
                    "method": "POST",
                    "url": "/api/flashcards/from-chat",
                    "body": {"user_id": "user123", "user_message": "What is photosynthesis?", "ai_response": "Photosynthesis is..."},
                    "description": "Create AI-enhanced flashcard from chat conversation"
                },
                "get_flashcards_for_review": {
                    "method": "GET",
                    "url": "/api/flashcards/review/due?user_id=user123&limit=10",
                    "description": "Get flashcards due for review using spaced repetition"
                },
                "submit_flashcard_review": {
                    "method": "POST",
                    "url": "/api/flashcards/review/submit",
                    "body": {"user_id": "user123", "flashcard_id": "card-abc", "correct": true, "response_time": 3000},
                    "description": "Submit review result and update spaced repetition schedule"
                },
                "educational_content": {
                    "method": "POST",
                    "url": "/api/education/process",
                    "body": "multipart/form-data with 'file' field",
                    "description": "Generate flashcards, quizzes, and summaries from documents"
                },
                "blob_sync": {
                    "method": "POST",
                    "url": "/api/blob-sync/sync-all",
                    "description": "Sync all Blob Storage files to Cosmos DB with vector embeddings"
                },
                "web_scraping": {
                    "method": "POST",
                    "url": "/api/scraper/scrape",
                    "body": {"url": "https://example.com/article"},
                    "description": "AI-optimized web scraping for clean content extraction"
                }
            },
            "quick_tests": {
                "health_check": "GET /health",
                "azure_search_debug": "GET /api/chat/debug/azure-search", 
                "chat_test": "POST /api/chat/simple with {\"message\": \"Hello\", \"user_id\": \"test\"}",
                "document_list": "GET /api/documents/list",
                "flashcard_health": "GET /api/flashcards/health"  # NEW
            },
            # NEW: FlashCard workflow
            "flashcard_workflow": {
                "step1": "User chats with AI: POST /api/chat/chat",
                "step2": "User says 'create flashcard' in chat",
                "step3": "System auto-creates enhanced flashcard",
                "step4": "Get cards for review: GET /api/flashcards/review/due",
                "step5": "Study and submit results: POST /api/flashcards/review/submit",
                "step6": "Track progress: GET /api/flashcards/stats"
            },
            "timestamp": datetime.now().isoformat()
        })

    # Error handlers (same as your original)
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            'success': False,
            'error': 'Endpoint not found',
            'path': request.path,
            'available_endpoints': [
                '/api/chat/chat',
                '/api/chat/debug/azure-search',
                '/api/documents/upload',
                '/api/flashcards/from-chat',     # NEW
                '/api/flashcards/review/due',   # NEW
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

# ─── UPDATED REGISTER BLUEPRINTS (with FlashCard routes) ──────────────────────
def register_blueprints(app):
    """Import and register all route Blueprints with fallbacks."""
    
    # Core Chat Routes (REQUIRED - from my complete code)
    try:
        from routes.chat_routes import chat_bp
        app.register_blueprint(chat_bp, url_prefix='/api/chat')
        logger.info("✅ Chat routes registered at /api/chat")
    except Exception as e:
        logger.error(f"❌ Failed to register chat routes: {e}")

    # NEW: FlashCard Routes (REQUIRED for flashcard functionality)
    try:
        from routes.flashcard_routes import flashcard_bp
        app.register_blueprint(flashcard_bp, url_prefix='/api/flashcards')
        logger.info("✅ FlashCard routes registered at /api/flashcards")
    except Exception as e:
        logger.error(f"❌ Failed to register flashcard routes: {e}")

    # Document Management Routes (REQUIRED - from my complete code) 
    try:
        # Try your naming convention first
        from routes.document_routes import document_bp
        app.register_blueprint(document_bp, url_prefix='/api/documents')
        logger.info("✅ Document routes (document_routes) registered at /api/documents")
    except ImportError:
        try:
            # Fallback to my naming convention
            from routes.documents_routes import documents_bp
            app.register_blueprint(documents_bp, url_prefix='/api/documents')
            logger.info("✅ Document routes (documents_routes) registered at /api/documents")
        except Exception as e:
            logger.error(f"❌ Failed to register document routes: {e}")

    # Educational Content Routes (OPTIONAL - your advanced feature)
    try:
        from routes.education_routes import education_bp
        app.register_blueprint(education_bp, url_prefix='/api/education')
        logger.info("✅ Education routes registered at /api/education")
    except Exception as e:
        logger.warning(f"⚠️ Education routes not available: {e}")

    # Blob Storage Sync Routes (OPTIONAL - your advanced feature)
    try:
        from routes.blob_sync_routes import blob_sync_bp
        app.register_blueprint(blob_sync_bp, url_prefix='/api/blob-sync')
        logger.info("✅ Blob Sync routes registered at /api/blob-sync")
    except Exception as e:
        logger.warning(f"⚠️ Blob sync routes not available: {e}")

    # Web Scraper Routes (OPTIONAL - your advanced feature)
    try:
        from routes.web_scraper_routes import web_scraper_bp
        app.register_blueprint(web_scraper_bp, url_prefix='/api/scraper')
        logger.info("✅ Web Scraper routes registered at /api/scraper")
    except Exception as e:
        logger.warning(f"⚠️ Web scraper routes not available: {e}")

    # Notion Integration Routes (OPTIONAL - enhanced version)
    try:
        from routes.notion_routes import notion_bp
        app.register_blueprint(notion_bp, url_prefix='/api/notion')
        logger.info("✅ Notion routes registered at /api/notion")
    except Exception as e:
        logger.warning(f"⚠️ Notion routes not available: {e}")

    # Training Routes (OPTIONAL - your advanced feature)
    try:
        from routes.training_routes import training_bp
        app.register_blueprint(training_bp, url_prefix='/api/training')
        logger.info("✅ Training routes registered at /api/training")
    except Exception as e:
        logger.warning(f"⚠️ Training routes not available: {e}")

# ─── ENHANCED RUN CLI ─────────────────────────────────────────────────────────
def run_cli():
    parser = argparse.ArgumentParser(description='Complete AI Personal Assistant Backend with FlashCards')
    parser.add_argument('--init', action='store_true', help='Initialize backend services')
    parser.add_argument('--port', type=int, default=5000, help='Port to run Flask server on')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='Host to bind Flask server to')
    parser.add_argument('--debug', action='store_true', help='Run in debug mode')
    parser.add_argument('--test', action='store_true', help='Run in test mode')
    parser.add_argument('--basic', action='store_true', help='Run with basic features only (my complete code)')
    parser.add_argument('--flashcards-only', action='store_true', help='Run with FlashCard system focus')  # NEW
    args = parser.parse_args()

    # Create necessary directories
    os.makedirs('./data/uploads', exist_ok=True)
    os.makedirs('./data/documents', exist_ok=True)

    print("🚀 Complete AI Personal Assistant Backend with FlashCards Starting...")
    print("=" * 70)
    
    # Check environment variables
    required_vars = ['COSMOS_DB_ENDPOINT', 'COSMOS_DB_KEY', 'AZURE_OPENAI_ENDPOINT', 'AZURE_OPENAI_API_KEY']
    search_vars = ['AZURE_SEARCH_ENDPOINT', 'AZURE_SEARCH_API_KEY']
    optional_vars = ['AZURE_STORAGE_CONNECTION_STRING', 'BLOB_CONTAINER_NAME', 'NOTION_API_TOKEN']
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    missing_search = [var for var in search_vars if not os.getenv(var)]
    missing_optional = [var for var in optional_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"⚠️ Missing required environment variables: {', '.join(missing_vars)}")
        print("📝 Core features and FlashCards may not work properly")
    else:
        print("✅ All core environment variables are set")
        print("🧠 FlashCard system should be fully functional")
    
    if missing_search:
        print(f"⚠️ Missing Azure AI Search variables: {', '.join(missing_search)}")
        print("📝 Azure AI Search integration will be disabled")
    else:
        print("✅ Azure AI Search environment variables are set")
        
    if missing_optional:
        print(f"💡 Optional environment variables not set: {', '.join(missing_optional)}")
        print("   - AZURE_STORAGE_CONNECTION_STRING: Blob sync will be disabled")
        print("   - NOTION_API_TOKEN: Notion integration will be disabled")

    if args.flashcards_only:
        print("🧠 Running in FLASHCARDS FOCUS mode")
        print("   ✅ Azure OpenAI Chat with FlashCard creation")
        print("   ✅ AI-enhanced FlashCards with spaced repetition")
        print("   ✅ FlashCard progress tracking and statistics")
        print("   ✅ Cosmos DB storage for flashcards and progress")
        print("   💡 Other advanced features available but not emphasized")

    elif args.basic:
        print("🔧 Running in BASIC mode - using core features only")
        print("   ✅ Azure OpenAI Chat")
        print("   ✅ Azure AI Search Integration") 
        print("   ✅ Cosmos DB Vector Search")
        print("   ✅ Document Upload & Processing")
        print("   ✅ Speech-to-Text Support")
        print("   ✅ Debug Tools")
        print("   🧠 FlashCard system available")

    elif args.init and not args.test:
        print("🔧 Initializing FULL AI Personal Assistant Backend services…")
        try:
            # Try to import your advanced backend
            from main_training import AITrainingBackend

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                global backend_instance
                backend_instance = AITrainingBackend()
                loop.run_until_complete(backend_instance.initialize_services())
                print("✅ Advanced backend initialization completed successfully!")
                print(f"🔧 Available services: {list(backend_instance.services.keys())}")
            finally:
                loop.close()

        except Exception as e:
            print(f"❌ Advanced backend initialization failed: {e}")
            print("⚠️ Falling back to basic features...")
            print("🔧 Basic features + FlashCards will still be available:")
            print("   ✅ Chat API, Document Upload, Azure AI Search Debug, FlashCard System")

    elif args.test:
        print("🧪 Running in TEST mode - no service initialization")
        print("🔧 All services available in standalone mode")

    # Display startup information  
    print("\n" + "=" * 70)
    print("🌐 Flask Server Configuration:")
    print(f"   Host: {args.host}")
    print(f"   Port: {args.port}")
    print(f"   Debug Mode: {args.debug}")
    print(f"   Frontend URL: http://localhost:{args.port}")
    
    print("\n🔗 Core API Endpoints (Always Available):")
    print(f"   Health Check: http://localhost:{args.port}/health")
    print(f"   API Status: http://localhost:{args.port}/api/status")
    print(f"   Chat API: http://localhost:{args.port}/api/chat/chat")
    print(f"   Document Upload: http://localhost:{args.port}/api/documents/upload")
    print(f"   Azure Search Debug: http://localhost:{args.port}/api/chat/debug/azure-search")
    
    print("\n🧠 FlashCard System Endpoints:")
    print(f"   FlashCard Health: http://localhost:{args.port}/api/flashcards/health")
    print(f"   Create from Chat: http://localhost:{args.port}/api/flashcards/from-chat")
    print(f"   Get Review Cards: http://localhost:{args.port}/api/flashcards/review/due")
    print(f"   Submit Review: http://localhost:{args.port}/api/flashcards/review/submit")
    print(f"   FlashCard Stats: http://localhost:{args.port}/api/flashcards/stats")
    
    print("\n🔧 Advanced Features (If Available):")
    print(f"   Education API: http://localhost:{args.port}/api/education/")
    print(f"   Blob Sync API: http://localhost:{args.port}/api/blob-sync/")
    print(f"   Web Scraper API: http://localhost:{args.port}/api/scraper/")
    print(f"   Notion API: http://localhost:{args.port}/api/notion/")
    
    print("\n🧪 Quick Tests:")
    print(f"   curl http://localhost:{args.port}/health")
    print(f"   curl http://localhost:{args.port}/api/flashcards/health")
    print(f"   curl http://localhost:{args.port}/api/chat/debug/azure-search")
    print(f"   curl -X POST -F 'file=@test.txt' http://localhost:{args.port}/api/documents/upload")
    
    print("\n🧠 FlashCard Workflow:")
    print("   1. Chat with AI: POST /api/chat/chat")
    print("   2. Say 'create flashcard' in your message")
    print("   3. AI creates enhanced flashcard automatically")
    print("   4. Review cards: GET /api/flashcards/review/due?user_id=YOUR_ID")
    print("   5. Submit answers: POST /api/flashcards/review/submit")
    print("   6. Track progress: GET /api/flashcards/stats?user_id=YOUR_ID")
    
    print("\n🚀 Starting Flask server...")
    print("=" * 70)
    
    # Start Flask server
    app = create_app()
    
    try:
        app.run(host=args.host, port=args.port, debug=args.debug)
    except KeyboardInterrupt:
        print("\n⚠️ Server stopped by user")
    except Exception as e:
        print(f"\n❌ Server error: {e}")
    finally:
        print("🔚 AI Personal Assistant Backend with FlashCards stopped")

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