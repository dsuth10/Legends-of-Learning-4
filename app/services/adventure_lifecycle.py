"""Student node lifecycle: start, complete, retry, and adventure progress updates."""

from __future__ import annotations

from typing import List, Optional, Tuple

from app.models import db
from app.models.adventure import Adventure, AdventureNode, NodeType
from app.models.adventure_progress import (
    AdventureAssignment,
    AdventureProgressStatus,
    CharacterAdventureProgress,
    CharacterNodeProgress,
    NodeProgressStatus,
)
from app.models.audit import AuditLog, EventType
from app.models.battle import Battle, BattleStatus
from app.models.education import QuestionSet
from app.services.adventure_graph import (
    AuthorizationError,
    ensure_progress_snapshot,
    evaluate_adventure_complete,
    get_or_create_adventure_progress,
    mark_unvisited_optional_nodes_skipped,
    recompute_unlocks_for_character,
    require_student_assignment,
)
from app.services.adventure_rewards import distribute_node_rewards
from app.utils.date_utils import get_utc_now


class LifecycleError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


COMPLETABLE_TYPES = {
    NodeType.START.value,
    NodeType.STORY.value,
    NodeType.REWARD.value,
    NodeType.MILESTONE.value,
    NodeType.END.value,
}


def _require_active_window(assignment: AdventureAssignment) -> None:
    from app.routes.adventures.serializers import assignment_window_status

    status = assignment_window_status(assignment)
    if status == "not_started_yet":
        raise LifecycleError("ADVENTURE_NOT_STARTED_YET", "This adventure has not started yet.")
    if status == "ended":
        raise LifecycleError("ADVENTURE_ENDED", "This adventure has ended.")


def _get_node_progress(
    character,
    node: AdventureNode,
    *,
    session,
) -> CharacterNodeProgress:
    row = CharacterNodeProgress.query.filter_by(
        character_id=character.id,
        node_id=node.id,
    ).first()
    if row is None:
        row = CharacterNodeProgress(
            character_id=character.id,
            node_id=node.id,
            status=NodeProgressStatus.LOCKED.value,
        )
        session.add(row)
    return row


def ensure_adventure_bootstrapped(
    character,
    adventure: Adventure,
    assignment: AdventureAssignment,
    *,
    session=None,
) -> CharacterAdventureProgress:
    if session is None:
        session = db.session
    progress = get_or_create_adventure_progress(
        character, adventure, assignment, session=session
    )
    if progress.status == AdventureProgressStatus.NOT_STARTED.value:
        progress.status = AdventureProgressStatus.IN_PROGRESS.value
        progress.started_at = get_utc_now()
    progress.last_active_at = get_utc_now()
    ensure_progress_snapshot(progress, adventure, assignment)
    recompute_unlocks_for_character(
        character, adventure, progress=progress, session=session
    )
    return progress


def start_node(
    character,
    adventure: Adventure,
    node: AdventureNode,
    assignment: AdventureAssignment,
    *,
    session=None,
) -> dict:
    if session is None:
        session = db.session

    _require_active_window(assignment)
    progress = ensure_adventure_bootstrapped(character, adventure, assignment, session=session)
    row = _get_node_progress(character, node, session=session)

    if row.status == NodeProgressStatus.COMPLETED.value:
        return _node_payload(node, row)

    if row.status not in (
        NodeProgressStatus.AVAILABLE.value,
        NodeProgressStatus.IN_PROGRESS.value,
        NodeProgressStatus.FAILED.value,
    ):
        raise LifecycleError("NODE_LOCKED", "This node is not available.")

    max_attempts = (node.completion_rules or {}).get("max_attempts")
    if max_attempts and row.attempts >= max_attempts and row.status != NodeProgressStatus.IN_PROGRESS.value:
        raise LifecycleError("NODE_MAX_ATTEMPTS_REACHED", "Maximum attempts reached for this node.")

    if row.status != NodeProgressStatus.IN_PROGRESS.value:
        row.status = NodeProgressStatus.IN_PROGRESS.value
        row.attempts = (row.attempts or 0) + 1
        row.started_at = row.started_at or get_utc_now()

    progress.current_node_id = node.id
    progress.last_active_at = get_utc_now()

    result = _node_payload(node, row)

    if node.node_type == NodeType.BATTLE.value:
        battle_payload = _start_battle_for_node(character, node, session=session)
        result.update(battle_payload)
    elif node.node_type == NodeType.QUIZ.value:
        result["redirect_url"] = (
            f"/student/adventures/{adventure.id}/nodes/{node.slug}/quiz"
        )
    elif node.node_type == NodeType.CHOICE.value:
        result["outgoing_choices"] = _outgoing_choices(node)

    session.add(
        AuditLog(
            event_type=EventType.ADVENTURE_NODE_START.value,
            event_data={
                "adventure_id": adventure.id,
                "node_id": node.id,
                "node_slug": node.slug,
            },
            user_id=character.student.user_id if character.student else None,
            character_id=character.id,
        )
    )
    return result


def _start_battle_for_node(character, node: AdventureNode, *, session) -> dict:
    from app.models.student import Student

    if not node.monster_id:
        raise LifecycleError("VALIDATION_ERROR", "Battle node has no monster configured.")

    student = character.student
    if not student:
        raise LifecycleError("NOT_FOUND", "Student profile not found.")

    question_set = None
    if node.question_set_id:
        question_set = QuestionSet.query.filter_by(
            id=node.question_set_id, is_active=True
        ).first()
    if question_set is None:
        question_set = QuestionSet.query.filter_by(is_active=True).first()
    if not question_set or question_set.questions.count() == 0:
        raise LifecycleError(
            "VALIDATION_ERROR",
            "No active question set available for battle.",
        )

    from app.models.battle import Monster

    monster = Monster.query.get(node.monster_id)
    mhp = monster.health if monster else 100

    battle = Battle(
        student_id=student.id,
        monster_id=node.monster_id,
        question_set_id=question_set.id,
        player_health=character.health,
        player_max_health=character.max_health,
        monster_health=mhp,
        monster_max_health=mhp,
        status=BattleStatus.ACTIVE,
        turn_log=[],
        adventure_node_id=node.id,
    )
    session.add(battle)
    session.flush()

    row = _get_node_progress(character, node, session=session)
    pdata = dict(row.progress_data or {})
    pdata["battle_id"] = battle.id
    row.progress_data = pdata

    return {
        "redirect_url": f"/student/battle/{battle.id}",
        "battle_id": battle.id,
    }


def complete_node(
    character,
    adventure: Adventure,
    node: AdventureNode,
    assignment: AdventureAssignment,
    *,
    score: Optional[int] = None,
    session=None,
) -> dict:
    if session is None:
        session = db.session

    _require_active_window(assignment)

    if node.node_type == NodeType.CHOICE.value:
        raise LifecycleError("CHOICE_REQUIRED", "Use /choose for choice nodes.")
    if node.node_type in (NodeType.BATTLE.value, NodeType.BOSS.value, NodeType.QUIZ.value):
        raise LifecycleError(
            "VALIDATION_ERROR",
            f"Node type '{node.node_type}' cannot be completed via this endpoint.",
        )
    if node.node_type not in COMPLETABLE_TYPES:
        raise LifecycleError("VALIDATION_ERROR", f"Cannot complete node type '{node.node_type}'.")

    progress = ensure_adventure_bootstrapped(
        character, adventure, assignment, session=session
    )
    row = _get_node_progress(character, node, session=session)

    if row.status == NodeProgressStatus.COMPLETED.value:
        return _completion_response(
            character,
            adventure,
            node,
            row,
            progress=progress,
            session=session,
            first_time=False,
        )

    if row.status != NodeProgressStatus.IN_PROGRESS.value:
        if row.status == NodeProgressStatus.AVAILABLE.value:
            row.status = NodeProgressStatus.IN_PROGRESS.value
            row.attempts = max(1, row.attempts or 0) + 1
            row.started_at = row.started_at or get_utc_now()
        else:
            raise LifecycleError("NODE_LOCKED", "This node is not in progress.")

    row.status = NodeProgressStatus.COMPLETED.value
    row.completed_at = get_utc_now()
    if score is not None:
        row.score = score

    rewards = distribute_node_rewards(
        character, node, score=row.score, session=session, commit=False
    )

    newly_unlocked = recompute_unlocks_for_character(
        character, adventure, progress=progress, session=session
    )
    adventure_complete = _finalize_adventure_if_done(
        character, adventure, assignment, progress=progress, session=session
    )

    session.add(
        AuditLog(
            event_type=EventType.ADVENTURE_NODE_COMPLETE.value,
            event_data={
                "adventure_id": adventure.id,
                "node_id": node.id,
                "node_slug": node.slug,
                "score": row.score,
            },
            user_id=character.student.user_id if character.student else None,
            character_id=character.id,
        )
    )

    return {
        "node": _node_payload(node, row)["node"],
        "rewards_distributed": rewards,
        "next_unlocked": _unlocked_summaries(adventure, newly_unlocked),
        "adventure_complete": adventure_complete,
    }


def complete_node_from_battle(
    character,
    node: AdventureNode,
    *,
    session=None,
) -> Optional[dict]:
    """Called from adventure_hooks when a linked battle is won."""
    if session is None:
        session = db.session

    adventure = node.adventure
    try:
        assignment = require_student_assignment(character, adventure.id)
    except AuthorizationError:
        return None

    row = _get_node_progress(character, node, session=session)
    if row.status == NodeProgressStatus.COMPLETED.value:
        return None

    row.status = NodeProgressStatus.COMPLETED.value
    row.completed_at = get_utc_now()
    row.started_at = row.started_at or get_utc_now()
    if row.attempts == 0:
        row.attempts = 1

    distribute_node_rewards(character, node, session=session, commit=False)
    progress = get_or_create_adventure_progress(
        character, adventure, assignment, session=session
    )
    newly_unlocked = recompute_unlocks_for_character(
        character, adventure, progress=progress, session=session
    )
    _finalize_adventure_if_done(
        character, adventure, assignment, progress=progress, session=session
    )

    session.add(
        AuditLog(
            event_type=EventType.ADVENTURE_NODE_COMPLETE.value,
            event_data={
                "adventure_id": adventure.id,
                "node_id": node.id,
                "node_slug": node.slug,
                "source": "battle",
            },
            user_id=character.student.user_id if character.student else None,
            character_id=character.id,
        )
    )
    return {"next_unlocked": newly_unlocked}


def retry_node(
    character,
    adventure: Adventure,
    node: AdventureNode,
    assignment: AdventureAssignment,
    *,
    session=None,
) -> dict:
    if session is None:
        session = db.session

    _require_active_window(assignment)
    row = _get_node_progress(character, node, session=session)

    if row.status == NodeProgressStatus.AVAILABLE.value:
        return _node_payload(node, row)

    if row.status != NodeProgressStatus.FAILED.value:
        raise LifecycleError("NODE_LOCKED", "Only failed nodes can be retried.")

    max_attempts = (node.completion_rules or {}).get("max_attempts")
    if max_attempts and row.attempts >= max_attempts:
        raise LifecycleError("NODE_MAX_ATTEMPTS_REACHED", "Maximum attempts reached.")

    row.status = NodeProgressStatus.AVAILABLE.value
    row.score = None
    return _node_payload(node, row)


def _completion_response(
    character,
    adventure: Adventure,
    node: AdventureNode,
    row: CharacterNodeProgress,
    *,
    progress: Optional[CharacterAdventureProgress] = None,
    session,
    first_time: bool,
) -> dict:
    rewards = []
    if first_time:
        rewards = distribute_node_rewards(
            character, node, score=row.score, session=session, commit=False
        )
    else:
        rewards = [
            {
                "type": r.type,
                "amount": r.amount,
                "item_id": r.item_id,
                "ability_id": r.ability_id,
                "badge_id": r.badge_id,
            }
            for r in node.rewards.all()
            if not r.is_conditional
            or (row.score is not None and (r.condition_json or {}).get("min_score_percent", 0) <= row.score)
        ]

    if progress is None:
        progress = CharacterAdventureProgress.query.filter_by(
            character_id=character.id,
            adventure_id=adventure.id,
        ).first()

    newly_unlocked = recompute_unlocks_for_character(
        character, adventure, progress=progress, session=session
    )
    adventure_complete = evaluate_adventure_complete(
        adventure, character, progress=progress
    )

    return {
        "node": _node_payload(node, row)["node"],
        "rewards_distributed": rewards,
        "next_unlocked": _unlocked_summaries(adventure, newly_unlocked),
        "adventure_complete": adventure_complete,
    }


def _finalize_adventure_if_done(
    character,
    adventure: Adventure,
    assignment: AdventureAssignment,
    *,
    progress: Optional[CharacterAdventureProgress] = None,
    session,
) -> bool:
    if progress is None:
        progress = get_or_create_adventure_progress(
            character, adventure, assignment, session=session
        )
    if not evaluate_adventure_complete(adventure, character, progress=progress):
        return False

    if progress.status != AdventureProgressStatus.COMPLETED.value:
        progress.status = AdventureProgressStatus.COMPLETED.value
        progress.completed_at = get_utc_now()
        mark_unvisited_optional_nodes_skipped(
            character, adventure, progress=progress, session=session
        )
        session.add(
            AuditLog(
                event_type=EventType.ADVENTURE_COMPLETE.value,
                event_data={"adventure_id": adventure.id},
                user_id=character.student.user_id if character.student else None,
                character_id=character.id,
            )
        )
    return True


def choose_node(
    character,
    adventure: Adventure,
    node: AdventureNode,
    choice_key: str,
    assignment: AdventureAssignment,
    *,
    session=None,
) -> dict:
    """Record a choice on a choice node, complete it, and unlock matching branches."""
    if session is None:
        session = db.session

    if node.node_type != NodeType.CHOICE.value:
        raise LifecycleError("VALIDATION_ERROR", "Node is not a choice node.")

    _require_active_window(assignment)
    progress = ensure_adventure_bootstrapped(
        character, adventure, assignment, session=session
    )
    row = _get_node_progress(character, node, session=session)

    valid_keys = {
        (e.condition_data or {}).get("choice_key")
        for e in node.outbound_edges.all()
        if e.condition_type == "choice"
    }
    valid_keys.discard(None)
    if choice_key not in valid_keys:
        raise LifecycleError("VALIDATION_ERROR", f"Unknown choice_key '{choice_key}'.")

    if row.status == NodeProgressStatus.COMPLETED.value:
        if row.choice_made == choice_key:
            return _completion_response(
                character,
                adventure,
                node,
                row,
                progress=progress,
                session=session,
                first_time=False,
            )
        raise LifecycleError(
            "CHOICE_ALREADY_MADE",
            "A different choice was already recorded for this node.",
        )

    if row.status not in (
        NodeProgressStatus.AVAILABLE.value,
        NodeProgressStatus.IN_PROGRESS.value,
    ):
        raise LifecycleError("NODE_LOCKED", "This node is not available.")

    if row.status != NodeProgressStatus.IN_PROGRESS.value:
        row.status = NodeProgressStatus.IN_PROGRESS.value
        row.attempts = max(1, (row.attempts or 0) + 1)
        row.started_at = row.started_at or get_utc_now()

    row.choice_made = choice_key
    row.status = NodeProgressStatus.COMPLETED.value
    row.completed_at = get_utc_now()

    progress.current_node_id = node.id
    progress.last_active_at = get_utc_now()

    rewards = distribute_node_rewards(
        character, node, score=row.score, session=session, commit=False
    )
    newly_unlocked = recompute_unlocks_for_character(
        character, adventure, progress=progress, session=session
    )
    adventure_complete = _finalize_adventure_if_done(
        character, adventure, assignment, progress=progress, session=session
    )

    session.add(
        AuditLog(
            event_type=EventType.ADVENTURE_NODE_COMPLETE.value,
            event_data={
                "adventure_id": adventure.id,
                "node_id": node.id,
                "node_slug": node.slug,
                "choice_key": choice_key,
            },
            user_id=character.student.user_id if character.student else None,
            character_id=character.id,
        )
    )

    return {
        "node": _node_payload(node, row)["node"],
        "rewards_distributed": rewards,
        "next_unlocked": _unlocked_summaries(adventure, newly_unlocked),
        "adventure_complete": adventure_complete,
    }


def _node_payload(node: AdventureNode, row: CharacterNodeProgress) -> dict:
    return {
        "node": {
            "id": node.id,
            "slug": node.slug,
            "status": row.status,
            "attempts": row.attempts,
            "score": row.score,
            "choice_made": row.choice_made,
            "started_at": row.started_at,
            "completed_at": row.completed_at,
        }
    }


def _unlocked_summaries(adventure: Adventure, node_ids: List[int]) -> List[dict]:
    if not node_ids:
        return []
    nodes = AdventureNode.query.filter(AdventureNode.id.in_(node_ids)).all()
    return [
        {"id": n.id, "slug": n.slug, "title": n.title, "node_type": n.node_type}
        for n in nodes
    ]


def _outgoing_choices(node: AdventureNode) -> List[dict]:
    from app.models.adventure import EdgeConditionType

    choices = []
    for edge in node.outbound_edges.all():
        if edge.condition_type == EdgeConditionType.CHOICE.value:
            key = (edge.condition_data or {}).get("choice_key")
            if key:
                choices.append({"choice_key": key, "label": edge.label or key})
    return choices
