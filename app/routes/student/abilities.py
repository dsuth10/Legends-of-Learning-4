from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.models import db
from app.models.character import Character
from app.models.ability import Ability, CharacterAbility
from app.models.user import User
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

    # Validate target (basic: must exist)
    target = Character.query.get(target_id)
    if not target:
        return jsonify({'success': False, 'message': 'Target not found.'}), 400

    # Call service to apply ability effect
    result = apply_ability_usage(current_user, character, ability, target, context)
    return jsonify(result) 