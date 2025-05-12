from flask import Blueprint, render_template, abort, request, redirect, url_for, flash, session
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
import io
import json
import logging
from app.models.equipment import Equipment, Inventory, EquipmentType, EquipmentSlot
from app.models.audit import EventType
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

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

    # Key metrics for the current teacher
    total_classes = Classroom.query.filter_by(teacher_id=current_user.id, is_active=True).count()
    total_students = db.session.query(User).\
        join(class_students, class_students.c.user_id == User.id).\
        join(Classroom, Classroom.id == class_students.c.class_id).\
        filter(Classroom.teacher_id == current_user.id).\
        distinct().\
        count()
    active_students = db.session.query(User).\
        join(class_students, class_students.c.user_id == User.id).\
        join(Classroom, Classroom.id == class_students.c.class_id).\
        filter(Classroom.teacher_id == current_user.id, User.is_active == True).\
        distinct().\
        count()
    inactive_students = total_students - active_students

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

    # Chart data for class composition and activity
    class_labels = []
    class_counts = []
    active_counts = []
    inactive_counts = []
    for c in classes:
        class_labels.append(c.name)
        total = c.students.count()
        class_counts.append(total)
        active = sum(1 for s in c.students if s.is_active)
        inactive = total - active
        active_counts.append(active)
        inactive_counts.append(inactive)

    return render_template(
        'teacher/dashboard.html',
        title='Teacher Dashboard',
        teacher=current_user,
        stats=stats,
        recent_activities=recent_activities,
        active_page='dashboard',
        classes=classes,
        total_classes=total_classes,
        total_students=total_students,
        active_students=active_students,
        inactive_students=inactive_students,
        class_labels=json.dumps(class_labels),
        class_counts=json.dumps(class_counts),
        active_counts=json.dumps(active_counts),
        inactive_counts=json.dumps(inactive_counts)
    )

@teacher_bp.route('/add-student', methods=['GET', 'POST'])
@login_required
@teacher_required
def add_student():
    classes = Classroom.query.filter_by(teacher_id=current_user.id, is_active=True).all()
    # Check if this is a reassignment confirmation
    if request.method == 'POST' and request.form.get('reassign_confirm') == '1':
        user_id = request.form.get('user_id')
        class_id = request.form.get('class_id')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        user = User.query.filter_by(id=user_id, role=UserRole.STUDENT).first()
        student_profile = Student.query.filter_by(user_id=user_id, class_id=None, status='unassigned').first()
        classroom = Classroom.query.get(class_id)
        if user and student_profile and classroom:
            # Update name fields if provided
            if first_name:
                user.first_name = first_name
            if last_name:
                user.last_name = last_name
            student_profile.class_id = classroom.id
            student_profile.status = 'active'
            db.session.commit()
            flash('Unassigned student reassigned to class!', 'success')
            return redirect(url_for('teacher.add_student'))
        else:
            flash('Could not reassign student. Please try again.', 'danger')
            return render_template('teacher/add_student.html', classes=classes)

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

        existing_user = User.query.filter((User.username == username) | (User.email == email), User.role == UserRole.STUDENT).first()
        if existing_user:
            student_profile = Student.query.filter_by(user_id=existing_user.id).first()
            if student_profile and student_profile.class_id is None and student_profile.status == 'unassigned':
                # Prompt for reassignment
                return render_template(
                    'teacher/add_student.html',
                    classes=classes,
                    reassignable_student={
                        'user_id': existing_user.id,
                        'username': existing_user.username,
                        'email': existing_user.email,
                        'first_name': first_name or existing_user.first_name,
                        'last_name': last_name or existing_user.last_name,
                        'class_id': class_id
                    }
                )
            else:
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
    preview_data = None
    preview_errors = []
    required_fields = {'username', 'email', 'password'}
    if request.method == 'POST':
        # Step 1: Handle mapping form submit
        if request.form.get('mapping_submit') == '1':
            mapping = {f: request.form.get(f) for f in required_fields}
            file_contents = request.form.get('file_contents')
            class_id = request.form.get('class_id')
            if not file_contents or not class_id:
                flash('Missing file or class selection.', 'danger')
                return render_template('teacher/import_students.html', classes=classes)
            reader = csv.DictReader(io.StringIO(file_contents))
            preview_data = []
            for i, row in enumerate(reader, start=2):
                username = row.get(mapping['username'], '').strip()
                email = row.get(mapping['email'], '').strip()
                password = row.get(mapping['password'], '').strip()
                first_name = row.get('first_name', '').strip() if 'first_name' in row else ''
                last_name = row.get('last_name', '').strip() if 'last_name' in row else ''
                error = None
                reassignable = False
                existing_user = User.query.filter((User.username == username) | (User.email == email), User.role == UserRole.STUDENT).first()
                if not username or not email or not password:
                    error = 'Missing required fields.'
                elif existing_user:
                    student_profile = Student.query.filter_by(user_id=existing_user.id).first()
                    if student_profile and student_profile.class_id is None and student_profile.status == 'unassigned':
                        reassignable = True
                        error = None
                    else:
                        error = 'Username or email already exists.'
                preview_data.append({
                    'username': username,
                    'email': email,
                    'password': password,
                    'first_name': first_name,
                    'last_name': last_name,
                    'error': error,
                    'reassignable': reassignable,
                    'user_id': existing_user.id if reassignable else None
                })
            session['import_preview_data'] = preview_data
            session['import_class_id'] = class_id
            return render_template('teacher/import_students.html', classes=classes, preview_data=preview_data, class_id=class_id)
        # Step 2: Confirmation step (as before)
        if request.form.get('confirm_import') == '1':
            preview_data = session.get('import_preview_data')
            class_id = session.get('import_class_id')
            if not preview_data or not class_id:
                flash('No preview data found. Please re-upload your CSV.', 'danger')
                return render_template('teacher/import_students.html', classes=classes)
            classroom = Classroom.query.get(class_id)
            if not classroom:
                flash('Class not found.', 'danger')
                return render_template('teacher/import_students.html', classes=classes)
            created = 0
            reassigned = 0
            failed = 0
            errors = []
            for i, row in enumerate(preview_data, start=2):
                if row.get('error'):
                    failed += 1
                    errors.append(f'Row {i}: {row["error"]}')
                    continue
                if row.get('reassignable') and row.get('user_id'):
                    # Reassign unassigned student
                    user_id = row['user_id']
                    student_profile = Student.query.filter_by(user_id=user_id, class_id=None, status='unassigned').first()
                    user = User.query.filter_by(id=user_id, role=UserRole.STUDENT).first()
                    if student_profile and user:
                        student_profile.class_id = classroom.id
                        student_profile.status = 'active'
                        # Optionally update name fields
                        if row.get('first_name'):
                            user.first_name = row['first_name']
                        if row.get('last_name'):
                            user.last_name = row['last_name']
                        db.session.commit()
                        reassigned += 1
                    else:
                        failed += 1
                        errors.append(f'Row {i}: Could not reassign student.')
                    continue
                # Normal creation
                username = row['username']
                email = row['email']
                password = row['password']
                first_name = row.get('first_name', '')
                last_name = row.get('last_name', '')
                existing_user = User.query.filter((User.username == username) | (User.email == email), User.role == UserRole.STUDENT).first()
                if existing_user:
                    failed += 1
                    errors.append(f'Row {i}: Username or email already exists.')
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
                student_profile = Student(user_id=new_user.id, class_id=classroom.id)
                db.session.add(student_profile)
                db.session.commit()
                created += 1
            results = {'created': created, 'reassigned': reassigned, 'failed': failed}
            if created or reassigned:
                flash(f'Successfully created {created} students, reassigned {reassigned} unassigned students.', 'success')
            if failed:
                flash(f'Failed to create or reassign {failed} students. See errors below.', 'danger')
            session.pop('import_preview_data', None)
            session.pop('import_class_id', None)
            return render_template('teacher/import_students.html', classes=classes, results=results, errors=errors)
        # Step 3: Initial upload step
        file = request.files.get('csv_file')
        class_id = request.form.get('class_id')
        if not file or not class_id:
            flash('CSV file and class selection are required.', 'danger')
            return render_template('teacher/import_students.html', classes=classes)
        try:
            stream = TextIOWrapper(file.stream, encoding='utf-8')
            reader = csv.DictReader(stream)
            csv_columns = reader.fieldnames
            if not csv_columns:
                flash('CSV file is empty or invalid.', 'danger')
                return render_template('teacher/import_students.html', classes=classes)
            if required_fields.issubset(csv_columns):
                preview_data = []
                for i, row in enumerate(reader, start=2):
                    username = row.get('username', '').strip()
                    email = row.get('email', '').strip()
                    password = row.get('password', '').strip()
                    first_name = row.get('first_name', '').strip()
                    last_name = row.get('last_name', '').strip()
                    error = None
                    reassignable = False
                    existing_user = User.query.filter((User.username == username) | (User.email == email), User.role == UserRole.STUDENT).first()
                    if not username or not email or not password:
                        error = 'Missing required fields.'
                    elif existing_user:
                        student_profile = Student.query.filter_by(user_id=existing_user.id).first()
                        if student_profile and student_profile.class_id is None and student_profile.status == 'unassigned':
                            reassignable = True
                            error = None
                        else:
                            error = 'Username or email already exists.'
                    preview_data.append({
                        'username': username,
                        'email': email,
                        'password': password,
                        'first_name': first_name,
                        'last_name': last_name,
                        'error': error,
                        'reassignable': reassignable,
                        'user_id': existing_user.id if reassignable else None
                    })
                session['import_preview_data'] = preview_data
                session['import_class_id'] = class_id
                return render_template('teacher/import_students.html', classes=classes, preview_data=preview_data, class_id=class_id)
            else:
                file.stream.seek(0)
                file_contents = file.read().decode('utf-8')
                return render_template(
                    'teacher/import_students.html',
                    classes=classes,
                    mapping_needed=True,
                    csv_columns=csv_columns,
                    required_fields=required_fields,
                    file_contents=file_contents,
                    class_id=class_id
                )
        except Exception as e:
            flash(f'Error processing CSV: {e}', 'danger')
            return render_template('teacher/import_students.html', classes=classes)
    # GET request
    return render_template('teacher/import_students.html', classes=classes)

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
            students_query = students_query.outerjoin(Character, (Character.student_id == Student.id) & (Character.is_active == True))
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
                students_query = students_query.filter(Character.character_class.ilike(f'%{character_class}%'))
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
    # Fetch character and inventory
    character = None
    equipped_items = []
    unequipped_items = []
    character = Character.query.filter_by(student_id=user.id, is_active=True).first()
    if character:
        equipped_items = [item for item in character.inventory_items if item.is_equipped]
        unequipped_items = [item for item in character.inventory_items if not item.is_equipped]
    if request.method == 'POST':
        user.first_name = request.form.get('first_name', user.first_name)
        user.last_name = request.form.get('last_name', user.last_name)
        user.email = request.form.get('email', user.email)
        user.is_active = request.form.get('is_active', str(user.is_active)).lower() == 'true'
        db.session.commit()
        flash('Student information updated.', 'success')
        return redirect(url_for('teacher.students', class_id=class_ids[0]))
    return render_template('teacher/edit_student.html', student=user, character=character, equipped_items=equipped_items, unequipped_items=unequipped_items)

@teacher_bp.route('/students/<int:user_id>/remove', methods=['POST'])
@login_required
@teacher_required
def remove_student(user_id):
    user = User.query.filter_by(id=user_id, role=UserRole.STUDENT).first_or_404()
    class_id = request.form.get('class_id', type=int)
    if not class_id:
        flash('Class ID missing. Please try again from the class view.', 'danger')
        return redirect(url_for('teacher.students'))
    classroom = Classroom.query.filter_by(id=class_id, teacher_id=current_user.id).first()
    # Debug: log students before removal
    logging.warning(f"[DEBUG] Before removal: class {class_id} students: {[u.id for u in classroom.students.all()]}")
    logging.warning(f"[DEBUG] Student profile before: {Student.query.filter_by(user_id=user.id, class_id=class_id).first()}")
    # Log association table before
    assoc_before = db.session.execute(class_students.select().where(class_students.c.class_id == class_id)).fetchall()
    logging.warning(f"[DEBUG] Association table before: {assoc_before}")
    if not classroom or not classroom.students.filter_by(id=user.id).first():
        flash('You do not have permission to remove this student from the selected class.', 'danger')
        return redirect(url_for('teacher.students', class_id=class_id))
    try:
        # Remove from classroom association
        classroom.remove_student(user)
        db.session.commit()
        # Log association table after
        assoc_after = db.session.execute(class_students.select().where(class_students.c.class_id == class_id)).fetchall()
        logging.warning(f"[DEBUG] Association table after: {assoc_after}")
        # Set student profile to unassigned
        student_profile = Student.query.filter_by(user_id=user.id, class_id=class_id).first()
        if student_profile:
            student_profile.class_id = None
            student_profile.status = 'unassigned'
            db.session.commit()
            flash('Student removed from class and marked as unassigned.', 'success')
        else:
            db.session.commit()
            flash('Student removed from class.', 'warning')
        # Debug: log students after removal
        classroom = Classroom.query.filter_by(id=class_id, teacher_id=current_user.id).first()
        logging.warning(f"[DEBUG] After removal: class {class_id} students: {[u.id for u in classroom.students.all()]}")
        student_profile = Student.query.filter_by(user_id=user.id).first()
        logging.warning(f"[DEBUG] Student profile after: {student_profile}")
    except Exception as e:
        logging.error(f"[ERROR] Exception during student removal: {e}")
        flash(f"Error removing student: {e}", 'danger')
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
    classes = Classroom.query.filter_by(teacher_id=current_user.id, is_active=True).all()
    class_id = request.args.get('class_id', type=int)
    selected_class = None
    class_labels = []
    class_counts = []
    active_counts = []
    inactive_counts = []
    if class_id:
        selected_class = Classroom.query.filter_by(id=class_id, teacher_id=current_user.id).first()
        if selected_class:
            class_labels = [selected_class.name]
            total = selected_class.students.count()
            class_counts = [total]
            active = sum(1 for s in selected_class.students if s.is_active)
            inactive = total - active
            active_counts = [active]
            inactive_counts = [inactive]
    return render_template(
        'teacher/analytics.html',
        active_page='analytics',
        classes=classes,
        selected_class=selected_class,
        class_labels=json.dumps(class_labels),
        class_counts=json.dumps(class_counts),
        active_counts=json.dumps(active_counts),
        inactive_counts=json.dumps(inactive_counts)
    )

@teacher_bp.route('/analytics/data')
@login_required
@teacher_required
def analytics_data():
    class_id = request.args.get('class_id', type=int)
    if not class_id:
        return {'error': 'Missing class_id'}, 400
    selected_class = Classroom.query.filter_by(id=class_id, teacher_id=current_user.id).first()
    if not selected_class:
        return {'error': 'Class not found or not authorized'}, 404
    class_labels = [selected_class.name]
    total = selected_class.students.count()
    class_counts = [total]
    active = sum(1 for s in selected_class.students if s.is_active)
    inactive = total - active
    active_counts = [active]
    inactive_counts = [inactive]
    return {
        'class_labels': class_labels,
        'class_counts': class_counts,
        'active_counts': active_counts,
        'inactive_counts': inactive_counts
    }

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

@teacher_bp.route('/unassigned-students')
@login_required
@teacher_required
def unassigned_students():
    # Query all unassigned students for the current teacher
    unassigned = (
        db.session.query(User, Student)
        .join(Student, Student.user_id == User.id)
        .filter(
            Student.class_id == None,
            Student.status == 'unassigned',
            User.is_active == True
        )
        .all()
    )
    # Fetch all classes for reassignment dropdown
    classes = Classroom.query.filter_by(teacher_id=current_user.id, is_active=True).all()
    return render_template(
        'teacher/unassigned_students.html',
        students=unassigned,
        classes=classes,
        active_page='unassigned_students'
    )

@teacher_bp.route('/unassigned-students/<int:user_id>/reassign', methods=['POST'])
@login_required
@teacher_required
def reassign_unassigned_student(user_id):
    class_id = request.form.get('class_id', type=int)
    student_profile = Student.query.filter_by(user_id=user_id, class_id=None, status='unassigned').first_or_404()
    classroom = Classroom.query.filter_by(id=class_id, teacher_id=current_user.id).first_or_404()
    # Reassign student
    student_profile.class_id = class_id
    student_profile.status = 'active'
    db.session.commit()
    flash('Student reassigned to class.', 'success')
    return redirect(url_for('teacher.unassigned_students'))

@teacher_bp.route('/unassigned-students/<int:user_id>/delete', methods=['POST'])
@login_required
@teacher_required
def delete_unassigned_student(user_id):
    student_profile = Student.query.filter_by(user_id=user_id, class_id=None, status='unassigned').first_or_404()
    user = User.query.filter_by(id=user_id, role=UserRole.STUDENT).first_or_404()
    db.session.delete(student_profile)
    db.session.delete(user)
    db.session.commit()
    flash('Unassigned student permanently deleted.', 'success')
    return redirect(url_for('teacher.unassigned_students'))

# --- Teacher Character Stat and Equipment Modification Endpoints ---

# Helper: Check teacher owns the student

def teacher_owns_student(teacher_id, student_id):
    student = User.query.filter_by(id=student_id, role=UserRole.STUDENT).first()
    if not student:
        return False
    # Check if student is in any class owned by teacher
    return any(c.teacher_id == teacher_id for c in student.classes)

# PATCH /api/teacher/student/<student_id>/stats
@teacher_bp.route('/api/teacher/student/<int:student_id>/stats', methods=['PATCH'])
@login_required
@teacher_required
def update_student_stats(student_id):
    if not teacher_owns_student(current_user.id, student_id):
        return {"success": False, "message": "Unauthorized: Not your student."}, 403
    character = Character.query.filter_by(student_id=student_id).first()
    if not character:
        return {"success": False, "message": "Character not found."}, 404
    data = request.get_json() or {}
    allowed_stats = ["health", "max_health", "strength", "defense", "gold", "level", "experience"]
    changes = {}
    for stat in allowed_stats:
        if stat in data:
            old = getattr(character, stat)
            # Convert to int for numeric stats
            if stat in ["health", "max_health", "strength", "defense", "gold", "level", "experience"]:
                try:
                    new = int(data[stat])
                except (ValueError, TypeError):
                    return {"success": False, "message": f"{stat} must be an integer."}, 400
            else:
                new = data[stat]
            # Example validation: stat ranges
            if stat == "health" and not (0 <= new <= character.max_health):
                return {"success": False, "message": f"Health must be 0-{character.max_health}"}, 400
            if stat == "strength" and not (1 <= new <= 100):
                return {"success": False, "message": "Strength must be 1-100"}, 400
            if stat == "defense" and not (1 <= new <= 100):
                return {"success": False, "message": "Defense must be 1-100"}, 400
            if stat == "gold" and not (0 <= new <= 10000):
                return {"success": False, "message": "Gold must be 0-10000"}, 400
            setattr(character, stat, new)
            changes[stat] = {"old": old, "new": new}
    try:
        db.session.commit()
        # Audit log
        AuditLog.log_event(
            EventType.CHARACTER_UPDATE,
            event_data={"changes": changes, "by": current_user.id},
            user_id=current_user.id,
            character_id=character.id
        )
        return {"success": True, "message": "Character stats updated.", "character": character.id, "audit_log": changes}
    except SQLAlchemyError as e:
        db.session.rollback()
        return {"success": False, "message": str(e)}, 500

# POST /api/teacher/student/<student_id>/inventory/add
@teacher_bp.route('/api/teacher/student/<int:student_id>/inventory/add', methods=['POST'])
@login_required
@teacher_required
def add_item_to_inventory(student_id):
    if not teacher_owns_student(current_user.id, student_id):
        return {"success": False, "message": "Unauthorized: Not your student."}, 403
    character = Character.query.filter_by(student_id=student_id).first()
    if not character:
        return {"success": False, "message": "Character not found."}, 404
    data = request.get_json() or {}
    equipment_id = data.get("equipment_id")
    if not equipment_id:
        return {"success": False, "message": "Missing equipment_id."}, 400
    equipment = Equipment.query.get(equipment_id)
    if not equipment:
        return {"success": False, "message": "Equipment not found."}, 404
    # Check inventory capacity (example: max 20 items)
    if character.inventory_items.count() >= 20:
        return {"success": False, "message": "Inventory full."}, 400
    inv = Inventory(character_id=character.id, equipment_id=equipment.id)
    db.session.add(inv)
    try:
        db.session.commit()
        AuditLog.log_event(
            EventType.EQUIPMENT_CHANGE,
            event_data={"action": "add", "equipment_id": equipment.id, "by": current_user.id},
            user_id=current_user.id,
            character_id=character.id
        )
        return {"success": True, "message": "Item added.", "inventory_id": inv.id}
    except SQLAlchemyError as e:
        db.session.rollback()
        return {"success": False, "message": str(e)}, 500

# POST /api/teacher/student/<student_id>/inventory/remove
@teacher_bp.route('/api/teacher/student/<int:student_id>/inventory/remove', methods=['POST'])
@login_required
@teacher_required
def remove_item_from_inventory(student_id):
    if not teacher_owns_student(current_user.id, student_id):
        return {"success": False, "message": "Unauthorized: Not your student."}, 403
    character = Character.query.filter_by(student_id=student_id).first()
    if not character:
        return {"success": False, "message": "Character not found."}, 404
    data = request.get_json() or {}
    inventory_id = data.get("inventory_id")
    inv = Inventory.query.filter_by(id=inventory_id, character_id=character.id).first()
    if not inv:
        return {"success": False, "message": "Inventory item not found."}, 404
    db.session.delete(inv)
    try:
        db.session.commit()
        AuditLog.log_event(
            EventType.EQUIPMENT_CHANGE,
            event_data={"action": "remove", "inventory_id": inventory_id, "by": current_user.id},
            user_id=current_user.id,
            character_id=character.id
        )
        return {"success": True, "message": "Item removed."}
    except SQLAlchemyError as e:
        db.session.rollback()
        return {"success": False, "message": str(e)}, 500

# PATCH /api/teacher/student/<student_id>/equipment/equip
@teacher_bp.route('/api/teacher/student/<int:student_id>/equipment/equip', methods=['PATCH'])
@login_required
@teacher_required
def equip_item(student_id):
    if not teacher_owns_student(current_user.id, student_id):
        return {"success": False, "message": "Unauthorized: Not your student."}, 403
    character = Character.query.filter_by(student_id=student_id).first()
    if not character:
        return {"success": False, "message": "Character not found."}, 404
    data = request.get_json() or {}
    inventory_id = data.get("inventory_id")
    inv = Inventory.query.filter_by(id=inventory_id, character_id=character.id).first()
    if not inv:
        return {"success": False, "message": "Inventory item not found."}, 404
    # Validate equipment slot
    slot = inv.equipment.slot
    # Unequip any item in the same slot
    for item in character.inventory_items:
        if item.is_equipped and item.equipment.slot == slot:
            item.is_equipped = False
    inv.is_equipped = True
    try:
        db.session.commit()
        AuditLog.log_event(
            EventType.EQUIPMENT_CHANGE,
            event_data={"action": "equip", "inventory_id": inventory_id, "by": current_user.id},
            user_id=current_user.id,
            character_id=character.id
        )
        return {"success": True, "message": "Item equipped."}
    except SQLAlchemyError as e:
        db.session.rollback()
        return {"success": False, "message": str(e)}, 500

# PATCH /api/teacher/student/<student_id>/equipment/unequip
@teacher_bp.route('/api/teacher/student/<int:student_id>/equipment/unequip', methods=['PATCH'])
@login_required
@teacher_required
def unequip_item(student_id):
    if not teacher_owns_student(current_user.id, student_id):
        return {"success": False, "message": "Unauthorized: Not your student."}, 403
    character = Character.query.filter_by(student_id=student_id).first()
    if not character:
        return {"success": False, "message": "Character not found."}, 404
    data = request.get_json() or {}
    inventory_id = data.get("inventory_id")
    # Debug logging
    print(f"[DEBUG] Unequip request: student_id={student_id}, inventory_id={inventory_id}")
    print(f"[DEBUG] Character ID: {character.id if character else 'None'}")
    inv = Inventory.query.filter_by(id=inventory_id, character_id=character.id).first()
    print(f"[DEBUG] Inventory found: {inv}")
    if not inv or not inv.is_equipped:
        print(f"[DEBUG] Inventory not found or not equipped. inv={inv}")
        return {"success": False, "message": "Item not equipped."}, 404
    inv.is_equipped = False
    try:
        db.session.commit()
        AuditLog.log_event(
            EventType.EQUIPMENT_CHANGE,
            event_data={"action": "unequip", "inventory_id": inventory_id, "by": current_user.id},
            user_id=current_user.id,
            character_id=character.id
        )
        print(f"[DEBUG] Item unequipped successfully. inv={inv}")
        return {"success": True, "message": "Item unequipped."}
    except SQLAlchemyError as e:
        db.session.rollback()
        print(f"[DEBUG] Exception during unequip: {e}")
        return {"success": False, "message": str(e)}, 500

@teacher_bp.route('/students/<int:class_id>/characters', methods=['GET'])
@login_required
@teacher_required
def student_characters(class_id):
    # Fetch all classes for sidebar/class selector
    classes = Classroom.query.filter_by(teacher_id=current_user.id, is_active=True).all()
    selected_class = Classroom.query.filter_by(id=class_id, teacher_id=current_user.id).first()
    if not selected_class:
        flash('Class not found or you do not have permission.', 'danger')
        return redirect(url_for('teacher.students'))

    # Fetch students and their characters for this class
    students_query = db.session.query(User, Student, Character).\
        join(Student, Student.user_id == User.id).\
        outerjoin(Character, (Character.student_id == Student.id) & (Character.is_active == True)).\
        filter(Student.class_id == class_id)
    student_tuples = students_query.all()
    students = []
    for user, student, character in student_tuples:
        equipped_items = []
        if character:
            equipped_items = [item for item in getattr(character, 'inventory_items', []) if getattr(item, 'is_equipped', False)]
        students.append({
            'user': user,
            'student': student,
            'character': character,
            'equipped_items': equipped_items
        })

    # Fetch all equipment for dropdown
    all_equipment = Equipment.query.order_by(Equipment.name.asc()).all()

    return render_template(
        'teacher/student_characters.html',
        classes=classes,
        selected_class=selected_class,
        students=students,
        all_equipment=all_equipment,
        active_page='student_characters'
    )

@teacher_bp.route('/api/teacher/characters/batch-action', methods=['POST'])
@login_required
@teacher_required
def batch_character_action():
    import logging
    data = request.get_json() or {}
    action = data.get('action')
    logging.warning(f"[DEBUG] batch_character_action called. Data: {data}")
    character_ids = data.get('character_ids', [])
    # Optional: item_id, status_value, etc.
    if not action or not character_ids or not isinstance(character_ids, list):
        return {"success": False, "message": "Missing or invalid action/character_ids."}, 400
    # Fetch all characters and check permissions
    characters = Character.query.filter(Character.id.in_(character_ids)).all()
    if len(characters) != len(character_ids):
        return {"success": False, "message": "One or more characters not found."}, 404
    # Check teacher owns all students
    for c in characters:
        student = Student.query.get(c.student_id)
        if not student or student.classroom.teacher_id != current_user.id:
            return {"success": False, "message": f"Unauthorized for character {c.id}."}, 403
    results = {}
    try:
        if action == 'reset-health':
            for c in characters:
                old = c.health
                c.health = c.max_health
                results[c.id] = {"old_health": old, "new_health": c.max_health, "success": True}
            db.session.commit()
            # Log batch event
            AuditLog.log_event(
                EventType.CHARACTER_UPDATE,
                event_data={"action": "batch-reset-health", "character_ids": character_ids, "by": current_user.id},
                user_id=current_user.id
            )
            return {"success": True, "message": "Health reset for selected characters.", "results": results}
        elif action == 'grant-item':
            item_id = data.get('item_id')
            if not item_id:
                return {"success": False, "message": "Missing item_id."}, 400
            from app.models.equipment import Equipment, Inventory
            equipment = Equipment.query.get(item_id)
            if not equipment:
                return {"success": False, "message": "Equipment not found."}, 404
            for c in characters:
                # Check inventory capacity (max 20 items)
                if c.inventory_items.count() >= 20:
                    results[c.id] = {"success": False, "reason": "Inventory full"}
                    continue
                inv = Inventory(character_id=c.id, equipment_id=equipment.id)
                db.session.add(inv)
                results[c.id] = {"success": True, "inventory_id": inv.id}
            try:
                db.session.commit()
                AuditLog.log_event(
                    EventType.EQUIPMENT_CHANGE,
                    event_data={
                        "action": "batch-grant-item",
                        "item_id": item_id,
                        "character_ids": character_ids,
                        "by": current_user.id,
                        "results": results
                    },
                    user_id=current_user.id
                )
                return {"success": True, "message": "Item granted to selected characters.", "results": results}
            except SQLAlchemyError as e:
                db.session.rollback()
                return {"success": False, "message": str(e)}, 500
        elif action == 'set-status':
            status_value = data.get('status_value')
            if status_value not in [True, False]:
                return {"success": False, "message": "Missing or invalid status_value."}, 400
            for c in characters:
                old = c.is_active
                c.is_active = status_value
                results[c.id] = {"old_status": old, "new_status": status_value, "success": True}
            try:
                db.session.commit()
                AuditLog.log_event(
                    EventType.CHARACTER_UPDATE,
                    event_data={
                        "action": "batch-set-status",
                        "character_ids": character_ids,
                        "status_value": status_value,
                        "by": current_user.id,
                        "results": results
                    },
                    user_id=current_user.id
                )
                return {"success": True, "message": "Status updated for selected characters.", "results": results}
            except SQLAlchemyError as e:
                db.session.rollback()
                return {"success": False, "message": str(e)}, 500
        elif action == 'reset-character':
            for c in characters:
                try:
                    db.session.delete(c)
                    results[c.id] = {"success": True}
                except Exception as e:
                    results[c.id] = {"success": False, "error": str(e)}
            try:
                db.session.commit()
                AuditLog.log_event(
                    EventType.CHARACTER_UPDATE,
                    event_data={
                        "action": "batch-reset-character",
                        "character_ids": character_ids,
                        "by": current_user.id,
                        "results": results
                    },
                    user_id=current_user.id
                )
                return {"success": True, "message": "Characters reset for selected students.", "results": results}
            except SQLAlchemyError as e:
                db.session.rollback()
                return {"success": False, "message": str(e)}, 500
        else:
            return {"success": False, "message": "Unknown batch action."}, 400
    except SQLAlchemyError as e:
        db.session.rollback()
        return {"success": False, "message": str(e)}, 500

# --- Clan Management API Endpoints ---

@teacher_bp.route('/api/teacher/clans', methods=['GET'])
@login_required
@teacher_required
def api_list_clans():
    class_id = request.args.get('class_id', type=int)
    if not class_id:
        return {"success": False, "message": "Missing class_id."}, 400
    classroom = Classroom.query.filter_by(id=class_id, teacher_id=current_user.id).first()
    if not classroom:
        return {"success": False, "message": "Class not found or unauthorized."}, 404
    clans = Clan.query.filter_by(class_id=class_id).all()
    result = []
    for clan in clans:
        members = [
            {
                "id": c.id,
                "name": c.name,
                "student_id": c.student_id,
                "user_id": c.student.user_id if c.student else None,
                "avatar_url": c.avatar_url,
                "level": c.level,
            }
            for c in clan.members
        ]
        result.append({
            "id": clan.id,
            "name": clan.name,
            "description": clan.description,
            "emblem": clan.emblem,
            "level": clan.level,
            "experience": clan.experience,
            "is_active": clan.is_active,
            "created_at": clan.created_at,
            "updated_at": clan.updated_at,
            "members": members,
        })
    return {"success": True, "clans": result}

@teacher_bp.route('/api/teacher/clans', methods=['POST'])
@login_required
@teacher_required
def api_create_clan():
    data = request.get_json() or {}
    class_id = data.get('class_id')
    name = data.get('name')
    description = data.get('description')
    emblem = data.get('emblem')
    if not class_id or not name:
        return {"success": False, "message": "Missing class_id or name."}, 400
    classroom = Classroom.query.filter_by(id=class_id, teacher_id=current_user.id).first()
    if not classroom:
        return {"success": False, "message": "Class not found or unauthorized."}, 404
    clan = Clan(name=name, class_id=class_id, description=description, emblem=emblem)
    db.session.add(clan)
    try:
        db.session.commit()
        return {"success": True, "clan_id": clan.id}
    except IntegrityError:
        db.session.rollback()
        return {"success": False, "message": "Clan name must be unique within the class."}, 400
    except Exception as e:
        db.session.rollback()
        return {"success": False, "message": str(e)}, 500

@teacher_bp.route('/api/teacher/clans/<int:clan_id>', methods=['PUT'])
@login_required
@teacher_required
def api_edit_clan(clan_id):
    data = request.get_json() or {}
    clan = Clan.query.get(clan_id)
    if not clan or clan.class_.teacher_id != current_user.id:
        return {"success": False, "message": "Clan not found or unauthorized."}, 404
    name = data.get('name')
    description = data.get('description')
    emblem = data.get('emblem')
    if name:
        clan.name = name
    if description is not None:
        clan.description = description
    if emblem is not None:
        clan.emblem = emblem
    try:
        db.session.commit()
        return {"success": True}
    except IntegrityError:
        db.session.rollback()
        return {"success": False, "message": "Clan name must be unique within the class."}, 400
    except Exception as e:
        db.session.rollback()
        return {"success": False, "message": str(e)}, 500

@teacher_bp.route('/api/teacher/clans/<int:clan_id>', methods=['DELETE'])
@login_required
@teacher_required
def api_delete_clan(clan_id):
    clan = Clan.query.get(clan_id)
    if not clan or clan.class_.teacher_id != current_user.id:
        return {"success": False, "message": "Clan not found or unauthorized."}, 404
    db.session.delete(clan)
    try:
        db.session.commit()
        return {"success": True}
    except Exception as e:
        db.session.rollback()
        return {"success": False, "message": str(e)}, 500

@teacher_bp.route('/api/teacher/clans/<int:clan_id>/add_member', methods=['POST'])
@login_required
@teacher_required
def api_add_clan_member(clan_id):
    data = request.get_json() or {}
    character_id = data.get('character_id')
    clan = Clan.query.get(clan_id)
    if not clan or clan.class_.teacher_id != current_user.id:
        return {"success": False, "message": "Clan not found or unauthorized."}, 404
    character = Character.query.get(character_id)
    if not character or character.clan_id == clan_id:
        return {"success": False, "message": "Character not found or already in this clan."}, 400
    try:
        clan.add_member(character)
        return {"success": True}
    except Exception as e:
        db.session.rollback()
        return {"success": False, "message": str(e)}, 400

@teacher_bp.route('/api/teacher/clans/<int:clan_id>/remove_member', methods=['POST'])
@login_required
@teacher_required
def api_remove_clan_member(clan_id):
    data = request.get_json() or {}
    character_id = data.get('character_id')
    clan = Clan.query.get(clan_id)
    if not clan or clan.class_.teacher_id != current_user.id:
        return {"success": False, "message": "Clan not found or unauthorized."}, 404
    character = Character.query.get(character_id)
    if not character or character.clan_id != clan_id:
        return {"success": False, "message": "Character not found or not in this clan."}, 400
    try:
        clan.remove_member(character)
        return {"success": True}
    except Exception as e:
        db.session.rollback()
        return {"success": False, "message": str(e)}, 400

@teacher_bp.route('/api/teacher/class/<int:class_id>/students', methods=['GET'])
@login_required
@teacher_required
def api_list_class_students(class_id):
    classroom = Classroom.query.filter_by(id=class_id, teacher_id=current_user.id).first()
    if not classroom:
        return {"success": False, "message": "Class not found or unauthorized."}, 404
    # Get all students in the class
    students = Student.query.filter_by(class_id=class_id).all()
    result = []
    for student in students:
        user = User.query.get(student.user_id)
        # Get all characters for this student
        characters = Character.query.filter_by(student_id=student.id).all()
        char_list = [
            {
                "id": c.id,
                "name": c.name,
                "level": c.level,
                "clan_id": c.clan_id,
                "avatar_url": c.avatar_url,
            }
            for c in characters
        ]
        result.append({
            "student_id": student.id,
            "user_id": student.user_id,
            "username": user.username if user else None,
            "first_name": user.first_name if user else None,
            "last_name": user.last_name if user else None,
            "status": student.status,
            "characters": char_list,
        })
    return {"success": True, "students": result}

@teacher_bp.route('/api/teacher/classes', methods=['GET'])
@login_required
@teacher_required
def api_list_teacher_classes():
    import logging
    logging.warning(f"[DEBUG] /api/teacher/classes called by user: {current_user} (id={getattr(current_user, 'id', None)})")
    classes = Classroom.query.filter_by(teacher_id=current_user.id, is_active=True).all()
    logging.warning(f"[DEBUG] Classes found: {[{'id': c.id, 'name': c.name} for c in classes]}")
    return {
        "success": True,
        "classes": [
            {"id": c.id, "name": c.name}
            for c in classes
        ]
    } 