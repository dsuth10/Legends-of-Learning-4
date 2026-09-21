# Phase 0 Research: Audio Meter Targeting

**Feature**: 005-audio-meter-targeting
**Date**: 2026-09-21
**Spec**: [spec.md](spec.md)

Purpose: resolve every open technical question before design so `plan.md` has no NEEDS CLARIFICATION markers. All findings are grounded in the existing volume meter implementation.

## Existing implementation baseline

| Concern | Current location | Current behaviour |
|---------|------------------|-------------------|
| Settings storage | `app/models/classroom_tool.py` (`ClassroomToolConfig.config_data` JSON, unique on `classroom_id` + `tool_type`) | Seven keys: `threshold`, `breach_duration_seconds`, `damage_amount`, `timer_minutes`, `base_xp_reward`, `base_gold_reward`, `breach_cooldown_seconds` |
| Config + display routes | `app/routes/teacher/classroom_tools.py` | `classroom_tools`, `classroom_tools_display`, config GET/POST, `api_volume_penalty`, `api_volume_reward` |
| Mic + timer + tiering | `static/js/tools/volume_meter.js` | Web Audio RMS with EMA smoothing, `requestAnimationFrame` loop, `rewardMultiplier *= 0.5`, `Math.floor` on payout |
| Tool bootstrapping | `static/js/tools/tool_registry.js`, `static/js/classroom_tools_display.js` | Registry keyed by tool id; display page injects config as JSON script tag |
| Setup page | `app/templates/teacher/classroom_tools.html`, `static/js/classroom_tools_config.js` | Class picker, numeric fields, save, launch display link |
| Targeting | `api_volume_penalty` / `api_volume_reward` | `Student.query.filter_by(class_id=class_id, status='active')` — whole class only |

Four gaps to close: no clan/individual targeting, HP damage always on, `Math.floor` instead of ceiling, and client-supplied payout amounts that the server trusts within a 0-100,000 range.

---

## D1. Where does session state live?

**Decision**: add a new model `AudioMeterSession` (table `audio_meter_sessions`) with an Alembic migration. Keep `ClassroomToolConfig.config_data` for reusable per-classroom settings only.

**Rationale**:
- FR-013 requires awards derived from a server-recorded trigger count. A count that only exists in the browser cannot satisfy this, and `config_data` is a settings row (one per classroom + tool), not a per-run record.
- FR-020 (one active session per classroom) needs a queryable status column.
- FR-014 / SC-006 need a durable id to reference from audit entries so a reduction can be explained later.
- The spec's fixed-roster assumption needs the participant list captured at start time; a settings blob would be overwritten by the next save.

**Alternatives considered**:
- *Everything in `config_data`*: rejected. Conflates durable preferences with transient run state, breaks as soon as two teachers or two tabs touch the same class, and gives no audit trail.
- *Flask server-side session cookie*: rejected. Dies on reload, is per-browser rather than per-classroom, and cannot be inspected for the one-active-session rule.
- *In-memory dict on the app object*: rejected. Lost on restart and wrong under multiple workers.

## D2. How is the participant set represented?

**Decision**: store both the teacher's selection and the resolved snapshot on the session row.

- Selection descriptor: `target_type` (`class` | `custom`) plus `target_clan_ids` and `target_student_ids` JSON lists, so the teacher's intent is auditable.
- Resolved snapshot: `participant_character_ids` JSON list, deduplicated, computed once at session start.

**Rationale**: the snapshot satisfies FR-004 (award at most once even when a student is selected both via clan and individually) with a plain set union, and satisfies the spec assumption that the roster is fixed at session start. Resolving at award time instead would let a mid-session clan change silently alter who gets paid.

**Alternatives considered**:
- *Re-resolve on every trigger and at completion*: rejected. Non-deterministic payouts and contradicts the spec's stated assumption.
- *Association table of session participants*: rejected as over-built for a transient, write-once list that is never queried by participant. A JSON list keeps the migration to a single table, consistent with how `config_data` already stores structured JSON.

**Vocabulary**: reuse the `class` / `clan` / `student` nouns already established by `api_assign_quest` in `app/routes/teacher/students_api.py` so teachers meet one mental model. This feature accepts multi-select, so it sends id lists rather than the single `target_id` that quest assignment uses.

## D3. How are awards made tamper-proof?

**Decision**: the client posts no amounts. Three endpoints — start, trigger, complete — and the server derives every number from the session row.

- `start` copies the current settings onto the session (`base_xp`, `base_gold`, `timer_minutes`, `hp_damage_enabled`, `hp_damage_amount`), locking them for the run.
- `trigger` increments `trigger_count` server-side and returns the new potential payout.
- `complete` computes `ceil(base / 2**trigger_count)` from the locked values and grants it.

**Rationale**: FR-013 and SC-005. Locking settings at start also prevents a mid-session settings save from changing the payout, and returning the authoritative payout from `trigger` means the projector displays the same number the server will grant rather than a parallel client calculation.

**Alternatives considered**:
- *Keep client-supplied amounts with tighter validation*: rejected. Any cap is still a cap an attacker can request in full.
- *Sign the config and verify the signature on completion*: rejected. More moving parts than a session row, and still trusts a client-reported trigger count.

**Timer authority**: `complete` also verifies that `started_at` plus the locked timer duration has actually elapsed (with a small grace window for clock and frame jitter) before granting. Without this check the display could complete instantly and collect the full reward. Paused time is reported by the client as accumulated pause milliseconds and added to the required elapsed threshold; a client under-reporting pause time only delays its own payout, so it cannot inflate the award.

## D4. The halving formula

**Decision**: integer ceiling division per tier, clamped to a floor of 1 when the base is above 0.

```python
def tier_amount(base: int, triggers: int) -> int:
    """Reward after n triggers: ceil(base / 2**n), never below 1 when base > 0."""
    if base <= 0:
        return 0
    divisor = 2 ** triggers
    return max(1, -(-base // divisor))
```

**Rationale**: `-(-base // divisor)` is exact integer ceiling division with no float rounding risk. Iterated halving with rounding up is mathematically identical to a single `ceil(base / 2**n)` (the standard nested-ceiling identity), so the closed form is safe and avoids a loop. Verifies against the spec example: base 100 gold gives 100, 50, 25, then `ceil(100/8) = ceil(12.5) = 13`. Base 1000 XP gives 1000, 500, 250, 125.

**Guard**: `2 ** triggers` grows unboundedly, so cap the exponent used in the calculation (the result is pinned at 1 long before that) to avoid pathological big-integer work if a session somehow records a huge trigger count.

**Alternatives considered**:
- *`math.ceil(base * 0.5 ** n)`*: rejected. Float error makes exact boundary cases (a base of 2 at high tiers) unreliable.
- *Floor, as today*: rejected. Produces 12 gold where the spec requires 13.

## D5. HP damage becomes optional

**Decision**: add `hp_damage_enabled` (default `False`) to the volume meter config defaults, keep the existing `damage_amount` key, and apply damage on trigger only when the flag is on and only to snapshot participants.

**Rationale**: FR-015 through FR-017. Adding a key to `DEFAULT_VOLUME_CONFIG` needs no migration because `_merge_volume_config` already fills missing keys from defaults, so existing classroom rows silently gain the safe default of off.

**Damage application**: reuse `Character.take_damage`, which already clamps at zero. Deliberately do **not** route through `app/services/behavior.py` `deduct_hp_for_behavior`: that would create `BehaviorIncident` rows and can start `FallenEvent` rescue windows, which FR-025 puts out of scope.

## D6. One active session per classroom

**Decision**: enforce in the service layer with a status query, not a database partial index.

`status` is an enum-backed string: `active`, `completed`, `abandoned`. Starting a session marks any existing `active` row for that classroom as `abandoned` (awarding nothing, per FR-012) and then inserts the new row, inside one transaction.

**Rationale**: SQLite is the development database here and its partial-index support across Alembic versions is inconsistent; a filtered unique constraint on "one active per classroom" is not portable. A service-level check inside a transaction is adequate for a single-teacher-per-classroom tool and keeps the migration plain. Index `classroom_id` and `status` so the lookup stays cheap.

**Reload handling**: a reload leaves the row `active` with no client driving it. Per the spec, that attempt is abandoned — the next start supersedes it. No durable resume is built.

## D7. Audit trail and student visibility

**Decision**: write one `AuditLog` row per rewarded character using the existing `TOOL_REWARD` event type, with a human-readable `description`, plus one batch summary row with `character_id=None`. Mirror this for `TOOL_PENALTY` when HP damage is enabled.

**Rationale**: no new `EventType` member is needed (`TOOL_REWARD` and `TOOL_PENALTY` already exist), so no enum migration. More importantly, the student Progress page already renders a per-character feed:

```959:972:app/routes/student_main.py
    # Recent Activity Feed
    try:
        recent_activities = AuditLog.query.filter(
            AuditLog.character_id == main_character.id
        ).order_by(AuditLog.event_timestamp.desc()).limit(15).all()
```

It reads `event_data['description']`. Writing per-character rows with a description such as "Quiet-time reward: 250 XP and 25 gold (halved twice after 2 noise triggers)" satisfies FR-014 and SC-006 with zero student-side code changes. Today's implementation only writes a single batch row with `character_id=None`, which never reaches this feed.

**Payload keys** on each per-character row: `tool`, `session_id`, `classroom_id`, `base_xp`, `base_gold`, `trigger_count`, `xp_awarded`, `gold_awarded`, `description`.

## D8. Reward application path

**Decision**: reuse `Character.gain_experience(amount)` for XP (it handles the level-up threshold and stat bumps) and `character.gold += amount` for gold, matching the existing `api_volume_reward` body. Commit once per session completion rather than per character.

**Rationale**: consistency with the tool's current behaviour and with quest rewards. `Character.gain_experience` internally calls `level_up`, which calls `self.save()`; this is pre-existing behaviour and is out of scope to refactor here. Wrapping the whole completion in one transaction still gives an all-or-nothing award.

## D9. Client-side changes

**Decision**: extend `static/js/tools/volume_meter.js` in place rather than adding a second tool.

- Replace the local `rewardMultiplier` payout calculation with the authoritative numbers returned by the `trigger` endpoint.
- Post `session_id` to trigger and complete; obtain it from the start endpoint.
- Mirror the ceiling formula only for optimistic display between responses.
- Keep the Web Audio RMS + EMA detection, the `requestAnimationFrame` loop, threshold, breach duration, and cooldown exactly as they are; no new dependency and no change to how noise is measured.

**Rationale**: the detection half already works and is the risky part to rewrite. Registering a second tool id would duplicate mic handling and leave two meters to maintain.

**Participant picker placement**: on the display page, before start, so the teacher chooses participants for that run (FR-018, and User Story 5's requirement that selection stays per-session). It needs a roster, so add a read-only targets endpoint returning the classroom's clans and students — the same shape idea as `assignment-targets` in `specs/003-adventure-player-polish/contracts/teacher-assignment-api.md`.

## D10. CSRF and transport

**Decision**: plain JSON `fetch` with `credentials: 'same-origin'`, no CSRF token, matching the existing calls.

**Rationale**: there is no global `CSRFProtect` registered in `app/__init__.py`; CSRF protection here comes from Flask-WTF forms only. The existing `api_volume_penalty` and `api_volume_reward` posts already work this way. Introducing token handling for these three endpoints alone would be inconsistent; authorization is enforced by `@login_required`, `@teacher_required`, and a per-classroom ownership check on every endpoint.

## D11. Response envelope

**Decision**: use the constitution's `{"success": true, "data": {...}}` envelope for the three new session endpoints.

**Rationale**: the constitution's API Patterns section mandates it, and Adventures already follows it. The older classroom tools endpoints return bare objects; those are left alone to avoid breaking the current display, and the new endpoints set the correct precedent. This inconsistency is noted in `plan.md` rather than hidden.

## D12. Validation

**Decision**: Pydantic `BaseModel` schemas in the service module for the three new request bodies, per the constitution's API Patterns section, with the existing clamp-style coercion retained for the settings POST.

**Rationale**: the constitution calls for Pydantic request validation. The settings endpoint's clamping behaviour is relied on by the current setup page, so it keeps its clamps and simply gains the `hp_damage_enabled` boolean.

---

## Resolved unknowns summary

| Question | Resolution |
|----------|-----------|
| Session state location | New `audio_meter_sessions` table (D1) |
| Participant representation | Selection descriptor + resolved character id snapshot (D2) |
| Tamper resistance | Server-derived amounts, locked settings, elapsed-time check (D3) |
| Rounding | Integer `ceil(base / 2**n)`, floor of 1 (D4) |
| HP optionality | New config key, default off, bypasses behavior service (D5) |
| Concurrency | Service-level status check, supersede-and-abandon (D6) |
| Student visibility | Per-character `TOOL_REWARD` rows with `description` (D7) |
| Award mechanics | `gain_experience` + gold increment, one transaction (D8) |
| Client strategy | Extend existing `volume_meter.js`, keep detection (D9) |
| CSRF | None, consistent with existing tool endpoints (D10) |
| Envelope | `{"success", "data"}` on new endpoints (D11) |
| Validation | Pydantic for new bodies, clamps retained for settings (D12) |

No NEEDS CLARIFICATION markers remain.
