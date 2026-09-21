"""Audio meter targeting: tier formula, sessions, and teacher APIs."""

from datetime import timedelta
import uuid

import pytest

from app.models.audit import AuditLog
from app.models.audio_meter import AudioMeterSession
from app.models.behavior import BehaviorIncident
from app.models.character import Character
from app.models.clan import Clan
from app.models.classroom import Classroom
from app.models.student import Student
from app.models.user import User, UserRole
from app.services.audio_meter import tier_amount
from app.utils.date_utils import get_utc_now

TEACHER_PASSWORD = "password123"


@pytest.fixture
def teacher(db_session):
    unique = uuid.uuid4().hex[:8]
    user = User(
        username=f"am_teacher_{unique}",
        email=f"am_teacher_{unique}@example.com",
        role=UserRole.TEACHER,
    )
    user.set_password(TEACHER_PASSWORD)
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def other_teacher(db_session):
    unique = uuid.uuid4().hex[:8]
    user = User(
        username=f"am_other_{unique}",
        email=f"am_other_{unique}@example.com",
        role=UserRole.TEACHER,
    )
    user.set_password(TEACHER_PASSWORD)
    db_session.add(user)
    db_session.commit()
    return user


def _make_student(db_session, classroom, first_name):
    unique = uuid.uuid4().hex[:8]
    user = User(
        username=f"{first_name.lower()}_{unique}",
        email=f"{first_name.lower()}_{unique}@example.com",
        role=UserRole.STUDENT,
        first_name=first_name,
        last_name="T",
    )
    user.set_password("password")
    db_session.add(user)
    db_session.flush()
    student = Student(user_id=user.id, class_id=classroom.id, gold=0)
    db_session.add(student)
    db_session.commit()
    return student


def _make_character(db_session, student, name, clan_id=None, xp=0, gold=0, health=100):
    character = Character(
        name=name,
        student_id=student.id,
        character_class="Warrior",
        level=1,
        experience=xp,
        health=health,
        max_health=100,
        power=10,
        max_power=10,
        power_points=0,
        defense=10,
        gold=gold,
        is_active=True,
        clan_id=clan_id,
    )
    db_session.add(character)
    db_session.commit()
    return character


@pytest.fixture
def classroom(db_session, teacher):
    unique = uuid.uuid4().hex[:5]
    room = Classroom(
        name="Year 5 Audio",
        teacher_id=teacher.id,
        join_code=f"A{unique}",
    )
    db_session.add(room)
    db_session.commit()
    return room


@pytest.fixture
def roster(db_session, classroom):
    clan_a = Clan(name="Team Oak", class_id=classroom.id)
    clan_b = Clan(name="Team Ash", class_id=classroom.id)
    db_session.add_all([clan_a, clan_b])
    db_session.commit()

    oak_s1 = _make_student(db_session, classroom, "Ada")
    oak_s2 = _make_student(db_session, classroom, "Cora")
    ash_s1 = _make_student(db_session, classroom, "Ben")
    none_s1 = _make_student(db_session, classroom, "Dee")
    skip_s1 = _make_student(db_session, classroom, "Eli")

    oak_c1 = _make_character(db_session, oak_s1, "Ada the Druid", clan_a.id, xp=10, gold=20)
    oak_c2 = _make_character(db_session, oak_s2, "Cora", clan_a.id, xp=10, gold=20)
    ash_c1 = _make_character(db_session, ash_s1, "Ben", clan_b.id, xp=10, gold=20)
    none_c1 = _make_character(db_session, none_s1, "Dee", None, xp=10, gold=20)

    return {
        "clan_a": clan_a,
        "clan_b": clan_b,
        "oak_s1": oak_s1,
        "oak_s2": oak_s2,
        "ash_s1": ash_s1,
        "none_s1": none_s1,
        "skip_s1": skip_s1,
        "oak_c1": oak_c1,
        "oak_c2": oak_c2,
        "ash_c1": ash_c1,
        "none_c1": none_c1,
    }


def login(client, username, password=TEACHER_PASSWORD):
    return client.post(
        "/auth/login",
        data={"username": username, "password": password},
        follow_redirects=True,
    )


def _save_config(client, class_id, **overrides):
    cfg = {
        "threshold": 0.35,
        "breach_duration_seconds": 5,
        "breach_cooldown_seconds": 2,
        "damage_amount": 10,
        "timer_minutes": 1,
        "base_xp_reward": 1000,
        "base_gold_reward": 100,
        "hp_damage_enabled": False,
    }
    cfg.update(overrides)
    return client.post(
        f"/teacher/api/classroom-tools/config/{class_id}",
        json={"config": cfg},
    )


def _start(client, class_id, payload):
    return client.post(
        f"/teacher/api/classroom-tools/{class_id}/audio-meter/sessions",
        json=payload,
    )


def _expire(db_session, session_id):
    session = db_session.get(AudioMeterSession, session_id)
    session.started_at = get_utc_now() - timedelta(seconds=session.timer_seconds + 30)
    db_session.commit()


def _complete(client, class_id, session_id, body=None):
    return client.post(
        f"/teacher/api/classroom-tools/{class_id}/audio-meter/sessions/{session_id}/complete",
        json=body or {},
    )


def _trigger(client, class_id, session_id, level=0.6):
    return client.post(
        f"/teacher/api/classroom-tools/{class_id}/audio-meter/sessions/{session_id}/trigger",
        json={"level": level},
    )


def _reload(db_session, character):
    db_session.refresh(character)
    return character


def test_tier_amount_table():
    assert [tier_amount(1000, n) for n in range(4)] == [1000, 500, 250, 125]
    assert [tier_amount(100, n) for n in range(4)] == [100, 50, 25, 13]
    assert tier_amount(1, 20) == 1
    assert tier_amount(0, 3) == 0


def test_targets_and_whole_class_award(client, db_session, teacher, classroom, roster):
    login(client, teacher.username)
    _save_config(client, classroom.id)
    targets = client.get(f"/teacher/api/classroom-tools/{classroom.id}/targets")
    assert targets.status_code == 200
    body = targets.get_json()
    assert body["success"] is True
    assert body["data"]["classroom"]["active_character_count"] == 4
    skip = next(s for s in body["data"]["students"] if s["id"] == roster["skip_s1"].id)
    assert skip["character_id"] is None

    started = _start(client, classroom.id, {"target_type": "class"})
    assert started.status_code == 201
    session = started.get_json()["data"]["session"]
    assert session["participant_count"] == 4
    assert roster["skip_s1"].id in session["skipped_student_ids"]
    _expire(db_session, session["id"])
    done = _complete(client, classroom.id, session["id"])
    assert done.status_code == 200
    data = done.get_json()["data"]
    assert data["xp_awarded_each"] == 1000
    assert data["gold_awarded_each"] == 100
    assert data["rewarded_count"] == 4


def test_clan_only_leaves_others_unchanged(client, db_session, teacher, classroom, roster):
    login(client, teacher.username)
    _save_config(client, classroom.id)
    started = _start(
        client,
        classroom.id,
        {"target_type": "custom", "clan_ids": [roster["clan_a"].id]},
    )
    session_id = started.get_json()["data"]["session"]["id"]
    _expire(db_session, session_id)
    _complete(client, classroom.id, session_id)

    oak = _reload(db_session, roster["oak_c1"])
    ash = _reload(db_session, roster["ash_c1"])
    none = _reload(db_session, roster["none_c1"])
    assert oak.experience == 1010
    assert oak.gold == 120
    assert ash.experience == 10
    assert ash.gold == 20
    assert none.experience == 10


def test_two_students_and_overlap_awards_once(client, db_session, teacher, classroom, roster):
    login(client, teacher.username)
    _save_config(client, classroom.id)
    started = _start(
        client,
        classroom.id,
        {
            "target_type": "custom",
            "clan_ids": [roster["clan_a"].id],
            "student_ids": [roster["oak_s1"].id, roster["ash_s1"].id],
        },
    )
    payload = started.get_json()["data"]["session"]
    ids = set(
        db_session.get(AudioMeterSession, payload["id"]).participant_character_ids
    )
    assert roster["oak_c1"].id in ids
    assert roster["ash_c1"].id in ids
    assert len(ids) == 3
    _expire(db_session, payload["id"])
    _complete(client, classroom.id, payload["id"])
    oak = _reload(db_session, roster["oak_c1"])
    assert oak.experience == 1010


def test_skip_student_without_character(client, db_session, teacher, classroom, roster):
    login(client, teacher.username)
    _save_config(client, classroom.id)
    started = _start(
        client,
        classroom.id,
        {
            "target_type": "custom",
            "student_ids": [roster["oak_s1"].id, roster["skip_s1"].id],
        },
    )
    session = started.get_json()["data"]["session"]
    assert session["participant_count"] == 1
    assert roster["skip_s1"].id in session["skipped_student_ids"]


def test_foreign_ids_and_no_participants_and_forbidden(
    client, db_session, teacher, other_teacher, classroom, roster
):
    login(client, teacher.username)
    _save_config(client, classroom.id)
    foreign_clan = _start(
        client, classroom.id, {"target_type": "custom", "clan_ids": [999999]}
    )
    assert foreign_clan.status_code == 400
    assert foreign_clan.get_json()["code"] == "VALIDATION_ERROR"
    assert AudioMeterSession.query.count() == 0

    empty = _start(
        client,
        classroom.id,
        {"target_type": "custom", "student_ids": [roster["skip_s1"].id]},
    )
    assert empty.status_code == 400
    assert empty.get_json()["code"] == "NO_PARTICIPANTS"

    client.get("/auth/logout")
    login(client, other_teacher.username)
    denied = _start(client, classroom.id, {"target_type": "class"})
    assert denied.status_code == 403


def test_two_and_three_triggers_award_ceiling(client, db_session, teacher, classroom, roster):
    login(client, teacher.username)
    _save_config(client, classroom.id)
    started = _start(
        client,
        classroom.id,
        {"target_type": "custom", "student_ids": [roster["oak_s1"].id]},
    )
    session_id = started.get_json()["data"]["session"]["id"]
    t1 = _trigger(client, classroom.id, session_id)
    t2 = _trigger(client, classroom.id, session_id)
    assert t2.get_json()["data"]["potential_xp"] == 250
    assert t2.get_json()["data"]["potential_gold"] == 25
    _expire(db_session, session_id)
    done = _complete(client, classroom.id, session_id)
    data = done.get_json()["data"]
    assert data["xp_awarded_each"] == 250
    assert data["gold_awarded_each"] == 25
    oak = _reload(db_session, roster["oak_c1"])
    assert oak.experience == 260
    assert oak.gold == 45

    started = _start(
        client,
        classroom.id,
        {"target_type": "custom", "student_ids": [roster["oak_s2"].id]},
    )
    session_id = started.get_json()["data"]["session"]["id"]
    for _ in range(3):
        _trigger(client, classroom.id, session_id)
    _expire(db_session, session_id)
    done = _complete(client, classroom.id, session_id)
    data = done.get_json()["data"]
    assert data["xp_awarded_each"] == 125
    assert data["gold_awarded_each"] == 13


def test_hp_optional_and_no_behavior_incident(client, db_session, teacher, classroom, roster):
    login(client, teacher.username)
    _save_config(client, classroom.id, hp_damage_enabled=False)
    started = _start(
        client,
        classroom.id,
        {"target_type": "custom", "student_ids": [roster["oak_s1"].id]},
    )
    session_id = started.get_json()["data"]["session"]["id"]
    trig = _trigger(client, classroom.id, session_id)
    assert trig.get_json()["data"]["hp_damage_applied"] is False
    oak = _reload(db_session, roster["oak_c1"])
    ash = _reload(db_session, roster["ash_c1"])
    assert oak.health == 100
    assert ash.health == 100

    _save_config(client, classroom.id, hp_damage_enabled=True, damage_amount=10)
    started = _start(
        client,
        classroom.id,
        {"target_type": "custom", "student_ids": [roster["oak_s1"].id]},
    )
    session_id = started.get_json()["data"]["session"]["id"]
    trig = _trigger(client, classroom.id, session_id)
    data = trig.get_json()["data"]
    assert data["hp_damage_applied"] is True
    assert roster["oak_c1"].id in data["damaged_character_ids"]
    oak = _reload(db_session, roster["oak_c1"])
    ash = _reload(db_session, roster["ash_c1"])
    assert oak.health == 90
    assert ash.health == 100
    assert BehaviorIncident.query.count() == 0


def test_complete_guards_and_tamper_payload(client, db_session, teacher, classroom, roster):
    login(client, teacher.username)
    _save_config(client, classroom.id)
    started = _start(
        client,
        classroom.id,
        {"target_type": "custom", "student_ids": [roster["oak_s1"].id]},
    )
    session_id = started.get_json()["data"]["session"]["id"]
    early = _complete(client, classroom.id, session_id)
    assert early.status_code == 409
    oak = _reload(db_session, roster["oak_c1"])
    assert oak.experience == 10

    _expire(db_session, session_id)
    done = _complete(
        client,
        classroom.id,
        session_id,
        {"xp_amount": 100000, "gold_amount": 100000, "paused_ms": 0},
    )
    assert done.status_code == 200
    data = done.get_json()["data"]
    assert data["xp_awarded_each"] == 1000
    oak = _reload(db_session, roster["oak_c1"])
    assert oak.experience == 1010

    again = _complete(client, classroom.id, session_id)
    assert again.status_code == 409


def test_abandon_then_complete_and_supersede(client, db_session, teacher, classroom, roster):
    login(client, teacher.username)
    _save_config(client, classroom.id)
    first = _start(
        client,
        classroom.id,
        {"target_type": "custom", "student_ids": [roster["oak_s1"].id]},
    )
    first_id = first.get_json()["data"]["session"]["id"]
    abandoned = client.delete(
        f"/teacher/api/classroom-tools/{classroom.id}/audio-meter/sessions/{first_id}"
    )
    assert abandoned.status_code == 200
    _expire(db_session, first_id)
    late = _complete(client, classroom.id, first_id)
    assert late.status_code == 409
    oak = _reload(db_session, roster["oak_c1"])
    assert oak.experience == 10

    second = _start(
        client,
        classroom.id,
        {"target_type": "custom", "student_ids": [roster["oak_s1"].id]},
    )
    third = _start(
        client,
        classroom.id,
        {"target_type": "custom", "student_ids": [roster["oak_s1"].id]},
    )
    assert third.get_json()["data"]["superseded_session_id"] == second.get_json()["data"]["session"]["id"]
    stale = db_session.get(AudioMeterSession, second.get_json()["data"]["session"]["id"])
    assert stale.status == "abandoned"


def test_audit_description_after_triggers(client, db_session, teacher, classroom, roster):
    login(client, teacher.username)
    _save_config(client, classroom.id)
    started = _start(
        client,
        classroom.id,
        {"target_type": "custom", "student_ids": [roster["oak_s1"].id]},
    )
    session_id = started.get_json()["data"]["session"]["id"]
    _trigger(client, classroom.id, session_id)
    _trigger(client, classroom.id, session_id)
    _expire(db_session, session_id)
    _complete(client, classroom.id, session_id)
    rows = AuditLog.query.filter_by(
        character_id=roster["oak_c1"].id, event_type="TOOL_REWARD"
    ).all()
    assert len(rows) == 1
    desc = rows[0].event_data["description"]
    assert "Quiet-time" in desc
    assert "250" in desc
    assert "2" in desc
    batch = AuditLog.query.filter_by(character_id=None, event_type="TOOL_REWARD").all()
    assert any(r.event_data.get("session_id") == session_id for r in batch)


def test_config_hp_flag_round_trip(client, teacher, classroom):
    login(client, teacher.username)
    never = client.get(f"/teacher/api/classroom-tools/config/{classroom.id}")
    assert never.status_code == 200
    assert never.get_json()["config"]["hp_damage_enabled"] is False
    saved = _save_config(client, classroom.id, hp_damage_enabled=True, damage_amount=15)
    assert saved.status_code == 200
    assert saved.get_json()["config"]["hp_damage_enabled"] is True
    again = client.get(f"/teacher/api/classroom-tools/config/{classroom.id}")
    assert again.get_json()["config"]["hp_damage_enabled"] is True
    assert again.get_json()["config"]["damage_amount"] == 15
    assert again.get_json()["config"]["base_xp_reward"] == 1000
