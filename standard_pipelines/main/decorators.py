from flask import request, jsonify, current_app
from functools import wraps

# TODO: Move this to auth/decorators.py
def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            return jsonify({'error': 'No API key provided'}), 401
            
        expected_api_key = current_app.config.get('INTERNAL_API_KEY')
        if not expected_api_key:
            current_app.logger.error('INTERNAL_API_KEY not configured')
            return jsonify({'error': 'Server configuration error'}), 500
            
        if api_key != expected_api_key:
            return jsonify({'error': 'Invalid API key'}), 401
            
        return f(*args, **kwargs)
    return decorated_function