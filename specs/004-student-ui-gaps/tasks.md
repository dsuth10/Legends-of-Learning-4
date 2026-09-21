# Tasks: Student UI Remaining Gaps

**Input**: Design documents from `specs/004-student-ui-gaps/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/student-chrome.md`, `quickstart.md`

**Tests**: Included. The plan and constitution require pytest for the chrome contract in `tests/test_student_ui_shell.py`. User Story 4 small-screen work is verified by `quickstart.md` smokes, not viewport pytest.

**Organization**: Tasks are grouped by user story so each story can be implemented, tested, and demonstrated independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel because it touches different files or has no dependency on incomplete tasks.
- **[Story]**: Maps to the user story phase. Setup, foundational, and polish tasks have no story label.
- Every task includes an exact file path.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm the current student pages and baseline tests before unifying chrome.

- [X] T001 Run baseline student suites in `tests/test_shop_api.py`, `tests/test_powers.py`, `tests/test_equipment_data_integration.py`, `tests/test_character_management.py`, and `tests/test_adventure_routes_student.py`
- [X] T002 [P] Review shell fragments and unused duplicate in `app/templates/student/base_student.html`, `app/templates/student/_student_header.html`, `app/templates/student/_student_sidebar.html`, and `app/templates/student/_student_layout.html`
- [X] T003 [P] Review duplicated nav/stats in `app/templates/student/character_new.html`, `app/templates/student/shop_new.html`, `app/templates/student/equipment_new.html`, and `app/templates/student/quests_new.html`
- [X] T004 [P] Review leftover pages still on Bootstrap `base.html` in `app/templates/student/progress.html`, `app/templates/student/clan.html`, `app/templates/student/profile.html`, and `app/templates/student/character_create.html`
- [X] T005 [P] Review which routes pass `main_character` / `student_profile` in `app/routes/student_main.py` and `app/routes/adventures/student.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared chrome service, destination list, and `base_student.html` slots that every story uses. Do not wrap leftover pages yet.

**Critical**: No user story work should begin until this phase is complete.

- [X] T006 Create `student_chrome_context(user)` returning profile, active character, classroom, and ordered clan members (current character first) in `app/services/student_chrome.py`
- [X] T007 Add display fields `hp_current`, `hp_max`, `power_current`, `power_max`, `xp_current`, `xp_next`, `gold`, `power_points`, and `party_members` (up to three other clan characters) in `app/services/student_chrome.py`
- [X] T008 [P] Create `static/css/student_shell.css` with a comment block for later small-screen rules
- [X] T009 Link `student_shell.css` and add `shell_header`, `shell_sidebar`, and `shell_main` blocks in `app/templates/student/base_student.html`
- [X] T010 Include identity bar and clan/classroom strip from `app/templates/student/_student_header.html` in the `base_student.html` header block
- [X] T011 Put the seven-destination list (Character, Quests, Shop, Equipment, Adventures, Progress, Powers) with `aria-current="page"` in `app/templates/student/_student_sidebar.html`
- [X] T012 Render stats from chrome helper fields (not inline `total_health` / fake gold fill) in `app/templates/student/_student_sidebar.html`

**Checkpoint**: A page that already extends `base_student.html` can include the shared header and sidebar. Leftover pages are still on `base.html`. Shop buy / equip / quest / powers behaviour is unchanged.

---

## Phase 3: User Story 1 - One student shell on every student destination (Priority: P1) — MVP

**Goal**: Character, Quests, Shop, Equipment, Adventures list, Progress, Powers, Clan, Profile, and Create character all use the shared chrome. Create character omits fabricated stats. Current destination is indicated.

**Independent Test**: From Character, visit the in-scope destinations and confirm the same frame and destination list. Repeat with a clan-less student and a no-character student on Create character. See `specs/004-student-ui-gaps/quickstart.md` §5 (shared chrome).

### Tests for User Story 1

> Write these tests first and ensure they FAIL until the pages are on the shell.

- [X] T013 [US1] Add GET chrome-presence tests for the ten in-scope destinations (destination labels, stats when a character exists, create-character without fabricated HP) in `tests/test_student_ui_shell.py`
- [X] T014 [US1] Add clan-less (classroom label, single strip tab) and current-destination (`aria-current` or equivalent) assertions in `tests/test_student_ui_shell.py`

### Implementation for User Story 1

- [X] T015 [US1] Pass `student_chrome_context` into Character, Quests, Shop, and Equipment renders in `app/routes/student_main.py`
- [X] T016 [US1] Pass `student_chrome_context` into Progress, Powers, Clan, Profile, and Create character renders in `app/routes/student_main.py`
- [X] T017 [US1] Pass `student_chrome_context` into the HTML list view in `app/routes/adventures/student.py` (JSON list unchanged)
- [X] T018 [P] [US1] Refactor `app/templates/student/character_new.html` to extend the `base_student.html` shell and drop duplicated header/sidebar markup
- [X] T019 [P] [US1] Refactor `app/templates/student/shop_new.html` to extend the `base_student.html` shell and drop duplicated header/sidebar markup
- [X] T020 [P] [US1] Refactor `app/templates/student/equipment_new.html` to extend the `base_student.html` shell and drop duplicated header/sidebar markup
- [X] T021 [P] [US1] Refactor `app/templates/student/quests_new.html` to extend the `base_student.html` shell and drop duplicated header/sidebar markup
- [X] T022 [P] [US1] Wrap `app/templates/student/powers.html` in the `base_student.html` shell without changing learn/equip/use behaviour
- [X] T023 [P] [US1] Switch `app/templates/student/progress.html` from `base.html` to the `base_student.html` shell, keeping existing progress content
- [X] T024 [P] [US1] Switch `app/templates/student/clan.html` from `base.html` to the `base_student.html` shell, keeping existing clan loading behaviour
- [X] T025 [P] [US1] Switch `app/templates/student/profile.html` from `base.html` to the `base_student.html` shell, keeping existing profile POST
- [X] T026 [US1] Switch `app/templates/student/character_create.html` to the student visual language with no fabricated HP/power bars in that template
- [X] T027 [US1] Switch `app/templates/student/adventures_list.html` from header-only to the full `base_student.html` shell
- [X] T028 [US1] Show classroom-only strip (one tab) when there is no clan, and omit stats/strip numbers when there is no character, in `app/templates/student/_student_header.html`
- [X] T029 [US1] Add Clan and Profile text links in the identity bar of `app/templates/student/_student_header.html` so those pages remain reachable from the shared frame

**Checkpoint**: User Story 1 is demoable on its own. Fake shop/equipment/quest controls may still exist. Power slots may still use a generic bolt. Phone CSS is not required.

---

## Phase 4: User Story 2 - Controls that look real actually work (Priority: P2)

**Goal**: Unfinished chrome is gone. Clan-mate tabs do not impersonate another student.

**Independent Test**: Walk Character, Quests, Shop, and Equipment and try every control that looks interactive. See `quickstart.md` §5 (honest controls).

### Tests for User Story 2

- [X] T030 [US2] Assert Character/Quests/Shop/Equipment HTML does not contain Special Offer, Auto Equip, Save Loadout, Filter Quests, or Click to Rotate in `tests/test_student_ui_shell.py`

### Implementation for User Story 2

- [X] T031 [P] [US2] Remove the Special Offer / wandering-merchant banner from `app/templates/student/shop_new.html`
- [X] T032 [P] [US2] Remove Auto Equip, Save Loadout, and the Click to Rotate hint from `app/templates/student/equipment_new.html`
- [X] T033 [P] [US2] Remove the Filter Quests control from `app/templates/student/quests_new.html`
- [X] T034 [P] [US2] Remove the Click to Rotate hint from `app/templates/student/character_new.html`
- [X] T035 [US2] Remove the documents/article icon with no destination from `app/templates/student/_student_header.html`
- [X] T036 [US2] Make clan-mate strip tabs non-interactive awareness (not links/buttons, not in tab order) in `app/templates/student/_student_header.html`

**Checkpoint**: User Stories 1 and 2 both work. Destination list and leftover-page shell remain. Type icons and class-name identity can wait.

---

## Phase 5: User Story 3 - Finish the four redesigned pages (Priority: P3)

**Goal**: Identity bar names class/clan, equipped powers show name plus type icon, party portraits only when clan-mates exist, resource bars are truthful, Equipment/Adventures/Character are in the shared list (already from T011; verify after page-specific leftovers).

**Independent Test**: Compare Character, Quests, Shop, and Equipment against the remaining design intent in `quickstart.md` §5 (finished redesigned pages).

### Tests for User Story 3

- [X] T037 [US3] Assert identity shows class name (and clan name when clanned), equipped ability name on Character, and no party-portrait cluster for a solo character in `tests/test_student_ui_shell.py`

### Implementation for User Story 3

- [X] T038 [US3] Show class name (and clan name when present) as the identity bar primary text instead of a comma-separated member list in `app/templates/student/_student_header.html`
- [X] T039 [US3] Implement `power_icon_for_ability` (type / `special_effect` → Material Icon ligature) in `app/services/student_chrome.py`
- [X] T040 [US3] Render equipped power names and type icons, with empty slots labelled Empty, in `app/templates/student/character_new.html`
- [X] T041 [US3] Render `party_members` portraits on Character and omit the cluster when the list is empty in `app/templates/student/character_new.html`
- [X] T042 [US3] Confirm Shop and Equipment gold/HP/power use chrome helper values with no decorative 85% gold fill in `app/templates/student/_student_sidebar.html`

**Checkpoint**: User Stories 1–3 work. Small-screen stacking can wait.

---

## Phase 6: User Story 4 - The shell still works on a small screen (Priority: P4)

**Goal**: Phone-sized viewports keep HP, gold, destinations, and primary actions reachable. Overflowing clan strips scroll. Keyboard users tab destination links, not clan tabs.

**Independent Test**: Narrow to ~390px and complete Character → Shop purchase; tab through chrome on a wide screen. See `quickstart.md` §5 (small screen).

### Implementation for User Story 4

- [X] T043 [US4] Stack the stats/destination column above main content below ~768px so Shop buy and Equipment slots stay on screen in `static/css/student_shell.css`
- [X] T044 [US4] Keep the clan strip horizontally scrollable with the current student identifiable in `static/css/student_shell.css` and `app/templates/student/_student_header.html`
- [X] T045 [US4] Ensure destination links stay in tab order and clan-mate tabs are not focusable in `app/templates/student/_student_header.html` and `app/templates/student/_student_sidebar.html`

**Checkpoint**: All four user stories are independently functional.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Regression, contract check, docs, leftover unused includes.

- [X] T046 [P] Verify HTML against `specs/004-student-ui-gaps/contracts/student-chrome.md`
- [X] T047 Run `pytest tests/test_student_ui_shell.py -q`
- [X] T048 Run regression suites in `tests/test_shop_api.py`, `tests/test_powers.py`, `tests/test_equipment_data_integration.py`, `tests/test_character_management.py`, and `tests/test_adventure_routes_student.py`
- [X] T049 Perform shared-chrome, honest-controls, redesigned-pages, small-screen, and create-character/login smokes in `specs/004-student-ui-gaps/quickstart.md`
- [X] T050 [P] Check linter diagnostics for `app/services/student_chrome.py`, `app/routes/student_main.py`, `app/routes/adventures/student.py`, `app/templates/student/base_student.html`, and `static/css/student_shell.css`
- [X] T051 Leave unrouted `app/templates/student/character.html` and `app/templates/student/shop.html` unused; do not resurrect them
- [X] T052 Mark spec 004 shipped in `docs/now.md` only after T047–T049 pass

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies; start immediately.
- **Foundational (Phase 2)**: Depends on Setup. Blocks all user stories (chrome service + shell slots + destination list).
- **User Story 1 (Phase 3)**: Depends on Foundational. Recommended MVP.
- **User Story 2 (Phase 4)**: Depends on Foundational. Can start on the four rebuilt templates after US1 refactors them (same files). Independently testable as “no fake actions” even if leftover pages were already wrapped.
- **User Story 3 (Phase 5)**: Depends on Foundational. Identity/powers/portraits touch header and Character after US1 shell refactor.
- **User Story 4 (Phase 6)**: Depends on Foundational CSS file (T008). Best after US1 so leftover pages exist to resize.
- **Polish (Phase 7)**: Depends on all desired user stories.

### User Story Dependencies

- **US1 - Shared shell**: No dependency on US2–US4. Needs Foundational service and sidebar.
- **US2 - Honest controls**: Touches `shop_new.html`, `equipment_new.html`, `quests_new.html`, `character_new.html` after US1 removes duplicated chrome. Sequential after US1 for one implementer.
- **US3 - Finish four pages**: Touches `_student_header.html` and `character_new.html` after US1. Can overlap US2 if US2 is done first on those files.
- **US4 - Small screens**: CSS-only plus strip overflow. Independent of power icons; needs pages already on the shell.

### Within Each User Story

- Tests (US1–US3) are listed before implementation and should fail until the templates/routes exist.
- Chrome service before route context before templates.
- Story checkpoint must pass before treating the story as done.

### Parallel Opportunities

- Setup reviews T002–T005 can run in parallel.
- Foundational T008 can run in parallel with T006–T007 (new CSS file vs new Python file).
- After T015–T017, template wraps T018–T025 can run in parallel (different templates).
- US2 removals T031–T034 can run in parallel (different templates) after US1 wraps those files.
- Polish T046 and T050 can run in parallel after implementation.

---

## Parallel Example: User Story 1

```text
Task: "Refactor app/templates/student/character_new.html to extend the base_student.html shell"
Task: "Refactor app/templates/student/shop_new.html to extend the base_student.html shell"
Task: "Refactor app/templates/student/equipment_new.html to extend the base_student.html shell"
Task: "Refactor app/templates/student/quests_new.html to extend the base_student.html shell"
```

Only after `student_chrome_context` is passed from `app/routes/student_main.py` and `app/routes/adventures/student.py`.

---

## Parallel Example: User Story 2

```text
Task: "Remove the Special Offer banner from app/templates/student/shop_new.html"
Task: "Remove Auto Equip, Save Loadout, and Click to Rotate from app/templates/student/equipment_new.html"
Task: "Remove the Filter Quests control from app/templates/student/quests_new.html"
Task: "Remove the Click to Rotate hint from app/templates/student/character_new.html"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup.
2. Complete Phase 2: Chrome service + shell slots + destination list.
3. Complete Phase 3: Put every in-scope page on that shell.
4. Stop and validate with `quickstart.md` shared-chrome steps and `pytest tests/test_student_ui_shell.py`.
5. Demo one student frame before deleting placeholder buttons.

### Incremental Delivery

1. US1 shell → students no longer bounce into the old layout.
2. US2 honest controls → nothing looks broken on the rebuilt pages.
3. US3 finish four pages → comps remaining gaps closed.
4. US4 small screens → classroom phones.
5. Phase 7 regression and smokes before calling 004 shipped.

### Recommended Option

Implement **sequentially P1 → P4** with one implementer: Foundational, US1, US2, US3, then US4. That matches the spec priorities and avoids colliding edits on `character_new.html`, `_student_header.html`, and `_student_sidebar.html`.

If two people are available after Foundational, put **US1 leftover pages** (Progress, Clan, Profile, Create character, Adventures list, Powers) on one track and keep the four rebuilt-page refactors on the other only after agreeing the shell block names. Do not parallel US2/US3 with those same four templates.

---

## Notes

- No Alembic migration. Do not add `abilities.icon`.
- Do not change `Character.total_health` / `total_power` semantics.
- Do not add a JavaScript build pipeline.
- Adventure map and battle screens stay out of scope.
- Login and Welcome stay out of scope (SC-008).
- Do not implement special offers, auto-equip, loadouts, quest filters, or portrait rotation.
- Update `docs/now.md` only in T052 after tests and smokes pass.
