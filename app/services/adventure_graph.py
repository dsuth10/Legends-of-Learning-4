"""Adventure graph validation, authorization, unlock recomputation, and progress helpers."""



from __future__ import annotations



from collections import defaultdict, deque

from dataclasses import dataclass, field

from typing import Dict, Iterable, List, Optional, Set, Tuple



from app.models import db

from app.models.adventure import (

    Adventure,

    AdventureEdge,

    AdventureNode,

    AdventureStatus,

    EdgeConditionType,

    EndSemantics,

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

from app.models.classroom import Classroom

from app.models.user import User, UserRole

from app.utils.date_utils import get_utc_now





# ---------------------------------------------------------------------------

# Authorization helpers (T016)

# ---------------------------------------------------------------------------





class AuthorizationError(Exception):

    """Raised when a caller lacks permission for an adventure action."""



    def __init__(self, code: str, message: str):

        self.code = code

        self.message = message

        super().__init__(message)





def teacher_owns_adventure(user: User, adventure: Adventure) -> bool:

    return adventure.teacher_id is not None and adventure.teacher_id == user.id





def teacher_can_read_adventure(user: User, adventure: Adventure) -> bool:

    if teacher_owns_adventure(user, adventure):

        return True

    return adventure.is_public and adventure.status != AdventureStatus.DRAFT.value





def teacher_can_edit_adventure(user: User, adventure: Adventure) -> bool:

    return teacher_owns_adventure(user, adventure)





def require_teacher_read(user: User, adventure: Adventure) -> None:

    if user.role != UserRole.TEACHER or not teacher_can_read_adventure(user, adventure):

        raise AuthorizationError("FORBIDDEN", "You do not have permission to view this adventure.")





def require_teacher_edit(user: User, adventure: Adventure) -> None:

    if user.role != UserRole.TEACHER or not teacher_can_edit_adventure(user, adventure):

        raise AuthorizationError("FORBIDDEN", "You do not have permission to edit this adventure.")





def teacher_owns_classroom(user: User, classroom_id: int) -> bool:

    classroom = db.session.get(Classroom, classroom_id)

    return classroom is not None and classroom.teacher_id == user.id





def require_teacher_classroom(user: User, classroom_id: int) -> Classroom:

    classroom = db.session.get(Classroom, classroom_id)

    if classroom is None:

        raise AuthorizationError("NOT_FOUND", "Classroom not found.")

    if user.role != UserRole.TEACHER or classroom.teacher_id != user.id:

        raise AuthorizationError("FORBIDDEN", "You do not own this classroom.")

    return classroom





def _active_assignments_for_character(character) -> List[AdventureAssignment]:

    """Return active assignments matching the character via class, clan, or direct."""

    student = character.student

    if student is None:

        return []



    filters = []

    if student.class_id:

        filters.append(

            db.and_(

                AdventureAssignment.classroom_id == student.class_id,

                AdventureAssignment.is_active.is_(True),

            )

        )

    if character.clan_id:

        filters.append(

            db.and_(

                AdventureAssignment.clan_id == character.clan_id,

                AdventureAssignment.is_active.is_(True),

            )

        )

    filters.append(

        db.and_(

            AdventureAssignment.character_id == character.id,

            AdventureAssignment.is_active.is_(True),

        )

    )



    if not filters:

        return []



    query = AdventureAssignment.query.filter(db.or_(*filters))

    now = get_utc_now()

    assignments = []

    for assignment in query.all():

        if assignment.starts_at and now < assignment.starts_at:

            continue

        if assignment.ends_at and now > assignment.ends_at:

            continue

        assignments.append(assignment)

    return assignments





def student_is_assigned(character, adventure_id: int) -> bool:

    return any(a.adventure_id == adventure_id for a in _active_assignments_for_character(character))





def require_student_assignment(character, adventure_id: int) -> AdventureAssignment:

    matches = [a for a in _active_assignments_for_character(character) if a.adventure_id == adventure_id]

    if not matches:

        raise AuthorizationError("NOT_ASSIGNED", "This adventure is not assigned to you.")

    return pick_assignment_for_character(character, matches)





class AssignmentError(Exception):

    def __init__(self, code: str, message: str):

        self.code = code

        self.message = message

        super().__init__(message)





def pick_assignment_for_character(

    character,

    matches: List[AdventureAssignment],

) -> AdventureAssignment:

    """Prefer the assignment that matches the student's current classroom."""

    student = character.student

    if student and student.class_id:

        for assignment in matches:

            if assignment.classroom_id == student.class_id:

                return assignment

    return matches[0]





def list_active_classroom_assignments(adventure: Adventure) -> List[AdventureAssignment]:

    """Active classroom-scoped assignments for an adventure."""

    return (

        AdventureAssignment.query.filter_by(

            adventure_id=adventure.id,

            is_active=True,

        )

        .filter(AdventureAssignment.classroom_id.isnot(None))

        .order_by(AdventureAssignment.id.asc())

        .all()

    )





def get_active_classroom_assignment(

    adventure_id: int,

    classroom_id: int,

) -> Optional[AdventureAssignment]:

    return AdventureAssignment.query.filter_by(

        adventure_id=adventure_id,

        classroom_id=classroom_id,

        is_active=True,

    ).first()





def create_classroom_assignment(

    adventure: Adventure,

    teacher: User,

    *,

    classroom_id: int,

    starts_at=None,

    ends_at=None,

) -> AdventureAssignment:

    """

    Create an active classroom assignment. Multiple classrooms may receive the

    same adventure; the same classroom cannot have two active assignments.

    """

    if adventure.status != AdventureStatus.PUBLISHED.value:

        raise AssignmentError("CONFLICT", "Only published adventures can be assigned.")



    require_teacher_classroom(teacher, classroom_id)



    existing = get_active_classroom_assignment(adventure.id, classroom_id)

    if existing:

        raise AssignmentError(

            "CONFLICT",

            "This adventure is already assigned to that classroom.",

        )



    assignment = AdventureAssignment(

        adventure_id=adventure.id,

        adventure_version=adventure.version,

        classroom_id=classroom_id,

        assigned_by_user_id=teacher.id,

        starts_at=starts_at,

        ends_at=ends_at,

        is_active=True,

    )

    db.session.add(assignment)

    db.session.commit()

    return assignment





# ---------------------------------------------------------------------------

# Snapshot pinning (US5 — T083)

# ---------------------------------------------------------------------------





def capture_graph_snapshot(

    adventure: Adventure,

    *,

    assignment: Optional[AdventureAssignment] = None,

) -> dict:

    """Serialize the live graph for mid-flight stability pinning."""

    from app.routes.adventures.serializers import edge_dict, node_dict



    return {

        "adventure_version": (

            assignment.adventure_version if assignment else adventure.version

        ),

        "end_semantics": adventure.end_semantics,

        "nodes": [node_dict(n) for n in adventure.nodes.all()],

        "edges": [edge_dict(e) for e in adventure.edges.all()],

    }





def ensure_progress_snapshot(

    progress: CharacterAdventureProgress,

    adventure: Adventure,

    assignment: Optional[AdventureAssignment] = None,

) -> None:

    """Pin graph JSON on first play so later teacher edits do not drift the run."""

    if progress.snapshot_json:

        return

    progress.snapshot_json = capture_graph_snapshot(

        adventure, assignment=assignment

    )





def progress_uses_snapshot(progress: Optional[CharacterAdventureProgress]) -> bool:

    return bool(progress and progress.snapshot_json)





def get_resolved_graph(

    adventure: Adventure,

    progress: Optional[CharacterAdventureProgress] = None,

) -> dict:

    """Return nodes/edges/end_semantics for student play (snapshot or live)."""

    if progress_uses_snapshot(progress):

        snap = progress.snapshot_json

        return {

            "from_snapshot": True,

            "adventure_version": snap.get("adventure_version", adventure.version),

            "end_semantics": snap.get("end_semantics", adventure.end_semantics),

            "nodes": snap.get("nodes", []),

            "edges": snap.get("edges", []),

        }

    return {

        "from_snapshot": False,

        "adventure_version": adventure.version,

        "end_semantics": adventure.end_semantics,

        "nodes": [

            {

                "id": n.id,

                "slug": n.slug,

                "title": n.title,

                "description": n.description,

                "lore": n.lore,

                "icon_url": n.icon_url,

                "node_type": n.node_type,

                "x": n.x,

                "y": n.y,

                "is_optional": n.is_optional,

                "is_start": n.is_start,

                "is_end": n.is_end,

                "question_set_id": n.question_set_id,

                "monster_id": n.monster_id,

                "completion_rules": n.completion_rules or {},

                "on_complete_actions": n.on_complete_actions or {},

            }

            for n in adventure.nodes.all()

        ],

        "edges": [

            {

                "id": e.id,

                "from_node_id": e.from_node_id,

                "to_node_id": e.to_node_id,

                "label": e.label,

                "condition_type": e.condition_type,

                "condition_data": e.condition_data or {},

                "unlock_semantics": e.unlock_semantics,

                "sort_order": e.sort_order,

            }

            for e in adventure.edges.all()

        ],

    }





def resolve_snapshot_node(

    adventure: Adventure,

    progress: Optional[CharacterAdventureProgress],

    slug: str,

) -> Optional[dict]:

    graph = get_resolved_graph(adventure, progress)

    for node in graph["nodes"]:

        if node.get("slug") == slug:

            return node

    return None





def count_in_progress_students(adventure_id: int) -> int:

    return CharacterAdventureProgress.query.filter_by(

        adventure_id=adventure_id,

        status=AdventureProgressStatus.IN_PROGRESS.value,

    ).count()





def _play_node_id(node) -> int:

    return node["id"] if isinstance(node, dict) else node.id





def _play_node_is_end(node) -> bool:

    if isinstance(node, dict):

        return bool(node.get("is_end")) or node.get("node_type") == NodeType.END.value

    return bool(node.is_end) or node.node_type == NodeType.END.value





def _play_node_is_optional(node) -> bool:

    return bool(node.get("is_optional") if isinstance(node, dict) else node.is_optional)





def _play_node_is_start(node) -> bool:

    return bool(node.get("is_start") if isinstance(node, dict) else node.is_start)





# ---------------------------------------------------------------------------

# Publish validation (T017)

# ---------------------------------------------------------------------------





@dataclass

class ValidationResult:

    ok_to_publish: bool

    errors: List[dict] = field(default_factory=list)

    warnings: List[dict] = field(default_factory=list)



    def to_dict(self) -> dict:

        return {

            "ok_to_publish": self.ok_to_publish,

            "errors": self.errors,

            "warnings": self.warnings,

        }





def _build_adjacency(

    nodes: List[AdventureNode], edges: List[AdventureEdge]

) -> Tuple[Dict[int, List[int]], Dict[int, List[int]]]:

    outbound: Dict[int, List[int]] = defaultdict(list)

    inbound: Dict[int, List[int]] = defaultdict(list)

    for edge in edges:

        outbound[edge.from_node_id].append(edge.to_node_id)

        inbound[edge.to_node_id].append(edge.from_node_id)

    for node in nodes:

        outbound.setdefault(node.id, [])

        inbound.setdefault(node.id, [])

    return outbound, inbound





def _reachable_from_starts(

    nodes: List[AdventureNode],

    outbound: Dict[int, List[int]],

    inbound: Dict[int, List[int]],

) -> Set[int]:

    start_ids = {n.id for n in nodes if n.is_start or not inbound[n.id]}

    if not start_ids:

        return set()



    visited: Set[int] = set()

    queue: deque[int] = deque(start_ids)

    while queue:

        node_id = queue.popleft()

        if node_id in visited:

            continue

        visited.add(node_id)

        for nxt in outbound.get(node_id, []):

            if nxt not in visited:

                queue.append(nxt)

    return visited





def validate_for_publish(adventure: Adventure) -> ValidationResult:

    """Blocking publish validation per data-model.md."""

    result = ValidationResult(ok_to_publish=True)

    nodes = list(adventure.nodes)

    edges = list(adventure.edges)



    if not nodes:

        result.errors.append(

            {"code": "NO_NODES", "message": "Adventure must contain at least one node."}

        )



    outbound, inbound = _build_adjacency(nodes, edges)

    start_nodes = [n for n in nodes if n.is_start or not inbound[n.id]]

    if not start_nodes:

        result.errors.append(

            {"code": "NO_START_NODE", "message": "Adventure must have at least one start node."}

        )



    reachable = _reachable_from_starts(nodes, outbound, inbound)

    for node in nodes:

        if node.is_end and node.id not in reachable:

            result.errors.append(

                {

                    "code": "END_UNREACHABLE",

                    "message": f"Node '{node.slug}' is not reachable from any start.",

                    "node_slug": node.slug,

                }

            )

        if not node.is_optional and node.id not in reachable and nodes:

            result.errors.append(

                {

                    "code": "ORPHAN_NODE",

                    "message": f"Non-optional node '{node.slug}' is unreachable.",

                    "node_slug": node.slug,

                }

            )



    for node in nodes:

        if node.node_type == NodeType.CHOICE.value:

            out = [e for e in edges if e.from_node_id == node.id]

            choice_keys = {

                e.condition_data.get("choice_key")

                for e in out

                if e.condition_type == EdgeConditionType.CHOICE.value

            }

            if len(out) < 2 or len(choice_keys) < 2:

                result.warnings.append(

                    {

                        "code": "CHOICE_FEW_OUTBOUND",

                        "message": "Choice node has fewer than 2 outbound edges.",

                        "node_slug": node.slug,

                    }

                )

        if node.node_type in (NodeType.BATTLE.value, NodeType.BOSS.value) and not node.monster_id:

            result.warnings.append(

                {

                    "code": "BATTLE_NO_MONSTER",

                    "message": "Battle node has no monster configured.",

                    "node_slug": node.slug,

                }

            )

        if node.node_type == NodeType.QUIZ.value and not node.question_set_id:

            result.warnings.append(

                {

                    "code": "QUIZ_NO_QUESTION_SET",

                    "message": "Quiz node has no question set configured.",

                    "node_slug": node.slug,

                }

            )



    if result.errors:

        result.ok_to_publish = False

    return result





# ---------------------------------------------------------------------------

# Unlock recomputation (T018)

# ---------------------------------------------------------------------------





def _edge_field(edge, name: str):

    return edge.get(name) if isinstance(edge, dict) else getattr(edge, name)





def _edge_condition_satisfied(

    edge,

    source_progress: Optional[CharacterNodeProgress],

) -> bool:

    if source_progress is None:

        return False

    if source_progress.status != NodeProgressStatus.COMPLETED.value:

        return False



    ctype = _edge_field(edge, "condition_type")

    data = _edge_field(edge, "condition_data") or {}



    if ctype == EdgeConditionType.ALWAYS.value:

        return True

    if ctype == EdgeConditionType.CHOICE.value:

        return source_progress.choice_made == data.get("choice_key")

    if ctype == EdgeConditionType.CRITERIA.value:

        if data.get("min_score_percent") is not None:

            if source_progress.score is None:

                return False

            if source_progress.score < data["min_score_percent"]:

                return False

        if data.get("no_failed_attempts"):

            if source_progress.attempts > 1 and source_progress.status == NodeProgressStatus.FAILED.value:

                return False

        if data.get("completed_within_seconds") and source_progress.started_at and source_progress.completed_at:

            elapsed = (source_progress.completed_at - source_progress.started_at).total_seconds()

            if elapsed > data["completed_within_seconds"]:

                return False

        return True

    return False





def _inbound_unlock_satisfied(

    node_id: int,

    inbound_edges: List[AdventureEdge],

    progress_by_node: Dict[int, CharacterNodeProgress],

) -> bool:

    if not inbound_edges:

        return True



    and_edges = [

        e for e in inbound_edges if _edge_field(e, "unlock_semantics") == UnlockSemantics.AND.value

    ]

    or_edges = [

        e for e in inbound_edges if _edge_field(e, "unlock_semantics") == UnlockSemantics.OR.value

    ]



    and_ok = all(

        _edge_condition_satisfied(

            e, progress_by_node.get(_edge_field(e, "from_node_id"))

        )

        for e in and_edges

    )

    or_ok = not or_edges or any(

        _edge_condition_satisfied(

            e, progress_by_node.get(_edge_field(e, "from_node_id"))

        )

        for e in or_edges

    )

    return and_ok and or_ok





def recompute_unlocks_for_character(

    character,

    adventure: Adventure,

    *,

    progress: Optional[CharacterAdventureProgress] = None,

    session=None,

) -> List[int]:

    """Re-evaluate locked/available nodes; returns newly unlocked node ids."""

    if session is None:

        session = db.session



    graph = get_resolved_graph(adventure, progress)

    nodes = graph["nodes"]

    edges = graph["edges"]

    inbound_map: Dict[int, List[AdventureEdge]] = defaultdict(list)

    for edge in edges:

        to_id = edge["to_node_id"] if isinstance(edge, dict) else edge.to_node_id

        inbound_map[to_id].append(edge)



    progress_rows = CharacterNodeProgress.query.filter_by(character_id=character.id).join(

        AdventureNode, AdventureNode.id == CharacterNodeProgress.node_id

    ).filter(AdventureNode.adventure_id == adventure.id).all()



    progress_by_node = {row.node_id: row for row in progress_rows}

    node_ids = {_play_node_id(n) for n in nodes}



    newly_unlocked: List[int] = []

    visited: Set[int] = set()



    for node in nodes:

        nid = _play_node_id(node)

        if nid in visited:

            continue

        visited.add(nid)



        row = progress_by_node.get(nid)

        if row and row.status in (

            NodeProgressStatus.COMPLETED.value,

            NodeProgressStatus.IN_PROGRESS.value,

            NodeProgressStatus.SKIPPED.value,

        ):

            continue



        should_unlock = _inbound_unlock_satisfied(nid, inbound_map[nid], progress_by_node)

        if not inbound_map[nid] and (_play_node_is_start(node) or not inbound_map[nid]):

            should_unlock = True



        if should_unlock:

            if row is None:

                row = CharacterNodeProgress(

                    character_id=character.id,

                    node_id=nid,

                    status=NodeProgressStatus.AVAILABLE.value,

                )

                session.add(row)

                progress_by_node[nid] = row

                newly_unlocked.append(nid)

            elif row.status == NodeProgressStatus.LOCKED.value:

                row.status = NodeProgressStatus.AVAILABLE.value

                newly_unlocked.append(nid)

            elif row.status == NodeProgressStatus.FAILED.value:

                row.status = NodeProgressStatus.AVAILABLE.value

                newly_unlocked.append(nid)



    return newly_unlocked





def mark_unvisited_optional_nodes_skipped(

    character,

    adventure: Adventure,

    *,

    progress: Optional[CharacterAdventureProgress] = None,

    session=None,

) -> List[int]:

    """Mark optional nodes the student never visited as skipped."""

    if session is None:

        session = db.session



    skip_statuses = {

        NodeProgressStatus.LOCKED.value,

        NodeProgressStatus.AVAILABLE.value,

        NodeProgressStatus.FAILED.value,

    }

    skipped_ids: List[int] = []

    graph = get_resolved_graph(adventure, progress)

    for node in graph["nodes"]:

        if not _play_node_is_optional(node):

            continue

        nid = _play_node_id(node)

        row = CharacterNodeProgress.query.filter_by(

            character_id=character.id,

            node_id=nid,

        ).first()

        if row is None:

            row = CharacterNodeProgress(

                character_id=character.id,

                node_id=nid,

                status=NodeProgressStatus.SKIPPED.value,

            )

            session.add(row)

            skipped_ids.append(nid)

        elif row.status in skip_statuses:

            row.status = NodeProgressStatus.SKIPPED.value

            skipped_ids.append(nid)

    return skipped_ids





def evaluate_adventure_complete(

    adventure: Adventure,

    character,

    *,

    progress: Optional[CharacterAdventureProgress] = None,

) -> bool:

    """Return True when end-semantics are satisfied for this character."""

    graph = get_resolved_graph(adventure, progress)

    end_nodes = [

        n for n in graph["nodes"] if _play_node_is_end(n) and not _play_node_is_optional(n)

    ]

    if not end_nodes:

        return False



    completed_ids = {

        row.node_id

        for row in CharacterNodeProgress.query.filter_by(

            character_id=character.id,

            status=NodeProgressStatus.COMPLETED.value,

        ).all()

    }



    end_semantics = graph["end_semantics"]

    if end_semantics == EndSemantics.ANY.value:

        return any(_play_node_id(n) in completed_ids for n in end_nodes)

    return all(_play_node_id(n) in completed_ids for n in end_nodes)





def detect_cycle_node_ids(

    nodes: Iterable[AdventureNode],

    edges: Iterable[AdventureEdge],

) -> Set[int]:

    """Return node ids participating in a directed cycle (for validation/tests)."""

    outbound, _ = _build_adjacency(list(nodes), list(edges))

    WHITE, GRAY, BLACK = 0, 1, 2

    color = {n.id: WHITE for n in nodes}

    cycle_nodes: Set[int] = set()



    def dfs(node_id: int, path: List[int]) -> None:

        color[node_id] = GRAY

        path.append(node_id)

        for nxt in outbound.get(node_id, []):

            if color[nxt] == GRAY:

                idx = path.index(nxt)

                cycle_nodes.update(path[idx:])

            elif color[nxt] == WHITE:

                dfs(nxt, path)

        path.pop()

        color[node_id] = BLACK



    for node in nodes:

        if color[node.id] == WHITE:

            dfs(node.id, [])

    return cycle_nodes





def get_or_create_adventure_progress(

    character,

    adventure: Adventure,

    assignment: Optional[AdventureAssignment] = None,

    *,

    session=None,

) -> CharacterAdventureProgress:

    if session is None:

        session = db.session

    row = CharacterAdventureProgress.query.filter_by(

        character_id=character.id,

        adventure_id=adventure.id,

    ).first()

    if row:

        return row

    row = CharacterAdventureProgress(

        character_id=character.id,

        adventure_id=adventure.id,

        assignment_id=assignment.id if assignment else None,

        status=AdventureProgressStatus.NOT_STARTED.value,

    )

    session.add(row)

    return row


def clone_adventure(source: Adventure, new_owner: User, *, title: Optional[str] = None) -> Adventure:
    """Deep-clone an adventure graph into a new draft owned by new_owner."""
    from app.models.adventure import NodeConsequence, NodeReward

    clone = Adventure(
        title=title or f"{source.title} (copy)",
        description=source.description,
        teacher_id=new_owner.id,
        background_image_url=source.background_image_url,
        theme=source.theme,
        width=source.width,
        height=source.height,
        status=AdventureStatus.DRAFT.value,
        is_public=False,
        end_semantics=source.end_semantics,
        version=1,
    )
    db.session.add(clone)
    db.session.flush()

    node_id_map: Dict[int, int] = {}
    for node in source.nodes.all():
        new_node = AdventureNode(
            adventure_id=clone.id,
            slug=node.slug,
            title=node.title,
            description=node.description,
            lore=node.lore,
            icon_url=node.icon_url,
            node_type=node.node_type,
            x=node.x,
            y=node.y,
            is_optional=node.is_optional,
            is_start=node.is_start,
            is_end=node.is_end,
            question_set_id=node.question_set_id,
            monster_id=node.monster_id,
            completion_rules=dict(node.completion_rules or {}),
            on_complete_actions=dict(node.on_complete_actions or {}),
        )
        db.session.add(new_node)
        db.session.flush()
        node_id_map[node.id] = new_node.id

        for reward in node.rewards.all():
            db.session.add(
                NodeReward(
                    node_id=new_node.id,
                    type=reward.type,
                    amount=reward.amount,
                    item_id=reward.item_id,
                    ability_id=reward.ability_id,
                    badge_id=reward.badge_id,
                    is_conditional=reward.is_conditional,
                    condition_json=dict(reward.condition_json or {}),
                )
            )
        for consequence in node.consequences.all():
            db.session.add(
                NodeConsequence(
                    node_id=new_node.id,
                    description=consequence.description,
                    xp_penalty=consequence.xp_penalty,
                    gold_penalty=consequence.gold_penalty,
                    hp_penalty=consequence.hp_penalty,
                    custom_json=dict(consequence.custom_json or {}),
                )
            )

    for edge in source.edges.all():
        db.session.add(
            AdventureEdge(
                adventure_id=clone.id,
                from_node_id=node_id_map[edge.from_node_id],
                to_node_id=node_id_map[edge.to_node_id],
                label=edge.label,
                condition_type=edge.condition_type,
                condition_data=dict(edge.condition_data or {}),
                unlock_semantics=edge.unlock_semantics,
                sort_order=edge.sort_order,
            )
        )

    db.session.commit()
    return clone


# ---------------------------------------------------------------------------
# Teacher progress roster (T068)
# ---------------------------------------------------------------------------


ADVENTURE_AUDIT_EVENT_TYPES = (
    "ADVENTURE_NODE_START",
    "ADVENTURE_NODE_COMPLETE",
    "ADVENTURE_COMPLETE",
)


def _resolve_roster_characters(
    adventure: Adventure,
    *,
    classroom_id: Optional[int] = None,
) -> List[Tuple["Character", "Student"]]:
    """Return (character, student) pairs from active assignments."""
    from app.models.character import Character
    from app.models.student import Student

    query = AdventureAssignment.query.filter_by(
        adventure_id=adventure.id,
        is_active=True,
    )
    if classroom_id is not None:
        query = query.filter_by(classroom_id=classroom_id)
    assignments = query.all()

    roster: Dict[int, Tuple[Character, Student]] = {}
    for assignment in assignments:
        if assignment.classroom_id:
            students = Student.query.filter_by(class_id=assignment.classroom_id).all()
            student_ids = [s.id for s in students]
            char_by_student: Dict[int, Character] = {}
            if student_ids:
                for character in Character.query.filter(
                    Character.student_id.in_(student_ids),
                    Character.is_active.is_(True),
                ).all():
                    char_by_student.setdefault(character.student_id, character)
            for student in students:
                character = char_by_student.get(student.id)
                if character and character.id not in roster:
                    roster[character.id] = (character, student)
        elif assignment.character_id:
            character = db.session.get(Character, assignment.character_id)
            if character and character.student and character.id not in roster:
                roster[character.id] = (character, character.student)
        elif assignment.clan_id:
            for character in Character.query.filter_by(
                clan_id=assignment.clan_id, is_active=True
            ).all():
                if character.student and character.id not in roster:
                    roster[character.id] = (character, character.student)
    return list(roster.values())


def aggregate_adventure_progress_roster(
    adventure: Adventure,
    teacher: User,
    *,
    classroom_id: Optional[int] = None,
) -> dict:
    """Build per-student progress roster without per-student N+1 queries."""
    require_teacher_edit(teacher, adventure)
    if classroom_id is not None:
        require_teacher_classroom(teacher, classroom_id)
        assigned = AdventureAssignment.query.filter_by(
            adventure_id=adventure.id,
            classroom_id=classroom_id,
            is_active=True,
        ).first()
        if not assigned:
            raise AuthorizationError(
                "NOT_FOUND", "Adventure is not assigned to this classroom."
            )

    roster = _resolve_roster_characters(adventure, classroom_id=classroom_id)
    char_ids = [char.id for char, _ in roster]
    empty_summary = {
        "total_students": 0,
        "not_started": 0,
        "in_progress": 0,
        "completed": 0,
    }
    if not char_ids:
        return {"students": [], "summary": empty_summary}

    node_ids = [n.id for n in adventure.nodes.all()]
    total_nodes = len(node_ids)

    progress_rows = CharacterAdventureProgress.query.filter(
        CharacterAdventureProgress.adventure_id == adventure.id,
        CharacterAdventureProgress.character_id.in_(char_ids),
    ).all()
    progress_by_char = {row.character_id: row for row in progress_rows}

    from sqlalchemy import func

    count_query = (
        db.session.query(
            CharacterNodeProgress.character_id,
            CharacterNodeProgress.status,
            func.count(CharacterNodeProgress.id),
        )
        .filter(CharacterNodeProgress.character_id.in_(char_ids))
    )
    if node_ids:
        count_query = count_query.filter(CharacterNodeProgress.node_id.in_(node_ids))
    count_rows = count_query.group_by(
        CharacterNodeProgress.character_id,
        CharacterNodeProgress.status,
    ).all()

    counts_by_char: Dict[int, Dict[str, int]] = {}
    for cid, status, cnt in count_rows:
        bucket = counts_by_char.setdefault(
            cid,
            {"completed": 0, "available": 0, "locked": 0, "failed": 0, "skipped": 0},
        )
        if status in bucket:
            bucket[status] = cnt

    for cid in char_ids:
        bucket = counts_by_char.setdefault(
            cid,
            {"completed": 0, "available": 0, "locked": 0, "failed": 0, "skipped": 0},
        )
        tracked = sum(bucket.values())
        bucket["locked"] += max(0, total_nodes - tracked)

    current_node_ids = {
        row.current_node_id for row in progress_rows if row.current_node_id
    }
    current_nodes: Dict[int, AdventureNode] = {}
    if current_node_ids:
        for node in AdventureNode.query.filter(
            AdventureNode.id.in_(current_node_ids)
        ).all():
            current_nodes[node.id] = node

    from app.models.audit import AuditLog

    audit_rows = (
        AuditLog.query.filter(
            AuditLog.character_id.in_(char_ids),
            AuditLog.event_type.in_(ADVENTURE_AUDIT_EVENT_TYPES),
        )
        .order_by(AuditLog.event_timestamp.desc())
        .all()
    )
    events_by_char: Dict[int, List[dict]] = defaultdict(list)
    for log in audit_rows:
        data = log.event_data or {}
        if data.get("adventure_id") != adventure.id:
            continue
        bucket = events_by_char[log.character_id]
        if len(bucket) >= 5:
            continue
        bucket.append(
            {
                "event_type": log.event_type,
                "node_slug": data.get("node_slug"),
                "score": data.get("score"),
                "timestamp": (
                    log.event_timestamp.isoformat() if log.event_timestamp else None
                ),
            }
        )

    students: List[dict] = []
    summary = {"not_started": 0, "in_progress": 0, "completed": 0}
    for character, student in roster:
        progress = progress_by_char.get(character.id)
        status = (
            progress.status
            if progress
            else AdventureProgressStatus.NOT_STARTED.value
        )
        if status == AdventureProgressStatus.NOT_STARTED.value:
            summary["not_started"] += 1
        elif status == AdventureProgressStatus.COMPLETED.value:
            summary["completed"] += 1
        elif status == AdventureProgressStatus.IN_PROGRESS.value:
            summary["in_progress"] += 1
        else:
            summary["not_started"] += 1

        current_node = None
        if progress and progress.current_node_id in current_nodes:
            node = current_nodes[progress.current_node_id]
            current_node = {
                "id": node.id,
                "slug": node.slug,
                "title": node.title,
                "node_type": node.node_type,
            }

        node_counts = counts_by_char.get(
            character.id,
            {
                "completed": 0,
                "available": 0,
                "locked": total_nodes,
                "failed": 0,
                "skipped": 0,
            },
        )
        students.append(
            {
                "user_id": student.user_id,
                "character_id": character.id,
                "name": character.name,
                "classroom_id": student.class_id,
                "status": status,
                "current_node": current_node,
                "node_counts": node_counts,
                "last_active_at": (
                    progress.last_active_at.isoformat()
                    if progress and progress.last_active_at
                    else None
                ),
                "recent_events": events_by_char.get(character.id, []),
                "has_failures": node_counts.get("failed", 0) > 0,
                "has_consequences": node_counts.get("failed", 0) > 0,
            }
        )

    summary["total_students"] = len(students)
    return {"students": students, "summary": summary}


def force_complete_adventure(
    teacher: User,
    adventure: Adventure,
    character,
    *,
    reason: Optional[str] = None,
    session=None,
) -> dict:
    """Teacher override: mark a student's adventure complete with audit logging."""
    if session is None:
        session = db.session

    require_teacher_edit(teacher, adventure)
    student = character.student
    if not student or not student.class_id:
        raise AuthorizationError("FORBIDDEN", "Student is not in a classroom.")

    require_teacher_classroom(teacher, student.class_id)

    assignment_filters = [
        AdventureAssignment.classroom_id == student.class_id,
        AdventureAssignment.character_id == character.id,
    ]
    if character.clan_id:
        assignment_filters.append(AdventureAssignment.clan_id == character.clan_id)

    assignment = AdventureAssignment.query.filter(
        AdventureAssignment.adventure_id == adventure.id,
        AdventureAssignment.is_active.is_(True),
        db.or_(*assignment_filters),
    ).first()
    if not assignment:
        raise AuthorizationError(
            "FORBIDDEN", "Student is not assigned to this adventure."
        )

    progress = get_or_create_adventure_progress(
        character, adventure, assignment, session=session
    )
    if progress.status == AdventureProgressStatus.COMPLETED.value:
        return {
            "character_id": character.id,
            "status": progress.status,
            "completed_at": progress.completed_at,
            "forced_by": teacher.id,
        }

    progress.status = AdventureProgressStatus.COMPLETED.value
    progress.completed_at = get_utc_now()
    progress.last_active_at = get_utc_now()
    mark_unvisited_optional_nodes_skipped(character, adventure, session=session)

    from app.models.audit import AuditLog, EventType

    session.add(
        AuditLog(
            event_type=EventType.ADVENTURE_COMPLETE.value,
            event_data={
                "adventure_id": adventure.id,
                "forced_by": teacher.id,
                "reason": reason,
                "source": "teacher_force_complete",
            },
            user_id=teacher.id,
            character_id=character.id,
        )
    )
    return {
        "character_id": character.id,
        "status": progress.status,
        "completed_at": progress.completed_at,
        "forced_by": teacher.id,
    }


