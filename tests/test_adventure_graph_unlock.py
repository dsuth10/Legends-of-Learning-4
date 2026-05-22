"""Foundational tests for adventure graph validation and unlock recomputation."""



import uuid



import pytest



from app.models.adventure import (

    AdventureStatus,

    EdgeConditionType,

    NodeType,

    UnlockSemantics,

)

from app.models.adventure_progress import CharacterNodeProgress, NodeProgressStatus

from app.services.adventure_graph import (

    AuthorizationError,

    detect_cycle_node_ids,

    evaluate_adventure_complete,

    recompute_unlocks_for_character,

    require_teacher_edit,

    require_teacher_read,

    teacher_can_read_adventure,

    validate_for_publish,

)

from tests.fixtures.adventure_factories import (

    add_edge,

    add_node,

    build_linear_adventure,

    create_adventure,

    seed_node_progress,

)





@pytest.fixture

def teacher_user(db_session):

    from app.models.user import User, UserRole



    unique = uuid.uuid4().hex[:8]

    user = User(

        username=f"graph_teacher_{unique}",

        email=f"graph_teacher_{unique}@test.com",

        role=UserRole.TEACHER,

        password="password123",

    )

    db_session.add(user)

    db_session.commit()

    return user





@pytest.fixture

def other_teacher(db_session):

    from app.models.user import User, UserRole



    unique = uuid.uuid4().hex[:8]

    user = User(

        username=f"other_teacher_{unique}",

        email=f"other_teacher_{unique}@test.com",

        role=UserRole.TEACHER,

        password="password123",

    )

    db_session.add(user)

    db_session.commit()

    return user





@pytest.fixture

def student_character(db_session):

    from app.models.character import Character

    from app.models.classroom import Classroom

    from app.models.student import Student

    from app.models.user import User, UserRole



    unique = uuid.uuid4().hex[:8]

    teacher = User(

        username=f"gteacher_{unique}",

        email=f"gteacher_{unique}@test.com",

        role=UserRole.TEACHER,

        password="password123",

    )

    db_session.add(teacher)

    db_session.commit()

    classroom = Classroom(name=f"GClass_{unique}", teacher_id=teacher.id, join_code=f"GC{unique}")

    db_session.add(classroom)

    db_session.commit()

    user = User(

        username=f"gstudent_{unique}",

        email=f"gstudent_{unique}@test.com",

        role=UserRole.STUDENT,

        password="password123",

    )

    db_session.add(user)

    db_session.commit()

    student = Student(user_id=user.id, class_id=classroom.id)

    db_session.add(student)

    db_session.commit()

    character = Character(name="GraphHero", student_id=student.id, character_class="Warrior")

    db_session.add(character)

    db_session.commit()

    return character





def test_validate_publish_blocks_no_start(db_session, teacher_user):

    adventure = create_adventure(teacher_user)

    a = add_node(adventure, "a", NodeType.STORY)

    b = add_node(adventure, "b", NodeType.STORY)

    add_edge(adventure, a, b)

    add_edge(adventure, b, a)

    db_session.commit()

    result = validate_for_publish(adventure)

    assert not result.ok_to_publish

    assert any(e["code"] == "NO_START_NODE" for e in result.errors)





def test_validate_publish_ok_linear(db_session, teacher_user):

    adventure, _ = build_linear_adventure(teacher_user)

    result = validate_for_publish(adventure)

    assert result.ok_to_publish

    assert not result.errors





def test_teacher_read_public_not_owned(db_session, teacher_user, other_teacher):

    adventure = create_adventure(teacher_user, status=AdventureStatus.PUBLISHED)

    adventure.is_public = True

    db_session.commit()

    assert teacher_can_read_adventure(other_teacher, adventure)

    with pytest.raises(AuthorizationError):

        require_teacher_edit(other_teacher, adventure)





def test_teacher_cannot_read_private_other(db_session, teacher_user, other_teacher):

    adventure = create_adventure(teacher_user, status=AdventureStatus.PUBLISHED)

    db_session.commit()

    with pytest.raises(AuthorizationError):

        require_teacher_read(other_teacher, adventure)





def test_recompute_unlocks_start_node(db_session, teacher_user, student_character):

    adventure, nodes = build_linear_adventure(teacher_user)

    unlocked = recompute_unlocks_for_character(student_character, adventure)

    assert nodes[0].id in unlocked





def test_recompute_unlocks_after_complete(db_session, teacher_user, student_character):

    adventure, nodes = build_linear_adventure(teacher_user)

    recompute_unlocks_for_character(student_character, adventure)

    db_session.commit()

    seed_node_progress(student_character, nodes[0], NodeProgressStatus.COMPLETED)

    unlocked = recompute_unlocks_for_character(student_character, adventure)

    db_session.commit()

    assert nodes[1].id in unlocked





def test_and_semantics_requires_all_inbound(db_session, teacher_user, student_character):

    adventure = create_adventure(teacher_user)

    a = add_node(adventure, "a", NodeType.STORY, is_start=True)

    b = add_node(adventure, "b", NodeType.STORY, is_start=True)

    merge = add_node(adventure, "merge", NodeType.MILESTONE)

    add_edge(adventure, a, merge, unlock_semantics=UnlockSemantics.AND)

    add_edge(adventure, b, merge, unlock_semantics=UnlockSemantics.AND)

    db_session.commit()



    seed_node_progress(student_character, a, NodeProgressStatus.COMPLETED)

    recompute_unlocks_for_character(student_character, adventure)

    db_session.commit()



    row = CharacterNodeProgress.query.filter_by(

        character_id=student_character.id, node_id=merge.id

    ).first()

    assert row is None or row.status == NodeProgressStatus.LOCKED.value



    seed_node_progress(student_character, b, NodeProgressStatus.COMPLETED)

    unlocked = recompute_unlocks_for_character(student_character, adventure)

    db_session.commit()

    assert merge.id in unlocked





def test_or_semantics_any_inbound(db_session, teacher_user, student_character):

    adventure = create_adventure(teacher_user)

    left = add_node(adventure, "left", NodeType.CHOICE, is_start=True)

    right = add_node(adventure, "right", NodeType.CHOICE, is_start=True)

    merge = add_node(adventure, "join", NodeType.STORY)

    add_edge(adventure, left, merge, unlock_semantics=UnlockSemantics.OR)

    add_edge(adventure, right, merge, unlock_semantics=UnlockSemantics.OR)

    db_session.commit()



    seed_node_progress(student_character, left, NodeProgressStatus.COMPLETED)

    unlocked = recompute_unlocks_for_character(student_character, adventure)

    db_session.commit()

    assert merge.id in unlocked





def test_choice_edge_condition(db_session, teacher_user, student_character):

    adventure = create_adventure(teacher_user)

    choice = add_node(adventure, "choice", NodeType.CHOICE, is_start=True)

    left_path = add_node(adventure, "left_path", NodeType.STORY)

    add_edge(

        adventure,

        choice,

        left_path,

        condition_type=EdgeConditionType.CHOICE,

        condition_data={"choice_key": "left"},

    )

    db_session.commit()



    row = seed_node_progress(

        student_character,

        choice,

        NodeProgressStatus.COMPLETED,

        choice_made="right",

    )

    unlocked = recompute_unlocks_for_character(student_character, adventure)

    db_session.commit()

    assert left_path.id not in unlocked



    row.choice_made = "left"

    db_session.commit()

    unlocked = recompute_unlocks_for_character(student_character, adventure)

    db_session.commit()

    assert left_path.id in unlocked





def test_detect_cycle(db_session, teacher_user):

    adventure = create_adventure(teacher_user)

    a = add_node(adventure, "a", NodeType.STORY, is_start=True)

    b = add_node(adventure, "b", NodeType.STORY)

    c = add_node(adventure, "c", NodeType.STORY)

    add_edge(adventure, a, b)

    add_edge(adventure, b, c)

    add_edge(adventure, c, a)

    db_session.commit()

    cycle_ids = detect_cycle_node_ids(list(adventure.nodes), list(adventure.edges))

    assert a.id in cycle_ids and b.id in cycle_ids and c.id in cycle_ids





def test_end_semantics_all(db_session, teacher_user, student_character):

    adventure = create_adventure(teacher_user)

    start = add_node(adventure, "start", NodeType.START, is_start=True)

    end1 = add_node(adventure, "end1", NodeType.END, is_end=True)

    end2 = add_node(adventure, "end2", NodeType.END, is_end=True)

    add_edge(adventure, start, end1)

    add_edge(adventure, start, end2)

    db_session.commit()



    seed_node_progress(student_character, end1, NodeProgressStatus.COMPLETED)

    assert not evaluate_adventure_complete(adventure, student_character)

    seed_node_progress(student_character, end2, NodeProgressStatus.COMPLETED)

    assert evaluate_adventure_complete(adventure, student_character)





def test_end_semantics_any(db_session, teacher_user, student_character):

    from app.models.adventure import EndSemantics



    adventure = create_adventure(teacher_user, end_semantics=EndSemantics.ANY)

    start = add_node(adventure, "start", NodeType.START, is_start=True)

    end1 = add_node(adventure, "end1", NodeType.END, is_end=True)

    end2 = add_node(adventure, "end2", NodeType.END, is_end=True)

    add_edge(adventure, start, end1)

    add_edge(adventure, start, end2)

    db_session.commit()



    seed_node_progress(student_character, end1, NodeProgressStatus.COMPLETED)

    assert evaluate_adventure_complete(adventure, student_character)





def test_criteria_edge_requires_min_score(db_session, teacher_user, student_character):

    adventure = create_adventure(teacher_user)

    quiz = add_node(adventure, "quiz", NodeType.QUIZ, is_start=True)

    bonus = add_node(adventure, "bonus", NodeType.REWARD)

    add_edge(

        adventure,

        quiz,

        bonus,

        condition_type=EdgeConditionType.CRITERIA,

        condition_data={"min_score_percent": 80},

    )

    db_session.commit()



    seed_node_progress(

        student_character, quiz, NodeProgressStatus.COMPLETED, score=70

    )

    recompute_unlocks_for_character(student_character, adventure)

    db_session.commit()

    row = CharacterNodeProgress.query.filter_by(

        character_id=student_character.id, node_id=bonus.id

    ).first()

    assert row is None or row.status == NodeProgressStatus.LOCKED.value



    row = seed_node_progress(

        student_character, quiz, NodeProgressStatus.COMPLETED, score=85

    )

    unlocked = recompute_unlocks_for_character(student_character, adventure)

    db_session.commit()

    assert bonus.id in unlocked





def test_optional_node_skipped_on_adventure_complete(db_session, teacher_user, student_character):

    from app.services.adventure_graph import mark_unvisited_optional_nodes_skipped



    adventure = create_adventure(teacher_user)

    start = add_node(adventure, "start", NodeType.START, is_start=True)

    optional = add_node(adventure, "optional", NodeType.REWARD, is_optional=True)

    end = add_node(adventure, "end", NodeType.END, is_end=True)

    add_edge(adventure, start, optional)

    add_edge(adventure, start, end)

    db_session.commit()



    seed_node_progress(student_character, start, NodeProgressStatus.COMPLETED)

    seed_node_progress(student_character, end, NodeProgressStatus.COMPLETED)

    skipped = mark_unvisited_optional_nodes_skipped(

        student_character, adventure, session=db_session

    )

    db_session.commit()

    assert optional.id in skipped

    row = CharacterNodeProgress.query.filter_by(

        character_id=student_character.id, node_id=optional.id

    ).first()

    assert row.status == NodeProgressStatus.SKIPPED.value





def test_branching_choice_locks_unselected_path(db_session, teacher_user, student_character):

    from tests.fixtures.adventure_factories import build_branching_adventure



    adventure, nodes = build_branching_adventure(teacher_user)

    recompute_unlocks_for_character(student_character, adventure)

    db_session.commit()



    seed_node_progress(

        student_character,

        nodes["start"],

        NodeProgressStatus.COMPLETED,

    )

    seed_node_progress(

        student_character,

        nodes["choice"],

        NodeProgressStatus.COMPLETED,

        choice_made="left",

    )

    unlocked = recompute_unlocks_for_character(student_character, adventure)

    db_session.commit()



    assert nodes["left_path"].id in unlocked

    right_row = CharacterNodeProgress.query.filter_by(

        character_id=student_character.id, node_id=nodes["right_path"].id

    ).first()

    assert right_row is None or right_row.status == NodeProgressStatus.LOCKED.value





def test_aggregate_progress_roster_service(db_session, teacher_user):

    from app.services.adventure_graph import aggregate_adventure_progress_roster

    from tests.fixtures.adventure_factories import (

        build_progress_classroom_with_students,

        create_student_character,

        seed_progress_roster_states,

    )



    classroom, _, adventure, nodes, _ = build_progress_classroom_with_students(

        teacher_user, student_count=60

    )

    roster = aggregate_adventure_progress_roster(

        adventure, teacher_user, classroom_id=classroom.id

    )

    assert roster["summary"]["total_students"] == 60



    _, in_progress = create_student_character(

        classroom.id, name="Mid", username_suffix="mid"

    )

    _, completed = create_student_character(

        classroom.id, name="Done", username_suffix="done2"

    )

    db_session.commit()

    seed_progress_roster_states(

        adventure,

        nodes,

        {"not_started": in_progress, "in_progress": in_progress, "completed": completed},

    )

    roster = aggregate_adventure_progress_roster(

        adventure, teacher_user, classroom_id=classroom.id

    )

    assert roster["summary"]["total_students"] == 62

    mid = next(s for s in roster["students"] if s["name"] == "Mid")

    assert mid["has_failures"] is True

    assert mid["node_counts"]["failed"] >= 1

    done = next(s for s in roster["students"] if s["name"] == "Done")

    assert done["status"] == "completed"

    assert done["last_active_at"] is not None


def test_snapshot_pins_unlock_graph_after_published_edit(db_session, teacher_user):
    """US5: in-flight student unlock graph uses snapshot, not live edits."""
    from app.models.adventure_progress import CharacterAdventureProgress
    from app.services.adventure_graph import (
        capture_graph_snapshot,
        ensure_progress_snapshot,
        get_resolved_graph,
        recompute_unlocks_for_character,
    )
    from tests.fixtures.adventure_factories import (
        assign_to_classroom,
        build_linear_adventure,
        create_student_character,
        seed_node_progress,
    )

    from app.models.classroom import Classroom

    adventure, nodes = build_linear_adventure(teacher_user)
    start, _, _ = nodes
    adventure.status = AdventureStatus.PUBLISHED.value
    db_session.commit()

    classroom = Classroom(
        name=f"Snap {uuid.uuid4().hex[:6]}",
        teacher_id=teacher_user.id,
        join_code=f"SN{uuid.uuid4().hex[:4]}",
    )
    db_session.add(classroom)
    db_session.commit()
    assignment = assign_to_classroom(adventure, classroom.id, teacher_user)

    _, character = create_student_character(
        classroom.id, name="Pinned", username_suffix="pin"
    )
    progress = CharacterAdventureProgress(
        character_id=character.id,
        adventure_id=adventure.id,
        assignment_id=assignment.id,
        status="in_progress",
    )
    db_session.add(progress)
    ensure_progress_snapshot(progress, adventure, assignment)
    seed_node_progress(character, start, NodeProgressStatus.COMPLETED)
    db_session.commit()

    snap_start = next(
        n for n in progress.snapshot_json["nodes"] if n["slug"] == start.slug
    )
    pinned_title = snap_start["title"]
    start.title = "Edited Start Title"
    adventure.version += 1
    db_session.commit()

    live = get_resolved_graph(adventure, None)
    pinned = get_resolved_graph(adventure, progress)
    live_start = next(n for n in live["nodes"] if n["slug"] == start.slug)
    pinned_start = next(n for n in pinned["nodes"] if n["slug"] == start.slug)
    assert live_start["title"] == "Edited Start Title"
    assert pinned_start["title"] == pinned_title
    assert pinned["from_snapshot"] is True

    recompute_unlocks_for_character(character, adventure, progress=progress)
    db_session.commit()
