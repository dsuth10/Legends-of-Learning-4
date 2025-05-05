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
from app.models.classroom import class_students
import random, string
from app.models.student import Student

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
        
        'total_students': db.session.query(User).\
            join(class_students, class_students.c.user_id == User.id).\
            join(Classroom, Classroom.id == class_students.c.class_id).\
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
            # Create Student profile with correct class_id
            student_profile = Student(user_id=new_user.id, class_id=classroom.id)
            db.session.add(student_profile)
            db.session.commit()
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
                # Create Student profile with correct class_id
                student_profile = Student(user_id=new_user.id, class_id=classroom.id)
                db.session.add(student_profile)
                db.session.commit()
                created += 1
            results = {'created': created, 'failed': failed}
            if created:
                flash(f'Successfully created {created} students.', 'success')
            if failed:
                flash(f'Failed to create {failed} students. See errors below.', 'danger')
        except Exception as e:
            flash(f'Error processing CSV: {e}', 'danger')
    return render_template('teacher/import_students.html', classes=classes, results=results, errors=errors)

@teacher_bp.route('/classes', methods=['GET', 'POST'])
@login_required
@teacher_required
def classes():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        max_students = request.form.get('max_students', 30)
        errors = []
        if not name:
            errors.append('Class name is required.')
        def generate_join_code():
            return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        join_code = generate_join_code()
        attempts = 0
        while Classroom.query.filter_by(join_code=join_code).first():
            join_code = generate_join_code()
            attempts += 1
            if attempts > 10:
                errors.append('Could not generate a unique join code. Please try again.')
                break
        classes = Classroom.query.filter_by(teacher_id=current_user.id, is_active=True).all()
        if errors:
            flash(' '.join(errors), 'danger')
            return render_template('teacher/classes.html', active_page='classes', classes=classes)
        try:
            new_class = Classroom(
                name=name,
                description=description,
                join_code=join_code,
                teacher_id=current_user.id,
                max_students=max_students
            )
            db.session.add(new_class)
            db.session.commit()
            flash('Class created successfully!', 'success')
            return redirect(url_for('teacher.classes'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating class: {e}', 'danger')
            return render_template('teacher/classes.html', active_page='classes', classes=classes)
    # GET handler: fetch and display all active classes for this teacher
    classes = Classroom.query.filter_by(teacher_id=current_user.id, is_active=True).all()
    return render_template('teacher/classes.html', active_page='classes', classes=classes)

@teacher_bp.route('/classes/<int:class_id>/archive', methods=['POST'])
@login_required
@teacher_required
def archive_class(class_id):
    class_to_archive = Classroom.query.get_or_404(class_id)
    if class_to_archive.teacher_id != current_user.id:
        flash('You do not have permission to archive this class.', 'danger')
        return redirect(url_for('teacher.classes'))
    if not class_to_archive.is_active:
        flash('Class is already archived.', 'info')
        return redirect(url_for('teacher.classes'))
    try:
        class_to_archive.is_active = False
        db.session.commit()
        flash('Class archived successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error archiving class: {e}', 'danger')
    return redirect(url_for('teacher.classes'))

@teacher_bp.route('/classes/<int:class_id>/delete', methods=['POST'])
@login_required
@teacher_required
def delete_class(class_id):
    class_to_delete = Classroom.query.get_or_404(class_id)
    if class_to_delete.teacher_id != current_user.id:
        flash('You do not have permission to delete this class.', 'danger')
        return redirect(url_for('teacher.classes'))
    try:
        db.session.delete(class_to_delete)
        db.session.commit()
        flash('Class deleted permanently.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting class: {e}', 'danger')
    return redirect(url_for('teacher.classes'))

@teacher_bp.route('/students', methods=['GET'])
@login_required
@teacher_required
def students():
    class_id = request.args.get('class_id', type=int)
    search = request.args.get('search', '').strip()
    # Advanced filters
    level = request.args.get('level', type=int)
    gold = request.args.get('gold', type=int)
    xp = request.args.get('xp', type=int)
    health = request.args.get('health', type=int)
    power = request.args.get('power', type=int)
    clan_id = request.args.get('clan_id', type=int)
    character_class = request.args.get('character_class', '').strip()
    # Sorting
    sort = request.args.get('sort', 'username')
    direction = request.args.get('direction', 'asc')

    classes = Classroom.query.filter_by(teacher_id=current_user.id, is_active=True).all()
    selected_class = None
    students = []
    clans = []
    character_classes = []
    if class_id:
        selected_class = Classroom.query.filter_by(id=class_id, teacher_id=current_user.id).first()
        if selected_class:
            students_query = db.session.query(User, Student, Character, Clan)
            students_query = students_query.join(Student, Student.user_id == User.id)
            students_query = students_query.outerjoin(Character, (Character.student_id == User.id) & (Character.is_active == True))
            students_query = students_query.outerjoin(Clan, Student.clan_id == Clan.id)
            students_query = students_query.filter(Student.class_id == class_id)
            if search:
                students_query = students_query.filter(
                    (User.username.ilike(f'%{search}%')) |
                    (User.first_name.ilike(f'%{search}%')) |
                    (User.last_name.ilike(f'%{search}%')) |
                    (User.email.ilike(f'%{search}%'))
                )
            if level is not None:
                students_query = students_query.filter(Student.level == level)
            if gold is not None:
                students_query = students_query.filter(Student.gold == gold)
            if xp is not None:
                students_query = students_query.filter(Student.xp == xp)
            if health is not None:
                students_query = students_query.filter(Student.health == health)
            if power is not None:
                students_query = students_query.filter(Student.power == power)
            if clan_id:
                students_query = students_query.filter(Student.clan_id == clan_id)
            if character_class:
                students_query = students_query.filter(Character.name.ilike(f'%{character_class}%'))
            # Sorting logic
            sort_map = {
                'username': User.username,
                'email': User.email,
                'level': Student.level,
                'gold': Student.gold,
                'xp': Student.xp,
                'health': Student.health,
                'power': Student.power,
                'character_class': Character.name,
                'clan': Clan.name,
            }
            sort_col = sort_map.get(sort, User.username)
            if direction == 'desc':
                sort_col = sort_col.desc()
            else:
                sort_col = sort_col.asc()
            students_query = students_query.order_by(sort_col)
            # Get all results as tuples (User, Student, Character, Clan)
            student_tuples = students_query.all()
            students = []
            for user, student, character, clan in student_tuples:
                students.append({
                    'user': user,
                    'student': student,
                    'character': character,
                    'clan': clan
                })
            clans = Clan.query.filter_by(class_id=class_id).all()
            character_classes = db.session.query(Character.name).filter(Character.student_id.in_([u.id for u,_,_,_ in student_tuples if u])).distinct().all()
            character_classes = [cc[0] for cc in character_classes if cc[0]]
        else:
            flash('Class not found or you do not have permission.', 'danger')
    return render_template(
        'teacher/students.html',
        classes=classes,
        selected_class=selected_class,
        students=students,
        search=search,
        level=level,
        gold=gold,
        xp=xp,
        health=health,
        power=power,
        clan_id=clan_id,
        character_class=character_class,
        clans=clans,
        character_classes=character_classes,
        sort=sort,
        direction=direction,
        active_page='students'
    )

@teacher_bp.route('/students/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@teacher_required
def edit_student(user_id):
    user = User.query.filter_by(id=user_id, role=UserRole.STUDENT).first_or_404()
    # Ensure the student is in a class owned by the current teacher
    class_ids = [c.id for c in user.classes if c.teacher_id == current_user.id]
    if not class_ids:
        abort(403)
    if request.method == 'POST':
        user.first_name = request.form.get('first_name', user.first_name)
        user.last_name = request.form.get('last_name', user.last_name)
        user.email = request.form.get('email', user.email)
        user.is_active = request.form.get('is_active', str(user.is_active)).lower() == 'true'
        db.session.commit()
        flash('Student information updated.', 'success')
        return redirect(url_for('teacher.students', class_id=class_ids[0]))
    # TODO: Render edit student form in template
    return render_template('teacher/edit_student.html', student=user)

@teacher_bp.route('/students/<int:user_id>/remove', methods=['POST'])
@login_required
@teacher_required
def remove_student(user_id):
    user = User.query.filter_by(id=user_id, role=UserRole.STUDENT).first_or_404()
    class_id = request.form.get('class_id', type=int)
    classroom = Classroom.query.filter_by(id=class_id, teacher_id=current_user.id).first()
    if not classroom or not user in classroom.students:
        abort(403)
    classroom.remove_student(user)
    db.session.commit()
    flash('Student removed from class.', 'success')
    return redirect(url_for('teacher.students', class_id=class_id))

@teacher_bp.route('/students/<int:user_id>/status', methods=['POST'])
@login_required
@teacher_required
def toggle_student_status(user_id):
    user = User.query.filter_by(id=user_id, role=UserRole.STUDENT).first_or_404()
    # Ensure the student is in a class owned by the current teacher
    class_ids = [c.id for c in user.classes if c.teacher_id == current_user.id]
    if not class_ids:
        abort(403)
    user.is_active = not user.is_active
    db.session.commit()
    flash(f'Student status set to {"Active" if user.is_active else "Inactive"}.', 'success')
    return redirect(url_for('teacher.students', class_id=class_ids[0]))

@teacher_bp.route('/clans')
@login_required
@teacher_required
def clans():
    return render_template('teacher/clans.html', active_page='clans')

@teacher_bp.route('/quests')
@login_required
@teacher_required
def quests():
    return render_template('teacher/quests.html', active_page='quests')

@teacher_bp.route('/shop')
@login_required
@teacher_required
def shop():
    return render_template('teacher/shop.html', active_page='shop')

@teacher_bp.route('/analytics')
@login_required
@teacher_required
def analytics():
    return render_template('teacher/analytics.html', active_page='analytics')

@teacher_bp.route('/backup')
@login_required
@teacher_required
def backup():
    return render_template('teacher/backup.html', active_page='backup')

@teacher_bp.route('/classes/<int:class_id>/edit', methods=['GET', 'POST'])
@login_required
@teacher_required
def edit_class(class_id):
    class_to_edit = Classroom.query.get_or_404(class_id)
    if class_to_edit.teacher_id != current_user.id:
        flash('You do not have permission to edit this class.', 'danger')
        return redirect(url_for('teacher.classes'))
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        max_students = request.form.get('max_students', 30)
        errors = []
        if not name:
            errors.append('Class name is required.')
        if errors:
            flash(' '.join(errors), 'danger')
            return render_template('teacher/edit_class.html', class_=class_to_edit)
        try:
            class_to_edit.name = name
            class_to_edit.description = description
            class_to_edit.max_students = max_students
            db.session.commit()
            flash('Class updated successfully!', 'success')
            return redirect(url_for('teacher.classes'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating class: {e}', 'danger')
            return render_template('teacher/edit_class.html', class_=class_to_edit)
    # GET: show form with current class details
    return render_template('teacher/edit_class.html', class_=class_to_edit)

@teacher_bp.route('/archived-classes')
@login_required
@teacher_required
def archived_classes():
    classes = Classroom.query.filter_by(teacher_id=current_user.id, is_active=False).all()
    return render_template('teacher/archived_classes.html', active_page='archived_classes', classes=classes) 