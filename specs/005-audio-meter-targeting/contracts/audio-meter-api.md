# API Contracts - Audio Meter Sessions

**Feature**: 005-audio-meter-targeting
**Date**: 2026-09-21
**Blueprint**: `teacher_bp` (`url_prefix="/teacher"`), routes defined in `app/routes/teacher/classroom_tools.py`
**Auth**: `@login_required` + `@teacher_required` on every endpoint, plus a per-classroom ownership check equivalent to `_teacher_owns_classroom`.

## Conventions

New endpoints use the constitution's envelope:

```json
{
  "success": true,
  "data": {}
}
```

Errors:

```json
{
  "success": false,
  "error": "Human readable message",
  "code": "VALIDATION_ERROR"
}
```

| Code | HTTP | When |
|------|------|------|
| `VALIDATION_ERROR` | 400 | Bad body, unknown clan/student for this classroom, empty participant selection |
| `FORBIDDEN` | 403 | Teacher does not own the classroom |
| `NOT_FOUND` | 404 | Session id does not exist, or belongs to another classroom |
| `CONFLICT` | 409 | Session not `active`, or completion attempted before the timer elapsed |
| `NO_PARTICIPANTS` | 400 | Selection resolves to zero active characters |

Transport: JSON `fetch` with `credentials: 'same-origin'`, no CSRF token. This matches the existing tool endpoints; there is no global `CSRFProtect` in `app/__init__.py` (research D10).

---

## 1. Participant targets

### `GET /teacher/api/classroom-tools/<int:class_id>/targets`

Roster for the participant picker on the display page. Read-only.

**200 response**:

```json
{
  "success": true,
  "data": {
    "classroom": { "id": 17, "name": "Year 5", "active_character_count": 28 },
    "clans": [
      { "id": 4, "name": "Team Oak", "member_count": 6 },
      { "id": 5, "name": "Team Ash", "member_count": 5 }
    ],
    "students": [
      { "id": 88, "name": "Ada L.", "character_id": 33, "character_name": "Ada the Druid", "clan_id": 4 },
      { "id": 91, "name": "Ben T.", "character_id": null, "character_name": null, "clan_id": null }
    ]
  }
}
```

`character_id: null` marks a student with no active character. The picker may list them disabled; selecting them is not an error, they are simply skipped (spec edge case).

**Errors**: `FORBIDDEN` 403.

---

## 2. Start a session

### `POST /teacher/api/classroom-tools/<int:class_id>/audio-meter/sessions`

Resolves participants, snapshots them, locks the current settings, and abandons any session still `active` for this classroom.

**Request** (whole class):

```json
{ "target_type": "class" }
```

**Request** (clans and individuals combined):

```json
{
  "target_type": "custom",
  "clan_ids": [4, 5],
  "student_ids": [91, 104]
}
```

Validation: `target_type` is `class` or `custom`. For `custom`, at least one of `clan_ids` / `student_ids` must be non-empty. Every id must belong to `class_id`.

**201 response**:

```json
{
  "success": true,
  "data": {
    "session": {
      "id": 12,
      "classroom_id": 17,
      "status": "active",
      "target_type": "custom",
      "target_label": "Team Oak, Team Ash, +2 students",
      "participant_count": 12,
      "skipped_student_ids": [91],
      "trigger_count": 0,
      "timer_seconds": 900,
      "started_at": "2026-09-21T05:12:00Z",
      "hp_damage_enabled": false,
      "hp_damage_amount": 10,
      "base_xp": 1000,
      "base_gold": 100,
      "potential_xp": 1000,
      "potential_gold": 100
    },
    "superseded_session_id": null
  }
}
```

`potential_xp` / `potential_gold` are the authoritative current tier and are what the display must render. `superseded_session_id` is non-null when a stale `active` session was abandoned; that session awards nothing.

**Errors**: `VALIDATION_ERROR` 400 (bad target, foreign clan or student id), `NO_PARTICIPANTS` 400, `FORBIDDEN` 403.

---

## 3. Record a noise trigger

### `POST /teacher/api/classroom-tools/<int:class_id>/audio-meter/sessions/<int:session_id>/trigger`

Called once per sustained threshold breach. The server increments the count and returns the new tier. The client sends no amounts.

**Request**:

```json
{ "level": 0.61 }
```

`level` is the observed noise level, recorded for diagnostics only. It does not affect the award.

**200 response**:

```json
{
  "success": true,
  "data": {
    "session_id": 12,
    "trigger_count": 2,
    "potential_xp": 250,
    "potential_gold": 25,
    "hp_damage_applied": false,
    "damaged_character_ids": [],
    "damage_amount": 0
  }
}
```

With `hp_damage_enabled` true, `hp_damage_applied` is true, `damage_amount` is the locked amount, and `damaged_character_ids` lists snapshot participants that took damage. Damage uses `Character.take_damage` (clamped at 0) and does **not** create `BehaviorIncident` or `FallenEvent` rows.

**Errors**: `NOT_FOUND` 404 (unknown session, or not this classroom's), `CONFLICT` 409 (session is `completed` or `abandoned`), `FORBIDDEN` 403.

Idempotency: not idempotent by design; each call is one counted trigger. The client's existing `breach_cooldown_seconds` prevents a single noisy moment from firing repeatedly.

---

## 4. Complete a session

### `POST /teacher/api/classroom-tools/<int:class_id>/audio-meter/sessions/<int:session_id>/complete`

Grants the current tier to every snapshot participant with an active character, in one transaction.

**Request**:

```json
{ "paused_ms": 42000 }
```

`paused_ms` is total accumulated pause time. The server requires
`now >= started_at + timer_seconds + (paused_ms / 1000) - grace`
before awarding. Under-reporting pause time only delays the client's own payout, so it cannot inflate the award.

**200 response**:

```json
{
  "success": true,
  "data": {
    "session_id": 12,
    "status": "completed",
    "trigger_count": 2,
    "base_xp": 1000,
    "base_gold": 100,
    "xp_awarded_each": 250,
    "gold_awarded_each": 25,
    "rewarded_count": 12,
    "rewarded_character_ids": [33, 41, 47],
    "skipped_student_ids": [91],
    "leveled_up_character_ids": [41]
  }
}
```

Awarded amounts are always `ceil(base / 2**trigger_count)` with a floor of 1 when the base is above 0, computed from the values locked on the session row. Any amount present in the request body is ignored.

**Errors**:

| Code | HTTP | When |
|------|------|------|
| `CONFLICT` | 409 | Session already `completed` or `abandoned`, or the timer has not elapsed |
| `NOT_FOUND` | 404 | Unknown session for this classroom |
| `FORBIDDEN` | 403 | Teacher does not own the classroom |

---

## 5. Abandon a session

### `DELETE /teacher/api/classroom-tools/<int:class_id>/audio-meter/sessions/<int:session_id>`

Backs the display's Reset control. Sets `status = abandoned`. Awards nothing (FR-012).

**200 response**:

```json
{ "success": true, "data": { "session_id": 12, "status": "abandoned" } }
```

Completing an already-abandoned session is a 409.

---

## 6. Settings endpoint change

### `GET|POST /teacher/api/classroom-tools/config/<int:class_id>`

Unchanged shape and unchanged bare-object response (no envelope), so the current setup page keeps working. One new key in `config`:

```json
{
  "tool_type": "volume_meter",
  "config": {
    "threshold": 0.35,
    "breach_duration_seconds": 5,
    "breach_cooldown_seconds": 2,
    "damage_amount": 10,
    "timer_minutes": 15,
    "base_xp_reward": 1000,
    "base_gold_reward": 100,
    "hp_damage_enabled": false
  },
  "is_active": false
}
```

`hp_damage_enabled` is coerced with `bool(...)` on save and defaults to `false` for every pre-existing classroom row, because `_merge_volume_config` backfills missing keys from `DEFAULT_VOLUME_CONFIG`.

---

## 7. Retired endpoints

`POST /teacher/api/classroom-tools/volume/penalty` and `POST /teacher/api/classroom-tools/volume/reward` are superseded by the session endpoints. They remain registered during this feature so an already-open display does not break mid-lesson, and their removal is a follow-up. New client code must not call them, because they accept client-supplied amounts and are whole-class only.

---

## Contract test checklist

| Test | Asserts |
|------|---------|
| Start with `target_type: class` | Participant count equals active characters in the class |
| Start with overlapping clan + student selection | Character appears once in the snapshot (FR-004) |
| Start with a foreign clan id | 400, no session row created |
| Start while another session is active | Prior row becomes `abandoned`, `superseded_session_id` returned, no award |
| Trigger x2 then complete, base 1000/100 | 250 XP and 25 gold per participant |
| Trigger x3 then complete, base 1000/100 | 125 XP and 13 gold per participant (ceiling, not 12) |
| Complete with an inflated body (`xp_amount: 100000`) | Still awards the derived tier only (SC-005) |
| Complete before the timer elapses | 409, no XP or gold change |
| Complete twice | Second call 409, no double award |
| Trigger with HP damage off | No HP change on any participant |
| Trigger with HP damage on | Only snapshot participants lose HP; no `BehaviorIncident` row created |
| Non-participant characters after completion | XP, gold, and HP unchanged (SC-003) |
| Any endpoint as a non-owning teacher | 403 |
| After completion | One `TOOL_REWARD` audit row per rewarded character with a `description`, plus one batch row |
