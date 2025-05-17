"""
Handles unassigned students: list, reassign, delete.
"""

from .blueprint import teacher_bp, teacher_required
from flask_login import login_required, current_user
from flask import render_template, request, redirect, url_for, flash
from app.models import db
from app.models.classroom import Classroom
from app.models.user import User, UserRole
from app.models.student import Student

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
