"""Error handling utilities for consistent error responses."""

from flask import jsonify, render_template
from app.models import db
import logging

logger = logging.getLogger(__name__)


def handle_database_error(e, context="operation"):
    """Handle database-related errors consistently.
    
    Args:
        e: The exception that occurred
        context: Description of what operation was being performed
        
    Returns:
        tuple: (error_message, status_code)
    """
    db.session.rollback()
    logger.error(f"Database error during {context}: {str(e)}", exc_info=True)
    
    # Provide user-friendly message
    if "UNIQUE constraint" in str(e) or "duplicate" in str(e).lower():
        return "This record already exists. Please check for duplicates.", 400
    elif "FOREIGN KEY constraint" in str(e):
        return "Cannot perform this operation due to related records. Please check dependencies.", 400
    elif "NOT NULL constraint" in str(e):
        return "Required information is missing. Please fill in all required fields.", 400
    else:
        return "A database error occurred. Please try again or contact support if the problem persists.", 500


def handle_validation_error(e, context="validation"):
    """Handle validation errors consistently.
    
    Args:
        e: The exception that occurred (usually ValueError)
        context: Description of what was being validated
        
    Returns:
        tuple: (error_message, status_code)
    """
    logger.warning(f"Validation error during {context}: {str(e)}")
    return str(e), 400


def handle_generic_error(e, context="operation", user_message=None):
    """Handle generic errors consistently.
    
    Args:
        e: The exception that occurred
        context: Description of what operation was being performed
        user_message: Optional user-friendly message (defaults to generic message)
        
    Returns:
        tuple: (error_message, status_code)
    """
    logger.error(f"Error during {context}: {str(e)}", exc_info=True)
    db.session.rollback()
    
    if user_message:
        return user_message, 500
    else:
        return "An unexpected error occurred. Please try again or contact support if the problem persists.", 500


def json_error_response(message, status_code=500, error_type=None, error_code=None):
    """Create a consistent JSON error response.
    
    Args:
        message: Error message for the user
        status_code: HTTP status code
        error_type: Optional error type identifier
        error_code: Optional error code for frontend handling
        
    Returns:
        Flask JSON response
    """
    response = {
        'success': False,
        'message': message
    }
    if error_type:
        response['error_type'] = error_type
    if error_code:
        response['error_code'] = error_code
    
    return jsonify(response), status_code


def json_success_response(data=None, message=None, status_code=200):
    """Create a consistent JSON success response.
    
    Args:
        data: Optional data to include in response
        message: Optional success message
        status_code: HTTP status code (default 200)
        
    Returns:
        Flask JSON response
    """
    response = {'success': True}
    if data:
        response['data'] = data
    if message:
        response['message'] = message
    
    return jsonify(response), status_code


