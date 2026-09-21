# Quickstart - Adventure Editor Enhancements

**Feature**: 002-adventure-editor-enhancements
**Date**: 2026-05-22
**Audience**: developers implementing or verifying the editor enhancements.

This quickstart assumes the base Adventures feature from `specs/001-adventures-map-system` is already present.

---

## 1. Prerequisites

| Tool | Version | Notes |
|---|---|---|
| Python | 3.8+ | project constitution |
| pip | latest | install project dependencies |
| SQLite | bundled with Python | local `instance/legends.db` |
| Browser | Chrome / Firefox / Edge / Safari | verify editor UI, pointer events, upload preview |

No Node install or JS build step is required.

---

## 2. Setup

```bash
# from repo root
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt -r requirements-dev.txt

alembic upgrade head
```

No new migration is expected for this feature. If schema changes become necessary during implementation, add an Alembic migration and run `alembic upgrade head` before testing.

---

## 3. Run Route Tests

Recommended focused tests after implementation:

```bash
pytest tests/test_adventure_routes_teacher.py -q
```

Expected new coverage:

- Teacher question-set options return only active sets owned by the logged-in teacher.
- Quiz node can save, clear, and reload `question_set_id`.
- Other-teacher question sets are rejected for quiz node updates.
- Adventure settings update preserves omitted fields.
- Background upload validation still rejects invalid files.
- Node coordinate update persists and bumps version for published adventures through existing behavior.

Run broader Adventures smoke tests if a route/schema change touches shared paths:

```bash
pytest tests/test_adventure_routes_teacher.py tests/test_adventure_routes_student.py tests/test_adventure_graph_unlock.py -q
```

---

## 4. Run The App

```bash
python run.py
```

Open `http://127.0.0.1:5000/teacher/adventures/list`, log in as a teacher, and open an existing adventure editor.

If you need seed users:

```bash
flask --app run:app seed-db
```

---

## 5. Manual Smoke - Quiz Question Sets

1. Create or confirm the teacher has at least one active question set in the Education area.
2. Open an adventure with a quiz node or add a new quiz node.
3. Select the quiz node in the map inspector.
4. Choose a question set from the quiz dropdown and save the node.
5. Refresh the editor.

Expected:

- The dropdown lists only the logged-in teacher's active question sets.
- The saved quiz node still shows the selected question set after refresh.
- Publish validation no longer warns that this quiz node lacks quiz content.
- If the teacher has no question sets, the inspector shows an empty-state message and a manage-question-sets link.

---

## 6. Manual Smoke - Adventure Settings

1. Open the editor for an owned adventure.
2. Click the settings control in the editor toolbar.
3. Change title, description, theme, completion rule, and sharing visibility where allowed.
4. Upload a valid PNG/JPEG/WebP background image.
5. Save settings and refresh the page.

Expected:

- Save confirmation appears without leaving the editor.
- Header title and background preview update after save/upload.
- Refreshed editor shows the same saved values.
- Invalid background uploads show an error and keep the prior background.
- Draft adventures cannot be made public.

---

## 7. Manual Smoke - Drag Reposition

1. Open an editable adventure with at least two connected nodes.
2. Drag a node to a new location.
3. Watch connected path lines while dragging.
4. Release the node and refresh the editor.
5. Turn on Connect nodes mode and try to drag a node.

Expected:

- The dragged node follows the pointer and connected lines remain attached during movement.
- The node remains at the new position after refresh.
- Very small movement still behaves like a click/selection.
- Nodes cannot be saved outside the visible map bounds.
- Dragging is disabled while Connect nodes mode is active.

---

## 8. Regression Checks

Before considering the feature ready:

```bash
pytest tests/test_adventure_routes_teacher.py -q
pytest tests/test_quest_models.py -q
```

The legacy quest tests are a regression guard. If pre-existing unrelated failures remain, document them in the implementation notes rather than treating them as introduced by this feature.

---

## 9. Implementation Notes

These notes capture how the shipped editor behaves, including caveats found during implementation.

### Shared editor behavior

- Success and JSON failures surface in `#editor-validation` (`aria-live`). Failed settings saves keep the form values; failed background uploads restore the previous canvas background; failed drags snap the node back to its last saved position.
- No Alembic migration was required. Quiz attachment uses existing `AdventureNode.question_set_id`; settings and coordinates use existing adventure/node columns.
- `GET /teacher/adventures/<id>` still serves the HTML editor by default. Pass `Accept: application/json` or `?format=json` for the JSON summary used by tests.

### Quiz question sets (US1)

- Options are built from the current user's legacy `Teacher` row (`Teacher.user_id` → `QuestionSet.teacher_id`), not from `User.id`. Teachers without that profile see an empty list, not an error.
- The editor bootstraps `questionSets` on page load. `GET /teacher/adventures/question-sets` returns the same payload for refresh or tests.
- The inspector dropdown includes a "none" option to clear `question_set_id`. Empty state links to `/teacher/education/sets/create`; every quiz inspector includes a manage link to `/teacher/education/sets`.
- Publish validation still flags quiz nodes that have no usable question set. A saved id that is no longer in the teacher's active list shows an unavailable warning.

### Adventure settings (US2)

- Toolbar **Settings** opens a Bootstrap modal. Save sends only dirty fields on `PATCH /teacher/adventures/<id>`.
- If a background file is chosen, Save uploads it first via `POST .../background`. That upload **persists immediately** and then a metadata PATCH runs if title/description/theme/end semantics/sharing also changed.
- Failed uploads keep the prior background. The stored filename is the sanitized original name under `/static/images/adventure_backgrounds/<id>/`, not a renamed `map.webp`.
- Default max upload size is 5 MB (`MAX_BACKGROUND_UPLOAD_BYTES`). Draft adventures cannot be made public (share checkbox is disabled until publish; the PATCH also rejects it).

### Drag reposition (US3)

- Pointer events on node groups, 4-pixel click-vs-drag threshold, live SVG transform and connected-edge updates, one coordinate PATCH on drop.
- Client clamps to adventure width/height before save. The API still only requires `x` and `y` ≥ 0.
- Drag is disabled in Connect nodes mode (`node-drag-disabled`) and when `canEdit` is false. Pointer cancel snaps back without saving.
- Published adventures bump `version` on a successful coordinate (or settings) PATCH, matching existing 001 behavior.

### Manual smoke UI cues

| Smoke | Control |
|---|---|
| Settings | Toolbar **Settings** button → `#adventure-settings-modal` |
| Quiz attach | Select a quiz node → inspector **Question set** dropdown → **Save node** |
| Drag | Pointer-drag a node while Connect mode is off; toggle **Connect nodes** to confirm drag is disabled |

### Regression results (Phase 6)

- `pytest tests/test_adventure_routes_teacher.py` — 19 passed.
- `pytest tests/test_adventure_routes_teacher.py tests/test_adventure_routes_student.py tests/test_adventure_graph_unlock.py` — all passed.
- `pytest tests/test_quest_models.py` — one **pre-existing** failure, not introduced by this feature: `TestQuest.test_quest_availability` raises `TypeError: can't compare offset-naive and offset-aware datetimes` in `Quest.is_available()` when `start_date` is set with `datetime.utcnow()`. Production `get_utc_now()` is timezone-aware. Do not treat this as an Adventures editor regression.
