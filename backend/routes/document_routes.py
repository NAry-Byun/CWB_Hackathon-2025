# routes/document_routes.py - Document upload handling

from flask import Blueprint, request, jsonify
import os
import logging
from datetime import datetime
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)

# ─── Blueprint Definition ─────────────────────────────────────────────────────
document_bp = Blueprint('documents', __name__)

# ─── Configuration ────────────────────────────────────────────────────────────
UPLOAD_FOLDER = './data/uploads'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'docx', 'md', 'csv', 'json'}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@document_bp.route('/upload', methods=['POST'])
def upload_document():
    """Handle document upload"""
    try:
        # Check if file is in request
        if 'file' not in request.files:
            return _error_response("No file provided", 400)
        
        file = request.files['file']
        
        # Check if file was selected
        if file.filename == '':
            return _error_response("No file selected", 400)
        
        # Validate file
        if not allowed_file(file.filename):
            return _error_response(
                f"File type not allowed. Supported: {', '.join(ALLOWED_EXTENSIONS)}", 
                400
            )
        
        # Secure the filename
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{filename}"
        
        # Save file
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(file_path)
        
        # Get file info
        file_size = os.path.getsize(file_path)
        
        logger.info(f"📄 File uploaded: {filename} ({file_size} bytes)")
        
        # Return success response
        result_data = {
            "document_id": timestamp,
            "filename": filename,
            "original_filename": file.filename,
            "file_path": file_path,
            "file_size": file_size,
            "upload_time": datetime.now().isoformat(),
            "status": "uploaded"
        }
        
        return _success_response(result_data, f"File '{file.filename}' uploaded successfully")
        
    except Exception as e:
        logger.error(f"❌ Upload error: {e}")
        return _error_response(f"Upload failed: {str(e)}", 500)

@document_bp.route('/list', methods=['GET'])
def list_documents():
    """List uploaded documents"""
    try:
        documents = []
        
        if os.path.exists(UPLOAD_FOLDER):
            for filename in os.listdir(UPLOAD_FOLDER):
                file_path = os.path.join(UPLOAD_FOLDER, filename)
                if os.path.isfile(file_path):
                    stat = os.stat(file_path)
                    documents.append({
                        "filename": filename,
                        "file_size": stat.st_size,
                        "upload_time": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "file_path": file_path
                    })
        
        documents.sort(key=lambda x: x['upload_time'], reverse=True)
        
        return _success_response({
            "documents": documents,
            "count": len(documents),
            "upload_folder": UPLOAD_FOLDER
        }, f"Found {len(documents)} documents")
        
    except Exception as e:
        logger.error(f"❌ List documents error: {e}")
        return _error_response(f"Failed to list documents: {str(e)}", 500)

@document_bp.route('/health', methods=['GET'])
def document_health():
    """Health check for document service"""
    return jsonify({
        "status": "healthy",
        "upload_folder": UPLOAD_FOLDER,
        "allowed_extensions": list(ALLOWED_EXTENSIONS),
        "max_file_size": MAX_FILE_SIZE,
        "folder_exists": os.path.exists(UPLOAD_FOLDER),
        "timestamp": datetime.now().isoformat()
    })

def _success_response(data, message="Success"):
    """Create standardized success response"""
    return jsonify({
        "success": True,
        "message": message,
        "data": data,
        "timestamp": datetime.now().isoformat()
    })

def _error_response(message, status_code=400):
    """Create standardized error response"""
    return jsonify({
        "success": False,
        "error": message,
        "timestamp": datetime.now().isoformat()
    }), status_code