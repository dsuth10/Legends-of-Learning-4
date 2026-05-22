"""Factory helpers for Adventures graph and progress test data."""



from __future__ import annotations

import uuid

from typing import Any, Dict, List, Optional, Tuple



from app.models import db

from app.models.adventure import (

    Adventure,

    AdventureEdge,

    AdventureNode,

    AdventureStatus,

    EdgeConditionType,

    EndSemantics,

    NodeReward,

    NodeType,

    UnlockSemantics,

)

from app.models.adventure_progress import (

    AdventureAssignment,

    AdventureProgressStatus,

    CharacterAdventureProgress,

    CharacterNodeProgress,

    NodeProgressStatus,

)

from app.models.user import User





def create_adventure(

    teacher: User,

    *,

    title: str = "Test Adventure",

    status: AdventureStatus = AdventureStatus.DRAFT,

    end_semantics: EndSemantics = EndSemantics.ALL,

) -> Adventure:

    adventure = Adventure(

        title=title,

        teacher_id=teacher.id,

        status=status.value,

        end_semantics=end_semantics.value,

    )

    db.session.add(adventure)

    db.session.flush()

    return adventure





def add_node(

    adventure: Adventure,

    slug: str,

    node_type: NodeType,

    *,

    title: Optional[str] = None,

    x: float = 0.0,

    y: float = 0.0,

    is_start: bool = False,

    is_end: bool = False,

    is_optional: bool = False,

    monster_id: Optional[int] = None,

    question_set_id: Optional[int] = None,

) -> AdventureNode:

    node = AdventureNode(

        adventure_id=adventure.id,

        slug=slug,

        title=title or slug.replace("_", " ").title(),

        node_type=node_type.value,

        x=x,

        y=y,

        is_start=is_start,

        is_end=is_end,

        is_optional=is_optional,

        monster_id=monster_id,

        question_set_id=question_set_id,

        completion_rules={},

        on_complete_actions={},

    )

    db.session.add(node)

    db.session.flush()

    return node





def add_edge(

    adventure: Adventure,

    from_node: AdventureNode,

    to_node: AdventureNode,

    *,

    condition_type: EdgeConditionType = EdgeConditionType.ALWAYS,

    condition_data: Optional[dict] = None,

    unlock_semantics: UnlockSemantics = UnlockSemantics.AND,

    label: Optional[str] = None,

    sort_order: int = 0,

) -> AdventureEdge:

    edge = AdventureEdge(

        adventure_id=adventure.id,

        from_node_id=from_node.id,

        to_node_id=to_node.id,

        condition_type=condition_type.value,

        condition_data=condition_data or {},

        unlock_semantics=unlock_semantics.value,

        label=label,

        sort_order=sort_order,

    )

    db.session.add(edge)

    db.session.flush()

    return edge





def build_linear_adventure(

    teacher: User,

    *,

    with_monster_id: Optional[int] = None,

) -> Tuple[Adventure, List[AdventureNode]]:

    """start -> battle -> end linear graph."""

    adventure = create_adventure(teacher, title="Linear Adventure")

    start = add_node(adventure, "start", NodeType.START, is_start=True, x=0, y=0)

    battle = add_node(

        adventure,

        "battle",

        NodeType.BATTLE,

        x=100,

        y=0,

        monster_id=with_monster_id,

    )

    end = add_node(adventure, "end", NodeType.END, is_end=True, x=200, y=0)

    add_edge(adventure, start, battle)

    add_edge(adventure, battle, end)

    db.session.commit()

    return adventure, [start, battle, end]





def assign_to_classroom(

    adventure: Adventure,

    classroom_id: int,

    teacher: User,

    *,

    version: Optional[int] = None,

) -> AdventureAssignment:

    assignment = AdventureAssignment(

        adventure_id=adventure.id,

        adventure_version=version if version is not None else adventure.version,

        classroom_id=classroom_id,

        assigned_by_user_id=teacher.id,

        is_active=True,

    )

    db.session.add(assignment)

    db.session.commit()

    return assignment





def seed_node_progress(

    character,

    node: AdventureNode,

    status: NodeProgressStatus,

    *,

    score: Optional[int] = None,

    choice_made: Optional[str] = None,

) -> CharacterNodeProgress:

    row = CharacterNodeProgress.query.filter_by(
        character_id=character.id,
        node_id=node.id,
    ).first()
    if row is None:
        row = CharacterNodeProgress(
            character_id=character.id,
            node_id=node.id,
        )
        db.session.add(row)
    row.status = status.value
    row.score = score
    row.choice_made = choice_made
    if status != NodeProgressStatus.LOCKED and row.attempts == 0:
        row.attempts = 1
    db.session.commit()
    return row





def adventure_graph_payload(

    *,

    title: str = "Test Adventure",

    nodes: Optional[list] = None,

    edges: Optional[list] = None,

) -> Dict[str, Any]:

    return {

        "title": title,

        "nodes": nodes or [],

        "edges": edges or [],

    }





def linear_three_node_slugs() -> Dict[str, str]:
    return {
        "start": "start",
        "battle": "battle",
        "end": "end",
    }


def publish_linear_adventure(
    teacher: User,
    *,
    monster_id: Optional[int] = None,
) -> Tuple[Adventure, List[AdventureNode], AdventureAssignment]:
    """Published start -> battle -> end adventure assigned to teacher's first classroom."""
    from app.models.adventure import AdventureStatus
    from app.models.classroom import Classroom

    adventure, nodes = build_linear_adventure(teacher, with_monster_id=monster_id)
    adventure.status = AdventureStatus.PUBLISHED.value
    adventure.version = 2
    db.session.commit()

    classroom = Classroom.query.filter_by(teacher_id=teacher.id).first()
    if classroom is None:
        classroom = Classroom(
            name="Adventure Test Class",
            teacher_id=teacher.id,
            join_code="ADVTEST",
        )
        db.session.add(classroom)
        db.session.commit()

    assignment = assign_to_classroom(adventure, classroom.id, teacher)
    return adventure, nodes, assignment


def build_branching_adventure(
    teacher: User,
) -> Tuple[Adventure, Dict[str, AdventureNode]]:
    """
    Branching graph: start -> choice -> left/right paths -> merge -> end,
    plus optional side bonus off the left path.
    """
    adventure = create_adventure(teacher, title="Branching Adventure")
    start = add_node(adventure, "start", NodeType.START, is_start=True, x=0, y=100)
    choice = add_node(adventure, "fork", NodeType.CHOICE, x=150, y=100)
    left_path = add_node(adventure, "left_path", NodeType.STORY, x=300, y=50)
    right_path = add_node(adventure, "right_path", NodeType.STORY, x=300, y=150)
    side_bonus = add_node(
        adventure,
        "side_bonus",
        NodeType.REWARD,
        x=300,
        y=0,
        is_optional=True,
    )
    merge = add_node(adventure, "merge", NodeType.MILESTONE, x=450, y=100)
    end = add_node(adventure, "end", NodeType.END, is_end=True, x=600, y=100)

    add_edge(adventure, start, choice)
    add_edge(
        adventure,
        choice,
        left_path,
        condition_type=EdgeConditionType.CHOICE,
        condition_data={"choice_key": "left"},
        label="Trust the wizard",
        sort_order=0,
    )
    add_edge(
        adventure,
        choice,
        right_path,
        condition_type=EdgeConditionType.CHOICE,
        condition_data={"choice_key": "right"},
        label="Walk away",
        sort_order=1,
    )
    add_edge(adventure, left_path, side_bonus)
    add_edge(
        adventure,
        left_path,
        merge,
        unlock_semantics=UnlockSemantics.OR,
    )
    add_edge(
        adventure,
        right_path,
        merge,
        unlock_semantics=UnlockSemantics.OR,
    )
    add_edge(adventure, merge, end)
    db.session.commit()

    nodes = {
        "start": start,
        "choice": choice,
        "left_path": left_path,
        "right_path": right_path,
        "side_bonus": side_bonus,
        "merge": merge,
        "end": end,
    }
    return adventure, nodes


def publish_branching_adventure(
    teacher: User,
) -> Tuple[Adventure, Dict[str, AdventureNode], AdventureAssignment]:
    """Published branching adventure assigned to teacher's first classroom."""
    from app.models.classroom import Classroom

    adventure, nodes = build_branching_adventure(teacher)
    adventure.status = AdventureStatus.PUBLISHED.value
    adventure.version = 2
    db.session.commit()

    classroom = Classroom.query.filter_by(teacher_id=teacher.id).first()
    if classroom is None:
        classroom = Classroom(
            name="Branch Test Class",
            teacher_id=teacher.id,
            join_code="BRANCH",
        )
        db.session.add(classroom)
        db.session.commit()

    assignment = assign_to_classroom(adventure, classroom.id, teacher)
    return adventure, nodes, assignment


def create_student_character(
    classroom_id: int,
    *,
    name: str,
    username_suffix: str,
) -> Tuple["Student", "Character"]:
    """Create a student user + active character in the given classroom."""
    from app.models.character import Character
    from app.models.student import Student
    from app.models.user import User, UserRole

    user = User(
        username=f"adv_stu_{username_suffix}",
        email=f"adv_stu_{username_suffix}@test.com",
        role=UserRole.STUDENT,
    )
    user.set_password("password123")
    db.session.add(user)
    db.session.flush()
    student = Student(user_id=user.id, class_id=classroom_id)
    db.session.add(student)
    db.session.flush()
    character = Character(
        name=name,
        student_id=student.id,
        character_class="Warrior",
        is_active=True,
    )
    db.session.add(character)
    db.session.flush()
    return student, character


def seed_progress_roster_states(
    adventure: Adventure,
    nodes: List[AdventureNode],
    characters: Dict[str, "Character"],
) -> None:
    """Seed not_started / in_progress / completed states for progress roster tests."""
    from app.models.adventure_progress import CharacterAdventureProgress
    from app.models.audit import AuditLog, EventType
    from app.utils.date_utils import get_utc_now

    start, battle, end = nodes[0], nodes[1], nodes[2]
    now = get_utc_now()

    in_prog = characters["in_progress"]
    db.session.add(
        CharacterAdventureProgress(
            character_id=in_prog.id,
            adventure_id=adventure.id,
            status=AdventureProgressStatus.IN_PROGRESS.value,
            current_node_id=battle.id,
            started_at=now,
            last_active_at=now,
        )
    )
    seed_node_progress(in_prog, start, NodeProgressStatus.COMPLETED)
    seed_node_progress(in_prog, battle, NodeProgressStatus.FAILED)

    completed = characters["completed"]
    db.session.add(
        CharacterAdventureProgress(
            character_id=completed.id,
            adventure_id=adventure.id,
            status=AdventureProgressStatus.COMPLETED.value,
            current_node_id=end.id,
            started_at=now,
            completed_at=now,
            last_active_at=now,
        )
    )
    seed_node_progress(completed, start, NodeProgressStatus.COMPLETED)
    seed_node_progress(completed, battle, NodeProgressStatus.COMPLETED, score=90)
    seed_node_progress(completed, end, NodeProgressStatus.COMPLETED)

    db.session.add(
        AuditLog(
            event_type=EventType.ADVENTURE_NODE_COMPLETE.value,
            character_id=completed.id,
            event_data={
                "adventure_id": adventure.id,
                "node_slug": start.slug,
                "score": None,
            },
        )
    )
    db.session.commit()


def build_progress_classroom_with_students(
    teacher: User,
    *,
    student_count: int = 60,
) -> Tuple["Classroom", List["Character"], Adventure, List[AdventureNode], AdventureAssignment]:
    """Classroom with N students and a published assigned linear adventure."""
    from app.models.classroom import Classroom

    unique = uuid.uuid4().hex[:6]
    classroom = Classroom(
        name=f"Progress Class {unique}",
        teacher_id=teacher.id,
        join_code=f"PC{unique}",
    )
    db.session.add(classroom)
    db.session.flush()

    characters: List = []
    for i in range(student_count):
        _, character = create_student_character(
            classroom.id,
            name=f"Student {i + 1}",
            username_suffix=f"{unique}_{i}",
        )
        characters.append(character)

    adventure, nodes = build_linear_adventure(teacher)
    adventure.status = AdventureStatus.PUBLISHED.value
    db.session.commit()
    assignment = assign_to_classroom(adventure, classroom.id, teacher)
    return classroom, characters, adventure, nodes, assignment


def seed_midflight_edit_scenario(
    teacher: User,
    *,
    classroom_id: Optional[int] = None,
) -> dict:
    """
    Published linear adventure with one student pinned pre-edit and room for a post-edit starter.

    Returns keys: adventure, nodes, assignment, classroom_id, student_early, student_late,
    character_early, character_late.
    """
    from app.models.classroom import Classroom
    from app.services.adventure_graph import ensure_progress_snapshot
    from app.services.adventure_lifecycle import ensure_adventure_bootstrapped

    if classroom_id is None:
        classroom = Classroom(
            name=f"Snapshot Class {uuid.uuid4().hex[:6]}",
            teacher_id=teacher.id,
            join_code=f"SN{uuid.uuid4().hex[:4]}",
        )
        db.session.add(classroom)
        db.session.flush()
        classroom_id = classroom.id

    adventure, nodes = build_linear_adventure(teacher)
    start = nodes[0]
    start.title = "Original Start Title"
    adventure.status = AdventureStatus.PUBLISHED.value
    adventure.version = 2
    db.session.commit()

    assignment = assign_to_classroom(adventure, classroom_id, teacher)
    student_early, character_early = create_student_character(
        classroom_id, name="Early Bird", username_suffix=f"early_{uuid.uuid4().hex[:6]}"
    )
    ensure_adventure_bootstrapped(
        character_early, adventure, assignment, session=db.session
    )
    progress = CharacterAdventureProgress.query.filter_by(
        character_id=character_early.id, adventure_id=adventure.id
    ).one()
    ensure_progress_snapshot(progress, adventure, assignment)
    db.session.commit()
    pinned_snapshot = dict(progress.snapshot_json or {})

    student_late, character_late = create_student_character(
        classroom_id, name="Late Joiner", username_suffix=f"late_{uuid.uuid4().hex[:6]}"
    )
    db.session.commit()

    return {
        "adventure": adventure,
        "nodes": nodes,
        "assignment": assignment,
        "classroom_id": classroom_id,
        "student_early": student_early,
        "student_late": student_late,
        "character_early": character_early,
        "character_late": character_late,
        "pinned_snapshot": pinned_snapshot,
        "start_node": start,
    }


def apply_published_graph_edit(adventure: Adventure, start_node: AdventureNode, *, new_title: str) -> int:
    """Simulate a teacher structural edit on a published adventure; returns new version."""
    start_node.title = new_title
    adventure.version += 1
    db.session.commit()
    return adventure.version


