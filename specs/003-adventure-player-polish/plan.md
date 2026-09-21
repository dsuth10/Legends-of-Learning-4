# Implementation Plan: Adventures Player and Editor Polish

**Branch**: `main` | **Date**: 2026-09-21 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/003-adventure-player-polish/spec.md`

## Summary

Polish the shipped Adventures player and editor using original roadmap Phase 5: character-marker travel, a student mini-map, keyboard/screen-reader (and small-screen) access, clan/individual assignment, and a node icon library. Implementation stays on the existing Flask/Jinja/vanilla JS stack from specs 001 and 002. No new tables: `adventure_assignments.clan_id` / `character_id` and `adventure_nodes.icon_url` already exist. The teacher create-assignment route currently rejects clan/character targets; student matching and the progress roster already understand those rows.

**Technical approach** (validated in Phase 0 — see `research.md`):

- Player travel uses existing `next_unlocked` plus map-load inference from latest `completed_at`; `sessionStorage` prevents repeat plays; `prefers-reduced-motion` skips motion.
- Mini-map is a student overlay on the existing scrollable `#map-container` (no new camera engine).
- Editor keyboard/undo/zoom live in a helper so `adventure_editor.js` does not grow further; undo is session-only and wraps existing node/edge APIs.
- New `app/services/adventure_assignment.py` creates/lists classroom, clan, and character assignments; leaving a clan keeps an already-started run.
- Icon catalog is Material Icon ligatures stored in `icon_url`; `null` means the type default.

## Technical Context

**Language/Version**: Python 3.8+ for backend code; JavaScript ES2017+ for editor and player; Jinja2 templates.

**Primary Dependencies**: Flask, Flask-Login, Flask-SQLAlchemy, Pydantic v2 in `app/forms/adventure_schemas.py`, SQLAlchemy models in `app/models/adventure.py` and `app/models/adventure_progress.py`, vanilla JS + SVG in `static/js/adventure_editor.js` and `static/js/adventure_player.js`.

**Storage**: Existing Adventures tables. No new migration expected. Icon ligatures in `adventure_nodes.icon_url`. Pending travel in `sessionStorage` only.

**Testing**: pytest with `tests/conftest.py` and existing adventure factories; new cases in `tests/test_adventure_routes_teacher.py` and `tests/test_adventure_routes_student.py`. Browser/manual smoke in `quickstart.md` (travel, mini-map, keyboard, reduced motion).

**Target Platform**: Existing Flask web app on Windows/Linux dev; modern desktop browsers plus a phone-sized responsive pass. No native app.

**Project Type**: Single Flask web application with server-rendered templates and static JavaScript.

**Performance Goals**:

- Travel finishes in under 1.5 seconds (SC-002).
- Mini-map jump visible within 1 second (FR-010).
- Editor undo/redo applies without a full page reload.
- Progress roster stays on the existing grouped-query path (no new N+1).

**Constraints**:

- No new JavaScript build pipeline or frontend framework.
- No schema changes unless a missing constraint is found at implementation; existing columns cover assignment targets and icons.
- JSON responses keep `{"success": bool, "data": ..., "errors": [...]}`.
- Teacher ownership via `require_teacher_edit` / classroom ownership; students only play assigned adventures.
- Class assignment behaviour must not regress (SC-008).
- Clan assignment is per-character progress, not shared clan progress.
- Legacy Quest / QuestLog behaviour unchanged.

**Scale/Scope**: One student on one adventure map at a time; maps typically 5–30 nodes, mini-map tested when content exceeds one screen. Teachers assign to one class, clan, or character per request. Icon catalog is a small curated list (on the order of 10–30 ligatures).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

The constitution at `/constitution.md` defines gates for code style, testing, architecture, database practices, security, error handling, documentation, project structure, API patterns, and service layering.

| # | Gate | Requirement | Plan adherence | Status |
|---|------|-------------|----------------|--------|
| G-1 | Code Style | Python 3.8+, PEP 8, readable focused functions | New assignment helpers in a dedicated service; player/editor JS split so existing files do not grow further. | PASS |
| G-2 | Testing | pytest coverage for new features and errors | Route tests for clan/character assign, duplicates, forbidden targets, leave-clan continue, icon save/clear, catalog defaults. Manual smoke for motion and keyboard. | PASS |
| G-3 | Architecture | Routes / models / services separated | Assignment create/list/target-auth in `app/services/adventure_assignment.py`; routes stay thin; travel/mini-map stay in static JS. | PASS |
| G-4 | Database / Migrations | SQLAlchemy + Alembic for schema changes | No schema changes planned; reuse `clan_id`, `character_id`, `icon_url`. | PASS |
| G-5 | Authentication / Authorization | Flask-Login and ownership checks | New assignment targets require teacher-owned class/clan/character; student access still goes through assignment matching. | PASS |
| G-6 | Templates / Static Files | Jinja2 by role, static under `/static` | Player/editor templates and CSS/JS stay in existing paths; Material Icons stylesheet on the player page. | PASS |
| G-7 | Security | Validate input, no secrets | Pydantic `AssignmentCreateSchema` and node update schema; target ownership checks; icon values limited to catalog or `/` paths at render time. | PASS |
| G-8 | Error Handling | Status codes and meaningful errors | Reuse `_json_err`; empty-clan warning in `data.warnings` (not an error); undo failure via existing live region. | PASS |
| G-9 | API Patterns | Pydantic + envelope | Create/list/targets/catalog JSON uses the existing envelope. | PASS |
| G-10 | Project Structure | Established directories | All files under `app/`, `static/`, `tests/`, `specs/`. | PASS |

**Initial gate decision**: PASS — no constitution violations, no Complexity Tracking entries required.

**Re-check after Phase 1 design**: PASS — data model and contracts are additive on existing tables, reuse the response envelope, and avoid a new architecture or migration. The only behavioural addition on the student service is "keep an already-started run after leaving a clan," which is specified and testable.

## Project Structure

### Documentation (this feature)

```text
specs/003-adventure-player-polish/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── teacher-assignment-api.md
│   ├── node-icons-api.md
│   └── player-map.md
├── checklists/
│   └── requirements.md
├── spec.md
└── tasks.md             # Phase 2 output, not created by /speckit-plan
```

### Source Code (repository root)

```text
app/
├── forms/
│   └── adventure_schemas.py                 # Existing AssignmentCreateSchema / NodeUpdateSchema
├── models/
│   ├── adventure.py                         # Existing icon_url; no model change expected
│   └── adventure_progress.py                # Existing clan_id / character_id
├── routes/
│   └── adventures/
│       ├── teacher.py                       # Enable clan/character create; list all; targets; catalog
│       ├── student.py                       # Leave-clan continue via service; no new endpoints expected
│       └── serializers.py                   # target_type / target_label on assignment_dict
├── services/
│   ├── adventure_assignment.py              # NEW — create/list/authorise classroom, clan, character
│   └── adventure_graph.py                   # student_is_assigned progress fallback; re-export if needed
└── templates/
    ├── teacher/
    │   ├── adventure_assignments.html       # Target type: class / clan / character
    │   ├── adventure_progress.html          # Filter all assignment targets
    │   └── adventure_editor.html            # Icon picker in inspector; keyboard help
    └── student/
        └── adventure_map.html               # Marker, mini-map region, Material Icons, live region

static/
├── css/
│   ├── adventure_editor.css                 # Zoom wrap, small-screen inspector stack
│   └── adventure_player.css                 # Marker, travel, mini-map, phone overlap
└── js/
    ├── adventure_editor.js                  # Wire inspector icon picker; keep graph CRUD
    ├── adventure_editor_commands.js         # NEW — session undo/redo + keyboard/zoom
    ├── adventure_player.js                  # Orchestrate state + detail actions
    └── adventure_player_map.js              # NEW — marker, travel, mini-map, camera jump

tests/
├── test_adventure_routes_teacher.py         # Clan/character assign, catalog, icons
├── test_adventure_routes_student.py         # Leave-clan continue; class assignment regression
└── fixtures/
    └── adventure_factories.py               # Clan/character assignment helpers if missing
```

**Structure Decision**: Stay in the existing single-app Flask layout. Prefer new focused JS/service files over growing `adventure_editor.js` (~1100 lines) and `adventure_graph.py` (~1800 lines). Do not add a frontend package or a new blueprint.

## Complexity Tracking

> No constitution violations were identified. This section is intentionally empty.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| *(none)* | *(n/a)* | *(n/a)* |
