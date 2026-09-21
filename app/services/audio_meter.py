"""Audio meter session lifecycle: targeting, triggers, and server-derived awards."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models import db
from app.models.audit import AuditLog, EventType
from app.models.audio_meter import AudioMeterSession, AudioMeterSessionStatus
from app.models.character import Character
from app.models.clan import Clan
from app.models.classroom import Classroom
from app.models.student import Student
from app.utils.date_utils import get_utc_now

COMPLETE_GRACE_SECONDS = 2.0
MAX_TIER_EXPONENT = 40
TOOL_TYPE = "volume_meter"


class AudioMeterError(Exception):
    """Service-layer error mapped to an HTTP envelope by the route."""

    def __init__(self, message: str, code: str, http_status: int):
        super().__init__(message)
        self.message = message
        self.code = code
        self.http_status = http_status


class StartSessionRequest(BaseModel):
    target_type: str
    clan_ids: List[int] = Field(default_factory=list)
    student_ids: List[int] = Field(default_factory=list)

    @field_validator("clan_ids", "student_ids", mode="before")
    @classmethod
    def _none_to_list(cls, value):
        return [] if value is None else value

    @model_validator(mode="after")
    def _check_target(self):
        if self.target_type not in ("class", "custom"):
            raise ValueError("target_type must be 'class' or 'custom'")
        if self.target_type == "custom" and not self.clan_ids and not self.student_ids:
            raise ValueError("custom targeting requires clan_ids or student_ids")
        return self


class TriggerRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    level: Optional[float] = None


class CompleteSessionRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    paused_ms: int = 0

    @field_validator("paused_ms", mode="before")
    @classmethod
    def _paused(cls, value):
        if value is None:
            return 0
        return max(0, int(value))


def tier_amount(base: int, triggers: int) -> int:
    """Reward after n triggers: ceil(base / 2**n), never below 1 when base > 0."""
    if base <= 0:
        return 0
    exponent = min(max(int(triggers), 0), MAX_TIER_EXPONENT)
    return max(1, -(-int(base) // (2 ** exponent)))


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _active_character(student: Student) -> Optional[Character]:
    return Character.query.filter_by(student_id=student.id, is_active=True).first()


def _student_display_name(student: Student) -> str:
    user = student.user
    if user and user.first_name:
        last = (user.last_name or "")[:1]
        suffix = f" {last}." if last else ""
        return f"{user.first_name}{suffix}".strip()
    if user:
        return user.get_display_name()
    return f"Student {student.id}"


def resolve_participants(
    classroom: Classroom,
    target_type: str,
    clan_ids: Optional[Sequence[int]] = None,
    student_ids: Optional[Sequence[int]] = None,
) -> Dict[str, Any]:
    """Return a deduplicated active-character snapshot for the teacher's selection."""
    clan_ids = list(clan_ids or [])
    student_ids = list(student_ids or [])

    if target_type == "class":
        students = Student.query.filter_by(class_id=classroom.id, status="active").all()
        return _snapshot_from_students(students, [], [])

    clans = Clan.query.filter(Clan.id.in_(clan_ids)).all() if clan_ids else []
    found_clan_ids = {c.id for c in clans}
    missing_clans = [cid for cid in clan_ids if cid not in found_clan_ids]
    if missing_clans or any(c.class_id != classroom.id for c in clans):
        raise AudioMeterError(
            "One or more clans do not belong to this classroom",
            "VALIDATION_ERROR",
            400,
        )

    students_by_id = []
    if student_ids:
        students_by_id = Student.query.filter(Student.id.in_(student_ids)).all()
        found = {s.id for s in students_by_id}
        if any(sid not in found for sid in student_ids) or any(
            s.class_id != classroom.id for s in students_by_id
        ):
            raise AudioMeterError(
                "One or more students do not belong to this classroom",
                "VALIDATION_ERROR",
                400,
            )

    selected = []
    seen_student_ids = set()
    for clan in clans:
        for character in Character.query.filter_by(clan_id=clan.id, is_active=True).all():
            student = character.student
            if not student or student.class_id != classroom.id or student.status != "active":
                continue
            if student.id not in seen_student_ids:
                selected.append(student)
                seen_student_ids.add(student.id)
    for student in students_by_id:
        if student.id not in seen_student_ids:
            selected.append(student)
            seen_student_ids.add(student.id)

    return _snapshot_from_students(selected, clan_ids, student_ids)


def _snapshot_from_students(
    students: List[Student],
    clan_ids: List[int],
    student_ids: List[int],
) -> Dict[str, Any]:
    characters = []
    skipped = []
    seen_char = set()
    for student in students:
        character = _active_character(student)
        if character is None:
            skipped.append(student.id)
            continue
        if character.id in seen_char:
            continue
        seen_char.add(character.id)
        characters.append(character)
    return {
        "characters": characters,
        "skipped_student_ids": skipped,
        "clan_ids": clan_ids,
        "student_ids": student_ids,
    }


def _target_label(
    classroom: Classroom,
    target_type: str,
    clan_ids: List[int],
    student_ids: List[int],
) -> str:
    if target_type == "class":
        return "Whole class"
    names = []
    if clan_ids:
        clans = Clan.query.filter(Clan.id.in_(clan_ids)).all()
        by_id = {c.id: c.name for c in clans}
        names.extend(by_id[cid] for cid in clan_ids if cid in by_id)
    leftover = len(student_ids)
    if leftover:
        names.append(f"+{leftover} students" if names else f"{leftover} students")
    return ", ".join(names) if names else "Custom"


def session_public_dict(session: AudioMeterSession, skipped_student_ids: Optional[List[int]] = None) -> dict:
    xp = tier_amount(session.base_xp, session.trigger_count)
    gold = tier_amount(session.base_gold, session.trigger_count)
    started = _as_utc(session.started_at)
    classroom = session.classroom
    return {
        "id": session.id,
        "classroom_id": session.classroom_id,
        "status": session.status,
        "target_type": session.target_type,
        "target_label": _target_label(
            classroom,
            session.target_type,
            list(session.target_clan_ids or []),
            list(session.target_student_ids or []),
        ),
        "participant_count": len(session.participant_character_ids or []),
        "skipped_student_ids": skipped_student_ids if skipped_student_ids is not None else [],
        "trigger_count": session.trigger_count,
        "timer_seconds": session.timer_seconds,
        "started_at": started.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hp_damage_enabled": bool(session.hp_damage_enabled),
        "hp_damage_amount": session.hp_damage_amount,
        "base_xp": session.base_xp,
        "base_gold": session.base_gold,
        "potential_xp": xp,
        "potential_gold": gold,
    }


def list_targets(classroom: Classroom) -> dict:
    students = Student.query.filter_by(class_id=classroom.id, status="active").all()
    clans = Clan.query.filter_by(class_id=classroom.id).order_by(Clan.name).all()
    student_payload = []
    active_chars = 0
    for student in students:
        character = _active_character(student)
        if character:
            active_chars += 1
        student_payload.append(
            {
                "id": student.id,
                "name": _student_display_name(student),
                "character_id": character.id if character else None,
                "character_name": character.name if character else None,
                "clan_id": character.clan_id if character else student.clan_id,
            }
        )
    return {
        "classroom": {
            "id": classroom.id,
            "name": classroom.name,
            "active_character_count": active_chars,
        },
        "clans": [
            {
                "id": clan.id,
                "name": clan.name,
                "member_count": Character.query.filter_by(
                    clan_id=clan.id, is_active=True
                ).count(),
            }
            for clan in clans
        ],
        "students": student_payload,
    }


def abandon_active_sessions(classroom_id: int) -> Optional[int]:
    rows = AudioMeterSession.query.filter_by(
        classroom_id=classroom_id,
        status=AudioMeterSessionStatus.ACTIVE.value,
    ).all()
    last_id = None
    for row in rows:
        row.status = AudioMeterSessionStatus.ABANDONED.value
        last_id = row.id
    return last_id


def start_session(
    classroom: Classroom,
    teacher_user_id: int,
    target_type: str,
    clan_ids: Sequence[int],
    student_ids: Sequence[int],
    settings: dict,
) -> Tuple[AudioMeterSession, Optional[int], List[int]]:
    resolved = resolve_participants(classroom, target_type, clan_ids, student_ids)
    characters = resolved["characters"]
    skipped = resolved["skipped_student_ids"]
    if not characters:
        raise AudioMeterError(
            "No active characters in the selection",
            "NO_PARTICIPANTS",
            400,
        )

    superseded = abandon_active_sessions(classroom.id)
    timer_minutes = int(settings.get("timer_minutes") or 15)
    session = AudioMeterSession(
        classroom_id=classroom.id,
        teacher_user_id=teacher_user_id,
        status=AudioMeterSessionStatus.ACTIVE.value,
        target_type=target_type,
        target_clan_ids=list(clan_ids or []),
        target_student_ids=list(student_ids or []),
        participant_character_ids=[c.id for c in characters],
        base_xp=int(settings.get("base_xp_reward") or 0),
        base_gold=int(settings.get("base_gold_reward") or 0),
        timer_seconds=max(1, timer_minutes) * 60,
        hp_damage_enabled=bool(settings.get("hp_damage_enabled", False)),
        hp_damage_amount=int(settings.get("damage_amount") or 0),
        trigger_count=0,
        started_at=get_utc_now(),
    )
    db.session.add(session)
    db.session.commit()
    return session, superseded, skipped


def get_owned_session(classroom_id: int, session_id: int) -> AudioMeterSession:
    session = db.session.get(AudioMeterSession, session_id)
    if session is None or session.classroom_id != classroom_id:
        raise AudioMeterError("Session not found", "NOT_FOUND", 404)
    return session


def _require_active(session: AudioMeterSession) -> None:
    if session.status != AudioMeterSessionStatus.ACTIVE.value:
        raise AudioMeterError(
            "Session is not active",
            "CONFLICT",
            409,
        )


def _load_snapshot_characters(session: AudioMeterSession) -> List[Character]:
    ids = list(session.participant_character_ids or [])
    if not ids:
        return []
    found = Character.query.filter(Character.id.in_(ids), Character.is_active.is_(True)).all()
    by_id = {c.id: c for c in found}
    return [by_id[i] for i in ids if i in by_id]


def _reward_description(xp: int, gold: int, triggers: int) -> str:
    base = f"Quiet-time reward: {xp} XP and {gold} gold"
    if triggers <= 0:
        return base
    if triggers == 1:
        halved = "once"
        trigger_word = "trigger"
    elif triggers == 2:
        halved = "twice"
        trigger_word = "triggers"
    else:
        halved = f"{triggers} times"
        trigger_word = "triggers"
    return f"{base} (halved {halved} after {triggers} noise {trigger_word})"


def record_trigger(session: AudioMeterSession, level: Optional[float] = None) -> dict:
    _require_active(session)
    session.trigger_count = int(session.trigger_count or 0) + 1
    damaged_ids = []
    damage_amount = 0
    applied = False
    if session.hp_damage_enabled:
        damage_amount = int(session.hp_damage_amount or 0)
        if damage_amount > 0:
            applied = True
            for character in _load_snapshot_characters(session):
                character.take_damage(damage_amount)
                damaged_ids.append(character.id)
            _write_penalty_audits(session, damaged_ids, damage_amount)

    db.session.add(session)
    db.session.commit()
    return {
        "session_id": session.id,
        "trigger_count": session.trigger_count,
        "potential_xp": tier_amount(session.base_xp, session.trigger_count),
        "potential_gold": tier_amount(session.base_gold, session.trigger_count),
        "hp_damage_applied": applied,
        "damaged_character_ids": damaged_ids,
        "damage_amount": damage_amount if applied else 0,
        "level": level,
    }


def _write_penalty_audits(session: AudioMeterSession, damaged_ids: List[int], amount: int) -> None:
    payload = {
        "tool": TOOL_TYPE,
        "session_id": session.id,
        "classroom_id": session.classroom_id,
        "damage_amount": amount,
        "trigger_count": session.trigger_count,
        "description": f"Quiet-time noise: {amount} HP",
    }
    for cid in damaged_ids:
        AuditLog.log_event(
            EventType.TOOL_PENALTY,
            user_id=session.teacher_user_id,
            character_id=cid,
            event_data=dict(payload),
            commit=False,
        )
    AuditLog.log_event(
        EventType.TOOL_PENALTY,
        user_id=session.teacher_user_id,
        character_id=None,
        event_data={
            **payload,
            "affected_character_ids": damaged_ids,
            "count": len(damaged_ids),
        },
        commit=False,
    )


def complete_session(
    session: AudioMeterSession,
    paused_ms: int = 0,
    now: Optional[datetime] = None,
) -> dict:
    _require_active(session)
    clock = _as_utc(now or get_utc_now())
    started = _as_utc(session.started_at)
    required = session.timer_seconds + (max(0, paused_ms) / 1000.0) - COMPLETE_GRACE_SECONDS
    elapsed = (clock - started).total_seconds()
    if elapsed < required:
        raise AudioMeterError(
            "Timer has not elapsed",
            "CONFLICT",
            409,
        )

    xp_each = tier_amount(session.base_xp, session.trigger_count)
    gold_each = tier_amount(session.base_gold, session.trigger_count)
    rewarded_ids = []
    leveled = []
    skipped = []

    snapshot_ids = list(session.participant_character_ids or [])
    characters = _load_snapshot_characters(session)
    present = {c.id for c in characters}
    for cid in snapshot_ids:
        if cid not in present:
            skipped.append(cid)

    description = _reward_description(xp_each, gold_each, session.trigger_count)
    for character in characters:
        before_level = character.level
        if gold_each > 0:
            character.gold += gold_each
        if xp_each > 0:
            character.gain_experience(xp_each)
        if character.level > before_level:
            leveled.append(character.id)
        rewarded_ids.append(character.id)
        AuditLog.log_event(
            EventType.TOOL_REWARD,
            user_id=session.teacher_user_id,
            character_id=character.id,
            event_data={
                "tool": TOOL_TYPE,
                "session_id": session.id,
                "classroom_id": session.classroom_id,
                "base_xp": session.base_xp,
                "base_gold": session.base_gold,
                "trigger_count": session.trigger_count,
                "xp_awarded": xp_each,
                "gold_awarded": gold_each,
                "description": description,
            },
            commit=False,
        )

    AuditLog.log_event(
        EventType.TOOL_REWARD,
        user_id=session.teacher_user_id,
        character_id=None,
        event_data={
            "tool": TOOL_TYPE,
            "session_id": session.id,
            "classroom_id": session.classroom_id,
            "base_xp": session.base_xp,
            "base_gold": session.base_gold,
            "trigger_count": session.trigger_count,
            "xp_awarded": xp_each,
            "gold_awarded": gold_each,
            "rewarded_character_ids": rewarded_ids,
            "skipped_student_ids": skipped,
            "count": len(rewarded_ids),
            "description": description,
        },
        commit=False,
    )

    session.status = AudioMeterSessionStatus.COMPLETED.value
    session.completed_at = clock
    session.xp_awarded_each = xp_each
    session.gold_awarded_each = gold_each
    db.session.add(session)
    db.session.commit()
    return {
        "session_id": session.id,
        "status": session.status,
        "trigger_count": session.trigger_count,
        "base_xp": session.base_xp,
        "base_gold": session.base_gold,
        "xp_awarded_each": xp_each,
        "gold_awarded_each": gold_each,
        "rewarded_count": len(rewarded_ids),
        "rewarded_character_ids": rewarded_ids,
        "skipped_student_ids": skipped,
        "leveled_up_character_ids": leveled,
    }


def abandon_session(session: AudioMeterSession) -> dict:
    _require_active(session)
    session.status = AudioMeterSessionStatus.ABANDONED.value
    db.session.add(session)
    db.session.commit()
    return {"session_id": session.id, "status": session.status}
