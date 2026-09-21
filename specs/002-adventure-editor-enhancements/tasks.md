# Tasks: Adventure Editor Enhancements

**Input**: Design documents from `specs/002-adventure-editor-enhancements/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/teacher-editor-api.md`, `quickstart.md`

**Tests**: Included because the feature spec and quickstart define independent test criteria for each user story.

**Organization**: Tasks are grouped by user story so each story can be implemented, tested, and demonstrated independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel because it touches different files or has no dependency on incomplete tasks.
- **[Story]**: Maps to the user story phase. Setup, foundational, and polish tasks have no story label.
- Every task includes an exact file path.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish the baseline and confirm this feature remains an additive editor enhancement.

- [x] T001 Run the baseline focused teacher route suite for `tests/test_adventure_routes_teacher.py`
- [x] T002 [P] Review the current editor template bootstrap data in `app/templates/teacher/adventure_editor.html`
- [x] T003 [P] Review the current editor JS render and inspector functions in `static/js/adventure_editor.js`
- [x] T004 [P] Review the existing Adventures teacher route update/upload behavior in `app/routes/adventures/teacher.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Add shared editor support used by all stories before story-specific controls are implemented.

**Critical**: No user story work should begin until this phase is complete.

- [x] T005 Add shared editor success/error banner helpers for JSON failures in `static/js/adventure_editor.js`
- [x] T006 Refine the shared `api` helper to handle non-JSON or failed fetch responses consistently in `static/js/adventure_editor.js`
- [x] T007 Add shared editor state for current adventure metadata and graph data updates in `static/js/adventure_editor.js`
- [x] T008 [P] Add minimal reusable editor status/preview styles in `static/css/adventure_editor.css`

**Checkpoint**: Editor has shared feedback and state helpers ready for quiz, settings, and drag work.

---

## Phase 3: User Story 1 - Attach Question Sets to Quiz Nodes (Priority: P1) - MVP

**Goal**: Teachers can select one of their available question sets for a quiz node, save it, and see the selection persist.

**Independent Test**: Create or open an adventure with a quiz node, assign one of the teacher's question sets, save, reopen the editor, and confirm the selection remains visible and the quiz node is no longer flagged as missing quiz content.

### Tests for User Story 1

- [x] T009 [P] [US1] Add Teacher and QuestionSet fixture helpers for adventure editor tests in `tests/fixtures/adventure_factories.py`
- [x] T010 [US1] Add route tests for `GET /teacher/adventures/question-sets` filtering active sets by current teacher in `tests/test_adventure_routes_teacher.py`
- [x] T011 [US1] Add route tests for saving, clearing, and reloading quiz node `question_set_id` in `tests/test_adventure_routes_teacher.py`
- [x] T012 [US1] Add route tests rejecting inactive or other-teacher `question_set_id` values on node create/update in `tests/test_adventure_routes_teacher.py`

### Implementation for User Story 1

- [x] T013 [US1] Add a teacher-owned question set option helper using the legacy `Teacher.user_id` bridge in `app/routes/adventures/teacher.py`
- [x] T014 [US1] Implement `GET /teacher/adventures/question-sets` with the standard response envelope in `app/routes/adventures/teacher.py`
- [x] T015 [US1] Pass `question_set_options` into the editor page context in `app/routes/adventures/teacher.py`
- [x] T016 [US1] Enforce teacher ownership for non-null `question_set_id` during node create and update in `app/routes/adventures/teacher.py`
- [x] T017 [US1] Bootstrap `questionSets` into `AdventureEditor.init` in `app/templates/teacher/adventure_editor.html`
- [x] T018 [US1] Extend `renderNodeInspector` to show quiz question-set dropdown, empty state, unavailable state, and manage link in `static/js/adventure_editor.js`
- [x] T019 [US1] Include `question_set_id` in quiz node save payloads and refresh graph state after save in `static/js/adventure_editor.js`
- [x] T020 [US1] Show publish readiness warnings for quiz nodes without valid question sets in `static/js/adventure_editor.js`

**Checkpoint**: User Story 1 is fully functional and independently testable as the MVP.

---

## Phase 4: User Story 2 - Edit Adventure Settings In The Editor (Priority: P2)

**Goal**: Teachers can edit adventure-level metadata, sharing, completion rule, and background image without leaving the editor.

**Independent Test**: Open an owned adventure, change title, description, theme, background image, and completion rule, save, refresh the editor, and confirm the saved values remain accurate.

### Tests for User Story 2

- [x] T021 [P] [US2] Add route tests for adventure metadata PATCH preserving omitted fields in `tests/test_adventure_routes_teacher.py`
- [x] T022 [P] [US2] Add route tests for invalid metadata and draft sharing validation in `tests/test_adventure_routes_teacher.py`
- [x] T023 [P] [US2] Add route tests for valid and invalid background upload behavior in `tests/test_adventure_routes_teacher.py`

### Implementation for User Story 2

- [x] T024 [US2] Add the settings modal markup and toolbar trigger in `app/templates/teacher/adventure_editor.html`
- [x] T025 [US2] Bootstrap current adventure settings into `AdventureEditor.init` in `app/templates/teacher/adventure_editor.html`
- [x] T026 [US2] Implement settings modal initialization, dirty-field detection, and save payload construction in `static/js/adventure_editor.js`
- [x] T027 [US2] Wire settings save to `PATCH /teacher/adventures/<id>` and update header/share state on success in `static/js/adventure_editor.js`
- [x] T028 [US2] Wire background file upload to `POST /teacher/adventures/<id>/background` with preview and rollback on failure in `static/js/adventure_editor.js`
- [x] T029 [US2] Apply the saved background image to the editor canvas view in `static/js/adventure_editor.js`
- [x] T030 [US2] Add settings modal and background preview styling in `static/css/adventure_editor.css`

**Checkpoint**: User Stories 1 and 2 work independently without leaving the editor.

---

## Phase 5: User Story 3 - Reposition Nodes By Dragging (Priority: P3)

**Goal**: Teachers can drag existing nodes on the map, see connected edges follow during movement, and persist the new position.

**Independent Test**: Drag an existing connected node, confirm connected paths follow the node, refresh the editor, and confirm the node remains at its new location.

### Tests for User Story 3

- [x] T031 [P] [US3] Add route tests for node `x` and `y` update persistence in `tests/test_adventure_routes_teacher.py`
- [x] T032 [P] [US3] Add route tests for published adventure version bump on node coordinate update in `tests/test_adventure_routes_teacher.py`

### Implementation for User Story 3

- [x] T033 [US3] Extend `renderGraph` node elements with pointer event handlers and drag metadata in `static/js/adventure_editor.js`
- [x] T034 [US3] Implement click-versus-drag threshold handling that preserves node selection and connect mode in `static/js/adventure_editor.js`
- [x] T035 [US3] Update node transforms and connected SVG edge endpoints live during drag in `static/js/adventure_editor.js`
- [x] T036 [US3] Clamp dropped node coordinates to adventure width and height before saving in `static/js/adventure_editor.js`
- [x] T037 [US3] Save one coordinate PATCH on drag release and snap back on failure in `static/js/adventure_editor.js`
- [x] T038 [US3] Add drag cursor and disabled-drag visual states in `static/css/adventure_editor.css`

**Checkpoint**: All user stories are independently functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Validate the complete feature, update docs, and reduce regression risk.

- [x] T039 [P] Update implementation notes and any discovered caveats in `specs/002-adventure-editor-enhancements/quickstart.md`
- [x] T040 [P] Verify the API contract still matches implemented routes in `specs/002-adventure-editor-enhancements/contracts/teacher-editor-api.md`
- [x] T041 Run focused tests for `tests/test_adventure_routes_teacher.py`
- [x] T042 Run broader Adventures regression tests for `tests/test_adventure_routes_teacher.py`, `tests/test_adventure_routes_student.py`, and `tests/test_adventure_graph_unlock.py`
- [x] T043 Run legacy quest regression tests for `tests/test_quest_models.py`
- [x] T044 Perform manual quiz question-set smoke steps from `specs/002-adventure-editor-enhancements/quickstart.md`
- [x] T045 Perform manual adventure settings smoke steps from `specs/002-adventure-editor-enhancements/quickstart.md`
- [x] T046 Perform manual drag reposition smoke steps from `specs/002-adventure-editor-enhancements/quickstart.md`
- [x] T047 Check edited files for linter diagnostics in `app/routes/adventures/teacher.py`, `app/templates/teacher/adventure_editor.html`, `static/js/adventure_editor.js`, and `static/css/adventure_editor.css`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies; can start immediately.
- **Foundational (Phase 2)**: Depends on Setup completion; blocks all user stories because shared JS feedback/state helpers are used by each story.
- **User Story 1 (Phase 3)**: Depends on Foundational; recommended MVP.
- **User Story 2 (Phase 4)**: Depends on Foundational; can be implemented independently from US1, but sequential delivery after US1 is recommended.
- **User Story 3 (Phase 5)**: Depends on Foundational; can be implemented independently from US1/US2, but sequential delivery after simpler editor work is recommended.
- **Polish (Phase 6)**: Depends on all desired user stories being complete.

### User Story Dependencies

- **US1 - Quiz Question Sets**: No dependency on US2 or US3. Requires Foundational shared editor helpers.
- **US2 - Adventure Settings**: No dependency on US1 or US3. Requires Foundational shared editor helpers.
- **US3 - Drag Reposition**: No dependency on US1 or US2. Requires Foundational shared editor helpers and current graph rendering.

### Within Each User Story

- Tests are listed before implementation and should fail before the implementation tasks are completed.
- Backend route/validation tasks should complete before template/JS tasks that consume their data.
- Template bootstrap tasks should complete before JS tasks that read new options/settings.
- Story checkpoint must be validated before treating the story as complete.

### Parallel Opportunities

- Setup review tasks T002-T004 can run in parallel.
- CSS task T008 can run in parallel with JS helper tasks T005-T007.
- US1 fixture task T009 can run in parallel with route test drafting T010-T012 once expected fixture shape is agreed.
- US2 route tests T021-T023 can run in parallel because they cover separate route behaviors.
- US3 route tests T031-T032 can run in parallel with non-overlapping editor CSS task T038.
- Documentation verification tasks T039-T040 can run in parallel after implementation.

---

## Parallel Example: User Story 1

```bash
Task: "Add Teacher and QuestionSet fixture helpers for adventure editor tests in tests/fixtures/adventure_factories.py"
Task: "Add route tests for GET /teacher/adventures/question-sets filtering active sets by current teacher in tests/test_adventure_routes_teacher.py"
```

After the endpoint exists:

```bash
Task: "Bootstrap questionSets into AdventureEditor.init in app/templates/teacher/adventure_editor.html"
Task: "Extend renderNodeInspector to show quiz question-set dropdown, empty state, unavailable state, and manage link in static/js/adventure_editor.js"
```

---

## Parallel Example: User Story 2

```bash
Task: "Add route tests for adventure metadata PATCH preserving omitted fields in tests/test_adventure_routes_teacher.py"
Task: "Add route tests for invalid metadata and draft sharing validation in tests/test_adventure_routes_teacher.py"
Task: "Add route tests for valid and invalid background upload behavior in tests/test_adventure_routes_teacher.py"
```

After tests are in place:

```bash
Task: "Add the settings modal markup and toolbar trigger in app/templates/teacher/adventure_editor.html"
Task: "Add settings modal and background preview styling in static/css/adventure_editor.css"
```

---

## Parallel Example: User Story 3

```bash
Task: "Add route tests for node x and y update persistence in tests/test_adventure_routes_teacher.py"
Task: "Add drag cursor and disabled-drag visual states in static/css/adventure_editor.css"
```

Most drag behavior lives in `static/js/adventure_editor.js`, so T033-T037 should be done sequentially to avoid same-file conflicts.

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup.
2. Complete Phase 2: Foundational shared editor helpers.
3. Complete Phase 3: User Story 1.
4. Stop and validate quiz question-set attachment independently with route tests and the quickstart smoke.
5. Demo or ship the MVP if only quiz nodes need unblocking.

### Incremental Delivery

1. Deliver US1 to unblock quiz nodes.
2. Deliver US2 to polish adventure-level settings and background editing.
3. Deliver US3 to improve visual authoring with drag repositioning.
4. Run Phase 6 regression and manual smoke checks before merge.

### Recommended Option

Implement sequentially in priority order: US1, then US2, then US3. This matches the plan's robust path because it ships the lowest-risk functional unblock first, then settings polish, then the more interaction-heavy drag behavior.

---

## Notes

- No Alembic migration is expected for this feature.
- Keep route responses in the existing `{"success": bool, "data": ..., "errors": [...]}` shape.
- Preserve existing adventure publishing, assignment, student play, and legacy quest behavior.
- Avoid adding a JavaScript build pipeline; keep editor work in the existing static JS file.
