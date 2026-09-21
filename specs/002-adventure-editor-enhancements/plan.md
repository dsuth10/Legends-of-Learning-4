# Implementation Plan: Adventure Editor Enhancements

**Branch**: `main` | **Date**: 2026-05-22 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/002-adventure-editor-enhancements/spec.md`

## Summary

Enhance the existing teacher Adventure Editor with three focused authoring improvements: attach teacher-owned question sets to quiz nodes, edit adventure-level settings without leaving the editor, and drag existing nodes to persist new map positions. The implementation extends the current Flask/Jinja/vanilla JS Adventures system already delivered by `001-adventures-map-system`; it does not require new schema tables or a new frontend framework.

**Technical approach** (validated in Phase 0 - see `research.md`):

- Reuse existing `AdventureUpdateSchema`, `NodeUpdateSchema`, `PATCH /teacher/adventures/<id>`, `PATCH /teacher/adventures/<id>/nodes/<node_id>`, and `POST /teacher/adventures/<id>/background` contracts wherever possible.
- Add one small teacher-scoped question-set option source so the editor can render quiz dropdowns and future refresh flows can fetch the same options.
- Keep all editor interactions inside `app/templates/teacher/adventure_editor.html` and `static/js/adventure_editor.js`, following the current inspector pattern used for battle monster selection.
- Implement drag with pointer events, a click-vs-drag threshold, live SVG edge updates, and one save on drop to avoid server chatter and full graph re-rendering during movement.
- Preserve current Adventures publishing, assignment, student play, version bump, ownership, and response-envelope behavior.

## Technical Context

**Language/Version**: Python 3.8+ for backend code; JavaScript ES2017+ for the editor; Jinja2 templates and Bootstrap-compatible markup already used by the current editor.

**Primary Dependencies**: Flask, Flask-Login, Flask-SQLAlchemy, Pydantic v2 schemas in `app/forms/adventure_schemas.py`, SQLAlchemy models in `app/models/adventure.py` and `app/models/education.py`, vanilla JS + SVG in `static/js/adventure_editor.js`.

**Storage**: Existing Adventures tables and existing `question_sets` table. No new migration expected. Uploaded backgrounds continue to use `static/images/adventure_backgrounds/<adventure_id>/`.

**Testing**: pytest with existing `tests/conftest.py` fixtures and patterns in `tests/test_adventure_routes_teacher.py`; browser/manual smoke via `quickstart.md`.

**Target Platform**: Existing Flask web application on Windows/Linux development environments; modern desktop browsers for the teacher editor. Pointer events cover mouse, pen, and touch where the browser supports them.

**Project Type**: Single Flask web application with server-rendered teacher templates and static JavaScript.

**Performance Goals**:

- Settings save confirmation visible within 2 seconds in normal local/test environments.
- Drag interaction remains visually smooth on maps up to 50 nodes, with no full graph reload during pointer movement.
- Repositioning sends one node-position save per completed drag, not one request per pointer move.
- Quiz-node question-set options are available on initial editor render without a mandatory extra round trip.

**Constraints**:

- No new JavaScript build pipeline or frontend framework.
- No schema changes unless implementation discovers a missing persisted field; existing columns already cover all feature data.
- All JSON responses keep the existing `{"success": bool, "data": ..., "errors": [...]}` envelope.
- Teacher ownership and edit permissions must continue through `require_teacher_read` / `require_teacher_edit`.
- Draft adventures cannot be made public; published-edit version bump behavior remains owned by existing route logic.
- Background upload validation remains MIME, extension, magic-byte, and size checked.
- Node dragging is disabled in connect mode and view-only/shared preview mode.

**Scale/Scope**: One teacher editing one adventure at a time; typical maps 5-30 nodes, tested drag behavior up to 50 nodes; question-set lists scoped to one teacher's active question sets.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

The constitution at `/constitution.md` defines gates for code style, testing, architecture, database practices, security, error handling, documentation, project structure, API patterns, and service layering.

| # | Gate | Requirement | Plan adherence | Status |
|---|------|-------------|----------------|--------|
| G-1 | Code Style | Python 3.8+, PEP 8, readable focused functions | Backend additions are small route/schema helpers following existing Adventures route style. | PASS |
| G-2 | Testing | pytest coverage for new features and errors | Add route tests for question-set listing/filtering, quiz-node attachment, metadata update, background errors, and node coordinate persistence. Manual smoke covers editor drag behavior. | PASS |
| G-3 | Architecture | Routes in `/app/routes`, models in `/app/models`, business logic separated when complex | This feature is route/template/JS enhancement work; no new service is needed unless question-set ownership lookup becomes reused beyond the editor. | PASS |
| G-4 | Database / Migrations | SQLAlchemy + Alembic for schema changes | No schema changes planned; existing `Adventure`, `AdventureNode.question_set_id`, and `QuestionSet` fields cover the feature. | PASS |
| G-5 | Authentication / Authorization | Flask-Login and proper role/ownership checks | New/updated teacher routes remain `@login_required`, `@teacher_required`, and teacher-scoped. | PASS |
| G-6 | Templates / Static Files | Jinja2 templates by role, static assets under `/static` | Editor markup stays in `app/templates/teacher/adventure_editor.html`; JS stays in `static/js/adventure_editor.js`. | PASS |
| G-7 | Security | Validate/sanitize input, CSRF/form care, no secrets | JSON payloads use existing Pydantic schemas; uploads use existing validation; question sets are filtered by current teacher. | PASS |
| G-8 | Error Handling | Proper status codes and meaningful user errors | Reuse `_json_err`, validation banner, and editor recovery behavior for failed saves/uploads/drags. | PASS |
| G-9 | API Patterns | Pydantic validation and consistent response envelope | Existing Adventures schemas and helpers are reused; the new question-set options response uses the same envelope. | PASS |
| G-10 | Project Structure | Use established directories | All planned files live in existing `app/`, `static/`, `tests/`, and `specs/` directories. | PASS |

**Initial gate decision**: PASS - no constitution violations, no Complexity Tracking entries required.

**Re-check after Phase 1 design**: PASS - data model and contracts remain additive, reuse existing tables and response conventions, and introduce no new architecture or migration risk.

## Project Structure

### Documentation (this feature)

```text
specs/002-adventure-editor-enhancements/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── teacher-editor-api.md
├── checklists/
│   └── requirements.md
├── spec.md
└── tasks.md             # Phase 2 output, not created by /speckit-plan
```

### Source Code (repository root)

```text
app/
├── forms/
│   └── adventure_schemas.py              # Existing; add response schema only if useful
├── models/
│   ├── adventure.py                      # Existing; no planned model changes
│   └── education.py                      # Existing QuestionSet model
├── routes/
│   └── adventures/
│       ├── teacher.py                    # Add question-set options and reuse update routes
│       └── serializers.py                # Existing node/adventure serialization
└── templates/
    └── teacher/
        └── adventure_editor.html         # Add settings modal and quiz options bootstrap data

static/
├── css/
│   └── adventure_editor.css              # Add styles only if needed for drag/settings states
└── js/
    └── adventure_editor.js               # Add settings save, quiz select, drag behavior, shared error helpers

tests/
├── test_adventure_routes_teacher.py      # Add route and persistence tests
└── fixtures/
    └── adventure_factories.py            # Reuse existing fixtures; extend only if needed
```

**Structure Decision**: Use the existing single-app Flask layout and enhance the existing Adventures editor files in place. The preferred implementation is narrowly scoped: one route-level question-set option source, one template update to pass settings/question-set data, one JavaScript update to support settings save, quiz node selection, and drag, plus focused tests in the existing teacher route test file.

## Complexity Tracking

> No constitution violations were identified. This section is intentionally empty.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| *(none)* | *(n/a)* | *(n/a)* |
