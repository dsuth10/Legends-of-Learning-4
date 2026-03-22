from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timedelta

from app.models import db
from app.models.character import Character
from app.models.ability import Ability, CharacterAbility
from app.models.audit import AuditLog
from app.routes.teacher.blueprint import student_required
from app.services.abilities import apply_ability_usage_multi
from app.services.powers import resolve_power_targets

bp = Blueprint('student_abilities', __name__, url_prefix='/student/abilities')


@bp.route('/use', methods=['POST'])
@login_required
@student_required
def use_ability():
    data = request.get_json() or {}
    ability_id = data.get('ability_id')
    target_id = data.get('target_id')
    context = data.get('context', 'general')

    student = current_user.student_profile
    character = Character.query.filter_by(student_id=student.id, is_active=True).first()
    if not character:
        return jsonify({'success': False, 'message': 'No active character found.'}), 400

    character.regenerate_power()
    db.session.add(character)
    db.session.commit()

    char_ability = CharacterAbility.query.filter_by(character_id=character.id, ability_id=ability_id).first()
    if not char_ability or not char_ability.is_equipped:
        return jsonify({'success': False, 'message': 'Ability not equipped or not owned.'}), 400

    ability = char_ability.ability
    now = datetime.utcnow()
    if char_ability.last_used_at:
        cooldown = ability.cooldown or 0
        elapsed = (now - char_ability.last_used_at).total_seconds()
        if elapsed < cooldown:
            return jsonify(
                {
                    'success': False,
                    'message': f'Ability is on cooldown for {int(cooldown - elapsed)} more seconds.',
                }
            ), 400

    cost = ability.cost or 0
    if character.power < cost:
        return jsonify(
            {
                'success': False,
                'message': f'Not enough power to use this ability (needs {cost}, you have {character.power}).',
            }
        ), 400

    if target_id is None:
        target_id = character.id

    try:
        targets = resolve_power_targets(character, ability, int(target_id))
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 400

    character.power -= cost
    db.session.add(character)
    db.session.flush()

    result = apply_ability_usage_multi(current_user, character, ability, targets, context, commit=True)

    if not result.get('success'):
        character.power += cost
        db.session.add(character)
        db.session.commit()

    return jsonify(result)


@bp.route('/history', methods=['GET'])
@login_required
@student_required
def ability_history():
    """Get ability usage history for the current student's character."""
    student = current_user.student_profile
    if not student:
        return jsonify({'success': False, 'message': 'No student profile found.'}), 400

    character = Character.query.filter_by(student_id=student.id, is_active=True).first()
    if not character:
        return jsonify({'success': False, 'message': 'No active character found.'}), 400

    limit = request.args.get('limit', 20, type=int)
    days = request.args.get('days', 7, type=int)
    ability_type = request.args.get('type', None)

    query = AuditLog.query.filter_by(
        character_id=character.id,
        event_type=AuditLog.EventType.ABILITY_USE.value,
    )

    if days:
        start_date = datetime.utcnow() - timedelta(days=days)
        query = query.filter(AuditLog.event_timestamp >= start_date)

    logs = query.order_by(AuditLog.event_timestamp.desc()).limit(limit).all()

    history = []
    for log in logs:
        event_data = log.event_data or {}
        if ability_type and event_data.get('ability_type') != ability_type:
            continue

        target_name = event_data.get('target_name')
        if not target_name and event_data.get('target_names'):
            names = event_data.get('target_names') or []
            target_name = ', '.join(names) if names else 'Unknown'

        history.append(
            {
                'id': log.id,
                'ability_name': event_data.get('ability_name', 'Unknown'),
                'ability_type': event_data.get('ability_type', 'unknown'),
                'target_name': target_name or 'Unknown',
                'effect_type': event_data.get('effect_type', 'unknown'),
                'effect_amount': event_data.get('effect_amount', 0),
                'context': event_data.get('context', 'general'),
                'xp_awarded': event_data.get('xp_awarded', 0),
                'success': event_data.get('success', True),
                'timestamp': log.event_timestamp.isoformat(),
            }
        )

    return jsonify({'success': True, 'history': history, 'count': len(history)})
