"""
API endpoints for batch actions, stats, inventory, equipment, etc.
"""

from .blueprint import teacher_bp, teacher_required
from flask_login import login_required, current_user
from flask import jsonify, request
from app.models import db
from app.models.classroom import Classroom
from app.models.user import User, UserRole
from app.models.student import Student
from app.models.character import Character
from app.models.equipment import Equipment, Inventory
from app.models.audit import AuditLog, EventType
from app.models.quest import Quest, QuestLog, QuestStatus
from app.models.clan import Clan
from app.services.quest_map_utils import find_available_coordinates
from sqlalchemy.exc import IntegrityError

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
            existing = Inventory.query.filter_by(character_id=character.id, item_id=equipment.id).first()
            if existing:
                results.append({'student_id': student_id, 'status': 'already_has_item'})
                continue
            # Add to inventory as unequipped
            new_inv = Inventory(character_id=character.id, item_id=equipment.id, is_equipped=False)
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

@teacher_bp.route('/api/teacher/student/<int:student_id>/award-gold', methods=['POST'])
@login_required
@teacher_required
def api_award_gold(student_id):
    if not teacher_owns_student(current_user.id, student_id):
        return jsonify({'success': False, 'message': 'Permission denied'}), 403
    data = request.get_json()
    amount = data.get('amount')
    reason = data.get('reason', '')
    if not isinstance(amount, int) or amount <= 0 or amount > 100000:
        return jsonify({'success': False, 'message': 'Invalid gold amount'}), 400
    student = Student.query.filter_by(id=student_id).first_or_404()
    character = Character.query.filter_by(student_id=student.id, is_active=True).first()
    if not character:
        return jsonify({'success': False, 'message': 'No active character found'}), 404
    character.gold += amount
    db.session.commit()
    # Audit log
    audit = AuditLog(
        character_id=character.id,
        event_type=EventType.GOLD_TRANSACTION.value,
        event_data={
            'action': 'award-gold',
            'amount': amount,
            'reason': reason,
            'teacher_id': current_user.id
        }
    )
    db.session.add(audit)
    db.session.commit()
    return jsonify({'success': True, 'message': f'Awarded {amount} gold.', 'gold': character.gold})

@teacher_bp.route('/api/teacher/student/<int:student_id>/award-xp', methods=['POST'])
@login_required
@teacher_required
def api_award_xp(student_id):
    if not teacher_owns_student(current_user.id, student_id):
        return jsonify({'success': False, 'message': 'Permission denied'}), 403
    data = request.get_json()
    amount = data.get('amount')
    reason = data.get('reason', '')
    if not isinstance(amount, int) or amount <= 0 or amount > 100000:
        return jsonify({'success': False, 'message': 'Invalid XP amount'}), 400
    student = Student.query.filter_by(id=student_id).first_or_404()
    character = Character.query.filter_by(student_id=student.id, is_active=True).first()
    if not character:
        return jsonify({'success': False, 'message': 'No active character found'}), 404
    character.gain_experience(amount)
    db.session.commit()
    # Audit log
    audit = AuditLog(
        character_id=character.id,
        event_type=EventType.XP_TRANSACTION.value,
        event_data={
            'action': 'award-xp',
            'amount': amount,
            'reason': reason,
            'teacher_id': current_user.id
        }
    )
    db.session.add(audit)
    db.session.commit()
    return jsonify({'success': True, 'message': f'Awarded {amount} XP.', 'xp': character.experience, 'level': character.level})

@teacher_bp.route('/api/teacher/assign-quest', methods=['POST'])
@login_required
@teacher_required
def api_assign_quest():
    data = request.get_json() or request.form
    quest_id = data.get('quest_id')
    target_type = data.get('target_type')
    target_id = data.get('target_id')
    if not quest_id or not target_type or not target_id:
        return jsonify({'success': False, 'message': 'Missing required parameters'}), 400
    # Validate quest
    quest = Quest.query.filter_by(id=quest_id).first()
    if not quest:
        return jsonify({'success': False, 'message': 'Invalid quest_id'}), 404
    # Determine targets
    characters = []
    if target_type == 'student':
        student = Student.query.filter_by(id=target_id).first()
        if not student:
            return jsonify({'success': False, 'message': 'Invalid student_id'}), 404
        # Authorization: teacher must own the student
        classroom = Classroom.query.filter_by(id=student.class_id, teacher_id=current_user.id).first()
        if not classroom:
            return jsonify({'success': False, 'message': 'Permission denied'}), 403
        char = Character.query.filter_by(student_id=student.id, is_active=True).first()
        if char:
            characters.append(char)
    elif target_type == 'clan':
        clan = Clan.query.filter_by(id=target_id).first()
        if not clan:
            return jsonify({'success': False, 'message': 'Invalid clan_id'}), 404
        # Authorization: teacher must own the class the clan belongs to
        classroom = Classroom.query.filter_by(id=clan.class_id, teacher_id=current_user.id).first()
        if not classroom:
            return jsonify({'success': False, 'message': 'Permission denied'}), 403
        chars = clan.members.filter_by(is_active=True).all()
        characters.extend(chars)
    elif target_type == 'class':
        classroom = Classroom.query.filter_by(id=target_id, teacher_id=current_user.id).first()
        if not classroom:
            return jsonify({'success': False, 'message': 'Invalid or unauthorized class_id'}), 404
        # Get all students in the class
        students = Student.query.filter_by(class_id=classroom.id).all()
        for student in students:
            char = Character.query.filter_by(student_id=student.id, is_active=True).first()
            if char:
                characters.append(char)
    else:
        return jsonify({'success': False, 'message': 'Invalid target_type'}), 400
    if not characters:
        return jsonify({'success': False, 'message': 'No target characters found'}), 404
    # Assign quest to each character
    assigned = 0
    skipped = 0
    errors = []
    for char in characters:
        # Check for existing QuestLog
        existing = QuestLog.query.filter_by(character_id=char.id, quest_id=quest.id).first()
        if existing:
            skipped += 1
            continue
        try:
            x, y = find_available_coordinates(char.id, db.session)
        except Exception as e:
            errors.append(f'No available coordinates for character {char.id}')
            skipped += 1
            continue
        new_log = QuestLog(
            character_id=char.id,
            quest_id=quest.id,
            status=QuestStatus.NOT_STARTED,
            x_coordinate=x,
            y_coordinate=y
        )
        db.session.add(new_log)
        try:
            db.session.commit()
            assigned += 1
        except IntegrityError:
            db.session.rollback()
            skipped += 1
        except Exception as e:
            db.session.rollback()
            errors.append(str(e))
            skipped += 1
    return jsonify({
        'success': True,
        'assigned': assigned,
        'skipped': skipped,
        'errors': errors
    })
