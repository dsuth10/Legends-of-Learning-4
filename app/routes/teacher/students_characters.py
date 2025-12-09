"""
Handles character management for students (view, batch actions, inventory, equipment, stats).
"""

from .blueprint import teacher_bp, teacher_required
from flask_login import login_required, current_user
from flask import render_template, request, redirect, url_for, flash
from app.models import db
from app.models.classroom import Classroom
from app.models.user import User
from app.models.student import Student
from app.models.character import Character
from app.models.equipment import Equipment

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
