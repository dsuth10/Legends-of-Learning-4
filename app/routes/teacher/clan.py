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
from app.models.achievement_badge import AchievementBadge

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
            "badges": [
                {"id": b.id, "name": b.name, "description": b.description, "icon": b.icon}
                for b in clan.badges
            ]
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
    banner = data.get('banner')
    theme_color = data.get('theme_color')
    if not class_id or not name:
        return {"success": False, "message": "Missing class_id or name."}, 400
    classroom = Classroom.query.filter_by(id=class_id, teacher_id=current_user.id).first()
    if not classroom:
        return {"success": False, "message": "Class not found or unauthorized."}, 404
    if emblem:
        existing = Clan.query.filter_by(class_id=class_id, emblem=emblem).first()
        if existing:
            return {"success": False, "message": "Icon already in use by another clan in this class."}, 400
    clan = Clan(name=name, class_id=class_id, description=description, emblem=emblem, banner=banner, theme_color=theme_color)
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
    banner = data.get('banner')
    theme_color = data.get('theme_color')
    if emblem:
        existing = Clan.query.filter(Clan.class_id == clan.class_id, Clan.emblem == emblem, Clan.id != clan_id).first()
        if existing:
            return {"success": False, "message": "Icon already in use by another clan in this class."}, 400
    if name:
        clan.name = name
    if description is not None:
        clan.description = description
    if emblem is not None:
        clan.emblem = emblem
    if banner is not None:
        clan.banner = banner
    if theme_color is not None:
        clan.theme_color = theme_color
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

@teacher_bp.route('/clans/dashboard')
@login_required
@teacher_required
def clan_dashboard():
    from app.models.classroom import Classroom
    from app.models.clan import Clan
    from app.models.clan_progress import ClanProgressHistory
    from app.models.audit import AuditLog
    from app.models.character import Character
    from datetime import datetime, timedelta
    from flask import request, render_template
    # Filters
    class_id = request.args.get('class_id', type=int)
    period = request.args.get('period', default='30d')  # e.g., '7d', '30d', 'all'
    now = datetime.utcnow()
    if period == '7d':
        since = now - timedelta(days=7)
    elif period == '30d':
        since = now - timedelta(days=30)
    else:
        since = None

    # Get all classes for filter dropdown
    classes = Classroom.query.filter_by(teacher_id=current_user.id, is_active=True).all()

    # Query clans for the teacher (optionally filter by class)
    clans_query = Clan.query.join(Classroom).filter(Classroom.teacher_id == current_user.id)
    if class_id:
        clans_query = clans_query.filter(Clan.class_id == class_id)
    clans = clans_query.all()

    # Aggregate data for each clan
    clan_data = []
    chart_labels = []
    chart_datasets = {
        "total_points": [],
        "active_members": [],
        "avg_completion_rate": [],
    }
    for clan in clans:
        # Latest progress metrics
        latest_progress = clan.progress_history.order_by(ClanProgressHistory.timestamp.desc()).first()
        # Time series for chart (last 30 days)
        progress_history = clan.progress_history
        if since:
            progress_history = progress_history.filter(ClanProgressHistory.timestamp >= since)
        progress_history = progress_history.order_by(ClanProgressHistory.timestamp.asc()).all()
        # Prepare chart data
        dates = [ph.timestamp.strftime('%Y-%m-%d') for ph in progress_history]
        points = [ph.total_points for ph in progress_history]
        members = [ph.active_members for ph in progress_history]
        completion = [ph.avg_completion_rate for ph in progress_history]
        # Recent activity (last 10 events)
        recent_activities = AuditLog.query \
            .filter(AuditLog.event_type.in_(['CLAN_JOIN', 'CLAN_LEAVE', 'QUEST_COMPLETE', 'QUEST_FAIL']),
                    AuditLog.character.has(Character.clan_id == clan.id)) \
            .order_by(AuditLog.event_timestamp.desc()) \
            .limit(10).all()
        activity_log = [{
            "type": AuditLog.EVENT_TYPES.get(a.event_type, a.event_type),
            "timestamp": a.event_timestamp,
            "description": a.event_data.get('description', '')
        } for a in recent_activities]

        clan_data.append({
            "id": clan.id,
            "name": clan.name,
            "level": clan.level,
            "experience": clan.experience,
            "member_count": clan.get_member_count(),
            "leader": clan.leader.name if clan.leader else None,
            "emblem": clan.emblem,
            "created_at": clan.created_at,
            "latest_metrics": latest_progress.to_dict() if latest_progress else {},
            "activity_log": activity_log,
            "chart": {
                "dates": dates,
                "total_points": points,
                "active_members": members,
                "avg_completion_rate": completion,
            }
        })
        chart_labels.append(clan.name)
        chart_datasets["total_points"].append(latest_progress.total_points if latest_progress else 0)
        chart_datasets["active_members"].append(latest_progress.active_members if latest_progress else 0)
        chart_datasets["avg_completion_rate"].append(latest_progress.avg_completion_rate if latest_progress else 0)

    chart_data = {
        "labels": chart_labels,
        "datasets": [
            {
                "label": "Total Points",
                "data": chart_datasets["total_points"],
                "backgroundColor": "#4e73df"
            },
            {
                "label": "Active Members",
                "data": chart_datasets["active_members"],
                "backgroundColor": "#1cc88a"
            },
            {
                "label": "Avg Completion Rate",
                "data": chart_datasets["avg_completion_rate"],
                "backgroundColor": "#36b9cc"
            }
        ]
    }

    return render_template(
        'teacher/clan_dashboard.html',
        classes=classes,
        clans=clan_data,
        chart_data=chart_data,
        selected_class_id=class_id,
        active_page='clans_dashboard'
    )

@teacher_bp.route('/api/badges', methods=['GET'])
@login_required
@teacher_required
def api_list_badges():
    badges = AchievementBadge.query.all()
    return {"success": True, "badges": [
        {"id": b.id, "name": b.name, "description": b.description, "icon": b.icon, "is_clan": b.is_clan, "is_student": b.is_student}
        for b in badges
    ]}

@teacher_bp.route('/api/clans/<int:clan_id>/badges', methods=['GET'])
@login_required
@teacher_required
def api_list_clan_badges(clan_id):
    clan = Clan.query.get(clan_id)
    if not clan or clan.class_.teacher_id != current_user.id:
        return {"success": False, "message": "Clan not found or unauthorized."}, 404
    return {"success": True, "badges": [
        {"id": b.id, "name": b.name, "description": b.description, "icon": b.icon}
        for b in clan.badges
    ]}

@teacher_bp.route('/api/clans/<int:clan_id>/badges', methods=['POST'])
@login_required
@teacher_required
def api_award_clan_badge(clan_id):
    data = request.get_json() or {}
    badge_id = data.get('badge_id')
    clan = Clan.query.get(clan_id)
    badge = AchievementBadge.query.get(badge_id)
    if not clan or clan.class_.teacher_id != current_user.id:
        return {"success": False, "message": "Clan not found or unauthorized."}, 404
    if not badge or not badge.is_clan:
        return {"success": False, "message": "Badge not found or not a clan badge."}, 400
    if badge in clan.badges:
        return {"success": False, "message": "Badge already awarded."}, 400
    clan.badges.append(badge)
    try:
        db.session.commit()
        return {"success": True}
    except Exception as e:
        db.session.rollback()
        return {"success": False, "message": str(e)}, 500 