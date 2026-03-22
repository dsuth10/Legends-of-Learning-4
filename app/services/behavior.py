"""Behavior / fallen / Cursed Die business logic."""

from __future__ import annotations

import logging
import random
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from app.models import db
from app.models.audit import AuditLog, EventType
from app.models.behavior import (
    BehaviorIncident,
    BehaviorInfraction,
    ClassroomBehaviorSettings,
    CursedDieFace,
    FallenEvent,
    FallenStatus,
    FallenTriggerSource,
)
from app.models.character import Character
from app.models.student import Student

logger = logging.getLogger(__name__)

MAX_CASCADE_DEPTH = 5

DEFAULT_INFRACTIONS: List[Tuple[str, int]] = [
    ("Phone out without permission", 8),
    ("Talking over the teacher", 8),
    ("Arriving late to class", 12),
    ("Forgetting materials", 8),
    ("Off-task during work time", 8),
    ("Custom / other", 5),
]

DEFAULT_FACES: List[Tuple[int, str, bool]] = [
    (1, "Clean up duty at the end of class", False),
    (2, "Complete a short reflection or self-assessment", False),
    (3, "Help tidy the room (chairs, whiteboard, materials)", False),
    (4, "Write three classroom rules and why they matter", False),
    (5, "Brief check-in with the teacher after class", False),
    (6, "Lucky escape — no consequence", True),
]


def get_or_create_settings(classroom_id: int) -> ClassroomBehaviorSettings:
    s = ClassroomBehaviorSettings.query.filter_by(classroom_id=classroom_id).first()
    if not s:
        s = ClassroomBehaviorSettings(classroom_id=classroom_id)
        db.session.add(s)
        db.session.flush()
    return s


def ensure_classroom_behavior_defaults(classroom_id: int) -> None:
    """Seed infractions and die faces if none exist."""
    get_or_create_settings(classroom_id)
    if BehaviorInfraction.query.filter_by(classroom_id=classroom_id).count() == 0:
        for name, hp in DEFAULT_INFRACTIONS:
            db.session.add(
                BehaviorInfraction(classroom_id=classroom_id, name=name, hp_cost=hp)
            )
    if CursedDieFace.query.filter_by(classroom_id=classroom_id).count() == 0:
        for num, desc, nothing in DEFAULT_FACES:
            db.session.add(
                CursedDieFace(
                    classroom_id=classroom_id,
                    face_number=num,
                    description=desc,
                    is_nothing=nothing,
                )
            )


def get_active_awaiting_fallen(character_id: int) -> Optional[FallenEvent]:
    return FallenEvent.query.filter_by(
        character_id=character_id,
        status=FallenStatus.AWAITING_RESCUE.value,
    ).first()


def _rescue_deadline(settings: ClassroomBehaviorSettings) -> datetime:
    minutes = settings.rescue_window_minutes or 5
    return datetime.utcnow() + timedelta(minutes=minutes)


def initiate_fall(
    character: Character,
    classroom_id: int,
    incident: Optional[BehaviorIncident] = None,
    trigger: FallenTriggerSource = FallenTriggerSource.BEHAVIOR,
) -> Optional[FallenEvent]:
    if character.health > 0:
        return None
    if get_active_awaiting_fallen(character.id):
        return None
    settings = get_or_create_settings(classroom_id)
    fe = FallenEvent(
        character_id=character.id,
        classroom_id=classroom_id,
        incident_id=incident.id if incident else None,
        trigger_source=trigger.value,
        status=FallenStatus.AWAITING_RESCUE.value,
        rescue_deadline=_rescue_deadline(settings),
    )
    db.session.add(fe)
    db.session.flush()
    return fe


def _log_behavior_penalty(
    character: Character,
    teacher_user_id: Optional[int],
    payload: Dict[str, Any],
) -> None:
    try:
        AuditLog.log_event(
            EventType.BEHAVIOR_PENALTY,
            event_data=payload,
            user_id=teacher_user_id,
            character_id=character.id,
        )
    except Exception as exc:  # pragma: no cover
        logger.warning("BEHAVIOR_PENALTY audit failed: %s", exc)


def deduct_hp_for_behavior(
    character: Character,
    classroom_id: int,
    teacher_user_id: Optional[int],
    hp_amount: int,
    description: str,
    infraction_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Apply HP loss, log incident, optionally start fallen flow."""
    if hp_amount <= 0:
        raise ValueError("hp_amount must be positive")
    student = Student.query.get(character.student_id)
    if not student or student.class_id != classroom_id:
        raise ValueError("Character is not in this classroom")

    incident = BehaviorIncident(
        character_id=character.id,
        classroom_id=classroom_id,
        infraction_id=infraction_id,
        hp_deducted=hp_amount,
        applied_by_user_id=teacher_user_id,
        description=description,
    )
    db.session.add(incident)
    db.session.flush()

    character.health = max(0, character.health - hp_amount)
    db.session.add(character)
    db.session.flush()

    fallen = None
    if character.health == 0:
        fallen = initiate_fall(character, classroom_id, incident=incident)

    db.session.commit()

    _log_behavior_penalty(
        character,
        teacher_user_id,
        {
            "incident_id": incident.id,
            "hp_deducted": hp_amount,
            "description": description,
            "infraction_id": infraction_id,
            "fallen_event_id": fallen.id if fallen else None,
        },
    )

    return {
        "success": True,
        "health": character.health,
        "max_health": character.max_health,
        "incident_id": incident.id,
        "fallen_event_id": fallen.id if fallen else None,
        "awaiting_rescue": bool(fallen),
    }


def get_die_face(classroom_id: int, face_number: int) -> Optional[CursedDieFace]:
    return CursedDieFace.query.filter_by(
        classroom_id=classroom_id, face_number=face_number
    ).first()


def _pick_better_roll(
    r1: int,
    r2: int,
    f1: Optional[CursedDieFace],
    f2: Optional[CursedDieFace],
) -> Tuple[int, Optional[CursedDieFace]]:
    if f1 and f1.is_nothing:
        return r1, f1
    if f2 and f2.is_nothing:
        return r2, f2
    if f1 and f2:
        return (r1, f1) if random.random() < 0.5 else (r2, f2)
    return (r1, f1) if f1 else (r2, f2)


def finalize_sentence_on_fallen(
    fallen: FallenEvent,
    chosen_face_number: int,
    chosen_face: Optional[CursedDieFace],
    second_roll: Optional[int] = None,
    *,
    skip_cascade: bool = False,
    audit_extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Set sentenced state, restore HP to 1, optional team ripple."""
    if chosen_face is None:
        raise ValueError(
            f"Cursed Die face {chosen_face_number} is missing for classroom "
            f"{fallen.classroom_id}. Ensure behavior defaults are seeded before rolling."
        )
    if chosen_face.classroom_id != fallen.classroom_id:
        raise ValueError("Cursed Die face does not belong to this fall's classroom.")
    if chosen_face.face_number != chosen_face_number:
        raise ValueError(
            f"Cursed Die face number mismatch: roll {chosen_face_number} vs "
            f"face {chosen_face.face_number}."
        )

    fallen.die_roll_result = chosen_face_number
    if second_roll is not None:
        fallen.second_die_roll = second_roll
    fallen.sentence_face_id = chosen_face.id
    fallen.status = FallenStatus.SENTENCED.value
    fallen.resolved_at = datetime.utcnow()

    ch = fallen.character
    ch.health = 1
    db.session.add(ch)
    db.session.add(fallen)

    cascade_triggered: List[int] = []
    if (
        not skip_cascade
        and not chosen_face.is_nothing
        and not fallen.team_damage_applied
    ):
        cascade_triggered = _apply_cascade_team_damage(fallen, depth=0)

    fallen.team_damage_applied = True
    db.session.add(fallen)
    db.session.commit()

    try:
        ev: Dict[str, Any] = {
            "fallen_event_id": fallen.id,
            "face_number": chosen_face_number,
            "second_die_roll": second_roll,
            "sentence": chosen_face.description,
            "is_nothing": bool(chosen_face.is_nothing),
            "cascade_new_falls": cascade_triggered,
        }
        if audit_extra:
            ev.update(audit_extra)
        AuditLog.log_event(
            EventType.CURSED_DIE_ROLL,
            event_data=ev,
            user_id=None,
            character_id=fallen.character_id,
        )
    except Exception as exc:  # pragma: no cover
        logger.warning("CURSED_DIE_ROLL audit failed: %s", exc)

    return {
        "success": True,
        "face_number": chosen_face_number,
        "second_die_roll": second_roll,
        "description": chosen_face.description,
        "is_nothing": chosen_face.is_nothing,
        "cascade_new_fallen_ids": cascade_triggered,
    }


def roll_cursed_die(
    fallen_event_id: int,
    teacher_user_id: Optional[int] = None,
) -> Dict[str, Any]:
    fallen = FallenEvent.query.get(fallen_event_id)
    if not fallen:
        return {"success": False, "message": "Fallen event not found."}
    if fallen.status != FallenStatus.AWAITING_RESCUE.value:
        return {"success": False, "message": "This fall is not awaiting a die roll."}

    ensure_classroom_behavior_defaults(fallen.classroom_id)
    db.session.flush()

    roll = random.randint(1, 6)
    face = get_die_face(fallen.classroom_id, roll)
    if face is None:
        return {
            "success": False,
            "message": f"Cursed Die face {roll} is missing for this classroom. "
                       "Please visit Behavior & Cursed Die settings to configure the die.",
        }
    return finalize_sentence_on_fallen(fallen, roll, face)


def roll_cursed_die_twice_pick_best(
    classroom_id: int,
) -> Tuple[int, Optional[CursedDieFace], int, Optional[CursedDieFace], int, Optional[CursedDieFace]]:
    r1 = random.randint(1, 6)
    r2 = random.randint(1, 6)
    f1 = get_die_face(classroom_id, r1)
    f2 = get_die_face(classroom_id, r2)
    best_n, best_f = _pick_better_roll(r1, r2, f1, f2)
    return r1, f1, r2, f2, best_n, best_f


def execute_cheat_death_effect(
    caster: Character,
    ability,
    target: Character,
    *,
    skip_assist_xp: bool = False,
) -> Dict[str, Any]:
    """Cheat Death: fallen teammate only; roll twice, take better outcome."""
    from app.models.ability import Ability

    if not isinstance(ability, Ability):
        return {
            "success": False,
            "message": "Invalid ability.",
            "amount": 0,
            "xp_awarded": 0,
            "effect_type": "utility",
        }

    fallen = get_active_awaiting_fallen(target.id)
    if not fallen:
        return {
            "success": False,
            "message": "Target has no active fall awaiting rescue.",
            "amount": 0,
            "xp_awarded": 0,
            "effect_type": "utility",
        }

    student = Student.query.get(target.student_id)
    if not student:
        return {
            "success": False,
            "message": "Student not found.",
            "amount": 0,
            "xp_awarded": 0,
            "effect_type": "utility",
        }

    r1, f1, r2, f2, best_n, best_f = roll_cursed_die_twice_pick_best(student.class_id)
    if best_f is None:
        return {
            "success": False,
            "message": (
                "Cursed Die is not fully configured for this class "
                f"(rolls {r1} and {r2}). Open Behavior & Cursed Die to set all six faces."
            ),
            "amount": 0,
            "xp_awarded": 0,
            "effect_type": "utility",
        }

    fallen.rescue_ability_id = ability.id
    fallen.rescued_by_character_id = caster.id

    skip_cascade = bool(best_f.is_nothing)
    other_roll = r2 if best_n == r1 else r1
    result = finalize_sentence_on_fallen(
        fallen,
        best_n,
        best_f,
        second_roll=other_roll if r1 != r2 else None,
        skip_cascade=skip_cascade,
        audit_extra={"cheat_death_rolls": [r1, r2]},
    )

    xp_awarded = 0
    if not skip_assist_xp and caster.id != target.id:
        xp_awarded = 8
        caster.gain_experience(xp_awarded)

    msg = (
        f"Cheat Death! Rolls {r1} and {r2}; outcome: {result.get('description', '')}."
    )
    return {
        "success": True,
        "message": msg,
        "amount": best_n,
        "xp_awarded": xp_awarded,
        "effect_type": "utility",
        "die_rolls": [r1, r2],
        "sentence": result,
    }


def try_resolve_fallen_on_revive(
    target: Character,
    caster: Character,
    ability,
) -> None:
    """Mark fallen event rescued after Revive sets HP to 1."""
    fallen = get_active_awaiting_fallen(target.id)
    if not fallen:
        return
    fallen.status = FallenStatus.RESCUED.value
    fallen.rescued_by_character_id = caster.id
    fallen.rescue_ability_id = ability.id
    fallen.resolved_at = datetime.utcnow()
    db.session.add(fallen)
    db.session.flush()
    try:
        AuditLog.log_event(
            EventType.BEHAVIOR_RESCUE,
            event_data={
                "fallen_event_id": fallen.id,
                "rescuer_character_id": caster.id,
                "ability_id": ability.id,
                "ability_name": ability.name,
            },
            user_id=None,
            character_id=target.id,
            commit=False,
        )
    except Exception as exc:  # pragma: no cover
        logger.warning("BEHAVIOR_RESCUE audit failed: %s", exc)


def attempt_rescue_revive(
    fallen_event_id: int,
    rescuer: Character,
    ability,
) -> Dict[str, Any]:
    """Teacher/manual rescue marking (optional)."""
    fallen = FallenEvent.query.get(fallen_event_id)
    if not fallen or fallen.status != FallenStatus.AWAITING_RESCUE.value:
        return {"success": False, "message": "No active fall to rescue."}
    target = fallen.character
    target.health = 1
    db.session.add(target)
    try_resolve_fallen_on_revive(target, rescuer, ability)
    db.session.commit()
    return {"success": True, "message": "Rescued."}


def _apply_cascade_team_damage(
    resolved_fallen: FallenEvent,
    depth: int,
) -> List[int]:
    """Teammates lose cascade HP; new falls get awaiting events. Returns new fallen_event ids."""
    if depth >= MAX_CASCADE_DEPTH:
        return []
    settings = get_or_create_settings(resolved_fallen.classroom_id)
    amt = settings.cascade_hp_damage or 0
    if amt <= 0:
        return []

    victim = resolved_fallen.character
    if not victim.clan_id:
        return []

    mates = (
        Character.query.filter_by(clan_id=victim.clan_id, is_active=True)
        .filter(Character.id != victim.id)
        .all()
    )

    new_ids: List[int] = []
    for m in mates:
        m.health = max(0, m.health - amt)
        db.session.add(m)
    db.session.flush()

    for m in mates:
        if m.health == 0 and not get_active_awaiting_fallen(m.id):
            fe = initiate_fall(
                m,
                resolved_fallen.classroom_id,
                incident=None,
                trigger=FallenTriggerSource.CASCADE,
            )
            if fe:
                new_ids.append(fe.id)
    db.session.flush()
    return new_ids


def resolve_expired_falls(classroom_id: int) -> List[Dict[str, Any]]:
    """Auto-roll die for falls past rescue deadline."""
    now = datetime.utcnow()
    pending = FallenEvent.query.filter_by(
        classroom_id=classroom_id,
        status=FallenStatus.AWAITING_RESCUE.value,
    ).filter(FallenEvent.rescue_deadline.isnot(None)).filter(FallenEvent.rescue_deadline < now).all()

    results = []
    for fe in pending:
        results.append(roll_cursed_die(fe.id))
    return results


def serialize_fallen_event(fe: FallenEvent) -> Dict[str, Any]:
    face = fe.sentence_face
    return {
        "id": fe.id,
        "character_id": fe.character_id,
        "character_name": fe.character.name if fe.character else None,
        "status": fe.status,
        "rescue_deadline": fe.rescue_deadline.isoformat() if fe.rescue_deadline else None,
        "trigger_source": fe.trigger_source,
        "die_roll_result": fe.die_roll_result,
        "second_die_roll": fe.second_die_roll,
        "sentence_description": face.description if face else None,
        "is_nothing": bool(face and face.is_nothing),
        "team_damage_applied": fe.team_damage_applied,
    }
