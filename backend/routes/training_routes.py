from flask import Blueprint, jsonify

training_bp = Blueprint('training', __name__)

@training_bp.route('/health', methods=['GET'])
def training_health():
    return jsonify({
        "status": "training routes are working",
        "message": "✅ Training endpoint loaded successfully"
    })
