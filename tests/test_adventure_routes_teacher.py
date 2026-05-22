"""Teacher Adventures API route tests (US1)."""

import json
import uuid

import pytest

from app.models.adventure import Adventure, AdventureStatus, NodeType
from app.models.adventure_progress import AdventureAssignment
from app.models.classroom import Classroom
from tests.fixtures.adventure_factories import (
    add_edge,
    add_node,
    build_linear_adventure,
    create_adventure,
)

TEACHER_PASSWORD = "password123"


@pytest.fixture
def teacher_user(db_session):
    from app.models.user import User, UserRole

    unique = uuid.uuid4().hex[:8]
    user = User(
        username=f"adv_teacher_{unique}",
        email=f"adv_teacher_{unique}@test.com",
        role=UserRole.TEACHER,
    )
    user.set_password(TEACHER_PASSWORD)
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def teacher_classroom(db_session, teacher_user):
    classroom = Classroom(
        name=f"Adv Class {uuid.uuid4().hex[:6]}",
        teacher_id=teacher_user.id,
        join_code=f"AC{uuid.uuid4().hex[:4]}",
    )
    db_session.add(classroom)
    db_session.commit()
    return classroom


def _login_teacher(client, teacher_user):
    return client.post(
        "/auth/login",
        data={"username": teacher_user.username, "password": TEACHER_PASSWORD},
        follow_redirects=True,
    )


def _json(client, method, url, data=None):
    return client.open(
        url,
        method=method,
        data=json.dumps(data) if data is not None else None,
        content_type="application/json",
    )


def test_teacher_list_create_read_archive_clone(client, db_session, teacher_user):
    _login_teacher(client, teacher_user)

    resp = _json(client, "GET", "/teacher/adventures/?format=json")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["success"] is True
    assert body["data"]["adventures"] == []

    resp = _json(
        client,
        "POST",
        "/teacher/adventures/",
        {"title": "My Adventure", "description": "Test"},
    )
    assert resp.status_code == 201
    adv_id = resp.get_json()["data"]["adventure"]["id"]

    resp = _json(client, "GET", f"/teacher/adventures/{adv_id}?format=json")
    assert resp.status_code == 200
    assert resp.get_json()["data"]["adventure"]["title"] == "My Adventure"

    resp = _json(client, "POST", f"/teacher/adventures/{adv_id}/clone", {})
    assert resp.status_code == 201
    clone_id = resp.get_json()["data"]["adventure"]["id"]
    assert clone_id != adv_id

    resp = _json(client, "DELETE", f"/teacher/adventures/{adv_id}")
    assert resp.status_code == 200
    assert resp.get_json()["data"]["adventure"]["status"] == AdventureStatus.ARCHIVED.value


def test_teacher_node_and_edge_crud_linear(client, db_session, teacher_user):
    _login_teacher(client, teacher_user)
    adventure = create_adventure(teacher_user, title="Linear")
    db_session.commit()
    aid = adventure.id

    resp = _json(
        client,
        "POST",
        f"/teacher/adventures/{aid}/nodes",
        {
            "slug": "start",
            "title": "Start",
            "node_type": "start",
            "x": 0,
            "y": 0,
            "is_start": True,
        },
    )
    assert resp.status_code == 201
    start_id = resp.get_json()["data"]["node"]["id"]

    resp = _json(
        client,
        "POST",
        f"/teacher/adventures/{aid}/nodes",
        {
            "slug": "end",
            "title": "End",
            "node_type": "end",
            "x": 200,
            "y": 0,
            "is_end": True,
        },
    )
    assert resp.status_code == 201
    end_id = resp.get_json()["data"]["node"]["id"]

    resp = _json(
        client,
        "POST",
        f"/teacher/adventures/{aid}/edges",
        {"from_node_id": start_id, "to_node_id": end_id},
    )
    assert resp.status_code == 201
    edge_id = resp.get_json()["data"]["edge"]["id"]

    resp = _json(client, "GET", f"/teacher/adventures/{aid}/graph")
    assert resp.status_code == 200
    graph = resp.get_json()["data"]
    assert len(graph["nodes"]) == 2
    assert len(graph["edges"]) == 1

    resp = _json(
        client,
        "PATCH",
        f"/teacher/adventures/{aid}/edges/{edge_id}",
        {"label": "path"},
    )
    assert resp.status_code == 200

    resp = _json(client, "DELETE", f"/teacher/adventures/{aid}/edges/{edge_id}")
    assert resp.status_code == 200


def test_publish_validation_and_assignment(
    client, db_session, teacher_user, teacher_classroom
):
    _login_teacher(client, teacher_user)
    adventure, nodes = build_linear_adventure(teacher_user)
    aid = adventure.id

    resp = _json(client, "POST", f"/teacher/adventures/{aid}/publish")
    assert resp.status_code == 200
    assert resp.get_json()["data"]["adventure"]["status"] == "published"

    resp = _json(
        client,
        "POST",
        f"/teacher/adventures/{aid}/assignments",
        {"classroom_id": teacher_classroom.id},
    )
    assert resp.status_code == 201
    assignment = resp.get_json()["data"]["assignment"]
    assert assignment["classroom_id"] == teacher_classroom.id
    assert assignment["adventure_version"] == adventure.version

    row = AdventureAssignment.query.get(assignment["id"])
    assert row is not None
    assert row.is_active is True


def test_teacher_choice_edge_validation(client, db_session, teacher_user):
    _login_teacher(client, teacher_user)
    adventure = create_adventure(teacher_user, title="Branch")
    db_session.commit()
    aid = adventure.id

    start = add_node(adventure, "start", NodeType.START, is_start=True)
    left = add_node(adventure, "left", NodeType.STORY)
    choice_node = add_node(adventure, "fork", NodeType.CHOICE)
    db_session.commit()

    resp = _json(
        client,
        "POST",
        f"/teacher/adventures/{aid}/edges",
        {
            "from_node_id": choice_node.id,
            "to_node_id": left.id,
            "condition_type": "choice",
            "condition_data": {},
        },
    )
    assert resp.status_code == 400

    resp = _json(
        client,
        "POST",
        f"/teacher/adventures/{aid}/edges",
        {
            "from_node_id": choice_node.id,
            "to_node_id": left.id,
            "condition_type": "choice",
            "condition_data": {"choice_key": "left"},
            "label": "Go left",
            "unlock_semantics": "or",
            "sort_order": 1,
        },
    )
    assert resp.status_code == 201
    edge = resp.get_json()["data"]["edge"]
    assert edge["condition_data"]["choice_key"] == "left"

    resp = _json(
        client,
        "POST",
        f"/teacher/adventures/{aid}/edges",
        {
            "from_node_id": start.id,
            "to_node_id": choice_node.id,
        },
    )
    assert resp.status_code == 201

    right = add_node(adventure, "right", NodeType.STORY)
    db_session.commit()
    resp = _json(
        client,
        "POST",
        f"/teacher/adventures/{aid}/edges",
        {
            "from_node_id": choice_node.id,
            "to_node_id": right.id,
            "condition_type": "criteria",
            "condition_data": {"min_score_percent": 90},
        },
    )
    assert resp.status_code == 201

    resp = _json(
        client,
        "PATCH",
        f"/teacher/adventures/{aid}/edges/{edge['id']}",
        {"condition_type": "criteria"},
    )
    assert resp.status_code == 400


def test_teacher_progress_roster_and_class_filter(
    client, db_session, teacher_user, teacher_classroom
):
    from tests.fixtures.adventure_factories import (
        assign_to_classroom,
        build_linear_adventure,
        create_student_character,
        seed_progress_roster_states,
    )

    _login_teacher(client, teacher_user)
    adventure, nodes = build_linear_adventure(teacher_user)
    adventure.status = AdventureStatus.PUBLISHED.value
    db_session.commit()
    assign_to_classroom(adventure, teacher_classroom.id, teacher_user)

    _, not_started = create_student_character(
        teacher_classroom.id, name="Not Started", username_suffix="ns"
    )
    _, in_progress = create_student_character(
        teacher_classroom.id, name="In Progress", username_suffix="ip"
    )
    _, completed = create_student_character(
        teacher_classroom.id, name="Completed", username_suffix="done"
    )
    db_session.commit()

    seed_progress_roster_states(
        adventure,
        nodes,
        {
            "not_started": not_started,
            "in_progress": in_progress,
            "completed": completed,
        },
    )

    resp = _json(
        client,
        "GET",
        f"/teacher/adventures/{adventure.id}/progress?format=json",
    )
    assert resp.status_code == 200
    data = resp.get_json()["data"]
    assert data["summary"]["total_students"] == 3
    assert data["summary"]["not_started"] == 1
    assert data["summary"]["in_progress"] == 1
    assert data["summary"]["completed"] == 1

    by_name = {s["name"]: s for s in data["students"]}
    assert by_name["In Progress"]["has_failures"] is True
    assert by_name["In Progress"]["current_node"]["slug"] == "battle"
    assert by_name["Completed"]["recent_events"]
    assert by_name["Not Started"]["status"] == "not_started"

    resp = _json(
        client,
        "GET",
        f"/teacher/adventures/{adventure.id}/progress?format=json&classroom_id={teacher_classroom.id}",
    )
    assert resp.status_code == 200
    assert resp.get_json()["data"]["summary"]["total_students"] == 3


def test_teacher_force_complete(client, db_session, teacher_user, teacher_classroom):
    from app.models.audit import AuditLog
    from tests.fixtures.adventure_factories import (
        assign_to_classroom,
        build_linear_adventure,
        create_student_character,
    )

    _login_teacher(client, teacher_user)
    adventure, _ = build_linear_adventure(teacher_user)
    adventure.status = AdventureStatus.PUBLISHED.value
    db_session.commit()
    assign_to_classroom(adventure, teacher_classroom.id, teacher_user)
    _, character = create_student_character(
        teacher_classroom.id, name="Stuck Student", username_suffix="stuck"
    )
    db_session.commit()

    resp = _json(
        client,
        "POST",
        f"/teacher/adventures/{adventure.id}/progress/{character.id}/force-complete",
        {"reason": "Illness"},
    )
    assert resp.status_code == 200
    body = resp.get_json()["data"]["adventure_progress"]
    assert body["status"] == "completed"
    assert body["forced_by"] == teacher_user.id

    log = (
        AuditLog.query.filter_by(character_id=character.id)
        .order_by(AuditLog.event_timestamp.desc())
        .first()
    )
    assert log.event_type == "ADVENTURE_COMPLETE"
    assert log.event_data.get("forced_by") == teacher_user.id
    assert log.event_data.get("source") == "teacher_force_complete"


def test_multi_class_assignment_progress_isolation(
    client, db_session, teacher_user, teacher_classroom
):
    """US4: same adventure on two classes; Class B starts fresh; Class A unchanged."""
    from app.models.adventure_progress import (
        AdventureProgressStatus,
        CharacterAdventureProgress,
        CharacterNodeProgress,
    )
    from tests.fixtures.adventure_factories import (
        assign_to_classroom,
        build_linear_adventure,
        create_student_character,
    )

    class_b = Classroom(
        name=f"Adv Class B {uuid.uuid4().hex[:6]}",
        teacher_id=teacher_user.id,
        join_code=f"BC{uuid.uuid4().hex[:4]}",
    )
    db_session.add(class_b)
    db_session.commit()

    _login_teacher(client, teacher_user)
    adventure, nodes = build_linear_adventure(teacher_user)
    adventure.status = AdventureStatus.PUBLISHED.value
    db_session.commit()
    aid = adventure.id
    start = nodes[0]

    resp = _json(
        client,
        "POST",
        f"/teacher/adventures/{aid}/assignments",
        {"classroom_id": teacher_classroom.id},
    )
    assert resp.status_code == 201
    assert resp.get_json()["data"]["assignment"]["progress_url"]

    student_a, char_a = create_student_character(
        teacher_classroom.id, name="Class A Hero", username_suffix="cla"
    )
    db_session.commit()
    db_session.refresh(student_a)
    client.get("/auth/logout", follow_redirects=True)
    client.post(
        "/auth/login",
        data={"username": student_a.user.username, "password": "password123"},
        follow_redirects=True,
    )
    r_start = _json(client, "POST", f"/student/adventures/{aid}/nodes/start/start")
    assert r_start.status_code == 200, r_start.get_json()
    r_done = _json(client, "POST", f"/student/adventures/{aid}/nodes/start/complete")
    assert r_done.status_code == 200, r_done.get_json()
    client.get("/auth/logout", follow_redirects=True)
    _login_teacher(client, teacher_user)

    progress_a = CharacterAdventureProgress.query.filter_by(
        character_id=char_a.id, adventure_id=aid
    ).one()
    assert progress_a.status == AdventureProgressStatus.IN_PROGRESS.value
    start_row = CharacterNodeProgress.query.filter_by(
        character_id=char_a.id, node_id=start.id
    ).one()
    assert start_row.status == "completed"

    resp = _json(
        client,
        "POST",
        f"/teacher/adventures/{aid}/assignments",
        {"classroom_id": class_b.id},
    )
    assert resp.status_code == 201

    resp = _json(
        client,
        "POST",
        f"/teacher/adventures/{aid}/assignments",
        {"classroom_id": teacher_classroom.id},
    )
    assert resp.status_code == 409

    _, char_b = create_student_character(
        class_b.id, name="Class B Hero", username_suffix="clb"
    )
    db_session.commit()

    progress_b = CharacterAdventureProgress.query.filter_by(
        character_id=char_b.id, adventure_id=aid
    ).first()
    assert progress_b is None

    resp = _json(
        client,
        "GET",
        f"/teacher/adventures/{aid}/progress?format=json&classroom_id={class_b.id}",
    )
    assert resp.status_code == 200
    assert resp.get_json()["data"]["summary"]["total_students"] == 1
    assert resp.get_json()["data"]["students"][0]["status"] == "not_started"

    resp = _json(
        client,
        "GET",
        f"/teacher/adventures/{aid}/progress?format=json&classroom_id={teacher_classroom.id}",
    )
    assert resp.status_code == 200
    by_name = {s["name"]: s for s in resp.get_json()["data"]["students"]}
    assert by_name["Class A Hero"]["status"] == "in_progress"

    progress_a_after = CharacterAdventureProgress.query.get(progress_a.id)
    assert progress_a_after.status == AdventureProgressStatus.IN_PROGRESS.value

    resp = _json(
        client,
        "GET",
        f"/teacher/adventures/{aid}/assignments?format=json",
    )
    assert resp.status_code == 200
    assignments = resp.get_json()["data"]["assignments"]
    assert len(assignments) == 2
    assert all(a.get("progress_url") for a in assignments)


def test_published_edit_bumps_version_preserves_assignment_pin(
    client, db_session, teacher_user, teacher_classroom
):
    """US5: editing published graph bumps adventure.version, not assignment pins or snapshots."""
    from app.models.adventure_progress import CharacterAdventureProgress
    from tests.fixtures.adventure_factories import seed_midflight_edit_scenario

    _login_teacher(client, teacher_user)
    ctx = seed_midflight_edit_scenario(teacher_user, classroom_id=teacher_classroom.id)
    adventure = ctx["adventure"]
    assignment = ctx["assignment"]
    start = ctx["start_node"]
    pinned = dict(ctx["pinned_snapshot"])
    version_before = adventure.version
    assign_version_before = assignment.adventure_version

    resp = _json(
        client,
        "PATCH",
        f"/teacher/adventures/{adventure.id}/nodes/{start.id}",
        {"title": "Teacher Renamed Start"},
    )
    assert resp.status_code == 200
    db_session.refresh(adventure)
    db_session.refresh(assignment)
    assert adventure.version == version_before + 1
    assert assignment.adventure_version == assign_version_before

    progress = CharacterAdventureProgress.query.filter_by(
        character_id=ctx["character_early"].id, adventure_id=adventure.id
    ).one()
    snap_start = next(
        n for n in progress.snapshot_json["nodes"] if n["slug"] == start.slug
    )
    pinned_start = next(n for n in pinned["nodes"] if n["slug"] == start.slug)
    assert snap_start["title"] == pinned_start["title"]

    resp = _json(
        client,
        "GET",
        f"/teacher/adventures/{adventure.id}/graph?format=json",
    )
    assert resp.status_code == 200
    assert resp.get_json()["data"]["in_progress_student_count"] >= 1


@pytest.fixture
def teacher_b_user(db_session):
    from app.models.user import User, UserRole

    unique = uuid.uuid4().hex[:8]
    user = User(
        username=f"adv_teacher_b_{unique}",
        email=f"adv_teacher_b_{unique}@test.com",
        role=UserRole.TEACHER,
    )
    user.set_password(TEACHER_PASSWORD)
    db_session.add(user)
    db_session.commit()
    return user


def test_shared_public_adventure_list_and_visibility(
    client, db_session, teacher_user, teacher_b_user
):
    """US6: public adventures appear in peer teacher list; private ones do not."""
    _login_teacher(client, teacher_user)
    public_adv, _ = build_linear_adventure(teacher_user)
    public_adv.title = "Shared Quest"
    public_adv.status = AdventureStatus.PUBLISHED.value
    public_adv.is_public = True
    private_adv = create_adventure(teacher_user, title="Private Quest")
    private_adv.status = AdventureStatus.PUBLISHED.value
    private_adv.is_public = False
    draft_public = create_adventure(teacher_user, title="Draft Public")
    draft_public.is_public = True
    db_session.commit()

    client.get("/auth/logout", follow_redirects=True)
    _login_teacher(client, teacher_b_user)

    resp = _json(client, "GET", "/teacher/adventures/?format=json")
    assert resp.status_code == 200
    titles = {a["title"] for a in resp.get_json()["data"]["adventures"]}
    assert "Shared Quest" in titles
    assert "Private Quest" not in titles
    assert "Draft Public" not in titles

    resp = _json(client, "GET", f"/teacher/adventures/{public_adv.id}?format=json")
    assert resp.status_code == 200
    adv = resp.get_json()["data"]["adventure"]
    assert adv["is_public"] is True
    assert adv["owner"]["id"] == teacher_user.id

    resp = _json(client, "GET", f"/teacher/adventures/{private_adv.id}?format=json")
    assert resp.status_code == 403

    resp = _json(client, "GET", "/teacher/adventures/?format=json&mine=false")
    assert resp.status_code == 200
    shared_only = resp.get_json()["data"]["adventures"]
    assert len(shared_only) == 1
    assert shared_only[0]["title"] == "Shared Quest"


def test_cross_teacher_clone_isolation_and_ownership(
    client, db_session, teacher_user, teacher_b_user, teacher_classroom
):
    """US6: Teacher B clones Teacher A's public adventure; edits and assigns clone only."""
    from app.models.adventure import AdventureNode, NodeReward

    _login_teacher(client, teacher_user)
    adventure, nodes = build_linear_adventure(teacher_user)
    adventure.title = "Original Map"
    adventure.status = AdventureStatus.PUBLISHED.value
    adventure.is_public = True
    db_session.add(
        NodeReward(node_id=nodes[1].id, type="experience", amount=50)
    )
    db_session.commit()
    original_id = adventure.id
    original_version = adventure.version
    original_title = adventure.title

    client.get("/auth/logout", follow_redirects=True)
    _login_teacher(client, teacher_b_user)

    resp = _json(
        client,
        "POST",
        f"/teacher/adventures/{original_id}/clone",
        {"title": "B Clone"},
    )
    assert resp.status_code == 201
    clone_body = resp.get_json()["data"]["adventure"]
    clone_id = clone_body["id"]
    assert clone_id != original_id
    assert clone_body["title"] == "B Clone"
    assert clone_body["status"] == AdventureStatus.DRAFT.value
    assert clone_body["is_public"] is False
    assert clone_body["owner"]["id"] == teacher_b_user.id

    resp = _json(
        client,
        "PATCH",
        f"/teacher/adventures/{original_id}",
        {"title": "Hacked Original"},
    )
    assert resp.status_code == 403

    resp = _json(
        client,
        "PATCH",
        f"/teacher/adventures/{clone_id}",
        {"title": "Renamed Clone"},
    )
    assert resp.status_code == 200
    assert resp.get_json()["data"]["adventure"]["title"] == "Renamed Clone"

    class_b = Classroom(
        name=f"Teacher B Class {uuid.uuid4().hex[:6]}",
        teacher_id=teacher_b_user.id,
        join_code=f"TB{uuid.uuid4().hex[:4]}",
    )
    db_session.add(class_b)
    db_session.commit()

    resp = _json(
        client,
        "POST",
        f"/teacher/adventures/{clone_id}/publish",
    )
    assert resp.status_code == 200

    resp = _json(
        client,
        "POST",
        f"/teacher/adventures/{clone_id}/assignments",
        {"classroom_id": class_b.id},
    )
    assert resp.status_code == 201

    db_session.refresh(adventure)
    original = db_session.get(Adventure, original_id)
    assert original.title == original_title
    assert original.version == original_version
    assert original.teacher_id == teacher_user.id
    assert AdventureAssignment.query.filter_by(adventure_id=original_id).count() == 0
    assert AdventureAssignment.query.filter_by(adventure_id=clone_id).count() == 1

    clone_nodes = AdventureNode.query.filter_by(adventure_id=clone_id).all()
    assert len(clone_nodes) == len(nodes)
    clone_rewards = NodeReward.query.join(AdventureNode).filter(
        AdventureNode.adventure_id == clone_id
    ).all()
    assert len(clone_rewards) == 1
    assert clone_rewards[0].amount == 50


def test_teacher_progress_query_budget(client, db_session, teacher_user):
    """Final phase: progress roster query count must not scale linearly with student count."""
    from contextlib import contextmanager

    from sqlalchemy import event

    from app.models import db
    from app.services.adventure_graph import aggregate_adventure_progress_roster
    from tests.fixtures.adventure_factories import build_progress_classroom_with_students

    small_class, _, small_adv, _, _ = build_progress_classroom_with_students(
        teacher_user, student_count=5
    )
    large_class, _, large_adv, _, _ = build_progress_classroom_with_students(
        teacher_user, student_count=60
    )
    db_session.commit()

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

    with count_queries() as small_count:
        small = aggregate_adventure_progress_roster(
            small_adv, teacher_user, classroom_id=small_class.id
        )
    with count_queries() as large_count:
        large = aggregate_adventure_progress_roster(
            large_adv, teacher_user, classroom_id=large_class.id
        )

    assert small["summary"]["total_students"] == 5
    assert large["summary"]["total_students"] == 60
    assert large_count["n"] <= small_count["n"] + 8, (
        f"Progress roster appears O(n): 5-student roster used {small_count['n']} queries, "
        f"60-student roster used {large_count['n']}"
    )
