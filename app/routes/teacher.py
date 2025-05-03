from flask import Blueprint, render_template, abort, request, redirect, url_for, flash
from flask_login import login_required, current_user
from functools import wraps
from datetime import datetime, timedelta
from ..models import db
from ..models.classroom import Classroom
from ..models.character import Character
from ..models.clan import Clan
from ..models.quest import Quest
from ..models.audit import AuditLog
from app.models.user import User, UserRole
from werkzeug.security import generate_password_hash
import csv
from io import TextIOWrapper
from werkzeug.utils import secure_filename

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

@teacher_bp.route('/dashboard')
@login_required
@teacher_required
def dashboard():
    """Teacher dashboard main view."""
    # Get stats for the current teacher
    stats = {
        'active_classes': Classroom.query.filter_by(
            teacher_id=current_user.id, 
            is_active=True
        ).count(),
        
        'total_students': db.session.query(Classroom.students).\
            join(Classroom.students).\
            filter(Classroom.teacher_id == current_user.id).\
            distinct().\
            count(),
        
        'active_clans': Clan.query.\
            join(Classroom, Clan.class_id == Classroom.id).\
            filter(Classroom.teacher_id == current_user.id,
                  Clan.is_active == True).\
            count(),
        
        'active_quests': Quest.query.\
            join(Classroom, Quest.id == Classroom.id).\
            filter(Classroom.teacher_id == current_user.id,
                  Quest.end_date >= datetime.utcnow()).\
            count()
    }

    # Get recent activities (last 7 days)
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    recent_activities = []
    
    # Get audit logs for relevant events
    audit_logs = AuditLog.query.\
        join(Character, AuditLog.character_id == Character.id).\
        join(Classroom, Classroom.id == Character.student_id).\
        filter(
            Classroom.teacher_id == current_user.id,
            AuditLog.event_timestamp >= seven_days_ago,
            AuditLog.event_type.in_([
                'QUEST_START', 'QUEST_COMPLETE', 'QUEST_FAIL',
                'CLAN_JOIN', 'CLAN_LEAVE', 'LEVEL_UP',
                'ABILITY_LEARN', 'EQUIPMENT_CHANGE'
            ])
        ).\
        order_by(AuditLog.event_timestamp.desc()).\
        limit(10).all()
    
    # Format audit logs for display
    for log in audit_logs:
        activity = {
            'title': AuditLog.EVENT_TYPES.get(log.event_type, log.event_type),
            'timestamp': log.event_timestamp,
            'description': f"{log.character.name} - {log.event_data.get('description', '')}",
            'details': log.event_data.get('details', '')
        }
        recent_activities.append(activity)

    # Fetch all active classes for the current teacher
    classes = Classroom.query.filter_by(teacher_id=current_user.id, is_active=True).all()

    return render_template(
        'teacher/dashboard.html',
        title='Teacher Dashboard',
        teacher=current_user,
        stats=stats,
        recent_activities=recent_activities,
        active_page='dashboard',
        classes=classes
    )

@teacher_bp.route('/add-student', methods=['GET', 'POST'])
@login_required
@teacher_required
def add_student():
    classes = Classroom.query.filter_by(teacher_id=current_user.id, is_active=True).all()
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        class_id = request.form.get('class_id')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')

        # Validation
        if not all([username, email, password, class_id]):
            flash('All fields are required.', 'danger')
            return render_template('teacher/add_student.html', classes=classes)

        if User.query.filter((User.username == username) | (User.email == email)).first():
            flash('Username or email already exists.', 'danger')
            return render_template('teacher/add_student.html', classes=classes)

        # Create user
        new_user = User(
            username=username,
            email=email,
            role=UserRole.STUDENT,
            first_name=first_name,
            last_name=last_name
        )
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        # Assign to class
        classroom = Classroom.query.get(class_id)
        if classroom:
            classroom.add_student(new_user)
            flash('Student account created and added to class!', 'success')
        else:
            flash('Class not found.', 'danger')

        return redirect(url_for('teacher.add_student'))

    return render_template('teacher/add_student.html', classes=classes)

@teacher_bp.route('/import-students', methods=['GET', 'POST'])
@login_required
@teacher_required
def import_students():
    classes = Classroom.query.filter_by(teacher_id=current_user.id, is_active=True).all()
    results = None
    errors = []
    if request.method == 'POST':
        file = request.files.get('csv_file')
        class_id = request.form.get('class_id')
        if not file or not class_id:
            flash('CSV file and class selection are required.', 'danger')
            return render_template('teacher/import_students.html', classes=classes)
        try:
            stream = TextIOWrapper(file.stream, encoding='utf-8')
            reader = csv.DictReader(stream)
            required_fields = {'username', 'email', 'password'}
            if not required_fields.issubset(reader.fieldnames):
                flash('CSV must have columns: username, email, password', 'danger')
                return render_template('teacher/import_students.html', classes=classes)
            classroom = Classroom.query.get(class_id)
            if not classroom:
                flash('Class not found.', 'danger')
                return render_template('teacher/import_students.html', classes=classes)
            created = 0
            failed = 0
            for i, row in enumerate(reader, start=2):  # start=2 for header row
                username = row.get('username', '').strip()
                email = row.get('email', '').strip()
                password = row.get('password', '').strip()
                first_name = row.get('first_name', '').strip()
                last_name = row.get('last_name', '').strip()
                if not username or not email or not password:
                    errors.append(f'Row {i}: Missing required fields.')
                    failed += 1
                    continue
                if User.query.filter((User.username == username) | (User.email == email)).first():
                    errors.append(f'Row {i}: Username or email already exists.')
                    failed += 1
                    continue
                new_user = User(
                    username=username,
                    email=email,
                    role=UserRole.STUDENT,
                    first_name=first_name,
                    last_name=last_name
                )
                new_user.set_password(password)
                db.session.add(new_user)
                db.session.commit()
                classroom.add_student(new_user)
                created += 1
            results = {'created': created, 'failed': failed}
            if created:
                flash(f'Successfully created {created} students.', 'success')
            if failed:
                flash(f'Failed to create {failed} students. See errors below.', 'danger')
        except Exception as e:
            flash(f'Error processing CSV: {e}', 'danger')
    return render_template('teacher/import_students.html', classes=classes, results=results, errors=errors) 