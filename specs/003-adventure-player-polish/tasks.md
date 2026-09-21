# Tasks: Adventures Player and Editor Polish

**Input**: Design documents from `specs/003-adventure-player-polish/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

**Tests**: Included for stories with backend contracts (US4 assignment, US5 icons). User Stories 1–3 are client-side; their independent tests are the quickstart smokes, not new pytest files.

**Organization**: Tasks are grouped by user story so each story can be implemented, tested, and demonstrated independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel because it touches different files or has no dependency on incomplete tasks.
- **[Story]**: Maps to the user story phase. Setup, foundational, and polish tasks have no story label.
- Every task includes an exact file path.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm the shipped 001/002 baseline before adding Phase 5 polish.

- [X] T001 Run the baseline adventure route suites in `tests/test_adventure_routes_teacher.py` and `tests/test_adventure_routes_student.py`
- [X] T002 [P] Review current student map render, complete/choose refresh, and node keyboard handlers in `static/js/adventure_player.js`
- [X] T003 [P] Review current player markup, keyboard help, and layout in `app/templates/student/adventure_map.html`
- [X] T004 [P] Review current editor graph render, inspector, and missing keydown/zoom/undo in `static/js/adventure_editor.js`
- [X] T005 [P] Review the clan/character rejection in `POST` assignment handling in `app/routes/adventures/teacher.py`
- [X] T006 [P] Review class/clan/character matching and roster resolution in `app/services/adventure_graph.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Add shared player and editor modules that later stories fill in, without growing the existing 1100-line editor and player files first.

**Critical**: No user story work should begin until this phase is complete.

- [X] T007 Create the player map module stub with `init`/`refresh` hooks in `static/js/adventure_player_map.js`
- [X] T008 Load `adventure_player_map.js` and add a polite `aria-live` status region in `app/templates/student/adventure_map.html`
- [X] T009 Call the player map module from `AdventurePlayer.init` and `refresh` in `static/js/adventure_player.js`
- [X] T010 [P] Create the editor command-stack stub with `init` in `static/js/adventure_editor_commands.js`
- [X] T011 Load `adventure_editor_commands.js` from `app/templates/teacher/adventure_editor.html`

**Checkpoint**: Player and editor pages load the new modules. Graph play and authoring still behave as they do today.

---

## Phase 3: User Story 1 - Travel animation after completing a node (Priority: P1) — MVP

**Goal**: Students see a character marker that travels from a completed node to newly unlocked successors, skips motion when reduced motion is requested, and replays once after a battle/quiz return.

**Independent Test**: Complete a story node that unlocks one successor and confirm travel; repeat with two successors, an end node, reduced motion, and a battle return. See `specs/003-adventure-player-polish/quickstart.md` §5.

### Implementation for User Story 1

- [X] T012 [P] [US1] Add character-marker and travel styles in `static/css/adventure_player.css`
- [X] T013 [US1] Render a character marker from `my_progress.current_node_id` (fallback: last completed, then available start) in `static/js/adventure_player_map.js`
- [X] T014 [US1] Animate travel along the connecting path using `next_unlocked` after on-map complete/choose in `static/js/adventure_player.js`
- [X] T015 [US1] Implement forked travel copies for two or more successors, leaving the main marker on the completed node, in `static/js/adventure_player_map.js`
- [X] T016 [US1] Skip travel when `next_unlocked` is empty and keep the marker on the completed node in `static/js/adventure_player_map.js`
- [X] T017 [US1] Honor `prefers-reduced-motion: reduce` by updating states with no motion in `static/js/adventure_player_map.js`
- [X] T018 [US1] Interrupt in-flight travel on node select, mini-map jump, or navigation and snap to the final state in `static/js/adventure_player_map.js`
- [X] T019 [US1] Infer pending travel on map load from latest `completed_at` plus available successors, and record seen keys in `sessionStorage`, in `static/js/adventure_player_map.js`
- [X] T020 [US1] Announce newly unlocked node titles through the player live region in `app/templates/student/adventure_map.html`

**Checkpoint**: User Story 1 is playable on its own. Mini-map, editor keyboard, assignment, and icons are not required.

---

## Phase 4: User Story 2 - Mini-map for orientation and camera jump (Priority: P2)

**Goal**: Students get an overview of a large map, see the current view and marker, and can jump the main view by pointer or keyboard.

**Independent Test**: Open an overflowing adventure, confirm the overview tracks the viewport, jump via click and via a focused overview mark, and check a phone-sized window. See `quickstart.md` §6.

### Implementation for User Story 2

- [X] T021 [US2] Add the overview landmark markup (`role="navigation"`, name "Adventure overview") in `app/templates/student/adventure_map.html`
- [X] T022 [US2] Draw a scaled overview of nodes/edges plus a viewport rectangle bound to `#map-container` scroll in `static/js/adventure_player_map.js`
- [X] T023 [US2] Jump the main view with `scrollTo` within one second when the overview is clicked in `static/js/adventure_player_map.js`
- [X] T024 [US2] Add keyboard-focusable marks for unlocked overview nodes (Enter/Space jumps) in `static/js/adventure_player_map.js`
- [X] T025 [US2] Position the overview so it does not cover the primary node action on phone-sized viewports in `static/css/adventure_player.css`
- [X] T026 [US2] De-emphasise or hide the overview when the full map already fits `#map-container` in `static/js/adventure_player_map.js`

**Checkpoint**: User Stories 1 and 2 both work. Travel still interrupts cleanly when the overview is used (T018).

---

## Phase 5: User Story 3 - Keyboard and screen-reader pass (Priority: P3)

**Goal**: Teachers can inspect, delete, zoom, and undo/redo map edits from the keyboard. Students can open and complete unlocked nodes from the keyboard. Locked nodes are not activatable. Small screens keep primary actions reachable.

**Independent Test**: Keyboard-only editor select/inspect/delete/undo/zoom; keyboard-only student complete a story node. See `quickstart.md` §7.

### Implementation for User Story 3

- [X] T027 [US3] Make editor node groups keyboard-focusable with accessible names `{title}, {node_type}` in `static/js/adventure_editor.js`
- [X] T028 [US3] Handle Tab/arrows, Enter inspect, Esc deselect, and Delete/Backspace (existing confirm) in `static/js/adventure_editor_commands.js`
- [X] T029 [US3] Implement `+`/`=` and `-` canvas zoom that keeps drag coordinates correct in `static/js/adventure_editor_commands.js`
- [X] T030 [US3] Add zoom-wrap styles in `static/css/adventure_editor.css`
- [X] T031 [US3] Implement session-only undo/redo (Ctrl/Cmd+Z, Ctrl/Cmd+Shift+Z or Ctrl/Cmd+Y) for place, move, connect, and delete in `static/js/adventure_editor_commands.js`
- [X] T032 [US3] Wrap successful place/move/connect/delete API calls in command-stack entries, and skip recording failed saves, in `static/js/adventure_editor.js`
- [X] T033 [US3] Improve student node names to `{title}, {node_type}, {status}`, keep locked nodes non-activatable, and Esc back to the map in `static/js/adventure_player.js`
- [X] T034 [US3] Announce editor selection, validation, and save outcomes through `#editor-validation` in `static/js/adventure_editor.js`
- [X] T035 [US3] Stack inspector/detail and keep primary actions reachable on phone-sized viewports in `static/css/adventure_editor.css` and `static/css/adventure_player.css`

**Checkpoint**: Keyboard and small-screen access work on both maps. Undo does not survive reload, per spec.

---

## Phase 6: User Story 4 - Assign to a clan or an individual student (Priority: P4)

**Goal**: Teachers can assign a published adventure to a clan or one student character. Class assignment stays. Progress and deactivation work for the new targets. Students who already started keep the run after leaving the clan.

**Independent Test**: Assign to a clan and to one student; confirm visibility; confirm class assignment unchanged; deactivate. See `quickstart.md` §8.

### Tests for User Story 4

- [X] T036 [P] [US4] Add clan and character assignment fixture helpers in `tests/fixtures/adventure_factories.py`
- [X] T037 [US4] Add teacher route tests for clan/character create, duplicate `CONFLICT`, other-teacher `FORBIDDEN`, list `target_type`/`target_label`, empty-clan warning, and `?assignment_id=` progress in `tests/test_adventure_routes_teacher.py`
- [X] T038 [US4] Add student route tests for clan visibility, individual visibility, class-assignment regression, and continue-after-leaving-clan in `tests/test_adventure_routes_student.py`

### Implementation for User Story 4

- [X] T039 [US4] Implement `create_adventure_assignment`, target ownership helpers, duplicate detection, and `list_active_assignments` in `app/services/adventure_assignment.py`
- [X] T040 [US4] Allow `student_is_assigned` / `require_student_assignment` to continue an already-started run whose `assignment_id` is still active after clan membership is lost in `app/services/adventure_graph.py`
- [X] T041 [US4] Remove the clan/character "not yet supported" rejection and call the new service from `create_assignment` in `app/routes/adventures/teacher.py`
- [X] T042 [US4] Implement `GET /teacher/adventures/<id>/assignment-targets` in `app/routes/adventures/teacher.py`
- [X] T043 [US4] Return all active assignment targets with `target_type`, `target_label`, `warnings`, and `progress_url` from `app/routes/adventures/serializers.py` and `app/routes/adventures/teacher.py`
- [X] T044 [US4] Scope the progress roster with `?assignment_id=` in `app/routes/adventures/teacher.py` and `app/services/adventure_graph.py`
- [X] T045 [US4] Add class/clan/character target controls to `app/templates/teacher/adventure_assignments.html`
- [X] T046 [US4] Show clan and individual assignments in the progress filter in `app/templates/teacher/adventure_progress.html`

**Checkpoint**: Clan and individual assignment work without changing class assignment. US1–US3 player behaviour is unchanged.

---

## Phase 7: User Story 5 - Choose a node icon from a library (Priority: P5)

**Goal**: Teachers pick a Material Icon from a catalog; the choice persists on `icon_url`; students see it. Clearing restores the type default. Type changes keep the override visible in the picker.

**Independent Test**: Change a battle icon, confirm editor and student map, clear to default. See `quickstart.md` §9.

### Tests for User Story 5

- [X] T047 [P] [US5] Add catalog tests that every `node_type` has exactly one default in `tests/test_adventure_routes_teacher.py`
- [X] T048 [US5] Add tests for saving, clearing (`null`), and student-state echo of `icon_url` in `tests/test_adventure_routes_teacher.py` and `tests/test_adventure_routes_student.py`

### Implementation for User Story 5

- [X] T049 [US5] Define the curated ligature catalog and type-default map in `app/services/adventure_icons.py`
- [X] T050 [US5] Implement `GET /teacher/adventures/node-icons` in `app/routes/adventures/teacher.py`
- [X] T051 [US5] Bootstrap the catalog into the editor page in `app/templates/teacher/adventure_editor.html`
- [X] T052 [US5] Add the inspector icon picker, current-vs-default indicator, and clear-override control in `static/js/adventure_editor.js`
- [X] T053 [US5] Render the chosen or default icon on editor nodes in `static/js/adventure_editor.js`
- [X] T054 [US5] Render the chosen or default icon on student nodes in `static/js/adventure_player.js`
- [X] T055 [US5] Include the Material Icons stylesheet on `app/templates/student/adventure_map.html` and `app/templates/teacher/adventure_editor.html`
- [X] T056 [US5] Keep `icon_url` when `node_type` changes and show stored vs new type default in the picker in `static/js/adventure_editor.js`

**Checkpoint**: All five user stories are independently functional.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Validate the full Phase 5 pass, keep docs truthful, and catch regressions.

- [X] T057 [P] Align any implemented caveats with `specs/003-adventure-player-polish/quickstart.md`
- [X] T058 [P] Verify implemented routes against `specs/003-adventure-player-polish/contracts/teacher-assignment-api.md` and `specs/003-adventure-player-polish/contracts/node-icons-api.md`
- [X] T059 [P] Verify player behaviour against `specs/003-adventure-player-polish/contracts/player-map.md`
- [X] T060 Run focused tests in `tests/test_adventure_routes_teacher.py` and `tests/test_adventure_routes_student.py`
- [X] T061 Run unlock regression tests in `tests/test_adventure_graph_unlock.py`
- [X] T062 Run legacy quest regression tests in `tests/test_quest_models.py`
- [X] T063 Perform travel smoke steps in `specs/003-adventure-player-polish/quickstart.md`
- [X] T064 Perform mini-map smoke steps in `specs/003-adventure-player-polish/quickstart.md`
- [X] T065 Perform keyboard smoke steps in `specs/003-adventure-player-polish/quickstart.md`
- [X] T066 Perform assignment smoke steps in `specs/003-adventure-player-polish/quickstart.md`
- [X] T067 Perform icon smoke steps in `specs/003-adventure-player-polish/quickstart.md`
- [X] T068 Check linter diagnostics for `app/services/adventure_assignment.py`, `app/services/adventure_icons.py`, `app/routes/adventures/teacher.py`, `static/js/adventure_player_map.js`, `static/js/adventure_editor_commands.js`, and related templates
- [X] T069 Mark spec 003 shipped in `docs/now.md` only after the smokes and tests above pass

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies; start immediately.
- **Foundational (Phase 2)**: Depends on Setup. Blocks all user stories because it adds the shared JS modules and player live region.
- **User Story 1 (Phase 3)**: Depends on Foundational. Recommended MVP.
- **User Story 2 (Phase 4)**: Depends on Foundational and should reuse the US1 marker/interrupt helpers in `static/js/adventure_player_map.js`. Independently testable as an overview even if travel is reduced-motion-only.
- **User Story 3 (Phase 5)**: Depends on Foundational. Editor work is independent of US1/US2. Player keyboard improvements touch `adventure_player.js` after travel wiring.
- **User Story 4 (Phase 6)**: Depends on Foundational only for sequencing convenience; no JS-module dependency. Can start in parallel with US1–US3 if staffed.
- **User Story 5 (Phase 7)**: Depends on Foundational. Icon drawing touches editor and player render functions; do it after US1 marker render to avoid merge conflicts in `adventure_player.js`.
- **Polish (Phase 8)**: Depends on all desired user stories.

### User Story Dependencies

- **US1 - Travel**: No dependency on US2–US5. Needs Foundational player map module.
- **US2 - Mini-map**: Uses the same `adventure_player_map.js` as US1. Can ship without travel polish, but interrupt-on-jump (T018) should already exist.
- **US3 - Keyboard**: Editor commands are independent. Player name/Esc work should land after US1 refresh flow so complete-from-keyboard still triggers travel.
- **US4 - Assignment**: Independent backend/UI story. Do not couple to player JS.
- **US5 - Icons**: Independent catalog/API; share render files with US1/US3, so sequential after those is safer for one implementer.

### Within Each User Story

- Tests (US4, US5) are listed before implementation and should fail until the service/route exists.
- Services before routes before templates/JS.
- Story checkpoint must pass before treating the story as done.

### Parallel Opportunities

- Setup reviews T002–T006 can run in parallel.
- Foundational T007 and T010 can run in parallel (different new files).
- US1 CSS T012 can start in parallel with marker JS T013.
- US4 fixtures T036 can start while US1–US3 are in progress (different files).
- US4 teacher tests T037 and student tests T038 can be drafted in parallel after fixtures.
- US5 catalog tests T047 can run in parallel with icon persistence tests T048 once the catalog shape is agreed.
- Polish T057–T059 can run in parallel after implementation.

---

## Parallel Example: User Story 1

```text
Task: "Add character-marker and travel styles in static/css/adventure_player.css"
Task: "Render a character marker from my_progress.current_node_id in static/js/adventure_player_map.js"
```

Then sequence travel, fork, reduced motion, interrupt, and sessionStorage in `adventure_player_map.js`.

---

## Parallel Example: User Story 4

```text
Task: "Add clan and character assignment fixture helpers in tests/fixtures/adventure_factories.py"
```

After fixtures:

```text
Task: "Add teacher route tests for clan/character create, duplicate CONFLICT, other-teacher FORBIDDEN in tests/test_adventure_routes_teacher.py"
Task: "Add student route tests for clan visibility, individual visibility, class-assignment regression, and continue-after-leaving-clan in tests/test_adventure_routes_student.py"
```

---

## Parallel Example: User Story 5

```text
Task: "Add catalog tests that every node_type has exactly one default in tests/test_adventure_routes_teacher.py"
Task: "Define the curated ligature catalog and type-default map in app/services/adventure_icons.py"
```

Editor picker and player icon render should not be parallel: both can collide with map render work from US1/US3.

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup.
2. Complete Phase 2: Foundational modules.
3. Complete Phase 3: Travel animation.
4. Stop and validate with `quickstart.md` §5.
5. Demo the player payoff before assignment or icons.

### Incremental Delivery

1. US1 travel → students can see where they unlocked.
2. US2 mini-map → large maps stay navigable.
3. US3 keyboard/a11y → classroom access.
4. US4 clan/individual assignment → teacher operational gap.
5. US5 icons → visual scan.
6. Phase 8 regression and smokes before calling 003 shipped.

### Recommended Option

Implement **sequentially P1 → P5** with one implementer: US1, US2, US3, then US4, then US5. That matches the spec priorities, avoids collisions in `adventure_player.js` / `adventure_editor.js`, and ships the player-facing payoff first.

If two people are available after Foundational, put **US4 on a second track** (pure backend/templates) while the first person stays on US1–US3. Do not parallel US5 with US1 on the same player render file.

---

## Notes

- No Alembic migration is expected. Reuse `adventure_assignments.clan_id` / `character_id` and `adventure_nodes.icon_url`.
- Keep JSON in `{"success": bool, "data": ..., "errors": [...]}`.
- Do not add a JavaScript build pipeline.
- Clan assignment is per-character progress, not shared clan progress.
- Class assignment must not regress (SC-008).
- Legacy `tests/test_quest_models.py` must still pass.
- Update `docs/now.md` only in T069 after tests and smokes pass.
