from flask import Blueprint, render_template
from flask_login import login_required, current_user
from .teacher import student_required
from flask_sqlalchemy import SQLAlchemy

student_bp = Blueprint('student', __name__, url_prefix='/student')
db = SQLAlchemy()

@student_bp.route('/dashboard')
@login_required
@student_required
def dashboard():
    """Student dashboard main view."""
    student_profile = getattr(current_user, 'student_profile', None)
    classes = list(getattr(current_user, 'classes', []))
    main_character = getattr(current_user, 'characters', None)
    if main_character is not None:
        main_character = main_character.filter_by(is_active=True).first()
    clan = getattr(student_profile, 'clan', None) if student_profile else None
    active_quests = main_character.quest_logs.filter_by(status='in_progress').all() if main_character else []
    recent_activities = list(current_user.audit_logs.order_by(db.desc('event_timestamp')).limit(10))
    return render_template(
        'student/dashboard.html',
        student=current_user,
        student_profile=student_profile,
        classes=classes,
        main_character=main_character,
        clan=clan,
        active_quests=active_quests,
        recent_activities=recent_activities
    )

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