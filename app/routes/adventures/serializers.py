"""JSON serialization helpers for Adventures API responses."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.models.adventure import (
    Adventure,
    AdventureEdge,
    AdventureNode,
    AdventureStatus,
    NodeConsequence,
    NodeReward,
)
from app.models.adventure_progress import (
    AdventureAssignment,
    AdventureProgressStatus,
    CharacterAdventureProgress,
    CharacterNodeProgress,
    NodeProgressStatus,
)
from app.models.user import User


def _owner_summary(user: Optional[User]) -> Optional[dict]:
    if user is None:
        return None
    name = user.display_name or user.username or f"User {user.id}"
    return {"id": user.id, "name": name}


def adventure_summary(
    adventure: Adventure,
    *,
    node_count: Optional[int] = None,
    edge_count: Optional[int] = None,
    assignment_count: Optional[int] = None,
) -> dict:
    owner = adventure.teacher
    return {
        "id": adventure.id,
        "title": adventure.title,
        "description": adventure.description,
        "status": adventure.status,
        "is_public": adventure.is_public,
        "version": adventure.version,
        "theme": adventure.theme,
        "width": adventure.width,
        "height": adventure.height,
        "end_semantics": adventure.end_semantics,
        "background_image_url": adventure.background_image_url,
        "owner": _owner_summary(owner),
        "node_count": node_count if node_count is not None else adventure.nodes.count(),
        "edge_count": edge_count if edge_count is not None else adventure.edges.count(),
        "assignment_count": (
            assignment_count
            if assignment_count is not None
            else adventure.assignments.filter_by(is_active=True).count()
        ),
        "created_at": getattr(adventure, "created_at", None),
        "updated_at": getattr(adventure, "updated_at", None),
    }


def reward_dict(reward: NodeReward) -> dict:
    return {
        "id": reward.id,
        "type": reward.type,
        "amount": reward.amount,
        "item_id": reward.item_id,
        "ability_id": reward.ability_id,
        "badge_id": reward.badge_id,
        "is_conditional": reward.is_conditional,
        "condition_json": reward.condition_json or {},
    }


def consequence_dict(consequence: NodeConsequence) -> dict:
    return {
        "id": consequence.id,
        "description": consequence.description,
        "xp_penalty": consequence.xp_penalty,
        "gold_penalty": consequence.gold_penalty,
        "hp_penalty": consequence.hp_penalty,
        "custom_json": consequence.custom_json or {},
    }


def node_dict(node: AdventureNode, *, include_children: bool = True) -> dict:
    payload = {
        "id": node.id,
        "slug": node.slug,
        "title": node.title,
        "description": node.description,
        "lore": node.lore,
        "icon_url": node.icon_url,
        "node_type": node.node_type,
        "x": node.x,
        "y": node.y,
        "is_optional": node.is_optional,
        "is_start": node.is_start,
        "is_end": node.is_end,
        "question_set_id": node.question_set_id,
        "monster_id": node.monster_id,
        "completion_rules": node.completion_rules or {},
        "on_complete_actions": node.on_complete_actions or {},
    }
    if include_children:
        payload["rewards"] = [reward_dict(r) for r in node.rewards.all()]
        payload["consequences"] = [consequence_dict(c) for c in node.consequences.all()]
    return payload


def edge_dict(edge: AdventureEdge) -> dict:
    return {
        "id": edge.id,
        "from_node_id": edge.from_node_id,
        "to_node_id": edge.to_node_id,
        "label": edge.label,
        "condition_type": edge.condition_type,
        "condition_data": edge.condition_data or {},
        "unlock_semantics": edge.unlock_semantics,
        "sort_order": edge.sort_order,
    }


def assignment_dict(
    assignment: AdventureAssignment,
    *,
    classroom_name: Optional[str] = None,
    progress_url: Optional[str] = None,
) -> dict:
    data = {
        "id": assignment.id,
        "adventure_id": assignment.adventure_id,
        "adventure_version": assignment.adventure_version,
        "classroom_id": assignment.classroom_id,
        "clan_id": assignment.clan_id,
        "character_id": assignment.character_id,
        "assigned_by_user_id": assignment.assigned_by_user_id,
        "starts_at": assignment.starts_at,
        "ends_at": assignment.ends_at,
        "is_active": assignment.is_active,
    }
    if classroom_name is not None:
        data["classroom_name"] = classroom_name
    if progress_url is not None:
        data["progress_url"] = progress_url
    return data


def node_progress_dict(row: CharacterNodeProgress) -> dict:
    return {
        "node_id": row.node_id,
        "status": row.status,
        "attempts": row.attempts,
        "score": row.score,
        "choice_made": row.choice_made,
        "started_at": row.started_at,
        "completed_at": row.completed_at,
    }


def node_status_dict(
    node: AdventureNode,
    row: Optional[CharacterNodeProgress],
) -> dict:
    status = row.status if row else NodeProgressStatus.LOCKED.value
    return {
        "id": node.id,
        "slug": node.slug,
        "title": node.title,
        "node_type": node.node_type,
        "status": status,
        "attempts": row.attempts if row else 0,
        "score": row.score if row else None,
        "choice_made": row.choice_made if row else None,
        "started_at": row.started_at if row else None,
        "completed_at": row.completed_at if row else None,
    }


def rewards_preview(node: AdventureNode) -> List[dict]:
    previews = []
    for reward in node.rewards.all():
        item = {
            "type": reward.type,
            "amount": reward.amount,
            "is_conditional": reward.is_conditional,
        }
        if reward.badge_id and reward.badge:
            item["badge_id"] = reward.badge_id
            item["badge_name"] = reward.badge.name
        condition = reward.condition_json or {}
        if reward.is_conditional and condition.get("min_score_percent"):
            item["condition_summary"] = f"Score {condition['min_score_percent']}%."
        previews.append(item)
    return previews


def assignment_window_status(assignment: AdventureAssignment) -> str:
    from app.utils.date_utils import get_utc_now

    now = get_utc_now()
    if assignment.starts_at and now < assignment.starts_at:
        return "not_started_yet"
    if assignment.ends_at and now > assignment.ends_at:
        return "ended"
    return "active"


def adventure_progress_summary(
    adventure: Adventure,
    progress: Optional[CharacterAdventureProgress],
    *,
    character,
) -> dict:
    from app.models.adventure import AdventureNode
    from app.models.adventure_progress import CharacterNodeProgress

    if progress is None:
        return {
            "status": AdventureProgressStatus.NOT_STARTED.value,
            "current_node": None,
            "node_counts": {
                "completed": 0,
                "available": 0,
                "locked": adventure.nodes.count(),
                "failed": 0,
                "skipped": 0,
            },
            "started_at": None,
            "last_active_at": None,
        }

    node_ids = [n.id for n in adventure.nodes.all()]
    rows = (
        CharacterNodeProgress.query.filter_by(character_id=character.id)
        .filter(CharacterNodeProgress.node_id.in_(node_ids))
        .all()
        if node_ids
        else []
    )
    counts = {
        "completed": 0,
        "available": 0,
        "locked": 0,
        "failed": 0,
        "skipped": 0,
    }
    for row in rows:
        key = row.status
        if key in counts:
            counts[key] += 1
    counts["locked"] += max(0, len(node_ids) - len(rows))

    current = None
    if progress.current_node_id:
        node = AdventureNode.query.get(progress.current_node_id)
        if node:
            current = {"id": node.id, "slug": node.slug, "title": node.title}

    return {
        "status": progress.status,
        "current_node": current,
        "node_counts": counts,
        "started_at": progress.started_at,
        "last_active_at": progress.last_active_at,
    }
