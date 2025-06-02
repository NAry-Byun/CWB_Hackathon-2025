def success_response(data, message="Success"):
    """Create success response"""
    return {
        'success': True,
        'message': message,
        'data': data
    }

def error_response(message, status_code=400):
    """Create error response"""
    return {
        'success': False,
        'error': message
    }, status_code

if __name__ == '__main__':
    # Initialize backend on startup when running as main module
    if __name__ != '__main__':
        initialize_backend_on_startup()
    
    # Create and run the app
    app = create_app()
    
    # Run with proper configuration
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_ENV') == 'development'
    
    logger.info(f"🚀 Starting Flask app on port {port}")
    app.run(host='0.0.0.0', port=port, debug=debug)