"""Hooks bridging legacy battle/quiz completion into Adventures node progress."""

from __future__ import annotations

import logging
from typing import Any, Optional

from app.models import db
from app.models.adventure import AdventureNode
from app.models.battle import BattleStatus
from app.services.adventure_lifecycle import complete_node_from_battle

logger = logging.getLogger(__name__)


def on_battle_resolved(battle: Any, *, session=None) -> Optional[dict]:
    """Complete the bound adventure node when a linked battle is won.

    No-op when the battle is not associated with an adventure node.
    """
    if session is None:
        session = db.session

    node_id = getattr(battle, "adventure_node_id", None)
    if not node_id:
        progress_data = getattr(battle, "adventure_progress_data", None)
        if isinstance(progress_data, dict):
            node_id = progress_data.get("node_id")
    if not node_id:
        return None

    if getattr(battle, "status", None) != BattleStatus.WON:
        return None

    node = session.get(AdventureNode, node_id)
    if not node:
        return None

    student = battle.student
    if not student:
        return None

    character = student.characters.filter_by(is_active=True).first()
    if not character:
        return None

    return complete_node_from_battle(character, node, session=session)


def on_quiz_resolved(
    character: Any,
    node_id: int,
    *,
    score: int,
    session=None,
) -> Optional[dict]:
    """Hook entry point for quiz resolution (wired from adventure_quiz)."""
    if not node_id:
        return None
    return None
