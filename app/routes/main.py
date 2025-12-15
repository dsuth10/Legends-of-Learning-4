from flask import Blueprint, render_template, redirect, url_for
from flask_login import current_user
from datetime import datetime
from app.models.user import UserRole

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def home():
    # Redirect authenticated users to their appropriate dashboard
    if current_user.is_authenticated:
        if current_user.role == UserRole.TEACHER:
            return redirect(url_for('teacher.dashboard'))
        elif current_user.role == UserRole.STUDENT:
            return redirect(url_for('student.character'))
    
    # Show welcome screen for unauthenticated users
    return render_template('welcome.html', year=datetime.now().year)

@main_bp.route('/test-template')
def test_template():
    return render_template('login.html') 