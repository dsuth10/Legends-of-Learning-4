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

# TODO: Move relevant routes and helpers from students.py into this file.

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
            existing = Inventory.query.filter_by(character_id=character.id, equipment_id=equipment.id).first()
            if existing:
                results.append({'student_id': student_id, 'status': 'already_has_item'})
                continue
            # Add to inventory as unequipped
            new_inv = Inventory(character_id=character.id, equipment_id=equipment.id, is_equipped=False)
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
