from app.models import db
from app.models.ability import Ability, CharacterAbility
from app.models.character import Character, StatusEffect
from app.models.audit import AuditLog
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


def _purge_expired_effects(target):
    for effect in target.status_effects.filter(StatusEffect.expires_at < datetime.utcnow()).all():
        db.session.delete(effect)
    db.session.flush()


def execute_ability_effect(caster, ability, target, *, skip_assist_xp=False):
    """
    Apply ability effect to one target. Does not commit, update last_used, or audit.
    Returns dict: success, message, amount, xp_awarded, effect_type
    """
    effect_type = ability.type
    amount = 0
    message = ''
    success = True
    xp_awarded = 0
    special = getattr(ability, 'special_effect', None) or None

    _purge_expired_effects(target)

    if effect_type == 'heal':
        if special == 'revive':
            if target.health > 0:
                success = False
                message = 'Target is not fallen (must be at 0 HP to revive).'
            else:
                target.health = 1
                amount = 1
                message = f'Revived {target.name} with 1 HP.'
                if target.id != caster.id and not skip_assist_xp:
                    xp_awarded = 5
                    caster.gain_experience(xp_awarded)
        elif special == 'full_heal':
            heal_amount = target.max_health - target.health
            if heal_amount <= 0:
                success = False
                message = f'{target.name} is already at full health.'
            else:
                target.health = target.max_health
                amount = heal_amount
                message = f'Fully healed {target.name}.'
                if target.id != caster.id and not skip_assist_xp:
                    xp_awarded = int(heal_amount * 0.5)
                    caster.gain_experience(xp_awarded)
        else:
            heal_amount = min(ability.power, target.max_health - target.health)
            if heal_amount <= 0:
                success = False
                message = 'Target is already at full health.'
            else:
                target.health += heal_amount
                amount = heal_amount
                message = f'Healed {target.name} for {heal_amount} HP.'
                if target.id != caster.id and not skip_assist_xp:
                    xp_awarded = int(heal_amount * 0.5)
                    caster.gain_experience(xp_awarded)

    elif effect_type == 'attack':
        damage = max(1, ability.power - int(target.defense / 2))
        alive = target.take_damage(damage)
        amount = damage
        message = f'Attacked {target.name} for {damage} damage.'
        if not alive:
            message += f' {target.name} was defeated!'
            xp_awarded = damage
            caster.gain_experience(xp_awarded)

    elif effect_type in ('defense', 'protect'):
        duration = ability.duration or 1
        expires_at = datetime.utcnow() + timedelta(minutes=duration)
        effect = StatusEffect(
            character_id=target.id,
            effect_type='protect',
            stat_affected='defense',
            amount=ability.power,
            expires_at=expires_at,
            source=ability.name,
        )
        db.session.add(effect)
        amount = ability.power
        message = f'Protected {target.name} (defense +{ability.power} for {duration} minutes).'

    elif effect_type == 'buff':
        duration = ability.duration or 1
        stat = 'power'
        expires_at = datetime.utcnow() + timedelta(minutes=duration)
        effect = StatusEffect(
            character_id=target.id,
            effect_type='buff',
            stat_affected=stat,
            amount=ability.power,
            expires_at=expires_at,
            source=ability.name,
        )
        db.session.add(effect)
        amount = ability.power
        message = f'Buffed {target.name} ({stat} +{ability.power} for {duration} minutes).'

    elif effect_type == 'debuff':
        duration = ability.duration or 1
        stat = 'power'
        expires_at = datetime.utcnow() + timedelta(minutes=duration)
        effect = StatusEffect(
            character_id=target.id,
            effect_type='debuff',
            stat_affected=stat,
            amount=-ability.power,
            expires_at=expires_at,
            source=ability.name,
        )
        db.session.add(effect)
        amount = -ability.power
        message = f'Debuffed {target.name} ({stat} {amount} for {duration} minutes).'

    elif effect_type == 'utility':
        if special == 'restore_power_full':
            max_p = getattr(target, 'max_power', target.power)
            restore_amount = max_p - target.power
            if restore_amount <= 0:
                success = False
                message = f"{target.name}'s power is already full."
            else:
                target.power = max_p
                amount = restore_amount
                message = f'Restored {target.name}\'s power to full.'
        else:
            amount = 0
            message = f'Used {ability.name} (utility effect).'

    else:
        amount = 0
        message = f'Used {ability.name} on {target.name}.'

    return {
        'success': success,
        'message': message,
        'amount': amount,
        'xp_awarded': xp_awarded,
        'effect_type': effect_type,
    }


def apply_ability_usage(user, character, ability, target, context, commit=True):
    """
    Apply the effect of an ability from character to a single target.
    """
    return apply_ability_usage_multi(user, character, ability, [target], context, commit=commit)


def apply_ability_usage_multi(user, character, ability, targets, context, commit=True):
    """
    Apply ability to one or more targets (e.g. all_allies). Deduct power cost before caller — route handles cost.
    """
    if not targets:
        return {
            'success': False,
            'message': 'No targets.',
            'effect': {'type': ability.type, 'amount': 0, 'target_ids': []},
            'cooldown': ability.cooldown,
            'character': _character_payload(character),
            'targets': [],
            'xp_awarded': 0,
        }

    multi = len(targets) > 1
    total_xp = 0
    messages = []
    any_success = False
    total_amount = 0

    for i, tgt in enumerate(targets):
        skip_xp = multi and i > 0
        res = execute_ability_effect(character, ability, tgt, skip_assist_xp=skip_xp)
        if res['success']:
            any_success = True
        total_amount += res['amount'] if isinstance(res['amount'], int) else 0
        total_xp += res['xp_awarded']
        messages.append(res['message'])

    char_ability = CharacterAbility.query.filter_by(character_id=character.id, ability_id=ability.id).first()
    if char_ability:
        char_ability.last_used_at = datetime.utcnow()

    if commit:
        db.session.commit()
    else:
        db.session.flush()

    combined_message = ' '.join(m for m in messages if m)
    if not any_success:
        combined_message = messages[0] if messages else 'Ability failed.'

    try:
        from flask import request

        AuditLog.log_event(
            AuditLog.EventType.ABILITY_USE,
            event_data={
                'ability_id': ability.id,
                'ability_name': ability.name,
                'ability_type': ability.type,
                'target_ids': [t.id for t in targets],
                'target_names': [t.name for t in targets],
                'effect_type': ability.type,
                'effect_amount': total_amount,
                'context': context,
                'xp_awarded': total_xp,
                'success': any_success,
                'multi_target': multi,
            },
            user_id=user.id if user else None,
            character_id=character.id,
            ip_address=request.remote_addr if request else None,
        )
    except Exception as e:
        logger.error('Failed to log ability usage: %s', e)

    db.session.refresh(character)
    refreshed_targets = []
    for tgt in targets:
        db.session.refresh(tgt)
        refreshed_targets.append(_target_payload(tgt))

    primary = targets[0]
    return {
        'success': any_success,
        'message': combined_message,
        'effect': {
            'type': ability.type,
            'amount': total_amount,
            'target_id': primary.id,
            'target_ids': [t.id for t in targets],
        },
        'cooldown': ability.cooldown,
        'character': _character_payload(character),
        'target': _target_payload(primary),
        'targets': refreshed_targets,
        'xp_awarded': total_xp,
    }


def _character_payload(ch):
    return {
        'id': ch.id,
        'name': ch.name,
        'health': ch.health,
        'max_health': ch.max_health,
        'power': ch.power,
        'max_power': getattr(ch, 'max_power', ch.power),
        'defense': ch.defense,
        'level': ch.level,
        'experience': ch.experience,
        'gold': ch.gold,
    }


def _target_payload(target):
    target_status_effects = []
    if hasattr(target, 'status_effects'):
        now = datetime.utcnow()
        for effect in target.status_effects.filter(StatusEffect.expires_at > now).all():
            target_status_effects.append(
                {
                    'effect_type': effect.effect_type,
                    'stat_affected': effect.stat_affected,
                    'amount': effect.amount,
                    'source': effect.source,
                    'expires_at': effect.expires_at.isoformat(),
                }
            )
    return {
        'id': target.id,
        'name': target.name,
        'health': target.health,
        'max_health': target.max_health,
        'power': target.power,
        'max_power': getattr(target, 'max_power', target.power),
        'defense': target.defense,
        'status_effects': target_status_effects,
    }
