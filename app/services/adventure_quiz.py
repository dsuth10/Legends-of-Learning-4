"""Quiz scoring and completion for Adventures quiz nodes."""

from __future__ import annotations

from typing import Dict, List, Optional

from app.models import db
from app.models.adventure import AdventureNode, NodeType
from app.models.adventure_progress import NodeProgressStatus
from app.models.education import Question
from app.services.adventure_lifecycle import LifecycleError, complete_node
from app.services.adventure_graph import require_student_assignment
from app.services.adventure_rewards import apply_node_consequences


def score_quiz_answers(node: AdventureNode, answers: List[dict]) -> int:
    """Return score percent 0-100 for submitted answers."""
    if not node.question_set_id:
        return 0

    answer_map = {int(a["question_id"]): a["answer"] for a in answers}
    questions = Question.query.filter(Question.set_id == node.question_set_id).all()
    if not questions:
        return 0

    correct = 0
    for question in questions:
        submitted = answer_map.get(question.id)
        if submitted is not None and str(submitted).strip() == str(question.correct_answer).strip():
            correct += 1
    return int(round(100 * correct / len(questions)))


def submit_quiz(
    character,
    adventure,
    node: AdventureNode,
    answers: List[dict],
    *,
    session=None,
) -> dict:
    """Score quiz, complete or fail node, apply consequences on exhaustion."""
    if session is None:
        session = db.session

    if node.node_type != NodeType.QUIZ.value:
        raise LifecycleError("VALIDATION_ERROR", "Node is not a quiz.")

    assignment = require_student_assignment(character, adventure.id)
    score = score_quiz_answers(node, answers)
    rules = node.completion_rules or {}
    min_score = rules.get("min_score_percent", 0)
    max_attempts = rules.get("max_attempts")

    from app.services.adventure_lifecycle import (
        _get_node_progress,
        ensure_adventure_bootstrapped,
    )

    ensure_adventure_bootstrapped(character, adventure, assignment, session=session)
    row = _get_node_progress(character, node, session=session)

    if row.status == NodeProgressStatus.COMPLETED.value:
        from app.services.adventure_lifecycle import _completion_response

        return _completion_response(
            character, adventure, node, row, session=session, first_time=False
        )

    row.score = score
    if score >= min_score:
        row.status = NodeProgressStatus.IN_PROGRESS.value
        if row.attempts == 0:
            row.attempts = 1
        return complete_node(
            character,
            adventure,
            node,
            assignment,
            score=score,
            session=session,
        )

    row.status = NodeProgressStatus.FAILED.value
    consequences_applied = []
    if max_attempts and row.attempts >= max_attempts:
        result = apply_node_consequences(character, node, session=session, commit=False)
        if result:
            consequences_applied.append(result)

    return {
        "node": {
            "id": node.id,
            "slug": node.slug,
            "status": row.status,
            "score": row.score,
            "attempts": row.attempts,
            "started_at": row.started_at,
            "completed_at": row.completed_at,
        },
        "rewards_distributed": [],
        "conditional_rewards_distributed": [],
        "next_unlocked": [],
        "consequences_applied": consequences_applied,
        "adventure_blocked": False,
        "adventure_complete": False,
    }
