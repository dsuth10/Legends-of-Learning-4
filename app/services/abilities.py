from app.models import db
from app.models.ability import Ability, CharacterAbility
from app.models.character import Character, StatusEffect
from app.models.audit import AuditLog  # If available
from datetime import datetime, timedelta

def apply_ability_usage(user, character, ability, target, context):
    """
    Apply the effect of an ability from character to target.
    Handles heal, buff, protect, attack, debuff, utility.
    """
    effect_type = ability.type
    amount = 0
    message = ''
    success = True
    xp_awarded = 0
    # Remove expired effects before applying new one
    for effect in target.status_effects.filter(StatusEffect.expires_at < datetime.utcnow()).all():
        db.session.delete(effect)
    db.session.flush()
    # HEAL: restore HP, no overheal, no XP if target at full health
    if effect_type == 'heal':
        heal_amount = min(ability.power, target.max_health - target.health)
        if heal_amount <= 0:
            success = False
            message = 'Target is already at full health.'
        else:
            target.health += heal_amount
            amount = heal_amount
            message = f'Healed {target.name} for {heal_amount} HP.'
            # Award assist XP if healing someone else
            if target.id != character.id:
                xp_awarded = int(heal_amount * 0.5)
                character.gain_experience(xp_awarded)
    # ATTACK: deal damage, consider defense
    elif effect_type == 'attack':
        # Simple formula: damage = power - target.defense/2
        damage = max(1, ability.power - int(target.defense / 2))
        alive = target.take_damage(damage)
        amount = damage
        message = f'Attacked {target.name} for {damage} damage.'
        if not alive:
            message += f' {target.name} was defeated!'
            xp_awarded = damage  # Award XP for defeating
            character.gain_experience(xp_awarded)
    # DEFENSE/PROTECT: temporarily increase defense
    elif effect_type in ('defense', 'protect'):
        duration = ability.duration or 1
        expires_at = datetime.utcnow() + timedelta(minutes=duration)
        effect = StatusEffect(
            character_id=target.id,
            effect_type='protect',
            stat_affected='defense',
            amount=ability.power,
            expires_at=expires_at,
            source=ability.name
        )
        db.session.add(effect)
        amount = ability.power
        message = f'Protected {target.name} (defense +{ability.power} for {duration} minutes).'
    # BUFF: temporarily increase a stat
    elif effect_type == 'buff':
        duration = ability.duration or 1
        stat = 'strength'  # Default, could be parameterized
        expires_at = datetime.utcnow() + timedelta(minutes=duration)
        effect = StatusEffect(
            character_id=target.id,
            effect_type='buff',
            stat_affected=stat,
            amount=ability.power,
            expires_at=expires_at,
            source=ability.name
        )
        db.session.add(effect)
        amount = ability.power
        message = f'Buffed {target.name} ({stat} +{ability.power} for {duration} minutes).'
    # DEBUFF: temporarily decrease a stat
    elif effect_type == 'debuff':
        duration = ability.duration or 1
        stat = 'strength'  # Default, could be parameterized
        expires_at = datetime.utcnow() + timedelta(minutes=duration)
        effect = StatusEffect(
            character_id=target.id,
            effect_type='debuff',
            stat_affected=stat,
            amount=-ability.power,
            expires_at=expires_at,
            source=ability.name
        )
        db.session.add(effect)
        amount = -ability.power
        message = f'Debuffed {target.name} ({stat} {amount} for {duration} minutes).'
    # UTILITY: generic effect (stub)
    elif effect_type == 'utility':
        amount = 0
        message = f'Used {ability.name} (utility effect).'
    else:
        amount = 0
        message = f'Used {ability.name} on {target.name}.'
    # Update cooldown
    char_ability = CharacterAbility.query.filter_by(character_id=character.id, ability_id=ability.id).first()
    if char_ability:
        char_ability.last_used_at = datetime.utcnow()
    db.session.commit()
    # Log event (stub)
    # AuditLog.log_event(...)
    return {
        'success': success,
        'message': message,
        'effect': {'type': effect_type, 'amount': amount, 'target_id': target.id},
        'cooldown': ability.cooldown,
        'character': character.to_dict() if hasattr(character, 'to_dict') else {},
        'target': target.to_dict() if hasattr(target, 'to_dict') else {},
        'xp_awarded': xp_awarded
    } 