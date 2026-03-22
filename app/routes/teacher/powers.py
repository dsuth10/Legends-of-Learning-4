"""
Teacher CRUD for custom powers (per teacher account; visible to their classes' students).
"""

from flask import jsonify, render_template, request
from flask_login import current_user, login_required

from app.models import db
from app.models.ability import Ability, AbilityType, CharacterAbility

from .blueprint import teacher_bp, teacher_required


@teacher_bp.route('/powers', methods=['GET'])
@login_required
@teacher_required
def powers_manage():
    defaults = Ability.query.filter_by(is_default=True).order_by(
        Ability.class_restriction, Ability.tier, Ability.level_requirement, Ability.name
    ).all()
    custom = Ability.query.filter_by(created_by_teacher_id=current_user.id).order_by(
        Ability.updated_at.desc()
    ).all()
    return render_template(
        'teacher/powers.html',
        active_page='powers',
        default_powers=defaults,
        custom_powers=custom,
    )


@teacher_bp.route('/powers/create', methods=['POST'])
@login_required
@teacher_required
def powers_create():
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()[:64]
    description = (data.get('description') or '').strip() or 'Custom power'
    type_str = (data.get('type') or 'utility').strip().lower()
    class_restriction = data.get('class_restriction')
    if class_restriction:
        class_restriction = str(class_restriction).strip()[:32] or None
    tier = (data.get('tier') or 'basic').strip().lower()[:16]
    if tier not in ('basic', 'advanced', 'elite'):
        tier = 'basic'
    target_type = (data.get('target_type') or 'self').strip().lower()[:32]
    if target_type not in ('self', 'single_ally', 'all_allies', 'single_enemy'):
        target_type = 'self'
    try:
        level_requirement = max(1, int(data.get('level_requirement', 1)))
    except (TypeError, ValueError):
        level_requirement = 1
    try:
        power = int(data.get('power', 0))
    except (TypeError, ValueError):
        power = 0
    try:
        cost = max(0, int(data.get('cost', 1)))
    except (TypeError, ValueError):
        cost = 1
    try:
        pp_cost = max(1, int(data.get('pp_cost', 1)))
    except (TypeError, ValueError):
        pp_cost = 1
    try:
        cooldown = max(0, int(data.get('cooldown', 0)))
    except (TypeError, ValueError):
        cooldown = 0
    try:
        duration = max(1, int(data.get('duration', 1)))
    except (TypeError, ValueError):
        duration = 1

    if not name:
        return jsonify({'success': False, 'message': 'Name is required.'}), 400

    try:
        AbilityType(type_str)
    except ValueError:
        return jsonify({'success': False, 'message': 'Invalid power type.'}), 400

    ab = Ability(
        name=name,
        type=type_str,
        description=description,
        level_requirement=level_requirement,
        power=power,
        cost=cost,
        cooldown=cooldown,
        duration=duration,
        tier=tier,
        class_restriction=class_restriction,
        target_type=target_type,
        pp_cost=pp_cost,
        is_default=False,
        created_by_teacher_id=current_user.id,
        prerequisite_id=None,
        special_effect=(data.get('special_effect') or None),
    )
    db.session.add(ab)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Power created.', 'id': ab.id})


@teacher_bp.route('/powers/<int:power_id>/edit', methods=['PUT', 'POST'])
@login_required
@teacher_required
def powers_edit(power_id):
    ab = Ability.query.get_or_404(power_id)
    if ab.is_default or ab.created_by_teacher_id != current_user.id:
        return jsonify({'success': False, 'message': 'You cannot edit this power.'}), 403

    data = request.get_json() or {}
    if 'name' in data:
        name = (data.get('name') or '').strip()[:64]
        if name:
            ab.name = name
    if 'description' in data:
        ab.description = (data.get('description') or '').strip() or ab.description
    if 'type' in data:
        type_str = str(data.get('type')).strip().lower()
        try:
            AbilityType(type_str)
            ab.type = type_str
        except ValueError:
            return jsonify({'success': False, 'message': 'Invalid type.'}), 400
    if 'class_restriction' in data:
        cr = data.get('class_restriction')
        ab.class_restriction = (str(cr).strip()[:32] if cr else None) or None
    if 'tier' in data:
        tier = str(data.get('tier')).strip().lower()
        if tier in ('basic', 'advanced', 'elite'):
            ab.tier = tier
    if 'target_type' in data:
        tt = str(data.get('target_type')).strip().lower()
        if tt in ('self', 'single_ally', 'all_allies', 'single_enemy'):
            ab.target_type = tt
    for key, attr, min_val in [
        ('level_requirement', 'level_requirement', 1),
        ('power', 'power', 0),
        ('cost', 'cost', 0),
        ('pp_cost', 'pp_cost', 1),
        ('cooldown', 'cooldown', 0),
        ('duration', 'duration', 1),
    ]:
        if key in data:
            try:
                val = max(min_val, int(data[key]))
                setattr(ab, attr, val)
            except (TypeError, ValueError):
                pass
    if 'special_effect' in data:
        ab.special_effect = data.get('special_effect') or None

    db.session.commit()
    return jsonify({'success': True, 'message': 'Power updated.'})


@teacher_bp.route('/powers/<int:power_id>/delete', methods=['DELETE', 'POST'])
@login_required
@teacher_required
def powers_delete(power_id):
    ab = Ability.query.get_or_404(power_id)
    if ab.is_default or ab.created_by_teacher_id != current_user.id:
        return jsonify({'success': False, 'message': 'You cannot delete this power.'}), 403

    if CharacterAbility.query.filter_by(ability_id=ab.id).first():
        return jsonify(
            {
                'success': False,
                'message': 'Students have learned this power; it cannot be deleted.',
            }
        ), 400

    db.session.delete(ab)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Power deleted.'})
