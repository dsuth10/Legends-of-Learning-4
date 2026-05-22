"""Teacher-facing Adventures routes (/teacher/adventures/*)."""

from __future__ import annotations

import os
from typing import Optional

from flask import (
    current_app,
    jsonify,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from pydantic import ValidationError
from werkzeug.utils import secure_filename

from app.forms.adventure_schemas import (
    AdventureCloneSchema,
    AdventureCreateSchema,
    AdventureUpdateSchema,
    AssignmentCreateSchema,
    AssignmentUpdateSchema,
    EdgeCreateSchema,
    EdgeUpdateSchema,
    ForceCompleteSchema,
    NodeConsequenceCreateSchema,
    NodeCreateSchema,
    NodeRewardCreateSchema,
    NodeUpdateSchema,
    error_response,
    success_response,
)
from app.models import db
from app.models.adventure import (
    Adventure,
    AdventureEdge,
    AdventureNode,
    AdventureStatus,
    NodeConsequence,
    NodeReward,
)
from app.models.adventure_progress import AdventureAssignment, CharacterNodeProgress
from app.routes.adventures.serializers import (
    adventure_summary,
    assignment_dict,
    consequence_dict,
    edge_dict,
    node_dict,
    reward_dict,
)
from app.routes.teacher.blueprint import teacher_required
from app.services.adventure_graph import (
    AssignmentError,
    AuthorizationError,
    aggregate_adventure_progress_roster,
    clone_adventure,
    count_in_progress_students,
    create_classroom_assignment,
    force_complete_adventure,
    list_active_classroom_assignments,
    require_teacher_classroom,
    require_teacher_edit,
    require_teacher_read,
    teacher_can_read_adventure,
    teacher_owns_adventure,
    validate_for_publish,
)
from flask import Blueprint

adventures_teacher_bp = Blueprint(
    "adventures_teacher",
    __name__,
    url_prefix="/teacher/adventures",
)

MAX_BACKGROUND_BYTES = int(os.environ.get("MAX_BACKGROUND_UPLOAD_BYTES", 5 * 1024 * 1024))
ALLOWED_MIME = {"image/png", "image/jpeg", "image/webp"}
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
MIME_TO_EXTENSIONS = {
    "image/png": {".png"},
    "image/jpeg": {".jpg", ".jpeg"},
    "image/webp": {".webp"},
}


def _extension_for(filename: str) -> str:
    _, ext = os.path.splitext(filename.lower())
    return ext


def _sniff_image_mime(data: bytes) -> Optional[str]:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def _validate_background_upload(upload) -> Optional[str]:
    """Return error message if invalid, else None."""
    if not upload or not upload.filename:
        return "Missing file upload."

    raw_name = upload.filename
    filename = secure_filename(raw_name)
    if not filename:
        return "Invalid filename."

    ext = _extension_for(filename)
    if ext not in ALLOWED_EXTENSIONS:
        return f"Unsupported file extension: {ext or '(none)'}"

    mime = (upload.mimetype or "").split(";")[0].strip().lower()
    if mime not in ALLOWED_MIME:
        return f"Unsupported MIME type: {mime or '(none)'}"

    allowed_ext_for_mime = MIME_TO_EXTENSIONS.get(mime, set())
    if ext not in allowed_ext_for_mime:
        return f"MIME type {mime} does not match extension {ext}."

    head = upload.read(512)
    upload.seek(0)
    sniffed = _sniff_image_mime(head)
    if sniffed != mime:
        return "File content does not match declared image type."

    upload.seek(0, os.SEEK_END)
    size = upload.tell()
    upload.seek(0)
    if size > MAX_BACKGROUND_BYTES:
        return "File exceeds maximum size."

    return None


def _status_for_code(code: str) -> int:
    return {
        "VALIDATION_ERROR": 400,
        "AUTH_REQUIRED": 401,
        "FORBIDDEN": 403,
        "NOT_FOUND": 404,
        "CONFLICT": 409,
        "PAYLOAD_TOO_LARGE": 413,
    }.get(code, 400)


def _json_ok(data=None, status=200):
    return jsonify(success_response(data)), status


def _json_err(code: str, message: str, status: Optional[int] = None, extra=None):
    st = status or _status_for_code(code)
    body = error_response(code, message, extra_errors=extra)
    return jsonify(body), st


def _get_adventure(adventure_id: int) -> Optional[Adventure]:
    return db.session.get(Adventure, adventure_id)


def _enriched_assignment_dict(assignment: AdventureAssignment) -> dict:
    from app.models.classroom import Classroom

    classroom_name = None
    progress_url = None
    if assignment.classroom_id:
        classroom = db.session.get(Classroom, assignment.classroom_id)
        classroom_name = classroom.name if classroom else None
        progress_url = url_for(
            "adventures_teacher.adventure_progress",
            adventure_id=assignment.adventure_id,
            classroom_id=assignment.classroom_id,
        )
    return assignment_dict(
        assignment,
        classroom_name=classroom_name,
        progress_url=progress_url,
    )


def _parse(schema_cls, data: dict):
    try:
        return schema_cls.model_validate(data)
    except ValidationError as exc:
        raise AuthorizationError("VALIDATION_ERROR", str(exc.errors()))


@adventures_teacher_bp.route("/", methods=["GET"])
@login_required
@teacher_required
def list_adventures():
    status_filters = request.args.getlist("status")
    mine_only = request.args.get("mine", "true").lower() != "false"
    query_text = (request.args.get("q") or "").strip()

    owned = Adventure.query.filter_by(teacher_id=current_user.id)
    if status_filters:
        owned = owned.filter(Adventure.status.in_(status_filters))
    if query_text:
        owned = owned.filter(Adventure.title.ilike(f"%{query_text}%"))

    adventures = list(owned.all())

    if not mine_only:
        adventures = []
        public = Adventure.query.filter(
            Adventure.is_public.is_(True),
            Adventure.status != AdventureStatus.DRAFT.value,
            Adventure.teacher_id != current_user.id,
        )
        if status_filters:
            public = public.filter(Adventure.status.in_(status_filters))
        if query_text:
            public = public.filter(Adventure.title.ilike(f"%{query_text}%"))
        adventures.extend(public.all())
    else:
        public = Adventure.query.filter(
            Adventure.is_public.is_(True),
            Adventure.teacher_id != current_user.id,
            Adventure.status != AdventureStatus.DRAFT.value,
        )
        if status_filters:
            public = public.filter(Adventure.status.in_(status_filters))
        if query_text:
            public = public.filter(Adventure.title.ilike(f"%{query_text}%"))
        adventures.extend(public.all())

    return _json_ok(
        {"adventures": [adventure_summary(a) for a in adventures]}
    )


@adventures_teacher_bp.route("/list", methods=["GET"])
@login_required
@teacher_required
def adventures_list_page():
    return render_template(
        "teacher/adventures_list.html",
        active_page="adventures",
        current_user_id=current_user.id,
    )


@adventures_teacher_bp.route("/", methods=["POST"])
@login_required
@teacher_required
def create_adventure():
    body = request.get_json(silent=True) or {}
    try:
        payload = AdventureCreateSchema.model_validate(body)
    except ValidationError as exc:
        return _json_err("VALIDATION_ERROR", str(exc.errors()))

    adventure = Adventure(
        title=payload.title,
        description=payload.description,
        teacher_id=current_user.id,
        background_image_url=payload.background_image_url,
        theme=payload.theme,
        width=payload.width,
        height=payload.height,
        end_semantics=payload.end_semantics.value,
        status=AdventureStatus.DRAFT.value,
    )
    db.session.add(adventure)
    db.session.commit()
    return _json_ok({"adventure": adventure_summary(adventure)}, status=201)


@adventures_teacher_bp.route("/<int:adventure_id>", methods=["GET"])
@login_required
@teacher_required
def read_adventure(adventure_id: int):
    adventure = _get_adventure(adventure_id)
    if not adventure:
        return _json_err("NOT_FOUND", "Adventure not found.", 404)
    try:
        require_teacher_read(current_user, adventure)
    except AuthorizationError as exc:
        return _json_err(exc.code, exc.message, _status_for_code(exc.code))

    if request.accept_mimetypes.best == "application/json" or request.args.get("format") == "json":
        return _json_ok({"adventure": adventure_summary(adventure)})

    in_progress_count = 0
    if adventure.status == AdventureStatus.PUBLISHED.value:
        in_progress_count = count_in_progress_students(adventure.id)

    from app.models.battle import Monster

    monsters = Monster.query.order_by(Monster.name).all()
    monster_options = [{"id": m.id, "name": m.name} for m in monsters]

    return render_template(
        "teacher/adventure_editor.html",
        adventure=adventure,
        in_progress_count=in_progress_count,
        can_edit=teacher_owns_adventure(current_user, adventure),
        monster_options=monster_options,
        active_page="adventures",
    )


@adventures_teacher_bp.route("/<int:adventure_id>/graph", methods=["GET"])
@login_required
@teacher_required
def adventure_graph(adventure_id: int):
    adventure = _get_adventure(adventure_id)
    if not adventure:
        return _json_err("NOT_FOUND", "Adventure not found.", 404)
    try:
        require_teacher_read(current_user, adventure)
    except AuthorizationError as exc:
        return _json_err(exc.code, exc.message, _status_for_code(exc.code))

    validation = validate_for_publish(adventure)
    in_progress_count = 0
    if adventure.status == AdventureStatus.PUBLISHED.value:
        in_progress_count = count_in_progress_students(adventure.id)
    return _json_ok(
        {
            "adventure": adventure_summary(adventure),
            "nodes": [node_dict(n) for n in adventure.nodes.all()],
            "edges": [edge_dict(e) for e in adventure.edges.all()],
            "validation": validation.to_dict(),
            "in_progress_student_count": in_progress_count,
        }
    )


@adventures_teacher_bp.route("/<int:adventure_id>", methods=["PATCH"])
@login_required
@teacher_required
def update_adventure(adventure_id: int):
    adventure = _get_adventure(adventure_id)
    if not adventure:
        return _json_err("NOT_FOUND", "Adventure not found.", 404)
    try:
        require_teacher_edit(current_user, adventure)
    except AuthorizationError as exc:
        return _json_err(exc.code, exc.message, _status_for_code(exc.code))

    body = request.get_json(silent=True) or {}
    try:
        payload = AdventureUpdateSchema.model_validate(body)
    except ValidationError as exc:
        return _json_err("VALIDATION_ERROR", str(exc.errors()))

    if payload.is_public and adventure.status == AdventureStatus.DRAFT.value:
        return _json_err(
            "VALIDATION_ERROR",
            "Cannot make a draft adventure public; publish first.",
        )

    for field, value in payload.model_dump(exclude_unset=True).items():
        if field == "end_semantics" and value is not None:
            value = value.value if hasattr(value, "value") else value
        setattr(adventure, field, value)

    if adventure.status == AdventureStatus.PUBLISHED.value:
        adventure.version += 1

    db.session.commit()
    return _json_ok({"adventure": adventure_summary(adventure)})


@adventures_teacher_bp.route("/<int:adventure_id>/publish", methods=["POST"])
@login_required
@teacher_required
def publish_adventure(adventure_id: int):
    adventure = _get_adventure(adventure_id)
    if not adventure:
        return _json_err("NOT_FOUND", "Adventure not found.", 404)
    try:
        require_teacher_edit(current_user, adventure)
    except AuthorizationError as exc:
        return _json_err(exc.code, exc.message, _status_for_code(exc.code))

    validation = validate_for_publish(adventure)
    if not validation.ok_to_publish:
        return _json_err(
            "CONFLICT",
            "Adventure cannot be published.",
            409,
            extra=validation.errors,
        )

    adventure.status = AdventureStatus.PUBLISHED.value
    adventure.version += 1
    db.session.commit()
    return _json_ok({"adventure": adventure_summary(adventure)})


@adventures_teacher_bp.route("/<int:adventure_id>", methods=["DELETE"])
@login_required
@teacher_required
def archive_adventure(adventure_id: int):
    adventure = _get_adventure(adventure_id)
    if not adventure:
        return _json_err("NOT_FOUND", "Adventure not found.", 404)
    try:
        require_teacher_edit(current_user, adventure)
    except AuthorizationError as exc:
        return _json_err(exc.code, exc.message, _status_for_code(exc.code))

    adventure.status = AdventureStatus.ARCHIVED.value
    db.session.commit()
    return _json_ok({"adventure": adventure_summary(adventure)})


@adventures_teacher_bp.route("/<int:adventure_id>/clone", methods=["POST"])
@login_required
@teacher_required
def clone_adventure_route(adventure_id: int):
    source = _get_adventure(adventure_id)
    if not source:
        return _json_err("NOT_FOUND", "Adventure not found.", 404)
    try:
        require_teacher_read(current_user, source)
    except AuthorizationError as exc:
        return _json_err(exc.code, exc.message, _status_for_code(exc.code))

    body = request.get_json(silent=True) or {}
    title = None
    if body:
        try:
            title = AdventureCloneSchema.model_validate(body).title
        except ValidationError as exc:
            return _json_err("VALIDATION_ERROR", str(exc.errors()))

    clone = clone_adventure(source, current_user, title=title)
    return _json_ok({"adventure": adventure_summary(clone)}, status=201)


@adventures_teacher_bp.route("/<int:adventure_id>/nodes", methods=["POST"])
@login_required
@teacher_required
def create_node(adventure_id: int):
    adventure = _get_adventure(adventure_id)
    if not adventure:
        return _json_err("NOT_FOUND", "Adventure not found.", 404)
    try:
        require_teacher_edit(current_user, adventure)
    except AuthorizationError as exc:
        return _json_err(exc.code, exc.message, _status_for_code(exc.code))

    body = request.get_json(silent=True) or {}
    try:
        payload = NodeCreateSchema.model_validate(body)
    except ValidationError as exc:
        return _json_err("VALIDATION_ERROR", str(exc.errors()))

    if AdventureNode.query.filter_by(adventure_id=adventure.id, slug=payload.slug).first():
        return _json_err("CONFLICT", f"Slug '{payload.slug}' already exists.", 409)

    node = AdventureNode(
        adventure_id=adventure.id,
        slug=payload.slug,
        title=payload.title,
        description=payload.description,
        lore=payload.lore,
        icon_url=payload.icon_url,
        node_type=payload.node_type.value,
        x=payload.x,
        y=payload.y,
        is_optional=payload.is_optional,
        is_start=payload.is_start,
        is_end=payload.is_end,
        question_set_id=payload.question_set_id,
        monster_id=payload.monster_id,
        completion_rules=payload.completion_rules,
        on_complete_actions=payload.on_complete_actions,
    )
    db.session.add(node)
    db.session.flush()

    for reward_payload in payload.rewards:
        db.session.add(
            NodeReward(
                node_id=node.id,
                type=reward_payload.type.value,
                amount=reward_payload.amount,
                item_id=reward_payload.item_id,
                ability_id=reward_payload.ability_id,
                badge_id=reward_payload.badge_id,
                is_conditional=reward_payload.is_conditional,
                condition_json=reward_payload.condition_json,
            )
        )

    if adventure.status == AdventureStatus.PUBLISHED.value:
        adventure.version += 1

    db.session.commit()
    return _json_ok({"node": node_dict(node)}, status=201)


@adventures_teacher_bp.route("/<int:adventure_id>/nodes/<int:node_id>", methods=["PATCH"])
@login_required
@teacher_required
def update_node(adventure_id: int, node_id: int):
    adventure = _get_adventure(adventure_id)
    if not adventure:
        return _json_err("NOT_FOUND", "Adventure not found.", 404)
    try:
        require_teacher_edit(current_user, adventure)
    except AuthorizationError as exc:
        return _json_err(exc.code, exc.message, _status_for_code(exc.code))

    node = AdventureNode.query.filter_by(id=node_id, adventure_id=adventure.id).first()
    if not node:
        return _json_err("NOT_FOUND", "Node not found.", 404)

    body = request.get_json(silent=True) or {}
    try:
        payload = NodeUpdateSchema.model_validate(body)
    except ValidationError as exc:
        return _json_err("VALIDATION_ERROR", str(exc.errors()))

    data = payload.model_dump(exclude_unset=True)
    if "node_type" in data and data["node_type"] is not None:
        data["node_type"] = data["node_type"].value

    for key, value in data.items():
        setattr(node, key, value)

    if adventure.status == AdventureStatus.PUBLISHED.value:
        adventure.version += 1

    db.session.commit()
    return _json_ok({"node": node_dict(node)})


@adventures_teacher_bp.route("/<int:adventure_id>/nodes/<int:node_id>", methods=["DELETE"])
@login_required
@teacher_required
def delete_node(adventure_id: int, node_id: int):
    adventure = _get_adventure(adventure_id)
    if not adventure:
        return _json_err("NOT_FOUND", "Adventure not found.", 404)
    try:
        require_teacher_edit(current_user, adventure)
    except AuthorizationError as exc:
        return _json_err(exc.code, exc.message, _status_for_code(exc.code))

    node = AdventureNode.query.filter_by(id=node_id, adventure_id=adventure.id).first()
    if not node:
        return _json_err("NOT_FOUND", "Node not found.", 404)

    affected = CharacterNodeProgress.query.filter_by(node_id=node.id).count()
    if affected and request.args.get("confirm") != "true":
        return _json_err(
            "CONFLICT",
            f"{affected} students have progress on this node. Re-issue with ?confirm=true.",
            409,
            extra=[
                {
                    "code": "AFFECTS_STUDENT_PROGRESS",
                    "message": f"{affected} students affected.",
                    "affected_students": affected,
                }
            ],
        )

    db.session.delete(node)
    if adventure.status == AdventureStatus.PUBLISHED.value:
        adventure.version += 1
    db.session.commit()
    return _json_ok(
        {
            "deleted_node_id": node_id,
            "affected_students": affected,
            "cleaned_progress_rows": affected,
        }
    )


@adventures_teacher_bp.route("/<int:adventure_id>/edges", methods=["POST"])
@login_required
@teacher_required
def create_edge(adventure_id: int):
    adventure = _get_adventure(adventure_id)
    if not adventure:
        return _json_err("NOT_FOUND", "Adventure not found.", 404)
    try:
        require_teacher_edit(current_user, adventure)
    except AuthorizationError as exc:
        return _json_err(exc.code, exc.message, _status_for_code(exc.code))

    body = request.get_json(silent=True) or {}
    try:
        payload = EdgeCreateSchema.model_validate(body)
    except ValidationError as exc:
        return _json_err("VALIDATION_ERROR", str(exc.errors()))

    for nid in (payload.from_node_id, payload.to_node_id):
        if not AdventureNode.query.filter_by(id=nid, adventure_id=adventure.id).first():
            return _json_err("NOT_FOUND", f"Node {nid} not found.", 404)

    edge = AdventureEdge(
        adventure_id=adventure.id,
        from_node_id=payload.from_node_id,
        to_node_id=payload.to_node_id,
        label=payload.label,
        condition_type=payload.condition_type.value,
        condition_data=payload.condition_data,
        unlock_semantics=payload.unlock_semantics.value,
        sort_order=payload.sort_order,
    )
    db.session.add(edge)
    if adventure.status == AdventureStatus.PUBLISHED.value:
        adventure.version += 1
    db.session.commit()
    return _json_ok({"edge": edge_dict(edge)}, status=201)


@adventures_teacher_bp.route("/<int:adventure_id>/edges/<int:edge_id>", methods=["PATCH"])
@login_required
@teacher_required
def update_edge(adventure_id: int, edge_id: int):
    adventure = _get_adventure(adventure_id)
    if not adventure:
        return _json_err("NOT_FOUND", "Adventure not found.", 404)
    try:
        require_teacher_edit(current_user, adventure)
    except AuthorizationError as exc:
        return _json_err(exc.code, exc.message, _status_for_code(exc.code))

    edge = AdventureEdge.query.filter_by(id=edge_id, adventure_id=adventure.id).first()
    if not edge:
        return _json_err("NOT_FOUND", "Edge not found.", 404)

    body = request.get_json(silent=True) or {}
    try:
        payload = EdgeUpdateSchema.model_validate(body)
    except ValidationError as exc:
        return _json_err("VALIDATION_ERROR", str(exc.errors()))

    data = payload.model_dump(exclude_unset=True)
    if "condition_type" in data and data["condition_type"] is not None:
        data["condition_type"] = data["condition_type"].value
    if "unlock_semantics" in data and data["unlock_semantics"] is not None:
        data["unlock_semantics"] = data["unlock_semantics"].value

    for key, value in data.items():
        setattr(edge, key, value)

    from app.forms.adventure_schemas import validate_edge_condition_pair
    from app.models.adventure import EdgeConditionType as EdgeCond

    ct = EdgeCond(edge.condition_type)
    validate_edge_condition_pair(ct, edge.condition_data or {})

    if adventure.status == AdventureStatus.PUBLISHED.value:
        adventure.version += 1
    db.session.commit()
    return _json_ok({"edge": edge_dict(edge)})


@adventures_teacher_bp.route("/<int:adventure_id>/edges/<int:edge_id>", methods=["DELETE"])
@login_required
@teacher_required
def delete_edge(adventure_id: int, edge_id: int):
    adventure = _get_adventure(adventure_id)
    if not adventure:
        return _json_err("NOT_FOUND", "Adventure not found.", 404)
    try:
        require_teacher_edit(current_user, adventure)
    except AuthorizationError as exc:
        return _json_err(exc.code, exc.message, _status_for_code(exc.code))

    edge = AdventureEdge.query.filter_by(id=edge_id, adventure_id=adventure.id).first()
    if edge:
        db.session.delete(edge)
        if adventure.status == AdventureStatus.PUBLISHED.value:
            adventure.version += 1
        db.session.commit()
    return _json_ok({"deleted_edge_id": edge_id})


@adventures_teacher_bp.route(
    "/<int:adventure_id>/nodes/<int:node_id>/rewards", methods=["POST"]
)
@login_required
@teacher_required
def create_reward(adventure_id: int, node_id: int):
    adventure = _get_adventure(adventure_id)
    if not adventure:
        return _json_err("NOT_FOUND", "Adventure not found.", 404)
    try:
        require_teacher_edit(current_user, adventure)
    except AuthorizationError as exc:
        return _json_err(exc.code, exc.message, _status_for_code(exc.code))

    node = AdventureNode.query.filter_by(id=node_id, adventure_id=adventure.id).first()
    if not node:
        return _json_err("NOT_FOUND", "Node not found.", 404)

    body = request.get_json(silent=True) or {}
    try:
        payload = NodeRewardCreateSchema.model_validate(body)
    except ValidationError as exc:
        return _json_err("VALIDATION_ERROR", str(exc.errors()))

    reward = NodeReward(
        node_id=node.id,
        type=payload.type.value,
        amount=payload.amount,
        item_id=payload.item_id,
        ability_id=payload.ability_id,
        badge_id=payload.badge_id,
        is_conditional=payload.is_conditional,
        condition_json=payload.condition_json,
    )
    db.session.add(reward)
    db.session.commit()
    return _json_ok({"reward": reward_dict(reward)}, status=201)


@adventures_teacher_bp.route(
    "/<int:adventure_id>/nodes/<int:node_id>/rewards/<int:reward_id>",
    methods=["DELETE"],
)
@login_required
@teacher_required
def delete_reward(adventure_id: int, node_id: int, reward_id: int):
    adventure = _get_adventure(adventure_id)
    if not adventure:
        return _json_err("NOT_FOUND", "Adventure not found.", 404)
    try:
        require_teacher_edit(current_user, adventure)
    except AuthorizationError as exc:
        return _json_err(exc.code, exc.message, _status_for_code(exc.code))

    reward = NodeReward.query.join(AdventureNode).filter(
        NodeReward.id == reward_id,
        AdventureNode.id == node_id,
        AdventureNode.adventure_id == adventure.id,
    ).first()
    if reward:
        db.session.delete(reward)
        db.session.commit()
    return _json_ok({"deleted_reward_id": reward_id})


@adventures_teacher_bp.route(
    "/<int:adventure_id>/nodes/<int:node_id>/consequences", methods=["POST"]
)
@login_required
@teacher_required
def create_consequence(adventure_id: int, node_id: int):
    adventure = _get_adventure(adventure_id)
    if not adventure:
        return _json_err("NOT_FOUND", "Adventure not found.", 404)
    try:
        require_teacher_edit(current_user, adventure)
    except AuthorizationError as exc:
        return _json_err(exc.code, exc.message, _status_for_code(exc.code))

    node = AdventureNode.query.filter_by(id=node_id, adventure_id=adventure.id).first()
    if not node:
        return _json_err("NOT_FOUND", "Node not found.", 404)

    body = request.get_json(silent=True) or {}
    try:
        payload = NodeConsequenceCreateSchema.model_validate(body)
    except ValidationError as exc:
        return _json_err("VALIDATION_ERROR", str(exc.errors()))

    consequence = NodeConsequence(
        node_id=node.id,
        description=payload.description,
        xp_penalty=payload.xp_penalty,
        gold_penalty=payload.gold_penalty,
        hp_penalty=payload.hp_penalty,
        custom_json=payload.custom_json,
    )
    db.session.add(consequence)
    db.session.commit()
    return _json_ok({"consequence": consequence_dict(consequence)}, status=201)


@adventures_teacher_bp.route(
    "/<int:adventure_id>/nodes/<int:node_id>/consequences/<int:consequence_id>",
    methods=["DELETE"],
)
@login_required
@teacher_required
def delete_consequence(adventure_id: int, node_id: int, consequence_id: int):
    adventure = _get_adventure(adventure_id)
    if not adventure:
        return _json_err("NOT_FOUND", "Adventure not found.", 404)
    try:
        require_teacher_edit(current_user, adventure)
    except AuthorizationError as exc:
        return _json_err(exc.code, exc.message, _status_for_code(exc.code))

    row = NodeConsequence.query.join(AdventureNode).filter(
        NodeConsequence.id == consequence_id,
        AdventureNode.id == node_id,
        AdventureNode.adventure_id == adventure.id,
    ).first()
    if row:
        db.session.delete(row)
        db.session.commit()
    return _json_ok({"deleted_consequence_id": consequence_id})


@adventures_teacher_bp.route("/<int:adventure_id>/assignments", methods=["POST"])
@login_required
@teacher_required
def create_assignment(adventure_id: int):
    adventure = _get_adventure(adventure_id)
    if not adventure:
        return _json_err("NOT_FOUND", "Adventure not found.", 404)
    try:
        require_teacher_edit(current_user, adventure)
    except AuthorizationError as exc:
        return _json_err(exc.code, exc.message, _status_for_code(exc.code))

    if adventure.status != AdventureStatus.PUBLISHED.value:
        return _json_err("CONFLICT", "Only published adventures can be assigned.", 409)

    body = request.get_json(silent=True) or {}
    try:
        payload = AssignmentCreateSchema.model_validate(body)
    except ValidationError as exc:
        return _json_err("VALIDATION_ERROR", str(exc.errors()))

    if payload.classroom_id:
        require_teacher_classroom(current_user, payload.classroom_id)
        try:
            assignment = create_classroom_assignment(
                adventure,
                current_user,
                classroom_id=payload.classroom_id,
                starts_at=payload.starts_at,
                ends_at=payload.ends_at,
            )
        except AssignmentError as exc:
            return _json_err(exc.code, exc.message, _status_for_code(exc.code))
        return _json_ok({"assignment": _enriched_assignment_dict(assignment)}, status=201)

    if payload.clan_id or payload.character_id:
        return _json_err(
            "VALIDATION_ERROR",
            "Clan and individual assignments are not yet supported.",
            400,
        )

    return _json_err("VALIDATION_ERROR", "classroom_id is required.", 400)


@adventures_teacher_bp.route(
    "/<int:adventure_id>/assignments/<int:assignment_id>", methods=["PATCH"]
)
@login_required
@teacher_required
def update_assignment(adventure_id: int, assignment_id: int):
    adventure = _get_adventure(adventure_id)
    if not adventure:
        return _json_err("NOT_FOUND", "Adventure not found.", 404)
    try:
        require_teacher_edit(current_user, adventure)
    except AuthorizationError as exc:
        return _json_err(exc.code, exc.message, _status_for_code(exc.code))

    assignment = AdventureAssignment.query.filter_by(
        id=assignment_id, adventure_id=adventure.id
    ).first()
    if not assignment:
        return _json_err("NOT_FOUND", "Assignment not found.", 404)

    body = request.get_json(silent=True) or {}
    try:
        payload = AssignmentUpdateSchema.model_validate(body)
    except ValidationError as exc:
        return _json_err("VALIDATION_ERROR", str(exc.errors()))

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(assignment, key, value)
    db.session.commit()
    return _json_ok({"assignment": _enriched_assignment_dict(assignment)})


@adventures_teacher_bp.route(
    "/<int:adventure_id>/assignments/<int:assignment_id>", methods=["DELETE"]
)
@login_required
@teacher_required
def deactivate_assignment(adventure_id: int, assignment_id: int):
    adventure = _get_adventure(adventure_id)
    if not adventure:
        return _json_err("NOT_FOUND", "Adventure not found.", 404)
    try:
        require_teacher_edit(current_user, adventure)
    except AuthorizationError as exc:
        return _json_err(exc.code, exc.message, _status_for_code(exc.code))

    assignment = AdventureAssignment.query.filter_by(
        id=assignment_id, adventure_id=adventure.id
    ).first()
    if not assignment:
        return _json_err("NOT_FOUND", "Assignment not found.", 404)

    assignment.is_active = False
    db.session.commit()
    return _json_ok({"assignment": _enriched_assignment_dict(assignment)})


@adventures_teacher_bp.route("/<int:adventure_id>/assignments", methods=["GET"])
@login_required
@teacher_required
def assignments_page(adventure_id: int):
    adventure = _get_adventure(adventure_id)
    if not adventure:
        return _json_err("NOT_FOUND", "Adventure not found.", 404)
    try:
        require_teacher_edit(current_user, adventure)
    except AuthorizationError as exc:
        return _json_err(exc.code, exc.message, _status_for_code(exc.code))

    from app.models.classroom import Classroom

    assignments = list_active_classroom_assignments(adventure)
    classroom_names = {
        c.id: c.name
        for c in Classroom.query.filter(
            Classroom.id.in_([a.classroom_id for a in assignments if a.classroom_id])
        ).all()
    }
    assigned_class_ids = {a.classroom_id for a in assignments if a.classroom_id}
    classes = Classroom.query.filter_by(teacher_id=current_user.id, is_active=True).all()

    if request.accept_mimetypes.best == "application/json" or request.args.get(
        "format"
    ) == "json":
        return _json_ok(
            {
                "assignments": [
                    _enriched_assignment_dict(a) for a in assignments
                ],
            }
        )

    return render_template(
        "teacher/adventure_assignments.html",
        adventure=adventure,
        assignments=assignments,
        classroom_names=classroom_names,
        assigned_class_ids=assigned_class_ids,
        classes=classes,
        active_page="adventures",
    )


@adventures_teacher_bp.route("/<int:adventure_id>/background", methods=["POST"])
@login_required
@teacher_required
def upload_background(adventure_id: int):
    adventure = _get_adventure(adventure_id)
    if not adventure:
        return _json_err("NOT_FOUND", "Adventure not found.", 404)
    try:
        require_teacher_edit(current_user, adventure)
    except AuthorizationError as exc:
        return _json_err(exc.code, exc.message, _status_for_code(exc.code))

    upload = request.files.get("file")
    upload_error = _validate_background_upload(upload)
    if upload_error:
        if upload_error == "File exceeds maximum size.":
            return _json_err("PAYLOAD_TOO_LARGE", upload_error, 413)
        return _json_err("VALIDATION_ERROR", upload_error, 400)

    filename = secure_filename(upload.filename)
    dest_dir = os.path.join(
        current_app.root_path,
        "..",
        "static",
        "images",
        "adventure_backgrounds",
        str(adventure.id),
    )
    dest_dir = os.path.normpath(dest_dir)
    os.makedirs(dest_dir, exist_ok=True)
    path = os.path.join(dest_dir, filename)
    upload.save(path)

    url = f"/static/images/adventure_backgrounds/{adventure.id}/{filename}"
    adventure.background_image_url = url
    db.session.commit()
    return _json_ok({"background_image_url": url})


@adventures_teacher_bp.route("/<int:adventure_id>/progress", methods=["GET"])
@login_required
@teacher_required
def adventure_progress(adventure_id: int):
    adventure = _get_adventure(adventure_id)
    if not adventure:
        return _json_err("NOT_FOUND", "Adventure not found.", 404)
    try:
        require_teacher_edit(current_user, adventure)
    except AuthorizationError as exc:
        return _json_err(exc.code, exc.message, _status_for_code(exc.code))

    classroom_id = request.args.get("classroom_id", type=int)
    try:
        roster = aggregate_adventure_progress_roster(
            adventure, current_user, classroom_id=classroom_id
        )
    except AuthorizationError as exc:
        return _json_err(exc.code, exc.message, _status_for_code(exc.code))

    if request.accept_mimetypes.best == "application/json" or request.args.get(
        "format"
    ) == "json":
        return _json_ok(roster)

    from app.models.classroom import Classroom

    assignments = list_active_classroom_assignments(adventure)
    assigned_class_ids = {a.classroom_id for a in assignments if a.classroom_id}
    classes = Classroom.query.filter(
        Classroom.id.in_(assigned_class_ids),
        Classroom.teacher_id == current_user.id,
    ).all()
    classroom_names = {c.id: c.name for c in classes}
    selected_classroom_name = (
        classroom_names.get(classroom_id) if classroom_id else None
    )

    return render_template(
        "teacher/adventure_progress.html",
        adventure=adventure,
        roster=roster,
        classes=classes,
        assignments=assignments,
        classroom_names=classroom_names,
        selected_classroom_id=classroom_id,
        selected_classroom_name=selected_classroom_name,
        active_page="adventures",
    )


@adventures_teacher_bp.route(
    "/<int:adventure_id>/progress/<int:character_id>/force-complete",
    methods=["POST"],
)
@login_required
@teacher_required
def force_complete_student(adventure_id: int, character_id: int):
    adventure = _get_adventure(adventure_id)
    if not adventure:
        return _json_err("NOT_FOUND", "Adventure not found.", 404)
    try:
        require_teacher_edit(current_user, adventure)
    except AuthorizationError as exc:
        return _json_err(exc.code, exc.message, _status_for_code(exc.code))

    from app.models.character import Character

    character = db.session.get(Character, character_id)
    if not character:
        return _json_err("NOT_FOUND", "Character not found.", 404)

    body = request.get_json(silent=True) or {}
    try:
        payload = ForceCompleteSchema.model_validate(body)
    except ValidationError as exc:
        return _json_err("VALIDATION_ERROR", str(exc.errors()))

    try:
        result = force_complete_adventure(
            current_user,
            adventure,
            character,
            reason=payload.reason,
            session=db.session,
        )
        db.session.commit()
    except AuthorizationError as exc:
        return _json_err(exc.code, exc.message, _status_for_code(exc.code))

    return _json_ok({"adventure_progress": result})
