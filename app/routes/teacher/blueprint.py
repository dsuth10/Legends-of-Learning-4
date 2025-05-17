from flask import Blueprint, abort
from flask_login import current_user
from functools import wraps
from app.models.user import UserRole

teacher_bp = Blueprint('teacher', __name__, url_prefix='/teacher')

def teacher_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != UserRole.TEACHER:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

def student_required(f):
    """
    Decorator to restrict access to students only.
    Usage: @login_required @student_required above a view function.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != UserRole.STUDENT:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function 