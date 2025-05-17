from .blueprint import teacher_bp, teacher_required
from flask_login import login_required, current_user
from flask import render_template, request, redirect, url_for, flash, session
from app.models import db
from app.models.classroom import Classroom
from app.models.user import User, UserRole
from app.models.student import Student
import random, string
from flask import jsonify

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

@teacher_bp.route('/api/teacher/classes', methods=['GET'])
@login_required
@teacher_required
def api_teacher_classes():
    classes = Classroom.query.filter_by(teacher_id=current_user.id, is_active=True).all()
    return jsonify({
        "success": True,
        "classes": [c.to_dict() for c in classes]
    }) 