from flask import Blueprint, request, jsonify
import asyncio
import sys
import os

# Add path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from main_training import AITrainingBackend
except ImportError:
    AITrainingBackend = None

try:
    from utils.azure_logger import setup_azure_logger
    logger = setup_azure_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

# Response helpers
def success_response(data, message="Success"):
    return jsonify({
        'success': True,
        'message': message,
        'data': data
    })

def error_response(message, status_code=400):
    return jsonify({
        'success': False,
        'error': message
    }), status_code

# Create blueprint
training_bp = Blueprint('training', __name__)

# Global training backend instance
training_backend = None

def get_training_backend():
    """Get training backend instance"""
    global training_backend
    
    if training_backend is None and AITrainingBackend:
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                training_backend = AITrainingBackend()
                loop.run_until_complete(training_backend.initialize_services())
                logger.info("✅ Training backend initialized")
            finally:
                loop.close()
        except Exception as e:
            logger.error(f"❌ Training backend initialization failed: {e}")
            training_backend = None
    
    return training_backend

@training_bp.route('/start', methods=['POST'])
def start_training():
    """Start comprehensive training"""
    try:
        backend = get_training_backend()
        if not backend:
            return error_response("Training backend not available", 503)
        
        # Run comprehensive training
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(backend.run_comprehensive_training())
            return success_response(result, "Training completed")
        finally:
            loop.close()
        
    except Exception as e:
        logger.error(f"❌ Training start error: {e}")
        return error_response(f"Failed to start training: {str(e)}", 500)

@training_bp.route('/stats', methods=['GET'])
def get_training_stats():
    """Get training statistics"""
    try:
        backend = get_training_backend()
        if not backend:
            return error_response("Training backend not available", 503)
        
        # Get statistics
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            stats = loop.run_until_complete(backend.get_training_statistics())
            return success_response(stats, "Statistics retrieved")
        finally:
            loop.close()
        
    except Exception as e:
        logger.error(f"❌ Training stats error: {e}")
        return error_response(f"Failed to get statistics: {str(e)}", 500)

@training_bp.route('/health', methods=['GET'])
def training_health():
    """Training service health check"""
    return jsonify({
        'status': 'healthy',
        'services': {
            'training_backend': training_backend is not None
        }
    })
