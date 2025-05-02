from flask import Blueprint, render_template
from flask_login import login_required, current_user
from .teacher import student_required

student_bp = Blueprint('student', __name__, url_prefix='/student')

@student_bp.route('/dashboard')
@login_required
@student_required
def dashboard():
    """Student dashboard main view."""
    return render_template('student/dashboard.html', student=current_user)

@student_bp.route('/profile')
@login_required
@student_required
def profile():
    return render_template('student/profile.html', student=current_user)

@student_bp.route('/quests')
@login_required
@student_required
def quests():
    return render_template('student/quests.html', student=current_user)

@student_bp.route('/clan')
@login_required
@student_required
def clan():
    return render_template('student/clan.html', student=current_user)

@student_bp.route('/character')
@login_required
@student_required
def character():
    return render_template('student/character.html', student=current_user)

@student_bp.route('/shop')
@login_required
@student_required
def shop():
    return render_template('student/shop.html', student=current_user)

@student_bp.route('/progress')
@login_required
@student_required
def progress():
    return render_template('student/progress.html', student=current_user) 