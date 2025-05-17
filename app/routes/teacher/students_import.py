"""
Handles importing and exporting students (CSV upload, preview, confirm).
"""

from .blueprint import teacher_bp, teacher_required
from flask_login import login_required, current_user
from flask import render_template, request, redirect, url_for, flash, session
from app.models import db
from app.models.classroom import Classroom
from app.models.user import User, UserRole
from app.models.student import Student
from sqlalchemy.exc import IntegrityError
import csv, io
from io import TextIOWrapper

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
