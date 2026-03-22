"""Tests for powers: learn rules, regen, targeting, effects, and HTTP routes."""
import uuid
from datetime import datetime, timedelta

import pytest

from app.models import db
from app.models.ability import Ability, AbilityType, CharacterAbility
from app.models.audit import AuditLog, EventType
from app.models.character import Character
from app.models.classroom import Classroom
from app.models.student import Student
from app.models.user import User, UserRole
from app.services.abilities import execute_ability_effect
from app.services.powers import (
    character_can_learn_power,
    grant_starter_powers,
    learn_power,
    resolve_power_targets,
)


def _make_teacher_student_character(db_session):
    """Teacher, classroom, student user, student row, warrior character with PP."""
    suf = uuid.uuid4().hex[:8]
    teacher = User(
        username=f'tpow_t_{suf}',
        email=f'tpow_t_{suf}@test.com',
        role=UserRole.TEACHER,
    )
    teacher.set_password('testpass')
    db_session.add(teacher)
    db_session.flush()
    classroom = Classroom(
        name=f'Class {suf}',
        teacher_id=teacher.id,
        join_code=f'PC{suf[:4]}',
    )
    db_session.add(classroom)
    db_session.flush()
    stu_user = User(
        username=f'tpow_s_{suf}',
        email=f'tpow_s_{suf}@test.com',
        role=UserRole.STUDENT,
    )
    stu_user.set_password('testpass')
    db_session.add(stu_user)
    db_session.flush()
    student = Student(user_id=stu_user.id, class_id=classroom.id, level=1, gold=500)
    db_session.add(student)
    db_session.flush()
    character = Character(
        name='PowHero',
        student_id=student.id,
        character_class='Warrior',
        level=3,
        power_points=5,
        power=10,
        max_power=10,
        health=100,
        max_health=100,
        defense=5,
        is_active=True,
    )
    db_session.add(character)
    db_session.flush()
    return {
        'teacher': teacher,
        'classroom': classroom,
        'stu_user': stu_user,
        'student': student,
        'character': character,
        'suf': suf,
    }


def _make_power(**kwargs):
    defaults = dict(
        name=f"P_{uuid.uuid4().hex[:6]}",
        type='heal',
        power=10,
        cooldown=0,
        duration=1,
        tier='basic',
        level_requirement=1,
        pp_cost=1,
        target_type='self',
        cost=0,
        is_default=True,
        class_restriction=None,
    )
    defaults.update(kwargs)
    ab = Ability(**defaults)
    db.session.add(ab)
    db.session.flush()
    return ab


@pytest.fixture
def powers_ctx(db_session):
    return _make_teacher_student_character(db_session)


# --- learn_power / character_can_learn_power ---


def test_learn_power_success_and_audit(db_session, powers_ctx):
    ch = powers_ctx['character']
    ab = _make_power(name='LearnMe', pp_cost=2)
    before_pp = ch.power_points
    res = learn_power(ch, ab, user_id=powers_ctx['stu_user'].id, ip_address='127.0.0.1')
    assert res['success'] is True
    db_session.commit()
    assert ch.power_points == before_pp - 2
    assert CharacterAbility.query.filter_by(character_id=ch.id, ability_id=ab.id).first()
    log = AuditLog.query.filter_by(event_type=EventType.POWER_LEARNED.value).first()
    assert log is not None
    assert log.event_data.get('ability_id') == ab.id
    assert log.event_data.get('pp_spent') == 2


def test_learn_power_insufficient_pp(db_session, powers_ctx):
    ch = powers_ctx['character']
    ch.power_points = 0
    db_session.commit()
    ab = _make_power(pp_cost=1)
    res = learn_power(ch, ab)
    assert res['success'] is False
    assert 'Power Points' in res['message']


def test_learn_power_wrong_class(db_session, powers_ctx):
    ch = powers_ctx['character']
    ab = _make_power(class_restriction='Sorcerer', name='SorcOnly')
    ok, reason = character_can_learn_power(ch, ab)
    assert ok is False
    assert 'Sorcerer' in reason


def test_learn_power_prerequisite(db_session, powers_ctx):
    ch = powers_ctx['character']
    base = _make_power(name='BasePrq')
    adv = _make_power(name='AdvPrq', prerequisite_id=base.id, pp_cost=1)
    ch.power_points = 5
    db_session.commit()
    ok, reason = character_can_learn_power(ch, adv)
    assert ok is False
    assert 'prerequisite' in reason.lower()
    learn_power(ch, base)
    db_session.commit()
    ok2, _ = character_can_learn_power(ch, adv)
    assert ok2 is True


def test_learn_power_already_known(db_session, powers_ctx):
    ch = powers_ctx['character']
    ab = _make_power()
    learn_power(ch, ab)
    db_session.commit()
    res = learn_power(ch, ab)
    assert res['success'] is False


# --- regenerate_power ---


def test_regenerate_power_no_change_within_hour(db_session, powers_ctx):
    ch = powers_ctx['character']
    ch.power = 5
    ch.max_power = 10
    now = datetime(2026, 1, 1, 12, 0, 0)
    ch.last_power_regen = now
    db_session.commit()
    ch.regenerate_power(now=now + timedelta(minutes=30))
    assert ch.power == 5


def test_regenerate_power_one_hour(db_session, powers_ctx):
    ch = powers_ctx['character']
    ch.power = 5
    ch.max_power = 10
    now = datetime(2026, 1, 1, 12, 0, 0)
    ch.last_power_regen = now
    db_session.commit()
    ch.regenerate_power(now=now + timedelta(hours=1))
    assert ch.power == 6
    assert ch.last_power_regen == now + timedelta(hours=1)


def test_regenerate_power_caps_at_max(db_session, powers_ctx):
    ch = powers_ctx['character']
    ch.power = 9
    ch.max_power = 10
    now = datetime(2026, 1, 1, 12, 0, 0)
    ch.last_power_regen = now
    db_session.commit()
    ch.regenerate_power(now=now + timedelta(hours=5))
    assert ch.power == 10


# --- resolve_power_targets ---


def test_resolve_self_target(db_session, powers_ctx):
    ch = powers_ctx['character']
    ab = _make_power(target_type='self')
    assert resolve_power_targets(ch, ab, ch.id) == [ch]


def test_resolve_self_wrong_target(db_session, powers_ctx):
    ch = powers_ctx['character']
    ab = _make_power(target_type='self')
    with pytest.raises(ValueError, match='yourself'):
        resolve_power_targets(ch, ab, 99999)


def test_resolve_single_ally_clanmate(db_session, powers_ctx):
    from app.models.clan import Clan

    ctx = powers_ctx
    ch = ctx['character']
    clan = Clan(name='PowClan', class_id=ctx['classroom'].id)
    db.session.add(clan)
    db.session.flush()
    ch.clan_id = clan.id
    ally = Character(
        name='Ally',
        student_id=ctx['student'].id,
        character_class='Warrior',
        clan_id=clan.id,
        is_active=False,
    )
    db.session.add(ally)
    db.session.flush()
    ab = _make_power(target_type='single_ally')
    targets = resolve_power_targets(ch, ab, ally.id)
    assert len(targets) == 1
    assert targets[0].id == ally.id


def test_resolve_all_allies_requires_clan(db_session, powers_ctx):
    ch = powers_ctx['character']
    ch.clan_id = None
    db_session.commit()
    ab = _make_power(target_type='all_allies')
    with pytest.raises(ValueError, match='clan'):
        resolve_power_targets(ch, ab, ch.id)


def test_resolve_unsupported_target_type(db_session, powers_ctx):
    ch = powers_ctx['character']
    ab = _make_power(target_type='all_enemies')
    with pytest.raises(ValueError, match='not supported'):
        resolve_power_targets(ch, ab, 1)


# --- execute_ability_effect ---


def test_execute_heal_basic(db_session, powers_ctx):
    ch = powers_ctx['character']
    ch.health = 50
    ab = _make_power(type='heal', power=20, special_effect=None)
    res = execute_ability_effect(ch, ab, ch)
    assert res['success'] is True
    assert ch.health == 70


def test_execute_attack(db_session, powers_ctx):
    caster = powers_ctx['character']
    target = Character(
        name='Victim',
        student_id=powers_ctx['student'].id,
        character_class='Warrior',
        health=100,
        max_health=100,
        defense=0,
        is_active=False,
    )
    db.session.add(target)
    db.session.flush()
    ab = _make_power(type='attack', power=15)
    res = execute_ability_effect(caster, ab, target)
    assert res['success'] is True
    assert target.health < 100


def test_execute_utility_restore_power_full(db_session, powers_ctx):
    ch = powers_ctx['character']
    ch.power = 2
    ch.max_power = 10
    ab = _make_power(type='utility', special_effect='restore_power_full')
    res = execute_ability_effect(ch, ab, ch)
    assert res['success'] is True
    assert res['amount'] == 8  # delta restored, not max_power
    assert ch.power == 10


def test_execute_utility_restore_power_full_already_full(db_session, powers_ctx):
    ch = powers_ctx['character']
    ch.power = 10
    ch.max_power = 10
    ab = _make_power(type='utility', special_effect='restore_power_full')
    res = execute_ability_effect(ch, ab, ch)
    assert res['success'] is False
    assert res['amount'] == 0
    assert ch.power == 10


def test_execute_revive(db_session, powers_ctx):
    caster = powers_ctx['character']
    target = Character(
        name='Down',
        student_id=powers_ctx['student'].id,
        character_class='Warrior',
        health=0,
        max_health=100,
        is_active=False,
    )
    db.session.add(target)
    db.session.flush()
    ab = _make_power(type='heal', special_effect='revive')
    res = execute_ability_effect(caster, ab, target)
    assert res['success'] is True
    assert target.health == 1


# --- grant_starter_powers ---


def test_grant_starter_powers_warrior(db_session, powers_ctx):
    ch = powers_ctx['character']
    _make_power(name='WarBasic', tier='basic', level_requirement=1, class_restriction='Warrior')
    _make_power(name='Universal', tier='basic', level_requirement=1, class_restriction=None)
    _make_power(name='SorcBasic', tier='basic', level_requirement=1, class_restriction='Sorcerer')
    db_session.commit()
    grant_starter_powers(ch)
    db_session.commit()
    names = {ca.ability.name for ca in ch.abilities.all()}
    assert 'WarBasic' in names
    assert 'Universal' in names
    assert 'SorcBasic' not in names


# --- HTTP routes ---


def test_student_powers_learn_route(client, db_session, powers_ctx):
    ctx = powers_ctx
    ab = _make_power(name='HttpLearn')
    db_session.commit()
    client.post(
        '/auth/login',
        data={'username': ctx['stu_user'].username, 'password': 'testpass'},
    )
    res = client.post(
        '/student/powers/learn',
        json={'ability_id': ab.id},
        content_type='application/json',
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data['success'] is True


def test_student_powers_equip_route(client, db_session, powers_ctx):
    ctx = powers_ctx
    ab = _make_power(name='HttpEquip')
    ch = ctx['character']
    ca = CharacterAbility(character_id=ch.id, ability_id=ab.id, is_equipped=False)
    db.session.add(ca)
    db_session.commit()
    client.post(
        '/auth/login',
        data={'username': ctx['stu_user'].username, 'password': 'testpass'},
    )
    res = client.post(
        '/student/powers/equip',
        json={'ability_id': ab.id, 'action': 'equip'},
        content_type='application/json',
    )
    assert res.status_code == 200
    assert res.get_json()['success'] is True
    db_session.refresh(ca)
    assert ca.is_equipped is True


def test_shop_buy_rejects_ability(client, db_session, powers_ctx):
    ctx = powers_ctx
    from app.models.equipment import Equipment

    eq = Equipment(name='GoldItem', type='weapon', slot='main_hand', cost=50)
    db.session.add(eq)
    ab = _make_power(name='NotForSale', cost=100)
    ctx['character'].gold = 1000
    db_session.commit()
    client.post(
        '/auth/login',
        data={'username': ctx['stu_user'].username, 'password': 'testpass'},
    )
    res = client.post(
        '/student/shop/buy',
        json={'item_id': ab.id, 'item_type': 'ability'},
        content_type='application/json',
    )
    assert res.status_code == 400
    assert 'Powers' in res.get_json().get('message', '')
    res2 = client.post(
        '/student/shop/buy',
        json={'item_id': eq.id, 'item_type': 'equipment'},
        content_type='application/json',
    )
    assert res2.status_code == 200
    assert res2.get_json()['success'] is True


def test_teacher_powers_manage_get(client, db_session, powers_ctx):
    ctx = powers_ctx
    client.post(
        '/auth/login',
        data={'username': ctx['teacher'].username, 'password': 'testpass'},
    )
    res = client.get('/teacher/powers')
    assert res.status_code == 200


def test_teacher_powers_create_edit_delete(client, db_session, powers_ctx):
    ctx = powers_ctx
    client.post(
        '/auth/login',
        data={'username': ctx['teacher'].username, 'password': 'testpass'},
    )
    res = client.post(
        '/teacher/powers/create',
        json={
            'name': 'Custom Zap',
            'description': 'zap',
            'type': 'utility',
            'tier': 'basic',
            'target_type': 'self',
            'level_requirement': 1,
            'power': 0,
            'cost': 1,
            'pp_cost': 1,
            'cooldown': 0,
            'duration': 1,
        },
        content_type='application/json',
    )
    assert res.status_code == 200
    pid = res.get_json()['id']
    res2 = client.post(
        f'/teacher/powers/{pid}/edit',
        json={'name': 'Custom Zap 2'},
        content_type='application/json',
    )
    assert res2.status_code == 200
    res3 = client.post(f'/teacher/powers/{pid}/delete')
    assert res3.status_code == 200
