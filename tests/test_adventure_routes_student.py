"""Student Adventures API route tests (US1)."""

import json
import uuid

import pytest

from app.models.adventure import AdventureRewardType, NodeType
from app.models.adventure_progress import (
    CharacterAdventureProgress,
    NodeProgressStatus,
)
from app.models.battle import Battle, Monster
from app.models.education import Question, QuestionSet
from tests.fixtures.adventure_factories import (
    add_node,
    publish_branching_adventure,
    publish_linear_adventure,
    seed_node_progress,
)

STUDENT_PASSWORD = "password123"
TEACHER_PASSWORD = "password123"


@pytest.fixture
def adventure_teacher(db_session):
    from app.models.user import User, UserRole

    unique = uuid.uuid4().hex[:8]
    user = User(
        username=f"adv_t_{unique}",
        email=f"adv_t_{unique}@test.com",
        role=UserRole.TEACHER,
    )
    user.set_password(TEACHER_PASSWORD)
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def adventure_student_setup(db_session, adventure_teacher):
    from app.models.character import Character
    from app.models.classroom import Classroom
    from app.models.student import Student
    from app.models.user import User, UserRole

    unique = uuid.uuid4().hex[:8]
    classroom = Classroom(
        name=f"Stu Class {unique}",
        teacher_id=adventure_teacher.id,
        join_code=f"SC{unique[:4]}",
    )
    db_session.add(classroom)
    db_session.commit()

    user = User(
        username=f"adv_s_{unique}",
        email=f"adv_s_{unique}@test.com",
        role=UserRole.STUDENT,
    )
    user.set_password(STUDENT_PASSWORD)
    db_session.add(user)
    db_session.commit()

    student = Student(user_id=user.id, class_id=classroom.id)
    db_session.add(student)
    db_session.commit()

    character = Character(
        name="AdvHero",
        student_id=student.id,
        character_class="Warrior",
        level=1,
        experience=0,
        gold=50,
        health=100,
        max_health=100,
        power=10,
        max_power=10,
        defense=5,
        is_active=True,
    )
    db_session.add(character)
    db_session.commit()

    monster = Monster(name="Goblin", health=50, attack=5, defense=2)
    db_session.add(monster)
    db_session.flush()

    from app.models.teacher import Teacher

    teacher_profile = Teacher(user_id=adventure_teacher.id)
    db_session.add(teacher_profile)
    db_session.flush()

    qset = QuestionSet(title="Adv Quiz", teacher_id=teacher_profile.id, is_active=True)
    db_session.add(qset)
    db_session.flush()
    db_session.add(
        Question(
            set_id=qset.id,
            text="2+2?",
            options=["3", "4", "5"],
            correct_answer="4",
            difficulty=1,
        )
    )
    db_session.commit()

    adventure, nodes, assignment = publish_linear_adventure(
        adventure_teacher, monster_id=monster.id
    )
    return {
        "user": user,
        "student": student,
        "character": character,
        "adventure": adventure,
        "nodes": nodes,
        "assignment": assignment,
        "monster": monster,
    }


def _login_student(client, user):
    return client.post(
        "/auth/login",
        data={"username": user.username, "password": STUDENT_PASSWORD},
        follow_redirects=True,
    )


def _json(client, method, url, data=None):
    return client.open(
        url,
        method=method,
        data=json.dumps(data) if data is not None else None,
        content_type="application/json",
    )


def test_student_linear_flow(client, db_session, adventure_student_setup):
    ctx = adventure_student_setup
    _login_student(client, ctx["user"])
    aid = ctx["adventure"].id
    slugs = {n.slug: n for n in ctx["nodes"]}

    resp = _json(client, "GET", "/student/adventures/?format=json")
    assert resp.status_code == 200
    adventures = resp.get_json()["data"]["adventures"]
    assert len(adventures) == 1

    resp = _json(client, "GET", f"/student/adventures/{aid}/state")
    assert resp.status_code == 200
    state = resp.get_json()["data"]
    start_progress = next(
        p for p in state["my_progress"]["nodes"] if p["node_id"] == slugs["start"].id
    )
    assert start_progress["status"] in ("available", "locked")

    resp = _json(client, "POST", f"/student/adventures/{aid}/nodes/start/start")
    assert resp.status_code == 200

    resp = _json(client, "POST", f"/student/adventures/{aid}/nodes/start/complete")
    assert resp.status_code == 200
    assert resp.get_json()["data"]["node"]["status"] == "completed"

    resp = _json(client, "GET", f"/student/adventures/{aid}/nodes/battle")
    assert resp.status_code == 200

    resp = _json(client, "POST", f"/student/adventures/{aid}/nodes/battle/start")
    assert resp.status_code == 200
    data = resp.get_json()["data"]
    assert "battle_id" in data

    resp = _json(client, "POST", f"/student/adventures/{aid}/nodes/end/start")
    assert resp.status_code == 409 or resp.status_code == 200

    seed_node_progress(
        ctx["character"],
        slugs["battle"],
        NodeProgressStatus.COMPLETED,
    )
    seed_node_progress(
        ctx["character"],
        slugs["start"],
        NodeProgressStatus.COMPLETED,
    )

    resp = _json(client, "POST", f"/student/adventures/{aid}/nodes/end/start")
    assert resp.status_code == 200

    resp = _json(client, "POST", f"/student/adventures/{aid}/nodes/end/complete")
    assert resp.status_code == 200
    assert resp.get_json()["data"].get("adventure_complete") is True


def test_student_idempotent_start_and_complete(client, db_session, adventure_student_setup):
    ctx = adventure_student_setup
    _login_student(client, ctx["user"])
    aid = ctx["adventure"].id

    _json(client, "POST", f"/student/adventures/{aid}/nodes/start/start")
    r1 = _json(client, "POST", f"/student/adventures/{aid}/nodes/start/complete")
    r2 = _json(client, "POST", f"/student/adventures/{aid}/nodes/start/complete")
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.get_json()["data"]["node"]["status"] == "completed"
    assert r2.get_json()["data"]["node"]["status"] == "completed"


@pytest.fixture
def branching_student_setup(db_session, adventure_teacher):
    from app.models.character import Character
    from app.models.classroom import Classroom
    from app.models.student import Student
    from app.models.user import User, UserRole

    unique = uuid.uuid4().hex[:8]
    classroom = Classroom(
        name=f"Branch Class {unique}",
        teacher_id=adventure_teacher.id,
        join_code=f"BC{unique[:4]}",
    )
    db_session.add(classroom)
    db_session.commit()

    user = User(
        username=f"branch_s_{unique}",
        email=f"branch_s_{unique}@test.com",
        role=UserRole.STUDENT,
    )
    user.set_password(STUDENT_PASSWORD)
    db_session.add(user)
    db_session.commit()

    student = Student(user_id=user.id, class_id=classroom.id)
    db_session.add(student)
    db_session.commit()

    character = Character(
        name="BranchHero",
        student_id=student.id,
        character_class="Warrior",
        is_active=True,
    )
    db_session.add(character)
    db_session.commit()

    adventure, nodes, assignment = publish_branching_adventure(adventure_teacher)
    return {
        "user": user,
        "character": character,
        "adventure": adventure,
        "nodes": nodes,
        "assignment": assignment,
    }


def test_student_choose_left_branch(client, db_session, branching_student_setup):
    ctx = branching_student_setup
    _login_student(client, ctx["user"])
    aid = ctx["adventure"].id
    nodes = ctx["nodes"]

    _json(client, "POST", f"/student/adventures/{aid}/nodes/start/start")
    _json(client, "POST", f"/student/adventures/{aid}/nodes/start/complete")

    resp = _json(
        client,
        "POST",
        f"/student/adventures/{aid}/nodes/fork/choose",
        {"choice_key": "left"},
    )
    assert resp.status_code == 200
    data = resp.get_json()["data"]
    assert data["node"]["choice_made"] == "left"
    assert data["node"]["status"] == "completed"
    unlocked_slugs = {n["slug"] for n in data["next_unlocked"]}
    assert "left_path" in unlocked_slugs
    assert "right_path" not in unlocked_slugs

    resp = _json(
        client,
        "POST",
        f"/student/adventures/{aid}/nodes/fork/choose",
        {"choice_key": "left"},
    )
    assert resp.status_code == 200
    assert resp.get_json()["data"]["node"]["choice_made"] == "left"

    resp = _json(
        client,
        "POST",
        f"/student/adventures/{aid}/nodes/fork/choose",
        {"choice_key": "right"},
    )
    assert resp.status_code == 409
    assert resp.get_json()["errors"][0]["code"] == "CHOICE_ALREADY_MADE"


def test_student_complete_without_optional_side(
    client, db_session, branching_student_setup
):
    ctx = branching_student_setup
    _login_student(client, ctx["user"])
    aid = ctx["adventure"].id
    nodes = ctx["nodes"]

    _json(client, "POST", f"/student/adventures/{aid}/nodes/start/start")
    _json(client, "POST", f"/student/adventures/{aid}/nodes/start/complete")
    _json(
        client,
        "POST",
        f"/student/adventures/{aid}/nodes/fork/choose",
        {"choice_key": "left"},
    )
    _json(client, "POST", f"/student/adventures/{aid}/nodes/left_path/start")
    _json(client, "POST", f"/student/adventures/{aid}/nodes/left_path/complete")
    _json(client, "POST", f"/student/adventures/{aid}/nodes/merge/start")
    _json(client, "POST", f"/student/adventures/{aid}/nodes/merge/complete")
    _json(client, "POST", f"/student/adventures/{aid}/nodes/end/start")
    resp = _json(client, "POST", f"/student/adventures/{aid}/nodes/end/complete")
    assert resp.status_code == 200
    assert resp.get_json()["data"].get("adventure_complete") is True

    resp = _json(client, "GET", f"/student/adventures/{aid}/state")
    side = next(
        p
        for p in resp.get_json()["data"]["my_progress"]["nodes"]
        if p["node_id"] == nodes["side_bonus"].id
    )
    assert side["status"] == "skipped"


def test_duplicate_character_progress_deduplication(
    client, db_session, adventure_teacher, adventure_student_setup
):
    """US4: one progress row per character per adventure across class assignments."""
    from app.models.classroom import Classroom
    from tests.fixtures.adventure_factories import assign_to_classroom

    ctx = adventure_student_setup
    aid = ctx["adventure"].id
    character = ctx["character"]
    _login_student(client, ctx["user"])

    _json(client, "POST", f"/student/adventures/{aid}/nodes/start/start")
    _json(client, "POST", f"/student/adventures/{aid}/nodes/start/complete")

    rows_before = CharacterAdventureProgress.query.filter_by(
        character_id=character.id, adventure_id=aid
    ).count()
    assert rows_before == 1

    unique = uuid.uuid4().hex[:8]
    class_b = Classroom(
        name=f"Dedup Class {unique}",
        teacher_id=adventure_teacher.id,
        join_code=f"DC{unique[:4]}",
    )
    db_session.add(class_b)
    db_session.commit()
    assign_to_classroom(ctx["adventure"], class_b.id, adventure_teacher)

    rows_after = CharacterAdventureProgress.query.filter_by(
        character_id=character.id, adventure_id=aid
    ).count()
    assert rows_after == 1

    resp = _json(client, "GET", f"/student/adventures/{aid}/state")
    assert resp.status_code == 200
    start_node = ctx["nodes"][0]
    start_progress = next(
        p
        for p in resp.get_json()["data"]["my_progress"]["nodes"]
        if p["node_id"] == start_node.id
    )
    assert start_progress["status"] == "completed"

    resp = _json(client, "GET", "/student/adventures/?format=json")
    adventures = resp.get_json()["data"]["adventures"]
    assert sum(1 for a in adventures if a["id"] == aid) == 1


def test_student_state_pins_graph_for_in_flight_after_teacher_edit(
    client, db_session, adventure_teacher
):
    """US5: early starter keeps snapshot; late starter sees post-edit live graph."""
    from tests.fixtures.adventure_factories import (
        apply_published_graph_edit,
        seed_midflight_edit_scenario,
    )

    ctx = seed_midflight_edit_scenario(adventure_teacher)
    adventure = ctx["adventure"]
    aid = adventure.id
    start = ctx["start_node"]

    client.get("/auth/logout", follow_redirects=True)
    client.post(
        "/auth/login",
        data={"username": ctx["student_early"].user.username, "password": "password123"},
        follow_redirects=True,
    )
    def _start_title(nodes):
        return next(n["title"] for n in nodes if n["slug"] == start.slug)

    resp = _json(client, "GET", f"/student/adventures/{aid}/state")
    assert resp.status_code == 200
    data = resp.get_json()["data"]
    assert _start_title(data["nodes"]) == "Original Start Title"
    assert data["adventure"]["pinned_from_snapshot"] is True

    apply_published_graph_edit(adventure, start, new_title="Revised Start Title")
    db_session.refresh(adventure)

    client.get("/auth/logout", follow_redirects=True)
    client.post(
        "/auth/login",
        data={"username": ctx["student_late"].user.username, "password": "password123"},
        follow_redirects=True,
    )
    resp = _json(client, "GET", f"/student/adventures/{aid}/state")
    assert resp.status_code == 200
    late_data = resp.get_json()["data"]
    assert _start_title(late_data["nodes"]) == "Revised Start Title"
    assert late_data["adventure"]["live_version"] == adventure.version

    client.get("/auth/logout", follow_redirects=True)
    client.post(
        "/auth/login",
        data={"username": ctx["student_early"].user.username, "password": "password123"},
        follow_redirects=True,
    )
    resp = _json(client, "GET", f"/student/adventures/{aid}/state")
    assert _start_title(resp.get_json()["data"]["nodes"]) == "Original Start Title"


def test_student_state_query_budget(client, db_session, adventure_student_setup):
    """Final phase: student /state must not issue per-node SQL queries."""
    from contextlib import contextmanager

    from sqlalchemy import event

    from app.models import db

    ctx = adventure_student_setup
    _login_student(client, ctx["user"])
    engine = db.session.get_bind()

    @contextmanager
    def count_queries():
        counter = {"n": 0}

        def _before(_conn, _cursor, _statement, _parameters, _context, _executemany):
            counter["n"] += 1

        event.listen(engine, "before_cursor_execute", _before)
        try:
            yield counter
        finally:
            event.remove(engine, "before_cursor_execute", _before)

    with count_queries() as counted:
        resp = _json(client, "GET", f"/student/adventures/{ctx['adventure'].id}/state")
    assert resp.status_code == 200
    node_count = len(resp.get_json()["data"]["nodes"])
    assert node_count >= 3
    assert counted["n"] <= 25, (
        f"Student state issued {counted['n']} SQL queries for {node_count} nodes; "
        "expected batched loading"
    )
