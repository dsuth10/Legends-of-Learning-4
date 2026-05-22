# Tasks: Adventures Quest Map System

**Input**: Design documents from `specs/001-adventures-map-system/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/teacher-api.md`, `contracts/student-api.md`, `quickstart.md`

**Tests**: Included because the feature specification defines independent tests for every user story and the implementation plan requires pytest coverage for models, services, routes, rewards, and legacy Quest regressions.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing. User Story 1 is the recommended MVP stop point.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on another incomplete task)
- **[Story]**: Maps to a user story from `spec.md` (`US1` through `US6`)
- Every task includes exact file paths

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the feature scaffolding and shared static/documentation locations without implementing behavior.

- [X] T001 Create Adventures route package scaffolding in `app/routes/adventures/__init__.py`, `app/routes/adventures/teacher.py`, and `app/routes/adventures/student.py`
- [X] T002 [P] Create Adventures service module placeholders in `app/services/adventure_graph.py`, `app/services/adventure_rewards.py`, `app/services/adventure_hooks.py`, and `app/services/adventure_quiz.py`
- [X] T003 [P] Create Adventures model placeholders in `app/models/adventure.py` and `app/models/adventure_progress.py`
- [X] T004 [P] Create Pydantic schema placeholder in `app/forms/adventure_schemas.py`
- [X] T005 [P] Create static asset placeholders in `static/js/adventure_editor.js`, `static/js/adventure_player.js`, `static/css/adventure_editor.css`, and `static/css/adventure_player.css`
- [X] T006 [P] Create upload/icon asset directories with `.gitkeep` files in `static/images/adventure_backgrounds/.gitkeep` and `static/images/adventure_node_icons/.gitkeep`
- [X] T007 [P] Create test fixture package scaffolding in `tests/fixtures/__init__.py` and `tests/fixtures/adventure_factories.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Implement shared database, schema, authorization, response, and graph/reward infrastructure required by all user stories.

**CRITICAL**: No user story work should begin until this phase is complete.

- [X] T008 Implement `Adventure`, `AdventureNode`, `AdventureEdge`, `NodeReward`, `NodeConsequence`, and enums in `app/models/adventure.py`
- [X] T009 Implement `AdventureAssignment`, `CharacterAdventureProgress`, `CharacterNodeProgress`, and progress enums in `app/models/adventure_progress.py`
- [X] T010 Register new model modules for Alembic discovery in `app/models/__init__.py`
- [X] T011 Create Alembic migration for the 8 Adventures tables, indexes, uniqueness constraints, and check constraints in `migrations/versions/<timestamp>_add_adventure_tables.py`
- [X] T012 Append `ADVENTURE_NODE_START`, `ADVENTURE_NODE_COMPLETE`, and `ADVENTURE_COMPLETE` to `EventType` and `EVENT_TYPES` in `app/models/audit.py`
- [X] T013 Implement shared API response and error Pydantic models in `app/forms/adventure_schemas.py`
- [X] T014 Implement teacher request schemas for adventure, node, edge, reward, consequence, assignment, and upload payloads in `app/forms/adventure_schemas.py`
- [X] T015 Implement student request schemas for node lifecycle, choice, retry, and quiz submit payloads in `app/forms/adventure_schemas.py`
- [X] T016 Implement teacher/student authorization helpers in `app/services/adventure_graph.py`
- [X] T017 Implement publish-time graph validation helpers in `app/services/adventure_graph.py`
- [X] T018 Implement unlock recomputation primitives, cycle short-circuiting, AND/OR inbound semantics, and end-semantics evaluation in `app/services/adventure_graph.py`
- [X] T019 Implement reward distribution and consequence application primitives with `commit=False` support in `app/services/adventure_rewards.py`
- [X] T020 Implement no-op-safe battle and quiz hook entry points in `app/services/adventure_hooks.py`
- [X] T021 Register `adventures_teacher_bp` and `adventures_student_bp` in `app/routes/__init__.py`
- [X] T022 [P] Add foundational model and constraint tests in `tests/test_adventure_models.py`
- [X] T023 [P] Add foundational graph validation and unlock tests in `tests/test_adventure_graph_unlock.py`
- [X] T024 [P] Add foundational reward atomicity tests in `tests/test_adventure_rewards.py`
- [X] T025 Run `alembic upgrade head` and document any migration caveats in `specs/001-adventures-map-system/quickstart.md`

**Checkpoint**: Foundation ready. User story implementation can begin.

---

## Phase 3: User Story 1 - Teacher visually authors a linear adventure and assigns it to a class (Priority: P1) MVP

**Goal**: A teacher can create a linear 3-node Adventure, publish it, assign it to a class, and a student can complete it on the map with rewards applied.

**Independent Test**: Teacher creates start -> battle -> end, assigns to a test class, student completes all three nodes, rewards land on the student's character, and legacy Quest regressions still pass.

### Tests for User Story 1

- [X] T026 [P] [US1] Add teacher route tests for list/create/read/archive/clone basics in `tests/test_adventure_routes_teacher.py`
- [X] T027 [P] [US1] Add teacher route tests for node and edge CRUD for a linear graph in `tests/test_adventure_routes_teacher.py`
- [X] T028 [P] [US1] Add teacher route tests for publish validation and class assignment in `tests/test_adventure_routes_teacher.py`
- [X] T029 [P] [US1] Add student route tests for list/state/detail/start/complete linear flow in `tests/test_adventure_routes_student.py`
- [X] T030 [P] [US1] Add student idempotency tests for repeated start and complete calls in `tests/test_adventure_routes_student.py`
- [X] T031 [P] [US1] Add reward distribution tests for XP, gold, equipment, ability, clan XP, special currency, and badge rewards in `tests/test_adventure_rewards.py`

### Implementation for User Story 1

- [X] T032 [US1] Implement teacher list/create/read/archive/clone routes in `app/routes/adventures/teacher.py`
- [X] T033 [US1] Implement teacher graph JSON route `GET /teacher/adventures/<id>/graph` in `app/routes/adventures/teacher.py`
- [X] T034 [US1] Implement teacher adventure metadata update and background upload routes in `app/routes/adventures/teacher.py`
- [X] T035 [US1] Implement node create/update/delete routes for linear graph authoring in `app/routes/adventures/teacher.py`
- [X] T036 [US1] Implement edge create/update/delete routes for directed linear connections in `app/routes/adventures/teacher.py`
- [X] T037 [US1] Implement reward and consequence create/delete routes for nodes in `app/routes/adventures/teacher.py`
- [X] T038 [US1] Implement publish route and blocking validation response handling in `app/routes/adventures/teacher.py`
- [X] T039 [US1] Implement class assignment create/update/deactivate routes in `app/routes/adventures/teacher.py`
- [X] T040 [US1] Implement student adventure list, map page, state JSON, and node detail routes in `app/routes/adventures/student.py`
- [X] T041 [US1] Implement student node start, complete, retry, and basic lifecycle services for non-choice linear nodes in `app/routes/adventures/student.py` and `app/services/adventure_graph.py`
- [X] T042 [US1] Implement direct quiz scoring route skeleton for quiz nodes in `app/routes/adventures/student.py` and `app/services/adventure_quiz.py`
- [X] T043 [US1] Implement battle-node start binding and progress metadata storage in `app/routes/adventures/student.py`
- [X] T044 [US1] Insert the no-op-safe battle completion hook call into the existing battle resolution path in `app/routes/student/battle.py`
- [X] T045 [US1] Implement teacher list and editor templates in `app/templates/teacher/adventures_list.html` and `app/templates/teacher/adventure_editor.html`
- [X] T046 [US1] Implement teacher assignment template in `app/templates/teacher/adventure_assignments.html`
- [X] T047 [US1] Implement student list, map, and node-detail templates in `app/templates/student/adventures_list.html`, `app/templates/student/adventure_map.html`, and `app/templates/student/_adventure_node_detail.html`
- [X] T048 [US1] Implement editor canvas, node placement, dragging, edge drawing, autosave, publish, and assignment calls in `static/js/adventure_editor.js`
- [X] T049 [US1] Implement student map rendering, node states, detail panel, and action calls in `static/js/adventure_player.js`
- [X] T050 [US1] Style teacher editor and student map states in `static/css/adventure_editor.css` and `static/css/adventure_player.css`
- [X] T051 [US1] Add additive Adventures nav links in `app/templates/student/_student_header.html` and `app/templates/teacher/base_dashboard.html`
- [X] T052 [US1] Add smoke-test fixture factories for the 3-node linear adventure in `tests/fixtures/adventure_factories.py`
- [X] T053 [US1] Run legacy regression `pytest tests/test_quest_models.py -v` and record the result in `specs/001-adventures-map-system/quickstart.md`

**Checkpoint**: User Story 1 is independently shippable as the MVP.

---

## Phase 4: User Story 2 - Branching paths and student choices (Priority: P2)

**Goal**: Teachers can author choice branches, re-join paths, optional side nodes, and conditional paths; students choose one branch and unlock only the correct downstream nodes.

**Independent Test**: Create one choice node with left/right paths that re-converge plus one optional side node; multiple test students verify left/right/optional behavior independently.

### Tests for User Story 2

- [X] T054 [P] [US2] Add branching, choice, optional-node, AND/OR re-join, and criteria-edge tests in `tests/test_adventure_graph_unlock.py`
- [X] T055 [P] [US2] Add teacher contract tests for choice and criteria edge payload validation in `tests/test_adventure_routes_teacher.py`
- [X] T056 [P] [US2] Add student `/choose` route tests for branch locking and repeated-choice idempotency in `tests/test_adventure_routes_student.py`
- [X] T057 [P] [US2] Add optional-node reward and completion tests in `tests/test_adventure_rewards.py`

### Implementation for User Story 2

- [X] T058 [US2] Extend edge validation and Pydantic discriminated unions for `choice` and `criteria` edge payloads in `app/forms/adventure_schemas.py`
- [X] T059 [US2] Extend graph unlock service for choice-key propagation, criteria filtering, optional-node skip logic, and mixed AND/OR semantics in `app/services/adventure_graph.py`
- [X] T060 [US2] Implement student `/choose` endpoint and locked-branch behavior in `app/routes/adventures/student.py`
- [X] T061 [US2] Extend teacher edge editor inspector for labels, condition type, choice keys, criteria, unlock semantics, and sort order in `static/js/adventure_editor.js`
- [X] T062 [US2] Extend student node detail panel to render choice options in `app/templates/student/_adventure_node_detail.html` and `static/js/adventure_player.js`
- [X] T063 [US2] Add visual styling for choice paths, optional nodes, skipped nodes, and re-join states in `static/css/adventure_player.css` and `static/css/adventure_editor.css`
- [X] T064 [US2] Add branching graph fixture factories in `tests/fixtures/adventure_factories.py`

**Checkpoint**: User Story 2 is independently testable without changing the US1 linear path.

---

## Phase 5: User Story 3 - Live student progress visibility for teachers (Priority: P3)

**Goal**: Teachers can see a roster of assigned students with status, current node, attempts, recent activity, and failures.

**Independent Test**: With three students at not-started, in-progress, and completed states, the progress view shows status, current node, last-active timestamp, and failure/consequence markers.

### Tests for User Story 3

- [X] T065 [P] [US3] Add teacher progress route tests for roster summaries and class filtering in `tests/test_adventure_routes_teacher.py`
- [X] T066 [P] [US3] Add progress aggregation service tests for node counts, current node, last-active timestamp, and failure flags in `tests/test_adventure_graph_unlock.py`
- [X] T067 [P] [US3] Add force-complete route and audit tests in `tests/test_adventure_routes_teacher.py`

### Implementation for User Story 3

- [X] T068 [US3] Implement progress aggregation query helpers with no per-student N+1 queries in `app/services/adventure_graph.py`
- [X] T069 [US3] Implement teacher progress JSON/page route and class filter support in `app/routes/adventures/teacher.py`
- [X] T070 [US3] Implement force-complete override service with audit logging in `app/services/adventure_graph.py` and `app/routes/adventures/teacher.py`
- [X] T071 [US3] Implement progress roster template in `app/templates/teacher/adventure_progress.html`
- [X] T072 [US3] Add recent-event rendering and failure/consequence indicators in `app/templates/teacher/adventure_progress.html`
- [X] T073 [US3] Add performance-oriented progress fixture with 60 students in `tests/fixtures/adventure_factories.py`

**Checkpoint**: User Story 3 is independently usable after any class assignment exists.

---

## Phase 6: User Story 4 - Reuse the same adventure across classes and terms (Priority: P3)

**Goal**: A teacher can assign the same published Adventure to multiple classes while each class's students start with independent progress and existing progress is unaffected.

**Independent Test**: Assign one adventure to Class A and have a student complete a node; assign the same adventure to Class B and confirm Class B students start fresh while Class A progress remains intact.

### Tests for User Story 4

- [X] T074 [P] [US4] Add multi-class assignment and progress isolation tests in `tests/test_adventure_routes_teacher.py`
- [X] T075 [P] [US4] Add duplicate-character assignment deduplication tests in `tests/test_adventure_routes_student.py`

### Implementation for User Story 4

- [X] T076 [US4] Harden assignment service for multiple active classroom assignments and duplicate-character deduplication in `app/services/adventure_graph.py`
- [X] T077 [US4] Extend teacher assignment UI to display all active class assignments and deactivate controls in `app/templates/teacher/adventure_assignments.html`
- [X] T078 [US4] Extend assignment route responses with class-scoped progress links in `app/routes/adventures/teacher.py`
- [X] T079 [US4] Extend progress view class scoping UI in `app/templates/teacher/adventure_progress.html`

**Checkpoint**: User Story 4 can be validated with two classes and one shared adventure.

---

## Phase 7: User Story 5 - Mid-flight edits do not disrupt students already playing (Priority: P3)

**Goal**: In-progress students remain pinned to the version/snapshot they started, while new starters see the edited version.

**Independent Test**: Student A starts an adventure; teacher edits structure/rewards; Student A still sees the original version and rewards, while Student B starts into the edited version.

### Tests for User Story 5

- [X] T080 [P] [US5] Add version-pin and snapshot tests for in-flight student stability in `tests/test_adventure_graph_unlock.py`
- [X] T081 [P] [US5] Add route tests for editing published adventures without corrupting existing progress in `tests/test_adventure_routes_teacher.py`
- [X] T082 [P] [US5] Add student state tests for old-version and new-version visibility in `tests/test_adventure_routes_student.py`

### Implementation for User Story 5

- [X] T083 [US5] Implement assignment-time `snapshot_json` population and read-through helpers in `app/services/adventure_graph.py`
- [X] T084 [US5] Update student state route to resolve nodes and edges from `snapshot_json` when present in `app/routes/adventures/student.py`
- [X] T085 [US5] Update teacher edit routes to bump versions and preserve existing assignment snapshots in `app/routes/adventures/teacher.py`
- [X] T086 [US5] Add published-edit warning and affected-students count in `app/templates/teacher/adventure_editor.html` and `static/js/adventure_editor.js`
- [X] T087 [US5] Add snapshot fixture factories for pre-edit and post-edit adventures in `tests/fixtures/adventure_factories.py`

**Checkpoint**: User Story 5 is independently testable with two students starting before/after an edit.

---

## Phase 8: User Story 6 - Share adventures with other teachers (Priority: P4)

**Goal**: A teacher can mark an Adventure shareable; another teacher can see it, clone it, edit the clone, and assign it without affecting the original.

**Independent Test**: Teacher A marks an adventure public; Teacher B sees it in shared list, clones it, edits clone title, assigns clone, and Teacher A's original remains unchanged.

### Tests for User Story 6

- [X] T088 [P] [US6] Add shared/public adventure list and visibility tests in `tests/test_adventure_routes_teacher.py`
- [X] T089 [P] [US6] Add cross-teacher clone isolation and ownership tests in `tests/test_adventure_routes_teacher.py`

### Implementation for User Story 6

- [X] T090 [US6] Harden teacher list and read authorization for public-but-not-owned adventures in `app/routes/adventures/teacher.py`
- [X] T091 [US6] Implement clone service that copies graph, rewards, and consequences into a new owned draft in `app/services/adventure_graph.py`
- [X] T092 [US6] Extend teacher list UI with owned/shared sections and clone actions in `app/templates/teacher/adventures_list.html`
- [X] T093 [US6] Add shareable/public toggle handling and owner labels in `app/templates/teacher/adventure_editor.html` and `static/js/adventure_editor.js`

**Checkpoint**: User Story 6 is independently testable with two teacher accounts.

---

## Final Phase: Polish & Cross-Cutting Concerns

**Purpose**: Clean up, document, validate performance/security/accessibility, and protect legacy behavior before implementation is considered complete.

- [X] T094 [P] Add graph integrity scanner for orphan nodes, unreachable ends, and dangling progress rows in `scripts/check_adventure_graph_integrity.py`
- [X] T095 [P] Update database structure documentation with new tables and relationships in `.cursor/rules/database-structure.mdc`
- [X] T096 [P] Update developer documentation for Adventures setup and smoke testing in `specs/001-adventures-map-system/quickstart.md`
- [X] T097 [P] Add accessibility labels and keyboard support notes for editor/player interactions in `app/templates/teacher/adventure_editor.html`, `app/templates/student/adventure_map.html`, and `static/js/adventure_editor.js`
- [X] T098 [P] Add background upload security checks for MIME, extension, size, and filename sanitization in `app/routes/adventures/teacher.py`
- [X] T099 Add performance assertions for student state and teacher progress queries in `tests/test_adventure_routes_student.py` and `tests/test_adventure_routes_teacher.py`
- [X] T100 Add complete quickstart smoke validation checklist results in `specs/001-adventures-map-system/quickstart.md`
- [X] T101 Run `pytest tests/test_quest_models.py -v` and record legacy regression status in `specs/001-adventures-map-system/quickstart.md`
- [X] T102 Run `pytest tests/test_adventure_models.py tests/test_adventure_graph_unlock.py tests/test_adventure_routes_teacher.py tests/test_adventure_routes_student.py tests/test_adventure_rewards.py -v` and record status in `specs/001-adventures-map-system/quickstart.md`
- [X] T103 Run full `pytest -q` suite and record status in `specs/001-adventures-map-system/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies. Can start immediately.
- **Foundational (Phase 2)**: Depends on Setup completion. Blocks all user stories.
- **US1 / MVP (Phase 3)**: Depends on Foundational. Recommended first delivery slice.
- **US2 (Phase 4)**: Depends on Foundational and benefits from US1 UI/routes, but graph logic is independently testable.
- **US3 (Phase 5)**: Depends on Foundational and at least one assignment/progress flow from US1.
- **US4 (Phase 6)**: Depends on US1 assignment/progress behavior and US3 class-scoped progress view.
- **US5 (Phase 7)**: Depends on US1 assignment/progress behavior and version field from Foundational.
- **US6 (Phase 8)**: Depends on US1 clone/list/edit surfaces and foundational ownership checks.
- **Polish**: Depends on whichever user stories are targeted for the release.

### User Story Dependencies

- **US1 (P1)**: No dependency on other stories after Foundational. This is the MVP.
- **US2 (P2)**: Can be implemented after Foundational; easiest after US1 editor/player surfaces exist.
- **US3 (P3)**: Requires assignment and progress rows, so it depends practically on US1.
- **US4 (P3)**: Requires assignment flow from US1 and progress filtering from US3.
- **US5 (P3)**: Requires assignment and player state from US1.
- **US6 (P4)**: Requires list/clone/edit ownership surfaces from US1.

### Within Each User Story

- Tests first; they should fail before implementation.
- Models and migration before services.
- Services before routes.
- Routes before templates and JS integration.
- Story checkpoint before moving to the next priority.

---

## Parallel Opportunities

- Setup tasks T002-T007 can run in parallel after T001.
- Foundational tests T022-T024 can be drafted in parallel after T008-T021 interfaces are sketched.
- In US1, teacher route tests T026-T028, student route tests T029-T030, and reward tests T031 can run in parallel.
- In US1, templates T045-T047 can run in parallel with static JS/CSS T048-T050 after route contracts stabilize.
- US2 tests T054-T057 can run in parallel.
- US3 tests T065-T067 can run in parallel.
- US4 tests T074-T075 can run in parallel.
- US5 tests T080-T082 can run in parallel.
- US6 tests T088-T089 can run in parallel.
- Polish documentation/security/accessibility tasks T094-T098 can run in parallel.

---

## Parallel Example: User Story 1

```bash
# Teacher contracts and route tests
Task: "T026 [P] [US1] Add teacher route tests for list/create/read/archive/clone basics in tests/test_adventure_routes_teacher.py"
Task: "T027 [P] [US1] Add teacher route tests for node and edge CRUD for a linear graph in tests/test_adventure_routes_teacher.py"
Task: "T028 [P] [US1] Add teacher route tests for publish validation and class assignment in tests/test_adventure_routes_teacher.py"

# Student and reward tests
Task: "T029 [P] [US1] Add student route tests for list/state/detail/start/complete linear flow in tests/test_adventure_routes_student.py"
Task: "T030 [P] [US1] Add student idempotency tests for repeated start and complete calls in tests/test_adventure_routes_student.py"
Task: "T031 [P] [US1] Add reward distribution tests for XP, gold, equipment, ability, clan XP, special currency, and badge rewards in tests/test_adventure_rewards.py"

# UI implementation after routes stabilize
Task: "T045 [US1] Implement teacher list and editor templates in app/templates/teacher/adventures_list.html and app/templates/teacher/adventure_editor.html"
Task: "T047 [US1] Implement student list, map, and node-detail templates in app/templates/student/adventures_list.html, app/templates/student/adventure_map.html, and app/templates/student/_adventure_node_detail.html"
Task: "T048 [US1] Implement editor canvas, node placement, dragging, edge drawing, autosave, publish, and assignment calls in static/js/adventure_editor.js"
Task: "T049 [US1] Implement student map rendering, node states, detail panel, and action calls in static/js/adventure_player.js"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup.
2. Complete Phase 2: Foundational.
3. Complete Phase 3: User Story 1.
4. Stop and validate:
   - `alembic upgrade head`
   - `pytest tests/test_quest_models.py -v`
   - `pytest tests/test_adventure_models.py tests/test_adventure_graph_unlock.py tests/test_adventure_routes_teacher.py tests/test_adventure_routes_student.py tests/test_adventure_rewards.py -v`
   - Manual quickstart smoke in `specs/001-adventures-map-system/quickstart.md`
5. Demo the MVP before starting branching or progress-view work.

### Incremental Delivery

1. Foundation -> database, schemas, services, blueprint registration.
2. US1 -> complete linear authoring + assignment + student play loop.
3. US2 -> branching and choices.
4. US3 -> teacher progress visibility.
5. US4 -> cross-class reuse.
6. US5 -> mid-flight edit stability.
7. US6 -> sharing and clone-from-peer.

### Recommended Option

Use **MVP-first delivery**: ship Setup + Foundational + US1, then stop for teacher/student feedback. This follows robust engineering practice because it validates the highest-risk cross-system path (authoring, assignment, student play, rewards, audit, and legacy regression) before adding branching, snapshotting, sharing, and polish layers.

---

## Validation Summary

- **Total tasks**: 103
- **Setup tasks**: 7
- **Foundational tasks**: 18
- **US1 tasks**: 28
- **US2 tasks**: 11
- **US3 tasks**: 9
- **US4 tasks**: 6
- **US5 tasks**: 8
- **US6 tasks**: 6
- **Polish tasks**: 10
- **Format validation**: Every task uses `- [ ] T###`, optional `[P]`, required `[US#]` for user-story phases only, and includes at least one file path.

