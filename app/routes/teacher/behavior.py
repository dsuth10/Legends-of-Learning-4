"""Teacher UI and API for behavior / Cursed Die / fallen events."""

from __future__ import annotations

from typing import Optional

from flask import jsonify, render_template, request, abort
from flask_login import current_user, login_required
from sqlalchemy import func

from app.models import db
from app.models.behavior import (
    BehaviorIncident,
    BehaviorInfraction,
    ClassroomBehaviorSettings,
    CursedDieFace,
    FallenEvent,
    FallenStatus,
)
from app.models.character import Character
from app.models.classroom import Classroom
from app.models.student import Student
from app.services import behavior as behavior_svc

from .blueprint import teacher_bp, teacher_required


@teacher_bp.route("/behavior", methods=["GET"])
@login_required
@teacher_required
def behavior_home():
    classes = Classroom.query.filter_by(
        teacher_id=current_user.id, is_active=True
    ).order_by(Classroom.name).all()
    return render_template(
        "teacher/behavior_home.html",
        classes=classes,
        active_page="behavior_home",
    )


def _classroom_or_404(class_id: int) -> Classroom:
    c = Classroom.query.filter_by(id=class_id, teacher_id=current_user.id).first()
    if not c:
        abort(404)
    return c


def _character_in_class(character_id: int, class_id: int) -> Optional[Character]:
    ch = Character.query.get(character_id)
    if not ch or not ch.is_active:
        return None
    st = Student.query.get(ch.student_id)
    if not st or st.class_id != class_id:
        return None
    return ch


@teacher_bp.route("/behavior/<int:class_id>/config", methods=["GET"])
@login_required
@teacher_required
def behavior_config(class_id):
    classroom = _classroom_or_404(class_id)
    behavior_svc.ensure_classroom_behavior_defaults(classroom.id)
    db.session.commit()
    return render_template(
        "teacher/behavior_config.html",
        classroom=classroom,
        active_page="behavior_config",
    )


@teacher_bp.route("/behavior/<int:class_id>/history", methods=["GET"])
@login_required
@teacher_required
def behavior_history(class_id):
    classroom = _classroom_or_404(class_id)
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 30, type=int), 100)
    q = BehaviorIncident.query.filter_by(classroom_id=classroom.id).order_by(
        BehaviorIncident.created_at.desc()
    )
    pagination = q.paginate(page=page, per_page=per_page, error_out=False)
    # Summary stats
    infraction_counts = (
        db.session.query(
            BehaviorInfraction.name,
            func.count(BehaviorIncident.id),
        )
        .join(
            BehaviorIncident,
            BehaviorIncident.infraction_id == BehaviorInfraction.id,
        )
        .filter(BehaviorIncident.classroom_id == classroom.id)
        .group_by(BehaviorInfraction.id)
        .all()
    )
    rescue_count = FallenEvent.query.filter_by(
        classroom_id=classroom.id, status=FallenStatus.RESCUED.value
    ).count()
    sentenced_count = FallenEvent.query.filter_by(
        classroom_id=classroom.id, status=FallenStatus.SENTENCED.value
    ).count()
    return render_template(
        "teacher/behavior_history.html",
        classroom=classroom,
        pagination=pagination,
        infraction_counts=infraction_counts,
        rescue_count=rescue_count,
        sentenced_count=sentenced_count,
        active_page="behavior_history",
    )


@teacher_bp.route("/behavior/<int:class_id>/die-display", methods=["GET"])
@login_required
@teacher_required
def behavior_die_display(class_id):
    classroom = _classroom_or_404(class_id)
    event_id = request.args.get("event_id", type=int)
    return render_template(
        "teacher/cursed_die_display.html",
        classroom=classroom,
        event_id=event_id,
        active_page="behavior_die",
    )


# --- JSON APIs ---


@teacher_bp.route("/api/behavior/<int:class_id>/bootstrap", methods=["GET"])
@login_required
@teacher_required
def api_behavior_bootstrap(class_id):
    _classroom_or_404(class_id)
    behavior_svc.ensure_classroom_behavior_defaults(class_id)
    db.session.commit()
    settings = behavior_svc.get_or_create_settings(class_id)
    infractions = (
        BehaviorInfraction.query.filter_by(classroom_id=class_id, is_active=True)
        .order_by(BehaviorInfraction.name)
        .all()
    )
    faces = (
        CursedDieFace.query.filter_by(classroom_id=class_id)
        .order_by(CursedDieFace.face_number)
        .all()
    )
    return jsonify(
        {
            "settings": {
                "cascade_hp_damage": settings.cascade_hp_damage,
                "rescue_window_minutes": settings.rescue_window_minutes,
            },
            "infractions": [
                {
                    "id": i.id,
                    "name": i.name,
                    "hp_cost": i.hp_cost,
                    "description": i.description,
                }
                for i in infractions
            ],
            "faces": [
                {
                    "id": f.id,
                    "face_number": f.face_number,
                    "description": f.description,
                    "is_nothing": f.is_nothing,
                }
                for f in faces
            ],
        }
    )


@teacher_bp.route("/api/behavior/<int:class_id>/settings", methods=["POST"])
@login_required
@teacher_required
def api_behavior_settings(class_id):
    _classroom_or_404(class_id)
    data = request.get_json() or {}
    s = behavior_svc.get_or_create_settings(class_id)
    if "cascade_hp_damage" in data:
        v = int(data["cascade_hp_damage"])
        if 0 <= v <= 500:
            s.cascade_hp_damage = v
    if "rescue_window_minutes" in data:
        v = int(data["rescue_window_minutes"])
        if 1 <= v <= 120:
            s.rescue_window_minutes = v
    db.session.add(s)
    db.session.commit()
    return jsonify({"success": True})


@teacher_bp.route("/api/behavior/<int:class_id>/infractions", methods=["POST"])
@login_required
@teacher_required
def api_behavior_infractions(class_id):
    _classroom_or_404(class_id)
    data = request.get_json() or {}
    action = data.get("action", "create")
    if action == "create":
        name = (data.get("name") or "").strip()
        hp_cost = int(data.get("hp_cost", 5))
        if not name or hp_cost < 1 or hp_cost > 500:
            return jsonify({"success": False, "message": "Invalid name or HP cost."}), 400
        row = BehaviorInfraction(
            classroom_id=class_id,
            name=name,
            hp_cost=hp_cost,
            description=(data.get("description") or "").strip() or None,
        )
        db.session.add(row)
        db.session.commit()
        return jsonify({"success": True, "id": row.id})
    if action == "update":
        row = BehaviorInfraction.query.filter_by(
            id=data.get("id"), classroom_id=class_id
        ).first()
        if not row:
            return jsonify({"success": False, "message": "Not found."}), 404
        if "name" in data:
            row.name = (data.get("name") or "").strip() or row.name
        if "hp_cost" in data:
            row.hp_cost = max(1, min(500, int(data["hp_cost"])))
        if "description" in data:
            row.description = (data.get("description") or "").strip() or None
        if "is_active" in data:
            row.is_active = bool(data["is_active"])
        db.session.add(row)
        db.session.commit()
        return jsonify({"success": True})
    if action == "delete":
        row = BehaviorInfraction.query.filter_by(
            id=data.get("id"), classroom_id=class_id
        ).first()
        if not row:
            return jsonify({"success": False, "message": "Not found."}), 404
        row.is_active = False
        db.session.add(row)
        db.session.commit()
        return jsonify({"success": True})
    return jsonify({"success": False, "message": "Unknown action."}), 400


@teacher_bp.route("/api/behavior/<int:class_id>/faces", methods=["POST"])
@login_required
@teacher_required
def api_behavior_faces(class_id):
    _classroom_or_404(class_id)
    data = request.get_json() or {}
    fn = int(data.get("face_number", 0))
    if fn < 1 or fn > 6:
        return jsonify({"success": False, "message": "face_number must be 1-6."}), 400
    face = CursedDieFace.query.filter_by(classroom_id=class_id, face_number=fn).first()
    if not face:
        return jsonify({"success": False, "message": "Face not found."}), 404
    if "description" in data:
        face.description = (data.get("description") or "").strip() or face.description
    if "is_nothing" in data:
        face.is_nothing = bool(data["is_nothing"])
    db.session.add(face)
    db.session.commit()
    return jsonify({"success": True})


@teacher_bp.route("/api/behavior/<int:class_id>/deduct", methods=["POST"])
@login_required
@teacher_required
def api_behavior_deduct(class_id):
    _classroom_or_404(class_id)
    data = request.get_json() or {}
    character_id = int(data.get("character_id", 0))
    ch = _character_in_class(character_id, class_id)
    if not ch:
        return jsonify({"success": False, "message": "Character not found in class."}), 404
    raw_inf = data.get("infraction_id")
    custom_desc = (data.get("custom_description") or "").strip()
    hp_custom = data.get("custom_hp")
    resolved_infraction_id = None
    if raw_inf is not None and str(raw_inf).strip() != "":
        inf = BehaviorInfraction.query.filter_by(
            id=int(raw_inf), classroom_id=class_id, is_active=True
        ).first()
        if not inf:
            return jsonify({"success": False, "message": "Invalid infraction."}), 400
        hp = inf.hp_cost
        desc = inf.name
        resolved_infraction_id = inf.id
    else:
        if not custom_desc:
            return jsonify({"success": False, "message": "Description required."}), 400
        try:
            hp = int(hp_custom)
        except (TypeError, ValueError):
            return jsonify({"success": False, "message": "Invalid custom HP."}), 400
        if hp < 1 or hp > 500:
            return jsonify({"success": False, "message": "HP out of range."}), 400
        desc = custom_desc
    try:
        out = behavior_svc.deduct_hp_for_behavior(
            ch,
            class_id,
            current_user.id,
            hp,
            desc,
            infraction_id=resolved_infraction_id,
        )
        return jsonify(out)
    except ValueError as e:
        return jsonify({"success": False, "message": str(e)}), 400


@teacher_bp.route("/api/behavior/<int:class_id>/fallen", methods=["GET"])
@login_required
@teacher_required
def api_behavior_fallen_list(class_id):
    _classroom_or_404(class_id)
    rows = FallenEvent.query.filter_by(
        classroom_id=class_id, status=FallenStatus.AWAITING_RESCUE.value
    ).all()
    return jsonify(
        {
            "fallen": [behavior_svc.serialize_fallen_event(fe) for fe in rows],
        }
    )


@teacher_bp.route("/api/behavior/<int:class_id>/roll/<int:event_id>", methods=["POST"])
@login_required
@teacher_required
def api_behavior_roll(class_id, event_id):
    _classroom_or_404(class_id)
    fe = FallenEvent.query.filter_by(id=event_id, classroom_id=class_id).first()
    if not fe:
        return jsonify({"success": False, "message": "Event not found."}), 404
    try:
        out = behavior_svc.roll_cursed_die(fe.id, teacher_user_id=current_user.id)
    except ValueError as exc:
        return jsonify({"success": False, "message": str(exc)}), 400
    return jsonify(out)


@teacher_bp.route("/api/behavior/<int:class_id>/resolve-expired", methods=["POST"])
@login_required
@teacher_required
def api_behavior_resolve_expired(class_id):
    _classroom_or_404(class_id)
    results = behavior_svc.resolve_expired_falls(class_id)
    return jsonify({"success": True, "results": results})


@teacher_bp.route("/api/behavior/<int:class_id>/display-result/<int:event_id>", methods=["GET"])
@login_required
@teacher_required
def api_behavior_display_result(class_id, event_id):
    _classroom_or_404(class_id)
    fe = FallenEvent.query.filter_by(id=event_id, classroom_id=class_id).first()
    if not fe:
        return jsonify({"success": False, "message": "Not found."}), 404
    face = fe.sentence_face
    return jsonify(
        {
            "success": True,
            "status": fe.status,
            "die_roll_result": fe.die_roll_result,
            "second_die_roll": fe.second_die_roll,
            "description": face.description if face else None,
            "is_nothing": bool(face and face.is_nothing),
            "character_name": fe.character.name if fe.character else None,
        }
    )
