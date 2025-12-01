"""
Handles editing, removing, and toggling status of individual students.
"""

from .blueprint import teacher_bp, teacher_required
from flask_login import login_required, current_user
from flask import render_template, request, redirect, url_for, flash, abort
from app.models import db
from app.models.classroom import Classroom, class_students
from app.models.user import User, UserRole
from app.models.student import Student
from app.models.character import Character
from app.models.equipment import Equipment, Inventory
from app.models.audit import AuditLog, EventType
import logging

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

    # Log association table before

    if not classroom or not classroom.students.filter_by(id=user.id).first():
        flash('You do not have permission to remove this student from the selected class.', 'danger')
        return redirect(url_for('teacher.students', class_id=class_id))
    try:
        # Remove from classroom association
        classroom.remove_student(user)
        db.session.commit()
        # Log association table after

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
