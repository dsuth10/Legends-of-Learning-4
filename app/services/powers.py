"""Powers: learn rules, clan targets, starter grants."""

from sqlalchemy import or_

from app.models import db
from app.models.ability import Ability, CharacterAbility
from app.models.character import Character


def clan_ally_character_ids(character):
    """Character ids in the same clan (including self). Empty if no clan."""
    if not character.clan_id:
        return [character.id]
    members = Character.query.filter_by(clan_id=character.clan_id).all()
    return [c.id for c in members]


def resolve_power_targets(caster, ability, target_id):
    """
    Build list of Character targets for this ability.
    Raises ValueError with message if invalid.
    """
    tt = (ability.target_type or 'self').lower()
    if tt == 'self':
        if int(target_id) != caster.id:
            raise ValueError('This power can only target yourself.')
        return [caster]

    if tt == 'single_ally':
        target = Character.query.get(target_id)
        if not target:
            raise ValueError('Target not found.')
        allowed = set(clan_ally_character_ids(caster))
        if target.id not in allowed:
            raise ValueError('You can only target yourself or members of your clan.')
        return [target]

    if tt == 'all_allies':
        if not caster.clan_id:
            raise ValueError('You must be in a clan to use this team power.')
        members = Character.query.filter_by(clan_id=caster.clan_id).all()
        if not members:
            return [caster]
        return members

    if tt == 'single_enemy':
        target = Character.query.get(target_id)
        if not target:
            raise ValueError('Target not found.')
        return [target]

    if tt in ('all_enemies', 'area'):
        raise ValueError('This target type is not supported yet.')

    raise ValueError('Unsupported target type for this power.')


def character_can_learn_power(character, ability):
    """Return (ok: bool, reason: str)."""
    if CharacterAbility.query.filter_by(character_id=character.id, ability_id=ability.id).first():
        return False, 'You already know this power.'

    if ability.level_requirement > character.level:
        return False, f'Requires level {ability.level_requirement}.'

    if ability.class_restriction:
        if ability.class_restriction.lower() != (character.character_class or '').lower():
            return False, f'Only {ability.class_restriction}s can learn this power.'

    pp_cost = getattr(ability, 'pp_cost', 1) or 1
    if character.power_points < pp_cost:
        return False, f'Not enough Power Points (need {pp_cost}).'

    if ability.prerequisite_id:
        if not CharacterAbility.query.filter_by(
            character_id=character.id, ability_id=ability.prerequisite_id
        ).first():
            return False, 'You must learn the prerequisite power first.'

    return True, ''


def learn_power(character, ability, *, user_id=None, ip_address=None):
    """
    Spend PP and create CharacterAbility. Auto-equip if fewer than 4 equipped.
    Caller must commit. Adds AuditLog (same transaction; does not commit).
    """
    ok, reason = character_can_learn_power(character, ability)
    if not ok:
        return {'success': False, 'message': reason}

    pp_cost = getattr(ability, 'pp_cost', 1) or 1
    character.power_points -= pp_cost

    equipped_n = CharacterAbility.query.filter_by(
        character_id=character.id, is_equipped=True
    ).count()
    ca = CharacterAbility(
        character_id=character.id,
        ability_id=ability.id,
        is_equipped=equipped_n < 4,
    )
    db.session.add(ca)
    db.session.flush()

    from app.models.audit import AuditLog, EventType

    db.session.add(
        AuditLog(
            event_type=EventType.POWER_LEARNED.value,
            user_id=user_id,
            character_id=character.id,
            event_data={
                'ability_id': ability.id,
                'ability_name': ability.name,
                'pp_spent': pp_cost,
            },
            ip_address=ip_address,
        )
    )

    return {
        'success': True,
        'message': f'Learned {ability.name}!',
        'character_ability_id': ca.id,
    }


def grant_starter_powers(character):
    """
    Auto-learn default basic powers with level_requirement <= 1 for class + universal.
    Does not commit.
    """
    q = Ability.query.filter(
        Ability.is_default.is_(True),
        Ability.tier == 'basic',
        Ability.level_requirement <= 1,
        or_(
            Ability.class_restriction.is_(None),
            Ability.class_restriction == character.character_class,
        ),
    )
    equipped_n = CharacterAbility.query.filter_by(
        character_id=character.id, is_equipped=True
    ).count()
    for ab in q.all():
        if CharacterAbility.query.filter_by(
            character_id=character.id, ability_id=ab.id
        ).first():
            continue
        use_equipped = equipped_n < 4
        ca = CharacterAbility(
            character_id=character.id,
            ability_id=ab.id,
            is_equipped=use_equipped,
        )
        db.session.add(ca)
        if use_equipped:
            equipped_n += 1
    db.session.flush()
