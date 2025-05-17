"""
Handles listing, searching, and filtering students for teachers.
"""

from .blueprint import teacher_bp, teacher_required
from flask_login import login_required, current_user
from flask import render_template, request, flash
from app.models import db
from app.models.classroom import Classroom
from app.models.user import User, UserRole
from app.models.student import Student
from app.models.character import Character
from app.models.clan import Clan

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
