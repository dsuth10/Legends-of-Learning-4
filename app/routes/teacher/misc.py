from .blueprint import teacher_bp, teacher_required
from flask_login import login_required, current_user
from flask import render_template, request, jsonify, flash
from app.models import db
from app.models.classroom import Classroom
from app.models.clan import Clan
from app.models.quest import Quest
from app.models.audit import AuditLog
from app.models.user import User
from app.models.character import Character
from app.models.shop import ShopPurchase
from app.models.student import Student
from app.models.equipment import Equipment
from app.models.ability import Ability
from app.models.shop_config import ShopItemOverride
import json
from datetime import datetime, timedelta, timezone

@teacher_bp.route('/dashboard')
@login_required
@teacher_required
def dashboard():
    # Get stats for the current teacher
    stats = {
        'active_classes': Classroom.query.filter_by(
            teacher_id=current_user.id, 
            is_active=True
        ).count(),
        'total_students': db.session.query(User).\
            join(Classroom.students).\
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
                  Quest.end_date >= datetime.now(timezone.utc).replace(tzinfo=None)).\
            count()
    }
    total_classes = Classroom.query.filter_by(teacher_id=current_user.id, is_active=True).count()
    total_students = db.session.query(User).\
        join(Classroom.students).\
        filter(Classroom.teacher_id == current_user.id).\
        distinct().\
        count()
    active_students = db.session.query(User).\
        join(Classroom.students).\
        filter(Classroom.teacher_id == current_user.id, User.is_active == True).\
        distinct().\
        count()
    inactive_students = total_students - active_students
    seven_days_ago = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=7)
    recent_activities = []
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
    for log in audit_logs:
        activity = {
            'title': AuditLog.EVENT_TYPES.get(log.event_type, log.event_type),
            'timestamp': log.event_timestamp,
            'description': f"{log.character.name} - {log.event_data.get('description', '')}",
            'details': log.event_data.get('details', '')
        }
        recent_activities.append(activity)
    classes = Classroom.query.filter_by(teacher_id=current_user.id, is_active=True).all()
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

@teacher_bp.route('/shop')
@login_required
@teacher_required
def shop():
    classes = Classroom.query.filter_by(teacher_id=current_user.id, is_active=True).all()
    class_id = request.args.get('class_id', type=int)
    
    # Default to first class if not specified/exists
    if not class_id and classes:
        class_id = classes[0].id
    
    selected_class = None
    if class_id:
        selected_class = Classroom.query.filter_by(id=class_id, teacher_id=current_user.id).first()
    
    items_data = []
    
    if selected_class:
        # Fetch all base items
        equipment = Equipment.query.all()
        abilities = Ability.query.all()
        
        # Fetch overrides
        overrides = ShopItemOverride.query.filter_by(classroom_id=selected_class.id).all()
        overrides_map = {(o.item_type, o.item_id): o for o in overrides}
        
        for eq in equipment:
            ov = overrides_map.get(('equipment', eq.id))
            items_data.append({
                'id': eq.id,
                'name': eq.name,
                'type': 'equipment',
                'category_display': 'Equipment',
                'base_cost': eq.cost,
                'override_cost': ov.override_cost if ov else None,
                'base_level': getattr(eq, 'level_requirement', 1),
                'override_level': ov.override_level_req if ov else None,
                'is_visible': ov.is_visible if ov else True,
                'image': eq.image_url or '/static/images/default_item.png'
            })
            
        for ab in abilities:
            ov = overrides_map.get(('ability', ab.id))
            items_data.append({
                'id': ab.id,
                'name': ab.name,
                'type': 'ability',
                'category_display': 'Ability',
                'base_cost': ab.cost,
                'override_cost': ov.override_cost if ov else None,
                'base_level': getattr(ab, 'level_requirement', 1),
                'override_level': ov.override_level_req if ov else None,
                'is_visible': ov.is_visible if ov else True,
                'image': '/static/images/default_item.png'
            })
            
    return render_template('teacher/shop.html', active_page='shop', classes=classes, selected_class=selected_class, items=items_data)

@teacher_bp.route('/shop/save', methods=['POST'])
@login_required
@teacher_required
def save_shop_config():
    data = request.get_json()
    class_id = data.get('class_id')
    updates = data.get('updates', [])
    
    if not class_id:
        return jsonify({'success': False, 'message': 'Missing class ID'}), 400
        
    classroom = Classroom.query.filter_by(id=class_id, teacher_id=current_user.id).first()
    if not classroom:
        return jsonify({'success': False, 'message': 'Classroom not found or unauthorized'}), 404
        
    try:
        # Simple strategy: Process each update. 
        # Ideally we might clear old overrides or upsert. 
        # Here we will upsert based on the updates sent.
        
        for update in updates:
            item_type = update.get('item_type')
            item_id = update.get('item_id')
            
            override = ShopItemOverride.query.filter_by(
                classroom_id=classroom.id,
                item_type=item_type,
                item_id=item_id
            ).first()
            
            if not override:
                override = ShopItemOverride(
                    classroom_id=classroom.id,
                    item_type=item_type,
                    item_id=item_id
                )
                db.session.add(override)
            
            # Update fields
            # Handle empty strings/nulls
            cost_val = update.get('override_cost')
            level_val = update.get('override_level')
            
            override.override_cost = int(cost_val) if cost_val not in (None, '') else None
            override.override_level_req = int(level_val) if level_val not in (None, '') else None
            override.is_visible = update.get('is_visible', True)
            
        db.session.commit()
        return jsonify({'success': True, 'message': 'Configuration saved successfully.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

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

@teacher_bp.route('/purchases')
@login_required
@teacher_required
def purchase_log():
    purchases = ShopPurchase.query.order_by(ShopPurchase.purchase_date.desc()).limit(100).all()
    purchase_data = []
    for p in purchases:
        student = Student.query.get(p.student_id)
        user = User.query.get(student.user_id) if student else None
        item_name = None
        if p.purchase_type == 'equipment':
            item = Equipment.query.get(p.item_id)
            item_name = item.name if item else 'Unknown Equipment'
        elif p.purchase_type == 'ability':
            item = Ability.query.get(p.item_id)
            item_name = item.name if item else 'Unknown Ability'
        else:
            item_name = 'Unknown'
        purchase_data.append({
            'student': user.username if user else 'Unknown',
            'item_name': item_name,
            'item_type': p.purchase_type,
            'gold_spent': p.gold_spent,
            'date': p.purchase_date.strftime('%Y-%m-%d %H:%M'),
        })
    return render_template('teacher/purchase_log.html', purchases=purchase_data, active_page='purchase_log') 