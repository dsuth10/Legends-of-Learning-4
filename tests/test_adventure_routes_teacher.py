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


def test_editor_page_includes_select_tool(client, db_session, teacher_user):
    _login_teacher(client, teacher_user)
    adventure = create_adventure(teacher_user, title="Select tool")
    db_session.commit()

    resp = client.get(f"/teacher/adventures/{adventure.id}")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert 'id="btn-select-mode"' in html
    assert "Click a node to select it" in html or "Select" in html


def test_teacher_can_delete_node(client, db_session, teacher_user):
    _login_teacher(client, teacher_user)
    adventure = create_adventure(teacher_user, title="Delete node")
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
            "x": 40,
            "y": 40,
            "is_start": True,
        },
    )
    assert resp.status_code == 201
    start_id = resp.get_json()["data"]["node"]["id"]

    resp = _json(client, "DELETE", f"/teacher/adventures/{aid}/nodes/{start_id}")
    assert resp.status_code == 200
    graph = _json(client, "GET", f"/teacher/adventures/{aid}/graph").get_json()["data"]
    assert graph["nodes"] == []


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


def test_list_question_sets_filters_active_by_teacher(client, db_session, teacher_user):
    from app.models.user import User, UserRole
    from tests.fixtures.adventure_factories import (
        create_question_set,
        ensure_teacher_profile,
    )

    profile_a = ensure_teacher_profile(teacher_user)
    active = create_question_set(profile_a, title="Active Fractions", is_active=True)
    create_question_set(profile_a, title="Inactive Set", is_active=False)

    other = User(
        username=f"adv_other_{uuid.uuid4().hex[:8]}",
        email=f"adv_other_{uuid.uuid4().hex[:8]}@test.com",
        role=UserRole.TEACHER,
    )
    other.set_password(TEACHER_PASSWORD)
    db_session.add(other)
    db_session.flush()
    profile_b = ensure_teacher_profile(other)
    create_question_set(profile_b, title="Other Teacher Set")
    db_session.commit()

    _login_teacher(client, teacher_user)
    resp = _json(client, "GET", "/teacher/adventures/question-sets")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["success"] is True
    sets = body["data"]["question_sets"]
    assert len(sets) == 1
    assert sets[0]["id"] == active.id
    assert sets[0]["title"] == "Active Fractions"
    assert sets[0]["question_count"] == 1


def test_quiz_node_question_set_save_clear_reload(client, db_session, teacher_user):
    from tests.fixtures.adventure_factories import (
        add_node,
        create_adventure,
        create_question_set,
        ensure_teacher_profile,
    )

    profile = ensure_teacher_profile(teacher_user)
    qset = create_question_set(profile, title="Math Quiz")
    adventure = create_adventure(teacher_user, title="Quiz Adventure")
    quiz = add_node(adventure, "quiz1", NodeType.QUIZ, x=100, y=50)
    db_session.commit()

    _login_teacher(client, teacher_user)
    aid = adventure.id

    resp = _json(
        client,
        "PATCH",
        f"/teacher/adventures/{aid}/nodes/{quiz.id}",
        {"question_set_id": qset.id},
    )
    assert resp.status_code == 200
    assert resp.get_json()["data"]["node"]["question_set_id"] == qset.id

    resp = _json(client, "GET", f"/teacher/adventures/{aid}/graph")
    assert resp.status_code == 200
    nodes = resp.get_json()["data"]["nodes"]
    quiz_row = next(n for n in nodes if n["id"] == quiz.id)
    assert quiz_row["question_set_id"] == qset.id

    resp = _json(
        client,
        "PATCH",
        f"/teacher/adventures/{aid}/nodes/{quiz.id}",
        {"question_set_id": None},
    )
    assert resp.status_code == 200
    assert resp.get_json()["data"]["node"]["question_set_id"] is None

    resp = _json(client, "GET", f"/teacher/adventures/{aid}/graph")
    quiz_row = next(n for n in resp.get_json()["data"]["nodes"] if n["id"] == quiz.id)
    assert quiz_row["question_set_id"] is None


def test_question_set_id_rejects_foreign_and_inactive(
    client, db_session, teacher_user
):
    from app.models.user import User, UserRole
    from tests.fixtures.adventure_factories import (
        add_node,
        create_adventure,
        create_question_set,
        ensure_teacher_profile,
    )

    profile = ensure_teacher_profile(teacher_user)
    inactive = create_question_set(profile, title="Inactive", is_active=False)

    other = User(
        username=f"adv_foreign_{uuid.uuid4().hex[:8]}",
        email=f"adv_foreign_{uuid.uuid4().hex[:8]}@test.com",
        role=UserRole.TEACHER,
    )
    other.set_password(TEACHER_PASSWORD)
    db_session.add(other)
    db_session.flush()
    foreign = create_question_set(ensure_teacher_profile(other), title="Foreign Set")

    adventure = create_adventure(teacher_user, title="Validation Adventure")
    quiz = add_node(adventure, "quiz1", NodeType.QUIZ)
    db_session.commit()
    aid = adventure.id

    _login_teacher(client, teacher_user)

    resp = _json(
        client,
        "POST",
        f"/teacher/adventures/{aid}/nodes",
        {
            "slug": "quiz-new",
            "title": "Quiz",
            "node_type": "quiz",
            "x": 50,
            "y": 50,
            "question_set_id": foreign.id,
        },
    )
    assert resp.status_code == 400
    assert resp.get_json()["success"] is False

    resp = _json(
        client,
        "PATCH",
        f"/teacher/adventures/{aid}/nodes/{quiz.id}",
        {"question_set_id": inactive.id},
    )
    assert resp.status_code == 400
    assert resp.get_json()["success"] is False

    resp = _json(
        client,
        "PATCH",
        f"/teacher/adventures/{aid}/nodes/{quiz.id}",
        {"question_set_id": foreign.id},
    )
    assert resp.status_code == 400
    assert resp.get_json()["success"] is False


def test_patch_adventure_metadata_preserves_omitted_fields(client, db_session, teacher_user):
    adventure = create_adventure(teacher_user, title="Original Title")
    adventure.description = "Keep this description"
    adventure.theme = "fantasy"
    adventure.end_semantics = "all"
    db_session.commit()

    _login_teacher(client, teacher_user)
    resp = _json(
        client,
        "PATCH",
        f"/teacher/adventures/{adventure.id}",
        {"title": "Updated Title", "theme": "sci-fi"},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["success"] is True
    adv = body["data"]["adventure"]
    assert adv["title"] == "Updated Title"
    assert adv["theme"] == "sci-fi"
    assert adv["description"] == "Keep this description"
    assert adv["end_semantics"] == "all"


def test_patch_adventure_invalid_metadata_and_draft_sharing(client, db_session, teacher_user):
    adventure = create_adventure(teacher_user, title="Draft Adventure")
    db_session.commit()

    _login_teacher(client, teacher_user)
    aid = adventure.id

    resp = _json(client, "PATCH", f"/teacher/adventures/{aid}", {"title": ""})
    assert resp.status_code == 400
    assert resp.get_json()["success"] is False

    resp = _json(client, "PATCH", f"/teacher/adventures/{aid}", {"end_semantics": "maybe"})
    assert resp.status_code == 400
    assert resp.get_json()["success"] is False

    resp = _json(client, "PATCH", f"/teacher/adventures/{aid}", {"is_public": True})
    assert resp.status_code == 400
    err = resp.get_json()
    assert err["success"] is False
    err_text = " ".join(
        (e.get("message") or "") for e in (err.get("errors") or [])
    ).lower()
    assert "draft" in err_text or "publish" in err_text


def test_background_upload_valid_and_invalid(client, db_session, teacher_user):
    import io

    adventure = create_adventure(teacher_user, title="Background Test")
    db_session.commit()

    _login_teacher(client, teacher_user)
    aid = adventure.id

    resp = client.post(
        f"/teacher/adventures/{aid}/background",
        data={"file": (io.BytesIO(b"not an image"), "notes.txt", "text/plain")},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 400
    assert resp.get_json()["success"] is False

    png_data = b"\x89PNG\r\n\x1a\n" + (b"\x00" * 200)
    resp = client.post(
        f"/teacher/adventures/{aid}/background",
        data={"file": (io.BytesIO(png_data), "map.png", "image/png")},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["success"] is True
    assert body["data"]["background_image_url"].startswith(
        f"/static/images/adventure_backgrounds/{aid}/"
    )

    db_session.refresh(adventure)
    assert adventure.background_image_url == body["data"]["background_image_url"]


def test_node_coordinate_update_persistence(client, db_session, teacher_user):
    adventure = create_adventure(teacher_user, title="Drag Adventure")
    node = add_node(adventure, "story1", NodeType.STORY, x=100, y=200)
    db_session.commit()

    _login_teacher(client, teacher_user)
    aid = adventure.id

    resp = _json(
        client,
        "PATCH",
        f"/teacher/adventures/{aid}/nodes/{node.id}",
        {"x": 350, "y": 425},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["success"] is True
    assert body["data"]["node"]["x"] == 350
    assert body["data"]["node"]["y"] == 425

    resp = _json(client, "GET", f"/teacher/adventures/{aid}/graph")
    assert resp.status_code == 200
    nodes = resp.get_json()["data"]["nodes"]
    node_row = next(n for n in nodes if n["id"] == node.id)
    assert node_row["x"] == 350
    assert node_row["y"] == 425


def test_published_node_coordinate_update_bumps_version(
    client, db_session, teacher_user
):
    adventure = create_adventure(
        teacher_user,
        title="Published Drag Adventure",
        status=AdventureStatus.PUBLISHED,
    )
    node = add_node(adventure, "start", NodeType.START, x=50, y=50)
    db_session.commit()
    version_before = adventure.version

    _login_teacher(client, teacher_user)
    resp = _json(
        client,
        "PATCH",
        f"/teacher/adventures/{adventure.id}/nodes/{node.id}",
        {"x": 120, "y": 180},
    )
    assert resp.status_code == 200
    assert resp.get_json()["success"] is True

    db_session.refresh(adventure)
    assert adventure.version == version_before + 1


def _make_clan(db_session, classroom, name):
    from app.models.clan import Clan

    clan = Clan(name=name, class_id=classroom.id)
    db_session.add(clan)
    db_session.commit()
    return clan


def test_teacher_assign_clan_and_character(
    client, db_session, teacher_user, teacher_classroom
):
    from tests.fixtures.adventure_factories import create_student_character

    unique = uuid.uuid4().hex[:6]
    clan = _make_clan(db_session, teacher_classroom, f"Team Oak {unique}")
    student, character = create_student_character(
        teacher_classroom.id, name="Ada the Druid", username_suffix=f"ada{unique}"
    )
    character.clan_id = clan.id
    db_session.commit()

    _login_teacher(client, teacher_user)
    adventure, _nodes = build_linear_adventure(teacher_user)
    adventure.status = AdventureStatus.PUBLISHED.value
    db_session.commit()
    aid = adventure.id

    resp = _json(client, "POST", f"/teacher/adventures/{aid}/assignments", {"clan_id": clan.id})
    assert resp.status_code == 201, resp.get_json()
    data = resp.get_json()["data"]
    assert data["assignment"]["target_type"] == "clan"
    assert data["assignment"]["clan_id"] == clan.id
    assert "Oak" in data["assignment"]["target_label"]
    assert data["assignment"]["progress_url"].endswith(f"assignment_id={data['assignment']['id']}")
    assert data["warnings"] == []

    resp = _json(
        client,
        "POST",
        f"/teacher/adventures/{aid}/assignments",
        {"character_id": character.id},
    )
    assert resp.status_code == 201, resp.get_json()
    char_data = resp.get_json()["data"]["assignment"]
    assert char_data["target_type"] == "character"
    assert char_data["character_id"] == character.id

    resp = _json(client, "GET", f"/teacher/adventures/{aid}/assignments?format=json")
    assert resp.status_code == 200
    types = {a["target_type"] for a in resp.get_json()["data"]["assignments"]}
    assert "clan" in types
    assert "character" in types

    resp = _json(
        client,
        "GET",
        f"/teacher/adventures/{aid}/progress?format=json&assignment_id={data['assignment']['id']}",
    )
    assert resp.status_code == 200
    names = [s["name"] for s in resp.get_json()["data"]["students"]]
    assert "Ada the Druid" in names


def test_teacher_assign_duplicate_and_foreign_targets(
    client, db_session, teacher_user, teacher_classroom
):
    from app.models.user import User, UserRole
    from tests.fixtures.adventure_factories import create_student_character

    unique = uuid.uuid4().hex[:6]
    clan = _make_clan(db_session, teacher_classroom, f"Wolves {unique}")
    _login_teacher(client, teacher_user)
    adventure, _nodes = build_linear_adventure(teacher_user)
    adventure.status = AdventureStatus.PUBLISHED.value
    db_session.commit()
    aid = adventure.id

    resp = _json(client, "POST", f"/teacher/adventures/{aid}/assignments", {"clan_id": clan.id})
    assert resp.status_code == 201
    resp = _json(client, "POST", f"/teacher/adventures/{aid}/assignments", {"clan_id": clan.id})
    assert resp.status_code == 409

    other = User(
        username=f"other_t_{unique}",
        email=f"other_t_{unique}@test.com",
        role=UserRole.TEACHER,
    )
    other.set_password(TEACHER_PASSWORD)
    db_session.add(other)
    db_session.commit()
    other_class = Classroom(
        name=f"Other Class {unique}",
        teacher_id=other.id,
        join_code=f"OT{unique[:4]}",
    )
    db_session.add(other_class)
    db_session.commit()
    foreign_clan = _make_clan(db_session, other_class, f"Foreign {unique}")
    _, foreign_char = create_student_character(
        other_class.id, name="Foreign Hero", username_suffix=f"fh{unique}"
    )
    db_session.commit()

    resp = _json(
        client, "POST", f"/teacher/adventures/{aid}/assignments", {"clan_id": foreign_clan.id}
    )
    assert resp.status_code == 403
    resp = _json(
        client,
        "POST",
        f"/teacher/adventures/{aid}/assignments",
        {"character_id": foreign_char.id},
    )
    assert resp.status_code == 403


def test_teacher_assign_empty_clan_warns(
    client, db_session, teacher_user, teacher_classroom
):
    unique = uuid.uuid4().hex[:6]
    clan = _make_clan(db_session, teacher_classroom, f"Empty Wolves {unique}")
    _login_teacher(client, teacher_user)
    adventure, _nodes = build_linear_adventure(teacher_user)
    adventure.status = AdventureStatus.PUBLISHED.value
    db_session.commit()

    resp = _json(
        client,
        "POST",
        f"/teacher/adventures/{adventure.id}/assignments",
        {"clan_id": clan.id},
    )
    assert resp.status_code == 201
    warnings = resp.get_json()["data"]["warnings"]
    assert warnings
    assert "no members" in warnings[0].lower()


def test_node_icon_catalog_has_one_default_per_type(client, db_session, teacher_user):
    from app.models.adventure import NodeType

    _login_teacher(client, teacher_user)
    resp = _json(client, "GET", "/teacher/adventures/node-icons")
    assert resp.status_code == 200
    icons = resp.get_json()["data"]["icons"]
    defaults = []
    for icon in icons:
        defaults.extend(icon.get("default_for") or [])
    assert sorted(defaults) == sorted(item.value for item in NodeType)
    assert len(defaults) == len(set(defaults))
    optional_images = {
        icon["id"]: icon
        for icon in icons
        if icon.get("id") in {"quest", "rest"}
    }
    assert set(optional_images) == {"quest", "rest"}
    assert all(not icon.get("default_for") for icon in optional_images.values())
    assert optional_images["quest"]["image_url"].endswith("node_quest.png")
    assert optional_images["rest"]["image_url"].endswith("node_rest.png")


def test_node_icon_save_and_clear(client, db_session, teacher_user):
    _login_teacher(client, teacher_user)
    adventure, nodes = build_linear_adventure(teacher_user)
    battle = next(n for n in nodes if n.node_type == NodeType.BATTLE.value)
    aid = adventure.id

    resp = _json(
        client,
        "PATCH",
        f"/teacher/adventures/{aid}/nodes/{battle.id}",
        {"icon_url": "castle"},
    )
    assert resp.status_code == 200
    assert resp.get_json()["data"]["node"]["icon_url"] == "castle"

    resp = _json(
        client,
        "PATCH",
        f"/teacher/adventures/{aid}/nodes/{battle.id}",
        {"icon_url": None},
    )
    assert resp.status_code == 200
    assert resp.get_json()["data"]["node"]["icon_url"] is None

    resp = _json(
        client,
        "PATCH",
        f"/teacher/adventures/{aid}/nodes/{battle.id}",
        {"icon_url": ""},
    )
    assert resp.status_code == 200
    assert resp.get_json()["data"]["node"]["icon_url"] is None
