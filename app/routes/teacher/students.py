from .blueprint import teacher_bp, teacher_required
from flask_login import login_required, current_user
from flask import render_template, request, redirect, url_for, flash, session, jsonify
from app.models import db
from app.models.classroom import Classroom
from app.models.character import Character
from app.models.clan import Clan
from app.models.user import User, UserRole
from app.models.student import Student
from app.models.equipment import Equipment, Inventory
from app.models.audit import AuditLog, EventType
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
import csv, io, logging
from io import TextIOWrapper

# --- Student Management Routes ---
# (Paste all relevant route functions and helpers here from __init__.py)

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
            students_query = db.session.query(User, Student)
            students_query = students_query.join(Student, Student.user_id == User.id)
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
            # Sorting logic (basic, can be improved)
            sort_map = {
                'username': User.username,
                'email': User.email,
                'level': Student.level,
                'gold': Student.gold,
                'xp': Student.xp,
                'health': Student.health,
                'power': Student.power,
            }
            sort_col = sort_map.get(sort, User.username)
            if direction == 'desc':
                sort_col = sort_col.desc()
            else:
                sort_col = sort_col.asc()
            students_query = students_query.order_by(sort_col)
            student_tuples = students_query.all()
            students = []
            for user, student in student_tuples:
                main_character = Character.query.filter_by(student_id=student.id, is_active=True).first()
                clan = main_character.clan if main_character and main_character.clan else None
                # Use Student's clan if Character's clan is None
                effective_clan = clan or (student.clan if hasattr(student, 'clan') and student.clan else None)
                if character_class and (not main_character or main_character.character_class != character_class):
                    continue
                if clan_id and (not effective_clan or effective_clan.id != clan_id):
                    continue
                students.append({
                    'user': user,
                    'student': student,
                    'character': main_character,
                    'clan': effective_clan
                })
            clans = Clan.query.filter_by(class_id=class_id).all()
            # Character classes for filter dropdown
            character_classes = db.session.query(Character.character_class).filter(Character.student_id.in_([s.id for _,s in student_tuples])).distinct().all()
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
                try:
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
                except IntegrityError:
                    db.session.rollback()
                    failed += 1
                    errors.append(f'Row {i}: Username or email already exists (detected at DB level).')
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

# --- API Endpoints and Helpers ---

def teacher_owns_student(teacher_id, student_id):
    student = Student.query.filter_by(id=student_id).first()
    if not student:
        return False
    classroom = Classroom.query.filter_by(id=student.class_id, teacher_id=teacher_id).first()
    return classroom is not None

@teacher_bp.route('/api/teacher/student/<int:student_id>/stats', methods=['GET'])
@login_required
@teacher_required
def api_student_stats(student_id):
    if not teacher_owns_student(current_user.id, student_id):
        return jsonify({'error': 'Permission denied'}), 403
    student = Student.query.filter_by(id=student_id).first_or_404()
    character = Character.query.filter_by(student_id=student.id, is_active=True).first()
    stats = {
        'level': student.level,
        'xp': student.xp,
        'gold': student.gold,
        'health': student.health,
        'power': student.power,
        'character_class': character.character_class if character else None
    }
    return jsonify(stats)

@teacher_bp.route('/api/teacher/student/<int:student_id>/inventory', methods=['GET'])
@login_required
@teacher_required
def api_student_inventory(student_id):
    if not teacher_owns_student(current_user.id, student_id):
        return jsonify({'error': 'Permission denied'}), 403
    character = Character.query.filter_by(student_id=student_id, is_active=True).first()
    if not character:
        return jsonify({'error': 'No active character found'}), 404
    inventory = [
        {
            'item_id': item.id,
            'name': item.name,
            'is_equipped': item.is_equipped
        }
        for item in character.inventory_items
    ]
    return jsonify({'inventory': inventory})

@teacher_bp.route('/api/teacher/student/<int:student_id>/equipment', methods=['GET'])
@login_required
@teacher_required
def api_student_equipment(student_id):
    if not teacher_owns_student(current_user.id, student_id):
        return jsonify({'error': 'Permission denied'}), 403
    character = Character.query.filter_by(student_id=student_id, is_active=True).first()
    if not character:
        return jsonify({'error': 'No active character found'}), 404
    equipped = [
        {
            'item_id': item.id,
            'name': item.name
        }
        for item in character.inventory_items if item.is_equipped
    ]
    return jsonify({'equipped': equipped})

@teacher_bp.route('/api/teacher/students/batch-character-action', methods=['POST'])
@login_required
@teacher_required
def batch_character_action():
    data = request.get_json()
    action = data.get('action')
    student_ids = data.get('student_ids', [])
    if not action or not student_ids:
        return jsonify({'error': 'Missing action or student_ids'}), 400
    results = []
    for student_id in student_ids:
        if not teacher_owns_student(current_user.id, student_id):
            results.append({'student_id': student_id, 'status': 'forbidden'})
            continue
        character = Character.query.filter_by(student_id=student_id, is_active=True).first()
        if not character:
            results.append({'student_id': student_id, 'status': 'no_character'})
            continue
        # Example: reset health
        if action in ('reset-health', 'reset_health'):
            character.health = character.max_health
            db.session.commit()
            # Add audit log
            audit = AuditLog(
                character_id=character.id,
                event_type=EventType.CHARACTER_UPDATE.value,
                event_data={
                    'action': 'batch-reset-health'
                }
            )
            db.session.add(audit)
            db.session.commit()
            results.append({'student_id': student_id, 'status': 'reset'})
        elif action == 'grant-item':
            item_id = data.get('item_id')
            if not item_id:
                results.append({'student_id': student_id, 'status': 'missing_item_id'})
                continue
            equipment = Equipment.query.filter_by(id=item_id).first()
            if not equipment:
                results.append({'student_id': student_id, 'status': 'item_not_found'})
                continue
            # Check if already in inventory
            existing = Inventory.query.filter_by(character_id=character.id, equipment_id=equipment.id).first()
            if existing:
                results.append({'student_id': student_id, 'status': 'already_has_item'})
                continue
            # Add to inventory as unequipped
            new_inv = Inventory(character_id=character.id, equipment_id=equipment.id, is_equipped=False)
            db.session.add(new_inv)
            db.session.commit()
            # Add audit log
            audit = AuditLog(
                character_id=character.id,
                event_type=EventType.EQUIPMENT_CHANGE.value,
                event_data={
                    'action': 'batch-grant-item',
                    'item_id': equipment.id,
                    'item_name': equipment.name
                }
            )
            db.session.add(audit)
            db.session.commit()
            results.append({'student_id': student_id, 'status': 'item_granted'})
        else:
            results.append({'student_id': student_id, 'status': 'unknown_action'})
    return jsonify({'results': results}) 