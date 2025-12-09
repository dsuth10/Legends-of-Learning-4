from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.models import db
from app.models.character import Character
from app.models.ability import Ability, CharacterAbility
from app.models.user import User
from app.models.audit import AuditLog
from app.routes.teacher.blueprint import student_required
from app.services.abilities import apply_ability_usage

bp = Blueprint('student_abilities', __name__, url_prefix='/student/abilities')

@bp.route('/use', methods=['POST'])
@login_required
@student_required
def use_ability():
    data = request.get_json()
    ability_id = data.get('ability_id')
    target_id = data.get('target_id')
    context = data.get('context', 'general')

    # Get the student's active character
    student = current_user.student_profile
    character = Character.query.filter_by(student_id=student.id, is_active=True).first()
    if not character:
        return jsonify({'success': False, 'message': 'No active character found.'}), 400

    # Validate ability ownership and equipped status
    char_ability = CharacterAbility.query.filter_by(character_id=character.id, ability_id=ability_id).first()
    if not char_ability or not char_ability.is_equipped:
        return jsonify({'success': False, 'message': 'Ability not equipped or not owned.'}), 400

    # Validate cooldown
    from datetime import datetime, timedelta
    ability = char_ability.ability
    now = datetime.utcnow()
    if char_ability.last_used_at:
        cooldown = ability.cooldown or 0
        elapsed = (now - char_ability.last_used_at).total_seconds()
        if elapsed < cooldown:
            return jsonify({'success': False, 'message': f'Ability is on cooldown for {int(cooldown - elapsed)} more seconds.'}), 400

    # Validate target - must be a Character
    # Note: In battle context, monster targeting would require special handling
    # For now, abilities in battle can target self or other characters
    target = Character.query.get(target_id)
    if not target:
        return jsonify({'success': False, 'message': 'Target not found.'}), 400

    # Validate context-specific requirements
    if context == 'quest':
        # Could add quest validation here (e.g., must have active quest)
        pass
    elif context == 'battle':
        # Could add battle validation here (e.g., must be in active battle)
        pass
    
    # Call service to apply ability effect
    result = apply_ability_usage(current_user, character, ability, target, context)
    return jsonify(result)

@bp.route('/history', methods=['GET'])
@login_required
@student_required
def ability_history():
    """Get ability usage history for the current student's character."""
    from datetime import datetime, timedelta
    
    student = current_user.student_profile
    if not student:
        return jsonify({'success': False, 'message': 'No student profile found.'}), 400
    
    character = Character.query.filter_by(student_id=student.id, is_active=True).first()
    if not character:
        return jsonify({'success': False, 'message': 'No active character found.'}), 400
    
    # Get query parameters
    limit = request.args.get('limit', 20, type=int)
    days = request.args.get('days', 7, type=int)
    ability_type = request.args.get('type', None)
    
    # Build query
    query = AuditLog.query.filter_by(
        character_id=character.id,
        event_type=AuditLog.EventType.ABILITY_USE.value
    )
    
    # Filter by date range
    if days:
        start_date = datetime.utcnow() - timedelta(days=days)
        query = query.filter(AuditLog.event_timestamp >= start_date)
    
    # Get logs
    logs = query.order_by(AuditLog.event_timestamp.desc()).limit(limit).all()
    
    # Format response
    history = []
    for log in logs:
        event_data = log.event_data or {}
        if ability_type and event_data.get('ability_type') != ability_type:
            continue
        
        history.append({
            'id': log.id,
            'ability_name': event_data.get('ability_name', 'Unknown'),
            'ability_type': event_data.get('ability_type', 'unknown'),
            'target_name': event_data.get('target_name', 'Unknown'),
            'effect_type': event_data.get('effect_type', 'unknown'),
            'effect_amount': event_data.get('effect_amount', 0),
            'context': event_data.get('context', 'general'),
            'xp_awarded': event_data.get('xp_awarded', 0),
            'success': event_data.get('success', True),
            'timestamp': log.event_timestamp.isoformat()
        })
    
    return jsonify({
        'success': True,
        'history': history,
        'count': len(history)
    }) 