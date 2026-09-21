# Tasks: Audio Meter Targeting

**Input**: Design documents from `specs/005-audio-meter-targeting/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/audio-meter-api.md`, `quickstart.md`

**Tests**: Included. The constitution requires pytest for new features, and [plan.md](plan.md) Phase D plus [contracts/audio-meter-api.md](contracts/audio-meter-api.md) list the cases. All live in `tests/test_audio_meter.py`.

**Organization**: Tasks are grouped by user story so each story can be implemented, tested, and demonstrated independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel because it touches different files or has no dependency on incomplete tasks.
- **[Story]**: Maps to the user story phase. Setup, foundational, and polish tasks have no story label.
- Every task includes an exact file path.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm the current volume meter surface before changing it.

- [X] T001 Review the existing whole-class meter in `app/routes/teacher/classroom_tools.py`, `app/models/classroom_tool.py`, `static/js/tools/volume_meter.js`, `static/js/classroom_tools_config.js`, and `static/js/classroom_tools_display.js`
- [X] T002 [P] Confirm student Progress already renders `AuditLog.event_data['description']` for `character_id` rows in `app/routes/student_main.py` (needed later for US4 visibility, no student-side change)
- [X] T003 [P] Run the existing teacher test baseline with `pytest tests/test_class_routes.py tests/test_character_management.py -q` so later audio-meter work has a known-good starting point

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Session table, service primitives, and the new settings default. No user story work until this phase is complete.

**Critical**: No user story work should begin until this phase is complete.

- [X] T004 Create `AudioMeterSession` and `AudioMeterSessionStatus` in `app/models/audio_meter.py` per [data-model.md](data-model.md) (columns, JSON lists, `ondelete='CASCADE'`, `idx_audio_meter_session_classroom_status`)
- [X] T005 Import `AudioMeterSession` and `AudioMeterSessionStatus` inside `init_db()` in `app/models/__init__.py`
- [X] T006 Import the new model in `migrations/env.py` so Alembic autogenerate can see `audio_meter_sessions`
- [X] T007 Generate the Alembic revision that creates `audio_meter_sessions` under `migrations/versions/`
- [X] T008 Run `alembic upgrade head` (config in `alembic.ini`) so the development database matches the new `audio_meter_sessions` revision under `migrations/versions/`
- [X] T009 Add `tier_amount(base, triggers)` using integer ceiling division (`max(1, -(-base // 2**min(triggers, 40)))`, zero stays zero) in `app/services/audio_meter.py`
- [X] T010 Add `resolve_participants(classroom, target_type, clan_ids, student_ids)` with classroom membership checks and character-id dedup in `app/services/audio_meter.py`
- [X] T011 Add `abandon_active_sessions(classroom_id)` and `start_session(...)` (lock settings from `ClassroomToolConfig`, snapshot `participant_character_ids`, supersede any active row) in `app/services/audio_meter.py`
- [X] T012 Add `complete_session(...)` that awards `tier_amount` XP via `Character.gain_experience` and gold via `character.gold += amount` to snapshot participants in one transaction in `app/services/audio_meter.py`
- [X] T013 Add `hp_damage_enabled: False` to `DEFAULT_VOLUME_CONFIG` and coerce it in the settings POST in `app/routes/teacher/classroom_tools.py`

**Checkpoint**: Model and migration exist. Service can resolve a roster, start a session, and compute a tier. Display still uses the old whole-class penalty/reward URLs.

---

## Phase 3: User Story 1 - Run a quiet-time session for selected participants (Priority: P1) — MVP

**Goal**: Teacher picks whole class, clan(s), and/or students; completing a zero-trigger session awards the locked base XP and gold only to snapshot participants.

**Independent Test**: Two-clan classroom. Select Clan A only, complete with zero triggers, confirm only Clan A members with active characters receive the full base. Clan B and unclanned students unchanged. See [quickstart.md](quickstart.md) §5.

### Tests for User Story 1

> Write these tests first and ensure they FAIL until the targeting endpoints exist.

- [X] T014 [US1] Add pytest fixtures (teacher, classroom, two clans, students with and without active characters) and targeting tests (whole class, one clan, two students, clan+overlapping student awards once, skipped student with no character) in `tests/test_audio_meter.py`
- [X] T015 [US1] Add 400 tests for a foreign clan/student id, `NO_PARTICIPANTS` when the selection has no active characters, and 403 for a non-owning teacher on start in `tests/test_audio_meter.py`

### Implementation for User Story 1

- [X] T016 [US1] Add Pydantic request models for start (`target_type`, `clan_ids`, `student_ids`) in `app/services/audio_meter.py` or a sibling module imported by the route
- [X] T017 [US1] Implement `GET /teacher/api/classroom-tools/<class_id>/targets` returning classroom, clans, and students (null `character_id` when none) in `app/routes/teacher/classroom_tools.py` per [contracts/audio-meter-api.md](contracts/audio-meter-api.md)
- [X] T018 [US1] Implement `POST /teacher/api/classroom-tools/<class_id>/audio-meter/sessions` calling `start_session`, returning 201 with `{"success": true, "data": {session, superseded_session_id}}` in `app/routes/teacher/classroom_tools.py`
- [X] T019 [US1] Implement `POST .../sessions/<session_id>/complete` calling `complete_session` and returning rewarded counts/ids in `app/routes/teacher/classroom_tools.py`
- [X] T020 [US1] Pass session start/complete URLs and the targets URL into display config in `app/routes/teacher/classroom_tools.py` and `app/templates/teacher/classroom_tools_display.html`
- [X] T021 [US1] Thread those URLs into the volume meter constructor via `buildToolConfig` in `static/js/classroom_tools_display.js`
- [X] T022 [US1] Add a pre-start participant picker (whole class, clan checkboxes, student checkboxes; disable students with no character) in `static/js/tools/volume_meter.js`
- [X] T023 [US1] Style the picker so it is usable on the projector layout in `static/css/classroom_tools.css`
- [X] T024 [US1] On Start, POST the selection to the start endpoint, store `session_id`, and on timer end POST complete (no client-computed `xp_amount`/`gold_amount`) in `static/js/tools/volume_meter.js`

**Checkpoint**: A teacher can complete a targeted zero-trigger session and only selected characters are paid. Trigger/HP/trust checks are not required yet. Old penalty/reward endpoints may still exist unused.

---

## Phase 4: User Story 2 - Noise triggers halve the remaining reward (Priority: P1)

**Goal**: Each sustained noise breach increments a server-side trigger count and halves the potential reward with ceiling rounding. The display shows the authoritative tier before the timer ends.

**Independent Test**: Base 1000 XP / 100 gold. One trigger → 500/50; two → 250/25; three → 125/13. Display updates on each trigger. See [quickstart.md](quickstart.md) §4.

### Tests for User Story 2

- [X] T025 [US2] Add a `tier_amount` table test for bases 1000/100 at 0–3 triggers (including gold 13, not 12) plus floor-of-1 and base-zero stays zero in `tests/test_audio_meter.py`
- [X] T026 [US2] Add route tests: two triggers then complete awards 250/25; three triggers then complete awards 125/13 per snapshot participant in `tests/test_audio_meter.py`

### Implementation for User Story 2

- [X] T027 [US2] Add `record_trigger(session, level=None)` that increments `trigger_count` only while `status == active` and returns the new `potential_xp`/`potential_gold` in `app/services/audio_meter.py`
- [X] T028 [US2] Implement `POST .../sessions/<session_id>/trigger` with Pydantic body (`level` optional/diagnostic) returning the envelope from [contracts/audio-meter-api.md](contracts/audio-meter-api.md) in `app/routes/teacher/classroom_tools.py`
- [X] T029 [US2] On sustained breach, POST trigger and render `potential_xp`/`potential_gold`/`trigger_count` from the response (stop using `Math.floor` × local multiplier for the granted amount) in `static/js/tools/volume_meter.js`
- [X] T030 [US2] Keep Web Audio RMS, EMA, threshold, breach duration, and cooldown behaviour unchanged in `static/js/tools/volume_meter.js`; only the payout path changes

**Checkpoint**: Completing after N triggers pays `ceil(base / 2^N)`. The projector shows the same numbers the server will grant.

---

## Phase 5: User Story 3 - HP damage is optional and off by default (Priority: P2)

**Goal**: Triggers never change HP unless the teacher turns HP damage on. When on, only snapshot participants take `Character.take_damage`; no behavior incidents.

**Independent Test**: Default session + trigger → HP unchanged, tier halves. Enable HP, start a new session, trigger → only participants lose HP. See [quickstart.md](quickstart.md) §7.

### Tests for User Story 3

- [X] T031 [US3] Add tests: default/off trigger leaves HP unchanged; enabled trigger damages only snapshot participants; no `BehaviorIncident` row is created in `tests/test_audio_meter.py`

### Implementation for User Story 3

- [X] T032 [US3] When `hp_damage_enabled` is locked true on the session, apply `Character.take_damage(hp_damage_amount)` to snapshot participants inside `record_trigger` in `app/services/audio_meter.py` (do not call `app/services/behavior.py`)
- [X] T033 [US3] Return `hp_damage_applied`, `damaged_character_ids`, and `damage_amount` from the trigger endpoint in `app/routes/teacher/classroom_tools.py`
- [X] T034 [US3] Add an HP-damage toggle (default off) and keep the damage-amount field enabled only while the toggle is on in `app/templates/teacher/classroom_tools.html`
- [X] T035 [US3] Read/write `hp_damage_enabled` with the rest of the config in `static/js/classroom_tools_config.js`

**Checkpoint**: Existing classrooms stay HP-off via `_merge_volume_config`. Optional HP never creates Cursed Die / behavior rows.

---

## Phase 6: User Story 4 - Session controls and honest completion (Priority: P2)

**Goal**: Pause/resume/reset work. Awards come only from locked bases + recorded triggers after the timer elapsed. Reset/abandon/reload grant nothing. Students see why a reward was reduced.

**Independent Test**: Complete a session and confirm amounts match `ceil(base / 2^triggers)`. POST complete with inflated amounts and still receive only the derived tier. Reset mid-session and confirm no award. See [quickstart.md](quickstart.md) §6, §8, §9.

### Tests for User Story 4

- [X] T036 [US4] Add tests: complete before elapsed time is 409 with no XP/gold change; complete with `xp_amount`/`gold_amount` 100000 still awards the derived tier; complete twice is 409; DELETE abandon then complete is 409 with no award in `tests/test_audio_meter.py`
- [X] T037 [US4] Add tests: starting a second session abandons the first unpaid; after completion each rewarded character has a `TOOL_REWARD` row whose `event_data.description` mentions quiet-time and trigger reduction when `trigger_count > 0` in `tests/test_audio_meter.py`

### Implementation for User Story 4

- [X] T038 [US4] Enforce `now >= started_at + timer_seconds + paused_ms/1000 - grace` inside `complete_session` in `app/services/audio_meter.py`; ignore any client-supplied award amounts
- [X] T039 [US4] Write one per-character `TOOL_REWARD` `AuditLog` (with `description`) plus one batch row on complete, and matching `TOOL_PENALTY` rows when HP was applied, in `app/services/audio_meter.py`
- [X] T040 [US4] Implement `DELETE .../sessions/<session_id>` setting `status = abandoned` and awarding nothing in `app/routes/teacher/classroom_tools.py`
- [X] T041 [US4] Pass the abandon URL into display config in `app/routes/teacher/classroom_tools.py` and `static/js/classroom_tools_display.js`
- [X] T042 [US4] Accumulate pause duration and send `paused_ms` on complete; Reset calls DELETE and does not award; pause still freezes breach timing in `static/js/tools/volume_meter.js`
- [X] T043 [US4] Stop calling `api_volume_penalty` / `api_volume_reward` from `static/js/tools/volume_meter.js` (leave the Flask handlers registered)

**Checkpoint**: Tampering with the display cannot inflate awards. Students see reduced quiet-time rewards on Progress with no student-route changes.

---

## Phase 7: User Story 5 - Configure once, reopen with the same preferences (Priority: P3)

**Goal**: Numeric settings and the HP toggle persist per classroom. Participant selection remains chosen per session before start.

**Independent Test**: Save settings, leave, reopen Classroom Tools for that class, confirm threshold/timer/bases/HP toggle. Start a session and still be able to change who participates. See spec User Story 5.

### Tests for User Story 5

- [X] T044 [US5] Add tests that GET config for a never-saved class includes `hp_damage_enabled: false`, and POST round-trips the flag plus existing numeric keys in `tests/test_audio_meter.py`

### Implementation for User Story 5

- [X] T045 [US5] Confirm settings GET/POST already merge and persist `hp_damage_enabled` through `_merge_volume_config` in `app/routes/teacher/classroom_tools.py` (fix any key dropped on save)
- [X] T046 [US5] Keep participant selection on the display session UI (not saved as the required next-run roster) in `static/js/tools/volume_meter.js` and `static/js/classroom_tools_config.js`

**Checkpoint**: Returning to Classroom Tools restores last numeric/HP preferences. Targeting is still chosen at start.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Guardrails that span stories.

- [X] T047 Confirm `static/js/tools/volume_meter.js` stays under ~500 lines; if the picker pushes it over, extract the picker into `static/js/tools/volume_meter_picker.js`
- [X] T048 [P] Confirm `app/routes/teacher/classroom_tools.py` stays under 500 lines; if not, move session routes to `app/routes/teacher/audio_meter.py` and import the module from `app/routes/teacher/__init__.py`
- [X] T049 [P] Run `pytest tests/test_audio_meter.py -v` then the full `pytest` suite
- [X] T050 Walk [quickstart.md](quickstart.md) sections 3–9 against a running `python run.py` (tiers including 13 gold, targeting, tamper POST, HP optional, Progress description, reset/reload)
- [X] T051 [P] After the feature is implemented, update Current in `docs/now.md` only if the shipped/next wording needs to change (do not invent a new backlog)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately.
- **Foundational (Phase 2)**: Depends on Setup. Blocks all user stories.
- **User Story 1 (Phase 3)**: Depends on Foundational. MVP.
- **User Story 2 (Phase 4)**: Depends on US1 complete (needs start + complete + snapshot).
- **User Story 3 (Phase 5)**: Depends on US2 (`record_trigger` must exist). Independently testable once wired.
- **User Story 4 (Phase 6)**: Depends on US1 complete path; trigger tests reuse US2. Can overlap US3 on different files (`tests/test_audio_meter.py` is shared — do not parallelize test edits).
- **User Story 5 (Phase 7)**: Depends on T013 and US3 config UI. Small and last.
- **Polish (Phase 8)**: After the stories you intend to ship.

### User Story Dependencies

- **User Story 1 (P1)**: After Phase 2. No other story required. MVP: targeted zero-trigger award.
- **User Story 2 (P1)**: After US1. Adds trigger + ceiling tier.
- **User Story 3 (P2)**: After US2. Adds optional HP on the same trigger path.
- **User Story 4 (P2)**: After US1 (and US2 for reduced-award descriptions). Adds abandon, elapsed-time gate, audit, pause `paused_ms`.
- **User Story 5 (P3)**: After settings default (T013) and US3 toggle. Persistence only.

US1 is independently demoable without triggers. US2–US4 share `classroom_tools.py`, `audio_meter.py` (service), and `volume_meter.js` — implement them sequentially, not in parallel, if one person is writing the code.

### Within Each User Story

- Tests first; they should fail until the endpoints exist.
- Service before routes.
- Routes before display JavaScript.
- Story complete before the next priority unless a [P] task truly touches a different file.

### Parallel Opportunities

- T002 and T003 during Setup.
- T034/T035 (templates/JS) can proceed beside T032/T033 after T031 is written, but not beside other edits to `classroom_tools.py`.
- T047 and T048 after implementation, in parallel with each other.
- T049 then T050 sequentially (tests before manual quickstart).

---

## Parallel Example: User Story 1

```text
# After T014–T015 tests exist and fail:
Task: "GET targets in app/routes/teacher/classroom_tools.py"
# then sequentially:
Task: "POST start in app/routes/teacher/classroom_tools.py"
Task: "POST complete in app/routes/teacher/classroom_tools.py"
# then UI (different files, after URLs exist):
Task: "Picker markup in static/js/tools/volume_meter.js"
Task: "Picker styles in static/css/classroom_tools.css"
```

Do not mark T017–T019 [P]: they all edit `app/routes/teacher/classroom_tools.py`.

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (blocks everything)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: clan-only zero-trigger award, non-participants unchanged
5. Demo if ready

### Incremental Delivery

1. Setup + Foundational → session table and `tier_amount` exist
2. US1 → targeted quiet completion (MVP)
3. US2 → ceiling-halved rewards and live display
4. US3 → optional HP, default off
5. US4 → tamper-proof complete, reset, student-visible descriptions
6. US5 → settings round-trip
7. Polish → size limits, full pytest, quickstart walkthrough

### Suggested MVP scope

User Story 1 only: participant picker + start + complete with server-derived full-tier awards. Do not ship US1 alone to a classroom that expects noise to reduce rewards; US2 is the second required increment for the stated product.

---

## Notes

- [P] tasks = different files, no dependency on incomplete work in the same file.
- New JSON endpoints use `{"success": true, "data": {...}}`. Existing config GET/POST stay bare objects.
- Leave `api_volume_penalty` and `api_volume_reward` registered until a later cleanup; new client code must not call them.
- HP damage uses `Character.take_damage` only — never `deduct_hp_for_behavior`.
- Commit after each task or logical group. Stop at any checkpoint to validate the story independently.
