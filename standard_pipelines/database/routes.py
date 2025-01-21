from datetime import datetime
from flask import jsonify, current_app
from . import database
from cryptography.fernet import Fernet
from standard_pipelines import db
import os

@database.route('/create_secure_object')
def create_secure_object():
    from standard_pipelines.data_flow.models import SecureObject
    try:
        # Create a new secure object with some test data
        secure_obj = SecureObject()
        secure_obj.encryption_key_id = "test_key_id"
        test_secret = "This is a super secret message!"
        secure_obj.secret = test_secret
        
        # Save to database
        db.session.add(secure_obj)
        db.session.commit()
        
        # Try to retrieve and decrypt
        retrieved_obj = SecureObject.query.get(secure_obj.id)
        if retrieved_obj is None:
            raise ValueError("Failed to retrieve created object")
            
        decrypted_secret = retrieved_obj.secret
        created_time = retrieved_obj.created_at
        if isinstance(created_time, datetime):
            created_time_str = created_time.isoformat()
        else:
            created_time_str = str(created_time)
        
        return jsonify({
            "status": "success",
            "message": "SecureObject created successfully",
            "data": {
                "id": str(secure_obj.id),
                "original_secret": test_secret,
                "decrypted_secret": decrypted_secret,
                "created_at": created_time_str
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error creating secure object: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
