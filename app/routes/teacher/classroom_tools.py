"""
Teacher classroom tools: config page, fullscreen display, volume meter APIs.
"""

import logging
from typing import Optional

from flask import jsonify, render_template, request, url_for
from flask_login import current_user, login_required

from app.models import db
from app.models.audit import AuditLog, EventType
from app.models.character import Character
from app.models.classroom import Classroom
from app.models.classroom_tool import ClassroomToolConfig
from app.models.student import Student

from .blueprint import teacher_bp, teacher_required

logger = logging.getLogger(__name__)

TOOL_TYPE_VOLUME = 'volume_meter'

DEFAULT_VOLUME_CONFIG = {
    'threshold': 0.35,
    'breach_duration_seconds': 5,
    'damage_amount': 10,
    'timer_minutes': 15,
    'base_xp_reward': 50,
    'base_gold_reward': 25,
    'breach_cooldown_seconds': 2,
}


def _teacher_owns_classroom(teacher_id: int, classroom_id: int) -> bool:
    return (
        Classroom.query.filter_by(id=classroom_id, teacher_id=teacher_id).first() is not None
    )


def _merge_volume_config(stored: Optional[dict]) -> dict:
    out = dict(DEFAULT_VOLUME_CONFIG)
    if stored:
        for key in DEFAULT_VOLUME_CONFIG:
            if key in stored:
                out[key] = stored[key]
    return out


def _get_or_create_volume_config_row(classroom_id: int) -> ClassroomToolConfig:
    row = ClassroomToolConfig.query.filter_by(
        classroom_id=classroom_id, tool_type=TOOL_TYPE_VOLUME
    ).first()
    if row is None:
        row = ClassroomToolConfig(
            classroom_id=classroom_id,
            tool_type=TOOL_TYPE_VOLUME,
            config_data=dict(DEFAULT_VOLUME_CONFIG),
            is_active=False,
        )
        db.session.add(row)
        db.session.commit()
    return row


@teacher_bp.route('/classroom-tools', methods=['GET'])
@login_required
@teacher_required
def classroom_tools():
    """Sidebar config page for classroom tools."""
    classes = Classroom.query.filter_by(teacher_id=current_user.id, is_active=True).order_by(
        Classroom.name
    ).all()
    return render_template(
        'teacher/classroom_tools.html',
        active_page='classroom_tools',
        classes=classes,
    )


@teacher_bp.route('/classroom-tools/display', methods=['GET'])
@login_required
@teacher_required
def classroom_tools_display():
    """Fullscreen projection view."""
    class_id = request.args.get('class_id', type=int)
    if not class_id:
        return render_template(
            'teacher/classroom_tools_display.html',
            error='Missing class_id. Add ?class_id= to the URL.',
            display_config=None,
            tool_ids=[],
        ), 400
    if not _teacher_owns_classroom(current_user.id, class_id):
        return render_template(
            'teacher/classroom_tools_display.html',
            error='You do not have access to this class.',
            display_config=None,
            tool_ids=[],
        ), 403

    tools_param = (request.args.get('tools') or TOOL_TYPE_VOLUME).strip()
    tool_ids = [t.strip() for t in tools_param.split(',') if t.strip()]
    if not tool_ids:
        tool_ids = [TOOL_TYPE_VOLUME]

    row = _get_or_create_volume_config_row(class_id)
    volume_cfg = _merge_volume_config(row.config_data)

    payload = {
        'class_id': class_id,
        'volume_meter': volume_cfg,
        'csrf_protected_urls': {
            'penalty': url_for('teacher.api_volume_penalty'),
            'reward': url_for('teacher.api_volume_reward'),
        },
    }
    return render_template(
        'teacher/classroom_tools_display.html',
        error=None,
        display_config=payload,
        tool_ids=tool_ids,
        class_id=class_id,
    )


@teacher_bp.route('/api/classroom-tools/config/<int:class_id>', methods=['GET'])
@login_required
@teacher_required
def api_classroom_tools_config(class_id):
    if not _teacher_owns_classroom(current_user.id, class_id):
        return jsonify({'error': 'Permission denied'}), 403
    row = _get_or_create_volume_config_row(class_id)
    return jsonify(
        {
            'tool_type': TOOL_TYPE_VOLUME,
            'config': _merge_volume_config(row.config_data),
            'is_active': row.is_active,
        }
    )


@teacher_bp.route('/api/classroom-tools/config/<int:class_id>', methods=['POST'])
@login_required
@teacher_required
def api_classroom_tools_config_save(class_id):
    if not _teacher_owns_classroom(current_user.id, class_id):
        return jsonify({'error': 'Permission denied'}), 403
    data = request.get_json() or {}
    cfg_in = data.get('config') or data
    merged = _merge_volume_config(cfg_in if isinstance(cfg_in, dict) else {})

    # Coerce / clamp
    merged['threshold'] = max(0.05, min(0.95, float(merged['threshold'])))
    merged['breach_duration_seconds'] = max(1, min(60, int(merged['breach_duration_seconds'])))
    merged['damage_amount'] = max(1, min(500, int(merged['damage_amount'])))
    merged['timer_minutes'] = max(1, min(120, int(merged['timer_minutes'])))
    merged['base_xp_reward'] = max(0, min(100_000, int(merged['base_xp_reward'])))
    merged['base_gold_reward'] = max(0, min(100_000, int(merged['base_gold_reward'])))
    merged['breach_cooldown_seconds'] = max(0, min(30, int(merged['breach_cooldown_seconds'])))

    row = _get_or_create_volume_config_row(class_id)
    row.config_data = merged
    if 'is_active' in data:
        row.is_active = bool(data['is_active'])
    db.session.add(row)
    db.session.commit()
    return jsonify({'success': True, 'config': merged})


@teacher_bp.route('/api/classroom-tools/volume/penalty', methods=['POST'])
@login_required
@teacher_required
def api_volume_penalty():
    """Apply damage to all active characters in the class."""
    data = request.get_json() or {}
    class_id = data.get('class_id')
    damage_amount = data.get('damage_amount')
    if class_id is None or damage_amount is None:
        return jsonify({'error': 'class_id and damage_amount required'}), 400
    try:
        class_id = int(class_id)
        damage_amount = int(damage_amount)
    except (TypeError, ValueError):
        return jsonify({'error': 'Invalid class_id or damage_amount'}), 400
    if damage_amount < 1 or damage_amount > 500:
        return jsonify({'error': 'damage_amount out of range'}), 400
    if not _teacher_owns_classroom(current_user.id, class_id):
        return jsonify({'error': 'Permission denied'}), 403

    students = Student.query.filter_by(class_id=class_id, status='active').all()
    affected = []
    for student in students:
        character = Character.query.filter_by(student_id=student.id, is_active=True).first()
        if not character:
            continue
        character.take_damage(damage_amount)
        affected.append(character.id)

    AuditLog.log_event(
        EventType.TOOL_PENALTY,
        user_id=current_user.id,
        character_id=None,
        event_data={
            'tool': TOOL_TYPE_VOLUME,
            'classroom_id': class_id,
            'damage_amount': damage_amount,
            'affected_character_ids': affected,
            'count': len(affected),
        },
        ip_address=request.remote_addr,
    )
    return jsonify({'success': True, 'affected_count': len(affected), 'character_ids': affected})


@teacher_bp.route('/api/classroom-tools/volume/reward', methods=['POST'])
@login_required
@teacher_required
def api_volume_reward():
    """Award XP and gold to all active characters (amounts already include client multiplier)."""
    data = request.get_json() or {}
    class_id = data.get('class_id')
    xp_amount = data.get('xp_amount')
    gold_amount = data.get('gold_amount')
    reward_multiplier = data.get('reward_multiplier', 1.0)

    if class_id is None or xp_amount is None or gold_amount is None:
        return jsonify({'error': 'class_id, xp_amount, and gold_amount required'}), 400
    try:
        class_id = int(class_id)
        xp_amount = int(xp_amount)
        gold_amount = int(gold_amount)
    except (TypeError, ValueError):
        return jsonify({'error': 'Invalid numeric fields'}), 400
    if xp_amount < 0 or gold_amount < 0 or xp_amount > 100_000 or gold_amount > 100_000:
        return jsonify({'error': 'Reward amounts out of range'}), 400
    if not _teacher_owns_classroom(current_user.id, class_id):
        return jsonify({'error': 'Permission denied'}), 403

    students = Student.query.filter_by(class_id=class_id, status='active').all()
    rewarded = []
    for student in students:
        character = Character.query.filter_by(student_id=student.id, is_active=True).first()
        if not character:
            continue
        if gold_amount > 0:
            character.gold += gold_amount
        if xp_amount > 0:
            character.gain_experience(xp_amount)
        character.save()
        rewarded.append(character.id)

    AuditLog.log_event(
        EventType.TOOL_REWARD,
        user_id=current_user.id,
        character_id=None,
        event_data={
            'tool': TOOL_TYPE_VOLUME,
            'classroom_id': class_id,
            'xp_per_character': xp_amount,
            'gold_per_character': gold_amount,
            'reward_multiplier': reward_multiplier,
            'rewarded_character_ids': rewarded,
            'count': len(rewarded),
        },
        ip_address=request.remote_addr,
    )
    return jsonify({'success': True, 'rewarded_count': len(rewarded), 'character_ids': rewarded})
