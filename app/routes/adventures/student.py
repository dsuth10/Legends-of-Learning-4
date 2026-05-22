"""Student-facing Adventures routes (/student/adventures/*)."""

from __future__ import annotations

from typing import Optional

from flask import jsonify, render_template, request
from flask_login import current_user, login_required
from pydantic import ValidationError

from app.forms.adventure_schemas import (
    NodeChooseSchema,
    QuizSubmitSchema,
    error_response,
    success_response,
)
from app.models import db
from app.models.adventure import Adventure, AdventureNode
from app.models.adventure_progress import (
    CharacterAdventureProgress,
    CharacterNodeProgress,
)
from app.models.character import Character
from app.models.student import Student
from app.routes.adventures.serializers import (
    adventure_progress_summary,
    adventure_summary,
    assignment_dict,
    assignment_window_status,
    edge_dict,
    node_dict,
    node_progress_dict,
    rewards_preview,
)
from app.routes.teacher.blueprint import student_required
from app.services.adventure_graph import (
    AuthorizationError,
    require_student_assignment,
    student_is_assigned,
)
from app.services.adventure_lifecycle import (
    LifecycleError,
    choose_node,
    complete_node,
    ensure_adventure_bootstrapped,
    retry_node,
    start_node,
)
from app.services.adventure_quiz import submit_quiz
from flask import Blueprint

adventures_student_bp = Blueprint(
    "adventures_student",
    __name__,
    url_prefix="/student/adventures",
)


def _status_for_code(code: str) -> int:
    return {
        "VALIDATION_ERROR": 400,
        "FORBIDDEN": 403,
        "NOT_FOUND": 404,
        "NOT_ASSIGNED": 403,
        "CONFLICT": 409,
        "NODE_LOCKED": 409,
        "NODE_MAX_ATTEMPTS_REACHED": 409,
        "ADVENTURE_NOT_STARTED_YET": 409,
        "ADVENTURE_ENDED": 409,
        "CHOICE_REQUIRED": 400,
        "CHOICE_ALREADY_MADE": 409,
    }.get(code, 400)


def _json_ok(data=None, status=200):
    return jsonify(success_response(data)), status


def _json_err(code: str, message: str, status: Optional[int] = None):
    st = status or _status_for_code(code)
    return jsonify(error_response(code, message)), st


def _active_character() -> Character:
    student = Student.query.filter_by(user_id=current_user.id).first()
    if not student:
        raise AuthorizationError("NOT_FOUND", "Student profile not found.")
    character = student.characters.filter_by(is_active=True).first()
    if not character:
        raise AuthorizationError("NOT_FOUND", "Active character not found.")
    return character


def _get_adventure(adventure_id: int) -> Adventure:
    adventure = db.session.get(Adventure, adventure_id)
    if not adventure:
        raise AuthorizationError("NOT_FOUND", "Adventure not found.")
    return adventure


def _get_node_by_slug(adventure: Adventure, slug: str) -> AdventureNode:
    node = AdventureNode.query.filter_by(adventure_id=adventure.id, slug=slug).first()
    if not node:
        raise AuthorizationError("NOT_FOUND", f"Node '{slug}' not found.")
    return node


@adventures_student_bp.route("/", methods=["GET"])
@login_required
@student_required
def list_adventures():
    character = _active_character()
    assignment_rows = []
    from app.services.adventure_graph import _active_assignments_for_character

    seen = set()
    for assignment in _active_assignments_for_character(character):
        if assignment.adventure_id in seen:
            continue
        seen.add(assignment.adventure_id)
        adventure = assignment.adventure
        progress = CharacterAdventureProgress.query.filter_by(
            character_id=character.id,
            adventure_id=adventure.id,
        ).first()
        assignment_rows.append(
            {
                "id": adventure.id,
                "title": adventure.title,
                "background_image_url": adventure.background_image_url,
                "theme": adventure.theme,
                "node_count": adventure.nodes.count(),
                "edge_count": adventure.edges.count(),
                "my_progress": adventure_progress_summary(
                    adventure, progress, character=character
                ),
                "assignment": {
                    **assignment_dict(assignment),
                    "window_status": assignment_window_status(assignment),
                },
            }
        )

    if request.accept_mimetypes.best == "application/json" or request.args.get("format") == "json":
        return _json_ok({"adventures": assignment_rows})

    return render_template(
        "student/adventures_list.html",
        adventures=assignment_rows,
        active_page="adventures",
    )


@adventures_student_bp.route("/<int:adventure_id>", methods=["GET"])
@login_required
@student_required
def adventure_map_page(adventure_id: int):
    character = _active_character()
    adventure = _get_adventure(adventure_id)
    if not student_is_assigned(character, adventure.id):
        return _json_err("NOT_ASSIGNED", "This adventure is not assigned to you.", 403)

    return render_template(
        "student/adventure_map.html",
        adventure=adventure,
        adventure_id=adventure.id,
        active_page="adventures",
    )


@adventures_student_bp.route("/<int:adventure_id>/state", methods=["GET"])
@login_required
@student_required
def adventure_state(adventure_id: int):
    try:
        character = _active_character()
        adventure = _get_adventure(adventure_id)
        assignment = require_student_assignment(character, adventure.id)
    except AuthorizationError as exc:
        return _json_err(exc.code, exc.message)
    except Exception as exc:
        if hasattr(exc, "code"):
            return _json_err(exc.code, str(exc))

    progress = ensure_adventure_bootstrapped(
        character, adventure, assignment, session=db.session
    )
    db.session.commit()

    from app.services.adventure_graph import get_resolved_graph

    graph = get_resolved_graph(adventure, progress)
    graph_nodes = graph["nodes"]
    graph_edges = graph["edges"]

    node_rows = CharacterNodeProgress.query.filter_by(character_id=character.id).join(
        AdventureNode, AdventureNode.id == CharacterNodeProgress.node_id
    ).filter(AdventureNode.adventure_id == adventure.id).all()
    progress_map = {r.node_id: r for r in node_rows}

    def _state_node_payload(n):
        return {
            "id": n["id"] if isinstance(n, dict) else n.id,
            "slug": n.get("slug") if isinstance(n, dict) else n.slug,
            "node_type": n.get("node_type") if isinstance(n, dict) else n.node_type,
            "title": n.get("title") if isinstance(n, dict) else n.title,
            "x": n.get("x") if isinstance(n, dict) else n.x,
            "y": n.get("y") if isinstance(n, dict) else n.y,
            "is_optional": n.get("is_optional") if isinstance(n, dict) else n.is_optional,
            "is_start": n.get("is_start") if isinstance(n, dict) else n.is_start,
            "is_end": n.get("is_end") if isinstance(n, dict) else n.is_end,
            "icon_url": n.get("icon_url") if isinstance(n, dict) else n.icon_url,
            "description": n.get("description") if isinstance(n, dict) else n.description,
            "lore": n.get("lore") if isinstance(n, dict) else n.lore,
        }

    return _json_ok(
        {
            "adventure": {
                "id": adventure.id,
                "title": adventure.title,
                "background_image_url": adventure.background_image_url,
                "theme": adventure.theme,
                "width": adventure.width,
                "height": adventure.height,
                "version": graph["adventure_version"],
                "live_version": adventure.version,
                "end_semantics": graph["end_semantics"],
                "pinned_from_snapshot": graph["from_snapshot"],
            },
            "nodes": [_state_node_payload(n) for n in graph_nodes],
            "edges": graph_edges if graph["from_snapshot"] else [edge_dict(e) for e in adventure.edges.all()],
            "my_progress": {
                "adventure_status": progress.status,
                "current_node_id": progress.current_node_id,
                "started_at": progress.started_at,
                "last_active_at": progress.last_active_at,
                "nodes": [
                    node_progress_dict(progress_map[n["id"] if isinstance(n, dict) else n.id])
                    if (n["id"] if isinstance(n, dict) else n.id) in progress_map
                    else {
                        "node_id": n["id"] if isinstance(n, dict) else n.id,
                        "status": "locked",
                        "attempts": 0,
                        "score": None,
                        "choice_made": None,
                        "started_at": None,
                        "completed_at": None,
                    }
                    for n in graph_nodes
                ],
            },
            "assignment": {
                **assignment_dict(assignment),
                "window_status": assignment_window_status(assignment),
            },
        }
    )


@adventures_student_bp.route("/<int:adventure_id>/nodes/<slug>", methods=["GET"])
@login_required
@student_required
def node_detail(adventure_id: int, slug: str):
    try:
        character = _active_character()
        adventure = _get_adventure(adventure_id)
        require_student_assignment(character, adventure.id)
        node = _get_node_by_slug(adventure, slug)
    except AuthorizationError as exc:
        return _json_err(exc.code, exc.message)

    row = CharacterNodeProgress.query.filter_by(
        character_id=character.id, node_id=node.id
    ).first()

    from app.models.adventure import EdgeConditionType

    outgoing = None
    if node.node_type == "choice":
        outgoing = []
        for edge in node.outbound_edges.all():
            if edge.condition_type == EdgeConditionType.CHOICE.value:
                key = (edge.condition_data or {}).get("choice_key")
                if key:
                    outgoing.append({"choice_key": key, "label": edge.label or key})

    return _json_ok(
        {
            "node": {
                "id": node.id,
                "slug": node.slug,
                "node_type": node.node_type,
                "title": node.title,
                "description": node.description,
                "lore": node.lore,
                "completion_rules": node.completion_rules or {},
                "rewards_preview": rewards_preview(node),
                "consequences_preview": [
                    {
                        "description": c.description,
                        "xp_penalty": c.xp_penalty,
                        "gold_penalty": c.gold_penalty,
                        "hp_penalty": c.hp_penalty,
                    }
                    for c in node.consequences.all()
                ],
                "my_progress": {
                    "status": row.status if row else "locked",
                    "attempts": row.attempts if row else 0,
                    "score": row.score if row else None,
                    "choice_made": row.choice_made if row else None,
                },
            },
            "outgoing_choices": outgoing,
        }
    )


@adventures_student_bp.route(
    "/<int:adventure_id>/nodes/<slug>/start", methods=["POST"]
)
@login_required
@student_required
def node_start(adventure_id: int, slug: str):
    try:
        character = _active_character()
        adventure = _get_adventure(adventure_id)
        assignment = require_student_assignment(character, adventure.id)
        node = _get_node_by_slug(adventure, slug)
        result = start_node(character, adventure, node, assignment, session=db.session)
        db.session.commit()
        return _json_ok(result)
    except AuthorizationError as exc:
        return _json_err(exc.code, exc.message)
    except LifecycleError as exc:
        return _json_err(exc.code, exc.message)


@adventures_student_bp.route(
    "/<int:adventure_id>/nodes/<slug>/complete", methods=["POST"]
)
@login_required
@student_required
def node_complete(adventure_id: int, slug: str):
    try:
        character = _active_character()
        adventure = _get_adventure(adventure_id)
        assignment = require_student_assignment(character, adventure.id)
        node = _get_node_by_slug(adventure, slug)
        result = complete_node(character, adventure, node, assignment, session=db.session)
        db.session.commit()
        return _json_ok(result)
    except AuthorizationError as exc:
        return _json_err(exc.code, exc.message)
    except LifecycleError as exc:
        return _json_err(exc.code, exc.message)


@adventures_student_bp.route(
    "/<int:adventure_id>/nodes/<slug>/choose", methods=["POST"]
)
@login_required
@student_required
def node_choose(adventure_id: int, slug: str):
    try:
        character = _active_character()
        adventure = _get_adventure(adventure_id)
        assignment = require_student_assignment(character, adventure.id)
        node = _get_node_by_slug(adventure, slug)
        body = request.get_json(silent=True) or {}
        payload = NodeChooseSchema.model_validate(body)
        result = choose_node(
            character,
            adventure,
            node,
            payload.choice_key,
            assignment,
            session=db.session,
        )
        db.session.commit()
        return _json_ok(result)
    except ValidationError as exc:
        return _json_err("VALIDATION_ERROR", str(exc.errors()))
    except AuthorizationError as exc:
        return _json_err(exc.code, exc.message)
    except LifecycleError as exc:
        return _json_err(exc.code, exc.message)


@adventures_student_bp.route(
    "/<int:adventure_id>/nodes/<slug>/retry", methods=["POST"]
)
@login_required
@student_required
def node_retry(adventure_id: int, slug: str):
    try:
        character = _active_character()
        adventure = _get_adventure(adventure_id)
        assignment = require_student_assignment(character, adventure.id)
        node = _get_node_by_slug(adventure, slug)
        result = retry_node(character, adventure, node, assignment, session=db.session)
        db.session.commit()
        return _json_ok(result)
    except AuthorizationError as exc:
        return _json_err(exc.code, exc.message)
    except LifecycleError as exc:
        return _json_err(exc.code, exc.message)


@adventures_student_bp.route(
    "/<int:adventure_id>/nodes/<slug>/quiz", methods=["GET"]
)
@login_required
@student_required
def quiz_page(adventure_id: int, slug: str):
    character = _active_character()
    adventure = _get_adventure(adventure_id)
    require_student_assignment(character, adventure.id)
    node = _get_node_by_slug(adventure, slug)
    return render_template(
        "student/_adventure_node_detail.html",
        adventure=adventure,
        node=node,
        quiz_mode=True,
    )


@adventures_student_bp.route(
    "/<int:adventure_id>/nodes/<slug>/quiz/submit", methods=["POST"]
)
@login_required
@student_required
def quiz_submit(adventure_id: int, slug: str):
    try:
        character = _active_character()
        adventure = _get_adventure(adventure_id)
        require_student_assignment(character, adventure.id)
        node = _get_node_by_slug(adventure, slug)
        body = request.get_json(silent=True) or {}
        payload = QuizSubmitSchema.model_validate(body)
        answers = [
            {"question_id": a.question_id, "answer": a.answer} for a in payload.answers
        ]
        result = submit_quiz(character, adventure, node, answers, session=db.session)
        db.session.commit()
        return _json_ok(result)
    except ValidationError as exc:
        return _json_err("VALIDATION_ERROR", str(exc.errors()))
    except AuthorizationError as exc:
        return _json_err(exc.code, exc.message)
    except LifecycleError as exc:
        return _json_err(exc.code, exc.message)
