# Implementation Plan: Adventures Quest Map System

**Branch**: `001-adventures-map-system` | **Date**: 2026-05-22 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/001-adventures-map-system/spec.md`

## Summary

Build a new, parallel map-based quest system ("Adventures") alongside the existing legacy `Quest` / `QuestLog` system, without modifying legacy code, data, or UI. Teachers visually author branching quest maps (background image + drag-and-drop typed nodes + directed edges) and assign them to classes (later: clans, individuals). Students play through the adventure on a map, completing typed nodes (`start` / `story` / `battle` / `quiz` / `choice` / `reward` / `milestone` / `boss` / `end`) to earn rewards and unlock the next path. Branching, choices, optional nodes, AND/OR re-join semantics, conditional rewards, retry limits with consequences, per-character progress, audit logging, and mid-flight stability (snapshot-on-assignment) are all in scope; clan-shared progress, cross-school sharing, time-limited nodes, analytics dashboards and a legacy-to-Adventures migration tool are explicitly out of scope.

**Technical approach** (validated in Phase 0 — see `research.md`):

- New SQLAlchemy models in `app/models/adventure.py` and `app/models/adventure_progress.py` (8 new tables), all FKs into existing identity tables (`users`, `characters`, `classrooms`, `clans`, `equipment`, `abilities`, `achievement_badge`, `question_sets`, `monsters`) with no schema edits to legacy tables.
- One additive change to `EventType` (three new values) — no schema break.
- A single, optional one-line hook into the existing battle-resolution code path to atomically close the bound adventure node on battle win.
- New Flask blueprints mounted under `/teacher/adventures/*` and `/student/adventures/*`, returning the project's standard `{"success": True, "data": ...}` JSON response shape.
- Service layer modules (`app/services/adventure_graph.py`, `adventure_rewards.py`, `adventure_hooks.py`) hold all unlock recomputation, validation, snapshotting, and reward distribution; routes call services and format responses (per the project constitution).
- Vanilla JS + SVG + Tailwind for the editor and student map (no build pipeline); JSON-first API surface keeps the door open for a future React Flow rewrite of the editor alone.
- Snapshot-on-assignment via an `adventure_version` column on the assignment row (Phase 4 of the feature roadmap), with optional full JSON snapshot on the per-character progress row if version pinning proves insufficient.

## Technical Context

**Language/Version**: Python 3.8+ (per constitution); JavaScript ES2017+ for editor/player JS (no transpiler).

**Primary Dependencies**: Flask 3.x, Flask-SQLAlchemy 3.x, Flask-Login, Flask-Migrate (Alembic), Flask-WTF (CSRF), Flask-JWT-Extended, Pydantic 2.x (request/response validation), SQLAlchemy 2.x, Jinja2 templates, Tailwind utility classes (already used elsewhere in the project), vanilla JS + SVG for the editor + player.

**Storage**: Existing project SQLite (`instance/legends.db`) via SQLAlchemy ORM, Alembic for all schema changes. Background image uploads stored under `static/images/adventure_backgrounds/<adventure_id>/` so they are served via the existing static path (per Assumption in the spec). One new migration adds the 8 adventure tables; a second additive migration extends `audit_log` only via the application-level `EventType` enum (no DDL).

**Testing**: pytest with the existing `tests/conftest.py` Alembic-driven fixture setup. New test files under `tests/`:
- `test_adventure_models.py` — relationships, cascades, constraints
- `test_adventure_graph_unlock.py` — DAG unlock recomputation algorithm on fixture graphs (linear, branch, choice, merge, cycle)
- `test_adventure_routes_teacher.py` — every teacher endpoint, happy path + auth-denied + invalid-input
- `test_adventure_routes_student.py` — every student endpoint, including idempotency tests
- `test_adventure_rewards.py` — atomic reward distribution + conditional rewards + consequences
- Regression: `tests/test_quest_models.py` MUST continue to pass unchanged (verifies FR-036: legacy untouched).

**Target Platform**: Linux/Windows server hosting Flask app; modern desktop browsers for teacher editor and student player (Chrome / Firefox / Edge / Safari, ES2017+). No native mobile or offline mode (per spec Out of Scope).

**Project Type**: Web application — Flask backend with server-rendered Jinja templates + small client-side JS modules for the editor and player. Single-process, single-codebase; no separate frontend/backend repositories.

**Performance Goals**:
- Student map first render: ≤ 2 s on a typical school network (SC-003).
- Node completion → updated visual state: ≤ 2 s (SC-004).
- Teacher progress roster (up to 60 students): ≤ 3 s (SC-009).
- Editor pan/zoom: 60 fps on a typical teacher laptop.
- No N+1 queries on student state load or teacher progress load (verified by query counters in tests).

**Constraints**:
- Strictly additive: zero modifications to legacy `quest*` tables, models, routes, templates, or services (FR-036). The single allowed legacy seam is a one-line call inside the existing battle-resolution code path to `adventure_hooks.on_battle_resolved(battle)`; the hook itself is a no-op for battles not bound to a node.
- All reward distribution and consequence application must be atomic in a single DB transaction (FR-030, FR-031), mirroring the established `Reward.distribute()` pattern.
- All student-facing node operations (start/complete/retry/choose) must be idempotent (FR-033).
- All authoring and play operations must enforce ownership / assignment scoping (FR-040).
- Background image upload size limit (default 5 MB) enforced at upload; oversize rejected with a friendly error.
- Self-loops (`from_node_id == to_node_id`) disallowed at the DB layer (`CHECK` constraint where supported, app-level guard elsewhere).
- API responses follow the constitution-mandated shape `{"success": bool, "data": ..., "errors": [...]}` (NOT the `{"ok": true}` shape suggested by the source roadmap — see research decision R5).

**Scale/Scope**:
- Up to ~60 students per assigned adventure (SC-009).
- Up to ~30 students concurrently completing the same adventure with zero observed reward duplication or unlock corruption (SC-005).
- Per-teacher adventure count: unbounded (no soft cap planned).
- Typical adventure size: 5–30 nodes for a class, ≤ 100 nodes worst-case (editor performance must remain smooth at 100).
- Schools running the system for a full term should observe ≥ 50% of assignments being reuses, not new authoring (SC-010).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

The constitution at `/constitution.md` enumerates gates across Code Style, Testing, Architecture, Database, Naming, Security, Error Handling, Documentation, Project Structure, Git Workflow, API Patterns, and Service Layer Patterns. Each gate is evaluated below.

| # | Gate | Constitution requirement | Plan adherence | Status |
|---|------|--------------------------|----------------|--------|
| G-1 | Code Style | Python 3.8+, PEP 8, type hints where appropriate, docstrings on classes and complex functions | All new modules will use type hints on public service functions and docstrings on every new SQLAlchemy model and service entry point. | PASS |
| G-2 | Testing | pytest, comprehensive coverage, test models / routes / services independently, use `tests/conftest.py` fixtures | New tests split across 5 files (models, graph unlock, teacher routes, student routes, rewards) with reuse of existing fixtures. Legacy `tests/test_quest_models.py` remains untouched and is the regression gate. | PASS |
| G-3 | Architecture: Separation of concerns | Business logic in `/app/services/`, routes in `/app/routes/`, models in `/app/models/` | Routes are thin and call into `adventure_graph`, `adventure_rewards`, `adventure_hooks` services. No DB queries in routes beyond loading the entry-point object and authorising. | PASS |
| G-4 | Architecture: Database / Migrations | SQLAlchemy ORM, Alembic migrations only, never `db.create_all()`, run `alembic upgrade head` after schema changes | Two new Alembic migrations: (a) create 8 adventure tables, (b) [if needed for portability] indices/check-constraints. No `db.create_all()` is introduced. | PASS |
| G-5 | Architecture: Authentication | Flask-Login for session, Flask-JWT-Extended for API | New teacher routes use Flask-Login + a `@teacher_required` decorator (mirrors existing pattern). Student routes use Flask-Login. No new auth surfaces. | PASS |
| G-6 | Architecture: Forms / CSRF | Flask-WTF for forms | Authoring endpoints accept JSON, but uploads and any HTML form posts use Flask-WTF and include CSRF tokens. | PASS |
| G-7 | Architecture: Templates / Blueprints | Jinja2 templates by role, blueprints by feature/role | New templates under `app/templates/teacher/adventure_*.html` and `app/templates/student/adventure_*.html`; new blueprint pair under `app/routes/adventures/`. | PASS |
| G-8 | Architecture: File size | ≤ 500 LOC per file when possible | Model split across `adventure.py` (template-side) and `adventure_progress.py` (per-character). Service modules split by responsibility. | PASS |
| G-9 | Database Best Practices | FKs with `ondelete`, association tables for M:N, indexes on FKs and frequent queries, validators where appropriate | Every FK declared with explicit `ondelete` (`CASCADE` for owning relationships, `SET NULL` for awarded items / external references). Indexes on `(teacher_id)`, `(adventure_id, node_type)`, `(character_id, status)`, `(character_id, adventure_id)` (unique), `(character_id, node_id)` (unique), and assignment lookup tuples. | PASS |
| G-10 | Naming | Plural lowercase table names with underscores; existing terms reused (Sorcerer/Warrior/Druid, WEAPON/ARMOR/...) | Table names: `adventures`, `adventure_nodes`, `adventure_edges`, `node_rewards`, `node_consequences`, `adventure_assignments`, `character_adventure_progress`, `character_node_progress`. Reuse existing enums where they overlap (`RewardType` values mirrored, with `BADGE` added). | PASS |
| G-11 | Security | No secrets in code, env vars for sensitive config, validate/sanitise input, CSRF on forms, secure cookies | All input validated via Pydantic models. Background image uploads validated for MIME + size + extension; stored outside the executable path. Ownership/assignment checks gate every action. | PASS |
| G-12 | Error Handling | Proper HTTP status codes, meaningful errors, logging, graceful DB errors, validate before processing | All API errors returned as `{"success": False, "errors": [{"code", "message"}]}` with appropriate HTTP status (400 for validation, 403 for auth, 404 for not-found, 409 for conflict like idempotent collision, 500 for unexpected). | PASS |
| G-13 | Documentation | Docstrings on classes / complex functions; keep README current; document API I/O | API contracts in `contracts/` document all teacher and student endpoints. Database structure update in `.cursor/rules/database-structure.mdc` after Phase 1 model code lands. | PASS |
| G-14 | Project Structure | Models in `/app/models/`, routes in `/app/routes/`, services in `/app/services/`, templates in `/app/templates/`, static in `/static/`, tests in `/tests/`, migrations in `/migrations/versions/` | Plan strictly conforms (see Project Structure below). | PASS |
| G-15 | Git Workflow | Meaningful commits, feature branches, test before commit | Feature branch `001-adventures-map-system` already in use. Phase-aligned PRs each ship with the corresponding new tests and `alembic upgrade head` step. | PASS |
| G-16 | API Patterns | Pydantic BaseModel for request/response validation; consistent `{"success": True, "data": {...}}` shape; appropriate HTTP status codes | All request bodies validated by Pydantic models in a new `app/forms/adventure_schemas.py`. All responses use `{"success", "data", "errors"}` (note: this overrides the `{"ok": true}` suggestion in the source roadmap — see research decision R5). | PASS |
| G-17 | Service Layer | Services in `/app/services/`, services handle multi-model ops, services return data not Flask responses, routes call services | `adventure_graph.recompute_unlocks(...)`, `adventure_rewards.distribute_node_rewards(...)`, `adventure_hooks.on_battle_resolved(...)` all return data structures only; routes wrap them with `{"success": ..., "data": ...}`. | PASS |

**Initial gate decision**: PASS — no violations, no Complexity Tracking entries required.

**Re-check after Phase 1 design**: PASS (revisited after data-model + contracts drafted; no new violations introduced; the only design tension surfaced was response-envelope shape, resolved by the constitution overriding the roadmap — recorded in research as R5).

## Project Structure

### Documentation (this feature)

```text
specs/001-adventures-map-system/
├── plan.md              # This file
├── research.md          # Phase 0 output — design decisions
├── data-model.md        # Phase 1 output — entities, relationships, constraints
├── quickstart.md        # Phase 1 output — local run / smoke-test recipe
├── contracts/           # Phase 1 output — teacher + student API contracts
│   ├── teacher-api.md
│   └── student-api.md
├── checklists/
│   └── requirements.md  # Pre-existing spec-quality checklist (passed)
├── spec.md              # The feature spec
└── tasks.md             # Phase 2 output (NOT created by /speckit-plan)
```

### Source Code (repository root)

The project already uses a single-app Flask layout (per `.cursor/rules/project-structure.mdc`). All new code slots into the existing directories — no new top-level folders. Lines marked **NEW** are added by this feature; everything else already exists and is untouched.

```text
app/
├── __init__.py
├── models/
│   ├── adventure.py                       # NEW — Adventure, AdventureNode, AdventureEdge,
│   │                                      #       NodeReward, NodeConsequence + their enums
│   ├── adventure_progress.py              # NEW — AdventureAssignment, CharacterAdventureProgress,
│   │                                      #       CharacterNodeProgress + their enums
│   ├── audit.py                           # MODIFIED — append 3 new EventType values only
│   ├── quest.py                           # UNCHANGED (regression-tested)
│   ├── battle.py                          # UNCHANGED structurally; one-line hook inserted in
│   │                                      #     the battle-resolution code path that calls
│   │                                      #     adventure_hooks.on_battle_resolved(battle)
│   └── ... (all other legacy models unchanged)
├── routes/
│   ├── adventures/                        # NEW — blueprint package
│   │   ├── __init__.py                    # NEW — exports adventures_teacher_bp + adventures_student_bp
│   │   ├── teacher.py                     # NEW — /teacher/adventures/* routes
│   │   └── student.py                     # NEW — /student/adventures/* routes
│   └── ... (all legacy route files unchanged)
├── services/
│   ├── adventure_graph.py                 # NEW — DAG validation + unlock recomputation + snapshotting
│   ├── adventure_rewards.py               # NEW — atomic distribute_node_rewards + apply_node_consequences
│   ├── adventure_hooks.py                 # NEW — on_battle_resolved(battle), on_quiz_resolved(...)
│   └── ... (all legacy services unchanged)
├── forms/
│   └── adventure_schemas.py               # NEW — Pydantic BaseModel I/O schemas for all routes
├── templates/
│   ├── teacher/
│   │   ├── adventures_list.html           # NEW
│   │   ├── adventure_editor.html          # NEW
│   │   ├── adventure_assignments.html     # NEW
│   │   ├── adventure_progress.html        # NEW
│   │   └── ... (all legacy teacher templates unchanged)
│   └── student/
│       ├── adventures_list.html           # NEW
│       ├── adventure_map.html             # NEW
│       ├── _adventure_node_detail.html    # NEW partial reused by editor preview
│       ├── _student_header.html           # MODIFIED — additive nav link to /student/adventures
│       └── ... (all legacy student templates unchanged)
└── utils/                                 # unchanged

static/
├── js/
│   ├── adventure_editor.js                # NEW — pan/zoom, place/move, edge draw, autosave
│   └── adventure_player.js                # NEW — render map, click-to-open, action wiring
├── css/
│   ├── adventure_editor.css               # NEW
│   └── adventure_player.css               # NEW
└── images/
    ├── adventure_backgrounds/             # NEW — uploaded backgrounds, per-adventure
    └── adventure_node_icons/              # NEW — default icons per node_type

migrations/versions/
├── <ts>_add_adventure_tables.py           # NEW — creates 8 adventure tables + indexes + check constraints
└── <ts>_add_adventure_audit_event_types.py# OPTIONAL — only needed if EventType is enforced at DB level
                                           #     (audit_log.event_type is varchar in current schema, so
                                           #      this migration is documentary; verified in research R4)

tests/
├── test_adventure_models.py               # NEW — relationships, cascades, UNIQUE + CHECK constraints
├── test_adventure_graph_unlock.py         # NEW — unlock algorithm on fixture graphs
├── test_adventure_routes_teacher.py       # NEW — teacher endpoint coverage + auth scoping
├── test_adventure_routes_student.py       # NEW — student endpoint coverage + idempotency
├── test_adventure_rewards.py              # NEW — atomic distribution + conditional + consequences
├── test_quest_models.py                   # UNCHANGED — regression gate for legacy untouched
└── conftest.py                            # UNCHANGED — reused as-is

scripts/
└── check_adventure_graph_integrity.py     # NEW — orphan-node / unreachable-end / dangling-progress scanner

.cursor/rules/
├── database-structure.mdc                 # MODIFIED — append new tables + relationships per workspace rule
└── project-structure.mdc                  # UNCHANGED (the new code fits the existing structure)
```

**Structure Decision**: Use the existing single-app Flask layout (the project's canonical structure documented in `.cursor/rules/project-structure.mdc`). The feature adds two new model files, one new blueprint package (`app/routes/adventures/`), three new service modules, one new schemas file, eight new templates, four new static assets, two new migrations, and five new test files. Zero existing files are restructured or moved. The only legacy-touching edits are: (a) appending three values to `EventType` in `app/models/audit.py`, (b) adding a one-line `adventure_hooks.on_battle_resolved(battle)` call inside the existing battle-resolution code path, (c) appending nav links in `_student_header.html` and the teacher dashboard template, (d) updating `.cursor/rules/database-structure.mdc` to document the new tables per the workspace rule. All four are explicitly additive and have no observable effect on legacy quest behaviour, satisfying FR-036.

## Complexity Tracking

> No constitution violations were identified. This section is intentionally empty.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| *(none)*  | *(n/a)*    | *(n/a)*                             |
