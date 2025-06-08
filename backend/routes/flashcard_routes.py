# routes/flashcard_routes.py - SIMPLE VERSION - NO ASYNC ISSUES

from flask import Blueprint, request, jsonify
import sys
import os
import logging
from datetime import datetime
from typing import Dict, Any, List

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
logger = logging.getLogger(__name__)

# Import services with error handling
try:
    from services.flashcard_service import FlashCardService
    logger.info("✅ FlashCardService imported successfully")
except ImportError as e:
    logger.warning(f"⚠️ FlashCardService not available: {e}")
    FlashCardService = None

try:
    from services.azure_openai_service import AzureOpenAIService
    logger.info("✅ AzureOpenAIService imported for flashcards")
except ImportError as e:
    logger.warning(f"⚠️ AzureOpenAIService not available for flashcards: {e}")
    AzureOpenAIService = None

# Blueprint definition
flashcard_bp = Blueprint('flashcards', __name__)

# Global service instances
flashcard_service = None
openai_service = None
services_initialized = False

def initialize_services():
    """Initialize flashcard services"""
    global flashcard_service, openai_service, services_initialized
    
    if services_initialized:
        return
    
    # Initialize OpenAI service first
    if AzureOpenAIService:
        try:
            openai_service = AzureOpenAIService()
            logger.info("✅ OpenAI service initialized for flashcards")
        except Exception as e:
            logger.error(f"❌ Failed to initialize OpenAI service: {e}")
            openai_service = None
    
    # Initialize FlashCard service
    if FlashCardService:
        try:
            flashcard_service = FlashCardService()
            if openai_service:
                flashcard_service.set_openai_service(openai_service)
            logger.info("✅ FlashCardService initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize FlashCardService: {e}")
            flashcard_service = None
    
    services_initialized = True

# Initialize services on import
initialize_services()

def _handle_cors():
    """Handle CORS preflight requests"""
    response = jsonify()
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type, Authorization")
    response.headers.add("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
    return response

def _success_response(data: Dict[str, Any], message: str = "Success") -> tuple:
    """Create standardized success response"""
    response = {
        "success": True,
        "message": message,
        "timestamp": datetime.now().isoformat(),
        "data": data
    }
    return jsonify(response), 200

def _error_response(error_message: str, status_code: int = 400) -> tuple:
    """Create standardized error response"""
    response = {
        "success": False,
        "error": error_message,
        "timestamp": datetime.now().isoformat(),
        "data": None
    }
    return jsonify(response), status_code

# ─── FLASHCARD CREATION ENDPOINTS ─────────────────────────────────────────────

@flashcard_bp.route('/create-from-conversation', methods=['POST', 'OPTIONS'])
def create_flashcard_from_conversation():
    """Create flashcard from chat conversation Q&A - SYNCHRONOUS"""
    if request.method == 'OPTIONS':
        return _handle_cors()
    
    if not flashcard_service:
        return _error_response("FlashCard service not available", 503)
    
    data = request.get_json()
    if not data:
        return _error_response("Request body is required", 400)
    
    # Validate required fields
    required_fields = ['user_id', 'question', 'answer']
    missing_fields = [field for field in required_fields if not data.get(field)]
    if missing_fields:
        return _error_response(f"Missing required fields: {', '.join(missing_fields)}", 400)
    
    user_id = data['user_id']
    question = data['question']
    answer = data['answer']
    conversation_context = data.get('conversation_context', [])
    
    logger.info(f"🧠 Creating flashcard from conversation for user {user_id}")
    
    try:
        # FIXED: Use synchronous method - NO ASYNC
        result = flashcard_service.create_flashcard_from_conversation_sync(
            user_id=user_id,
            question=question,
            answer=answer,
            conversation_context=conversation_context
        )
        
        if result['success']:
            logger.info(f"✅ Flashcard created: {result['flashcard_id']}")
            return _success_response(result, "Flashcard created successfully")
        else:
            logger.error(f"❌ Failed to create flashcard: {result.get('error')}")
            return _error_response(result.get('error', 'Unknown error'), 500)
    
    except Exception as e:
        logger.error(f"❌ Flashcard creation failed: {e}")
        return _error_response(f"Failed to create flashcard: {str(e)}", 500)

@flashcard_bp.route('/create-manual', methods=['POST', 'OPTIONS'])
def create_manual_flashcard():
    """Create flashcard manually with front and back - SYNCHRONOUS"""
    if request.method == 'OPTIONS':
        return _handle_cors()
    
    if not flashcard_service:
        return _error_response("FlashCard service not available", 503)
    
    data = request.get_json()
    if not data:
        return _error_response("Request body is required", 400)
    
    required_fields = ['user_id', 'front', 'back']
    missing_fields = [field for field in required_fields if not data.get(field)]
    if missing_fields:
        return _error_response(f"Missing required fields: {', '.join(missing_fields)}", 400)
    
    try:
        # FIXED: Use synchronous method - NO ASYNC
        result = flashcard_service.create_flashcard_from_conversation_sync(
            user_id=data['user_id'],
            question=data['front'],
            answer=data['back'],
            conversation_context=data.get('context', [])
        )
        
        if result['success']:
            return _success_response(result, "Manual flashcard created successfully")
        else:
            return _error_response(result.get('error', 'Unknown error'), 500)
    
    except Exception as e:
        logger.error(f"❌ Manual flashcard creation failed: {e}")
        return _error_response(f"Failed to create flashcard: {str(e)}", 500)

# ─── FLASHCARD REVIEW ENDPOINTS ───────────────────────────────────────────────

@flashcard_bp.route('/review/due', methods=['GET', 'OPTIONS'])
def get_flashcards_for_review():
    """Get flashcards due for review - SYNCHRONOUS"""
    if request.method == 'OPTIONS':
        return _handle_cors()
    
    if not flashcard_service:
        return _error_response("FlashCard service not available", 503)
    
    user_id = request.args.get('user_id')
    if not user_id:
        return _error_response("user_id parameter is required", 400)
    
    limit = int(request.args.get('limit', 10))
    deck_name = request.args.get('deck_name')
    
    logger.info(f"📚 Getting flashcards for review - user: {user_id}, limit: {limit}")
    
    try:
        # FIXED: Use synchronous method - NO ASYNC
        flashcards = flashcard_service.get_flashcards_for_review_sync(
            user_id=user_id,
            limit=limit,
            deck_name=deck_name
        )
        
        return _success_response({
            "flashcards": flashcards,
            "count": len(flashcards),
            "limit": limit,
            "deck_name": deck_name
        }, f"Found {len(flashcards)} flashcards for review")
    
    except Exception as e:
        logger.error(f"❌ Failed to get flashcards for review: {e}")
        return _error_response(f"Failed to get flashcards: {str(e)}", 500)

@flashcard_bp.route('/review/submit', methods=['POST', 'OPTIONS'])
def submit_flashcard_review():
    """Submit flashcard review result - SYNCHRONOUS"""
    if request.method == 'OPTIONS':
        return _handle_cors()
    
    if not flashcard_service:
        return _error_response("FlashCard service not available", 503)
    
    data = request.get_json()
    if not data:
        return _error_response("Request body is required", 400)
    
    required_fields = ['user_id', 'flashcard_id', 'correct']
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        return _error_response(f"Missing required fields: {', '.join(missing_fields)}", 400)
    
    user_id = data['user_id']
    flashcard_id = data['flashcard_id']
    correct = bool(data['correct'])
    response_time = data.get('response_time')  # milliseconds
    
    logger.info(f"📊 Submitting review: {flashcard_id} = {correct} for user {user_id}")
    
    try:
        # FIXED: Use synchronous method - NO ASYNC
        result = flashcard_service.review_flashcard_sync(
            user_id=user_id,
            flashcard_id=flashcard_id,
            correct=correct,
            response_time=response_time
        )
        
        if result['success']:
            logger.info(f"✅ Review submitted successfully for {flashcard_id}")
            return _success_response(result, "Review submitted successfully")
        else:
            return _error_response(result.get('error', 'Unknown error'), 500)
    
    except Exception as e:
        logger.error(f"❌ Failed to submit review: {e}")
        return _error_response(f"Failed to submit review: {str(e)}", 500)

# ─── FLASHCARD MANAGEMENT ENDPOINTS ───────────────────────────────────────────

@flashcard_bp.route('/list', methods=['GET', 'OPTIONS'])
def list_user_flashcards():
    """List all flashcards for a user - SYNCHRONOUS"""
    if request.method == 'OPTIONS':
        return _handle_cors()
    
    if not flashcard_service:
        return _error_response("FlashCard service not available", 503)
    
    user_id = request.args.get('user_id')
    if not user_id:
        return _error_response("user_id parameter is required", 400)
    
    limit = int(request.args.get('limit', 50))
    deck_name = request.args.get('deck_name')
    
    logger.info(f"📚 Listing flashcards for user {user_id}, limit: {limit}")
    
    try:
        # FIXED: Use synchronous method - NO ASYNC
        flashcards = flashcard_service.get_user_flashcards_sync(
            user_id=user_id,
            limit=limit,
            deck_name=deck_name
        )
        
        return _success_response({
            "flashcards": flashcards,
            "count": len(flashcards),
            "limit": limit,
            "deck_name": deck_name
        }, f"Found {len(flashcards)} flashcards")
    
    except Exception as e:
        logger.error(f"❌ Failed to list flashcards: {e}")
        return _error_response(f"Failed to list flashcards: {str(e)}", 500)

@flashcard_bp.route('/stats', methods=['GET', 'OPTIONS'])
def get_flashcard_stats():
    """Get flashcard statistics for a user - SYNCHRONOUS"""
    if request.method == 'OPTIONS':
        return _handle_cors()
    
    if not flashcard_service:
        return _error_response("FlashCard service not available", 503)
    
    user_id = request.args.get('user_id')
    if not user_id:
        return _error_response("user_id parameter is required", 400)
    
    logger.info(f"📊 Getting stats for user {user_id}")
    
    try:
        # FIXED: Use synchronous method - NO ASYNC
        stats = flashcard_service.get_flashcard_stats_sync(user_id)
        return _success_response(stats, "Flashcard statistics retrieved successfully")
    
    except Exception as e:
        logger.error(f"❌ Failed to get flashcard stats: {e}")
        return _error_response(f"Failed to get stats: {str(e)}", 500)

@flashcard_bp.route('/delete/<flashcard_id>', methods=['DELETE', 'OPTIONS'])
def delete_flashcard(flashcard_id):
    """Delete a flashcard - SYNCHRONOUS"""
    if request.method == 'OPTIONS':
        return _handle_cors()
    
    if not flashcard_service:
        return _error_response("FlashCard service not available", 503)
    
    user_id = request.args.get('user_id')
    if not user_id:
        return _error_response("user_id parameter is required", 400)
    
    logger.info(f"🗑️ Deleting flashcard {flashcard_id} for user {user_id}")
    
    try:
        # FIXED: Use synchronous method - NO ASYNC
        success = flashcard_service.delete_flashcard_sync(user_id, flashcard_id)
        
        if success:
            return _success_response({
                "deleted": True,
                "flashcard_id": flashcard_id
            }, "Flashcard deleted successfully")
        else:
            return _error_response("Failed to delete flashcard", 500)
    
    except Exception as e:
        logger.error(f"❌ Failed to delete flashcard: {e}")
        return _error_response(f"Failed to delete flashcard: {str(e)}", 500)

# ─── INTEGRATION ENDPOINTS ────────────────────────────────────────────────────

@flashcard_bp.route('/from-chat', methods=['POST', 'OPTIONS'])
def create_flashcard_from_chat():
    """Create flashcard from recent chat conversation - SYNCHRONOUS"""
    if request.method == 'OPTIONS':
        return _handle_cors()
    
    if not flashcard_service:
        return _error_response("FlashCard service not available", 503)
    
    data = request.get_json()
    if not data:
        return _error_response("Request body is required", 400)
    
    user_id = data.get('user_id')
    if not user_id:
        return _error_response("user_id is required", 400)
    
    # This endpoint expects the frontend to send the last Q&A from chat
    user_message = data.get('user_message')
    ai_response = data.get('ai_response')
    
    if not user_message or not ai_response:
        return _error_response("user_message and ai_response are required", 400)
    
    logger.info(f"🧠 Creating flashcard from chat for user {user_id}")
    logger.info(f"    Question: {user_message[:100]}...")
    logger.info(f"    Answer: {ai_response[:100]}...")
    
    try:
        # FIXED: Use synchronous method - NO ASYNC
        result = flashcard_service.create_flashcard_from_conversation_sync(
            user_id=user_id,
            question=user_message,
            answer=ai_response,
            conversation_context=data.get('context', [])
        )
        
        if result['success']:
            logger.info(f"✅ Flashcard created from chat: {result['flashcard_id']}")
            return _success_response(result, "Flashcard created from chat conversation")
        else:
            logger.error(f"❌ Failed to create flashcard from chat: {result.get('error')}")
            return _error_response(result.get('error', 'Unknown error'), 500)
    
    except Exception as e:
        logger.error(f"❌ Failed to create flashcard from chat: {e}")
        return _error_response(f"Failed to create flashcard: {str(e)}", 500)

# ─── HEALTH AND DEBUG ENDPOINTS ───────────────────────────────────────────────

@flashcard_bp.route('/health', methods=['GET', 'OPTIONS'])
def flashcard_health():
    """Health check for flashcard service - SYNCHRONOUS"""
    if request.method == 'OPTIONS':
        return _handle_cors()
    
    if not flashcard_service:
        return jsonify({
            "status": "unhealthy",
            "service": "FlashCard Service",
            "error": "FlashCard service not available",
            "timestamp": datetime.now().isoformat(),
            "available_services": {
                "flashcard_service": False,
                "openai_service": openai_service is not None
            }
        }), 503
    
    try:
        # FIXED: Use synchronous method - NO ASYNC
        health_data = flashcard_service.health_check_sync()
        
        # Add endpoint information
        health_data.update({
            "timestamp": datetime.now().isoformat(),
            "endpoints": [
                "/create-from-conversation",
                "/create-manual", 
                "/review/due",
                "/review/submit",
                "/list",
                "/stats",
                "/delete/<id>",
                "/from-chat",
                "/health",
                "/test"
            ],
            "features": [
                "Simple flashcard creation",
                "Spaced repetition algorithm (SM-2)",
                "Progress tracking with statistics",
                "Basic difficulty assessment",
                "File-based storage (no async issues)",
                "Conversation context preservation"
            ],
            "available_services": {
                "flashcard_service": True,
                "openai_service": openai_service is not None,
                "cosmos_db": False,  # Using file storage
                "file_storage": True
            },
            "storage_type": "file_based",
            "async_handling": "completely_synchronous"  # FIXED
        })
        
        status_code = 200 if health_data.get("status") == "healthy" else 503
        return jsonify(health_data), status_code
    
    except Exception as e:
        logger.error(f"❌ Flashcard health check failed: {e}")
        return jsonify({
            "status": "unhealthy",
            "service": "FlashCard Service",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
            "available_services": {
                "flashcard_service": True,
                "openai_service": openai_service is not None,
                "cosmos_db": False,
                "file_storage": False
            }
        }), 500

@flashcard_bp.route('/test', methods=['GET', 'OPTIONS'])
def test_flashcard_system():
    """Test endpoint for flashcard system - SYNCHRONOUS"""
    if request.method == 'OPTIONS':
        return _handle_cors()
    
    return jsonify({
        "status": "FlashCard routes working",
        "message": "FlashCard system ready - SYNCHRONOUS VERSION",
        "timestamp": datetime.now().isoformat(),
        "service_status": {
            "flashcard_service": flashcard_service is not None,
            "openai_service": openai_service is not None,
            "services_initialized": services_initialized
        },
        "storage_type": "file_based",
        "async_handling": "completely_synchronous_no_event_loop_issues",  # FIXED
        "usage": {
            "create_from_chat": "POST /from-chat with {user_id, user_message, ai_response}",
            "get_for_review": "GET /review/due?user_id=USER_ID",
            "submit_review": "POST /review/submit with {user_id, flashcard_id, correct}",
            "get_stats": "GET /stats?user_id=USER_ID",
            "list_cards": "GET /list?user_id=USER_ID",
            "delete_card": "DELETE /delete/<id>?user_id=USER_ID"
        },
        "integration": {
            "chat_system": "Integrated with existing chat routes",
            "ai_enhancement": "Basic keyword-based tagging (no async AI calls)",
            "spaced_repetition": "SM-2 algorithm for optimal review scheduling",
            "storage": "JSON files (no database async issues)"
        },
        "example_workflow": [
            "1. User asks question in chat",
            "2. AI responds with answer", 
            "3. User says 'create flashcard' or clicks flashcard button",
            "4. System creates flashcard with basic enhancement",
            "5. Flashcard appears in review queue",
            "6. User reviews and system adjusts scheduling"
        ],
        "test_commands": {
            "health_check": "GET /api/flashcards/health",
            "test_creation": "POST /api/flashcards/from-chat",
            "get_stats": "GET /api/flashcards/stats?user_id=test_user"
        },
        "advantages": [
            "No async/event loop issues",
            "File-based storage (reliable)",
            "Immediate functionality",
            "Simple but effective"
        ]
    })

# ─── DEBUG ENDPOINT ───────────────────────────────────────────────────────────

@flashcard_bp.route('/debug/create-test', methods=['POST', 'OPTIONS'])
def debug_create_test_flashcard():
    """Debug endpoint to create a test flashcard - SYNCHRONOUS"""
    if request.method == 'OPTIONS':
        return _handle_cors()
    
    if not flashcard_service:
        return _error_response("FlashCard service not available", 503)
    
    # Create a test flashcard
    test_data = {
        "user_id": "debug_user",
        "user_message": "What is the purpose of flashcards in learning?",
        "ai_response": "Flashcards are a learning tool that uses active recall and spaced repetition to help improve memory retention. They work by presenting a question or prompt on one side and the answer on the other, forcing the learner to retrieve information from memory."
    }
    
    logger.info("🧪 Creating debug test flashcard")
    
    try:
        # FIXED: Use synchronous method - NO ASYNC
        result = flashcard_service.create_flashcard_from_conversation_sync(
            user_id=test_data["user_id"],
            question=test_data["user_message"],
            answer=test_data["ai_response"],
            conversation_context=[]
        )
        
        if result['success']:
            logger.info(f"✅ Debug flashcard created: {result['flashcard_id']}")
            return _success_response({
                "test_data": test_data,
                "result": result,
                "debug": True,
                "storage": "file_based",
                "async_fix": "completely_synchronous"  # FIXED
            }, "Debug flashcard created successfully")
        else:
            return _error_response(f"Debug flashcard creation failed: {result.get('error')}", 500)
    
    except Exception as e:
        logger.error(f"❌ Debug flashcard creation failed: {e}")
        return _error_response(f"Debug flashcard creation failed: {str(e)}", 500)