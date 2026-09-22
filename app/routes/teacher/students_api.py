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
from app.models.clan import Clan

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
    inventory = []
    for item in character.inventory_items:
        eq = item.equipment or item.item
        inventory.append({
            'inventory_id': item.id,
            'item_id': item.item_id,
            'name': eq.name if eq else None,
            'is_equipped': item.is_equipped,
        })
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
    equipped = []
    for item in character.inventory_items.filter_by(is_equipped=True):
        eq = item.equipment or item.item
        equipped.append({
            'inventory_id': item.id,
            'item_id': item.item_id,
            'name': eq.name if eq else None,
        })
    return jsonify({'equipped': equipped})

def _batch_character_action_impl():
    data = request.get_json() or {}
    action = data.get('action')
    student_ids = list(data.get('student_ids') or [])
    character_ids = list(data.get('character_ids') or [])

    if character_ids:
        for cid in character_ids:
            ch = Character.query.filter_by(id=cid, is_active=True).first()
            if not ch:
                continue
            if not teacher_owns_student(current_user.id, ch.student_id):
                continue
            if ch.student_id not in student_ids:
                student_ids.append(ch.student_id)

    student_ids = list(dict.fromkeys(int(s) for s in student_ids))

    if not action or not student_ids:
        return jsonify({'success': False, 'message': 'Missing action or character/student ids'}), 400

    results = {}
    for student_id in student_ids:
        if not teacher_owns_student(current_user.id, student_id):
            results[str(student_id)] = {'success': False, 'message': 'forbidden'}
            continue
        character = Character.query.filter_by(student_id=student_id, is_active=True).first()
        if not character:
            results[str(student_id)] = {'success': False, 'message': 'no_character'}
            continue
        cid_key = str(character.id)
        if action in ('reset-health', 'reset_health'):
            character.health = character.max_health
            db.session.add(character)
            db.session.add(
                AuditLog(
                    character_id=character.id,
                    event_type=EventType.CHARACTER_UPDATE.value,
                    event_data={'action': 'batch-reset-health'},
                )
            )
            results[cid_key] = {'success': True, 'new_health': character.health}
        elif action == 'grant-item':
            item_id = data.get('item_id')
            if not item_id:
                results[cid_key] = {'success': False, 'message': 'missing_item_id'}
                continue
            equipment = Equipment.query.filter_by(id=item_id).first()
            if not equipment:
                results[cid_key] = {'success': False, 'message': 'item_not_found'}
                continue
            existing = Inventory.query.filter_by(character_id=character.id, item_id=equipment.id).first()
            if existing:
                results[cid_key] = {'success': False, 'message': 'already_has_item'}
                continue
            new_inv = Inventory(character_id=character.id, item_id=equipment.id, is_equipped=False)
            db.session.add(new_inv)
            db.session.add(
                AuditLog(
                    character_id=character.id,
                    event_type=EventType.EQUIPMENT_CHANGE.value,
                    event_data={
                        'action': 'batch-grant-item',
                        'item_id': equipment.id,
                        'item_name': equipment.name,
                    },
                )
            )
            results[cid_key] = {'success': True}
        elif action in ('reset-character', 'reset_character'):
            db.session.delete(character)
            results[cid_key] = {'success': True}
        else:
            results[cid_key] = {'success': False, 'message': 'unknown_action'}

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

    ok = any(r.get('success') for r in results.values())
    return jsonify(
        {
            'success': ok,
            'message': 'Batch action completed.' if ok else 'No changes applied.',
            'results': results,
        }
    )


@teacher_bp.route('/api/teacher/students/batch-character-action', methods=['POST'])
@login_required
@teacher_required
def batch_character_action():
    return _batch_character_action_impl()


@teacher_bp.route('/api/teacher/characters/batch-action', methods=['POST'])
@login_required
@teacher_required
def batch_character_action_by_character_id():
    """Same as batch-character-action; accepts character_ids (preferred by Character Management UI)."""
    return _batch_character_action_impl()

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
    return (
        jsonify(
            {
                'success': False,
                'message': 'Quests have been retired. Assign learning paths with Adventures.',
                'code': 'QUESTS_RETIRED',
            }
        ),
        410,
    )

