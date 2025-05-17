from .blueprint import teacher_bp, teacher_required
from flask_login import login_required, current_user
from flask import render_template, request, jsonify, flash, current_app
from app.models import db
from app.models.classroom import Classroom
from app.models.clan import Clan
from app.models.character import Character
from app.models.audit import AuditLog, EventType
from app.models.user import User
from app.models.clan_progress import ClanProgressHistory
from app.models.student import Student
import os
from flask_jwt_extended import jwt_required
from datetime import datetime, timedelta

@teacher_bp.route('/clans')
@login_required
@teacher_required
def clans():
    return render_template('teacher/clans.html', active_page='clans')

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
    if not character:
        return {"success": False, "message": "Character not found."}, 400
    try:
        # If character is already in a different clan, remove from previous clan first
        if character.clan_id and character.clan_id != clan_id:
            prev_clan = Clan.query.get(character.clan_id)
            if prev_clan:
                prev_clan.remove_member(character)
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
    students = (
        db.session.query(User, Student)
        .join(Student, Student.user_id == User.id)
        .filter(Student.class_id == class_id)
        .all()
    )
    result = []
    for user, student in students:
        characters = []
        for character in student.characters:
            characters.append({
                "id": character.id,
                "name": character.name,
                "clan_id": character.clan_id,
                "avatar_url": character.avatar_url,
            })
        result.append({
            "user_id": user.id,
            "username": user.username,
            "characters": characters
        })
    return {"success": True, "students": result}

@teacher_bp.route('/api/teacher/clan-icons', methods=['GET'])
@login_required
@teacher_required
def api_list_clan_icons():
    icon_dir = os.path.join(current_app.root_path, '..', 'static', 'images', 'clan_icons')
    icon_dir = os.path.normpath(icon_dir)
    try:
        icons = [f for f in os.listdir(icon_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.svg'))]
        # Return URLs for frontend use
        icon_urls = [f'/static/images/clan_icons/{icon}' for icon in icons]
        return {"success": True, "icons": icon_urls}
    except Exception as e:
        return {"success": False, "message": str(e)}, 500

@teacher_bp.route('/api/clans/<int:clan_id>/metrics', methods=['GET'], endpoint='api_get_clan_metrics')
@jwt_required
def api_get_clan_metrics(clan_id):
    metrics = calculate_clan_metrics(clan_id)
    if not metrics:
        return jsonify({'error': 'Clan not found'}), 404
    return jsonify(metrics)

@teacher_bp.route('/api/clans/<int:clan_id>/history', methods=['GET'], endpoint='api_get_clan_history')
@jwt_required
def api_get_clan_history(clan_id):
    days = request.args.get('days', 30, type=int)
    cutoff = datetime.utcnow() - timedelta(days=days)
    history = ClanProgressHistory.query.filter(
        ClanProgressHistory.clan_id == clan_id,
        ClanProgressHistory.timestamp >= cutoff
    ).order_by(ClanProgressHistory.timestamp).all()
    return jsonify([
        {
            'timestamp': h.timestamp.isoformat(),
            'avg_completion_rate': h.avg_completion_rate,
            'total_points': h.total_points,
            'active_members': h.active_members,
            'avg_daily_points': h.avg_daily_points,
            'quest_completion_rate': h.quest_completion_rate,
            'avg_member_level': h.avg_member_level,
            'percentile_rank': h.percentile_rank
        } for h in history
    ]) 