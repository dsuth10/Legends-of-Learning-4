# Quickstart — Adventures Quest Map System

**Feature**: 001-adventures-map-system
**Date**: 2026-05-22
**Audience**: any developer picking up an Adventures implementation slice (Phase 1 onward) and wanting to run the feature end-to-end locally.

This document is a developer's recipe for getting the Adventures feature running on a fresh checkout, then walking the User Story 1 (P1) flow as a smoke test. It does NOT duplicate the spec, plan, research, data-model, or contracts — for "why?" questions read those documents in this folder.

---

## 1. Prerequisites

| Tool | Version | Notes |
|---|---|---|
| Python | 3.8+ | matches the project constitution |
| pip | latest | for `pip install -r requirements.txt` |
| Git | any | feature branch `001-adventures-map-system` |
| SQLite | bundled with Python | for `instance/legends.db` |
| Browser | Chrome / Firefox / Edge / Safari, ES2017+ | for the editor / player |

No Node, no React, no build pipeline. (Per research decision R1.)

---

## 2. First-time setup

```bash
# from repo root
python -m venv .venv
source .venv/Scripts/activate   # Windows Git Bash; use ".venv/bin/activate" on macOS/Linux
pip install -r requirements.txt -r requirements-dev.txt

# (re)create the dev DB from migrations — including the new adventures migration
rm -f instance/legends.db
alembic upgrade head
```

If `alembic upgrade head` reports anything other than "Reached head", **stop and fix it before continuing** (see `.cursor/rules/database-management.mdc`).

### Migration caveats (Phase 2 — `001_adventure_tables`)

- **Revision chain**: `001_adventure_tables` revises `b1c2d3e4f5a6` (the behavior-system seed migration). On a DB already at `b1c2d3e4f5a6`, `alembic upgrade head` adds the eight Adventures tables in one step.
- **Fresh test DBs**: pytest's `conftest.py` may stamp `001_adventure_tables` directly when an intermediate legacy migration fails on empty SQLite (known pre-existing Alembic ordering issue with `d4b3c2a1f0e9`). Adventure tables are still created via `db.create_all()` fallback; this does not affect production upgrades from a fully migrated `instance/legends.db`.
- **No audit DDL**: the three new `EventType` values (`ADVENTURE_NODE_START`, `ADVENTURE_NODE_COMPLETE`, `ADVENTURE_COMPLETE`) are application-level only; `audit_log.event_type` remains `VARCHAR(50)`.
- **Verify after upgrade**:

```bash
sqlite3 instance/legends.db "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'adventure%' OR name LIKE 'character_%progress' OR name LIKE 'node_%';"
python -m pytest tests/test_adventure_models.py tests/test_adventure_graph_unlock.py tests/test_adventure_rewards.py -q
```

### Migration `002_battle_adventure_node` (Phase 3 — US1)

- Adds nullable `battles.adventure_node_id` FK → `adventure_nodes.id` so adventure-bound battles persist across fight requests and `on_battle_resolved` can complete the correct node.
- Run after `001_adventure_tables`: `alembic upgrade head`.

### Phase 3 test results (2026-05-22)

| Suite | Result |
|---|---|
| `pytest tests/test_adventure_routes_teacher.py tests/test_adventure_routes_student.py tests/test_adventure_rewards.py -v` | **13 passed** |
| `pytest tests/test_quest_models.py -v` | **31 passed, 1 failed** (`TestQuest::test_quest_availability` — pre-existing `TypeError` on datetime comparison; unrelated to Adventures) |

MVP API smoke (automated): teacher creates/publishes/assigns a linear adventure; student lists, loads state, starts/completes start and end nodes; idempotent `/complete` verified.

### Final phase test results (2026-05-22)

| Suite | Result |
|---|---|
| `pytest tests/test_adventure_models.py tests/test_adventure_graph_unlock.py tests/test_adventure_routes_teacher.py tests/test_adventure_routes_student.py tests/test_adventure_rewards.py -v` | **55 passed** |
| `pytest tests/test_quest_models.py -v` | **31 passed, 1 failed** (same pre-existing `test_quest_availability`; unrelated to Adventures) |
| `pytest -q` (full suite) | **203 passed, 2 failed** (pre-existing: `test_class_capacity`, `test_quest_availability`; neither Adventures-related) |
| `python scripts/check_adventure_graph_integrity.py` | **OK** (no issues on empty/clean DB) |

Polish deliverables in this phase:
- Graph integrity scanner: `scripts/check_adventure_graph_integrity.py`
- Background upload hardening: MIME + extension + magic-byte sniff + size cap in `app/routes/adventures/teacher.py`
- Accessibility: ARIA labels, roles, keyboard hints on editor/player templates and JS
- Performance guards: sublinear teacher progress roster queries; bounded student `/state` query count
- Database docs: Adventures tables added to `.cursor/rules/database-structure.mdc`

Automated smoke checklist (Section 8):

- [x] `alembic upgrade head` reports "Reached head" (production DB path; see migration caveats for pytest fallback).
- [x] Adventure route/reward/model tests pass (`55 passed`).
- [x] `pytest tests/test_quest_models.py` — 31/32 pass; 1 pre-existing failure unchanged from Phase 3.
- [x] Integrity scanner runs clean on a fresh DB.
- [ ] Manual steps 4.2–4.3 (browser smoke) — run locally after `python run.py`.
- [ ] Teacher progress view manual check — run locally after seed + assignment.

---

## 3. Running the app

```bash
python run.py
```

The Flask dev server should come up on `http://127.0.0.1:5000`. The two new routes mounted by this feature are:

- `http://127.0.0.1:5000/teacher/adventures/`
- `http://127.0.0.1:5000/student/adventures/`

If either returns 404, check that the Adventures blueprints are registered in `app/routes/__init__.py`:

```python
from app.routes.adventures import adventures_teacher_bp, adventures_student_bp
# ...
app.register_blueprint(adventures_teacher_bp)
app.register_blueprint(adventures_student_bp)
```

---

## 4. Smoke test — User Story 1 (P1) end-to-end

This is the **independent test** named in the spec for US-1. Completing this smoke means the MVP loop works on your machine.

### 4.1 Seed a teacher, a class, and a few students

```bash
# Use the existing seed CLI (already wired in app/commands.py)
flask --app run:app seed-db
```

This creates:
- A teacher account (default credentials in `.env.example` — typically `teacher@example.com` / `password`).
- One classroom with three test students and their characters.

Verify with:

```bash
# Open the SQLite DB and confirm:
sqlite3 instance/legends.db "SELECT id, email, role FROM users LIMIT 5;"
sqlite3 instance/legends.db "SELECT id, name FROM classrooms LIMIT 3;"
sqlite3 instance/legends.db "SELECT id, name FROM students LIMIT 5;"
```

### 4.2 Author a 3-node linear adventure (teacher)

1. Log in as the teacher.
2. In the sidebar, click **Adventures** (the new nav entry added by this feature). You should land at `/teacher/adventures/`.
3. Click **New Adventure**, give it a title (e.g. "Smoke Test"), accept the default fantasy background, then click **Create**.
4. In the editor (`/teacher/adventures/<id>/edit`):
   - Click the **Start** node type in the toolbar, then click the left side of the map. A start node appears.
   - Click the **Battle** node type, then click the middle of the map. A battle node appears.
   - In the inspector for the new battle node, pick any seeded `Monster` from the dropdown.
   - Click the **End** node type, then click the right side of the map.
   - Connect start → battle and battle → end by Shift-dragging from one node to the next (or use the "connect" toggle).
   - Click **Save** (it should also be auto-saving every 5 s).
5. Click **Publish**. The validation panel should report ✓ for all checks.
6. Click **Assign**, pick your test classroom, leave dates blank, **Confirm**.

Expected: the adventure now shows `status: published`, version 1, and one active assignment. The classroom's students can see it.

### 4.3 Play through as a student

1. Log out, log in as one of the seeded students (`student1@example.com` / `password` — see `app/commands.py` for actuals).
2. In the sidebar, click **Adventures**. The list should show "Smoke Test" with `not_started` progress.
3. Click "Smoke Test". The map page loads with the start node showing the "available" visual state and the other two locked.
4. Click the start node → detail panel opens → click **Begin** (or whatever the start-action label is). Node transitions to `completed`; the battle node unlocks (visually changes from locked to available).
5. Click the battle node → detail panel → click **Enter Battle**. You are redirected to the existing battle flow. Win the battle.
6. On returning to the adventure map (or refreshing it), the battle node is `completed`, rewards have landed on the character (check `/student/character` for XP/gold deltas), and the end node is now `available`.
7. Click the end node → click **Finish**. Adventure status flips to `completed`. A completion banner shows.

If all the above happens without console errors and without legacy quest UI changing, the MVP smoke is green.

### 4.4 Verify legacy quest system is untouched (FR-036)

Critical regression check.

```bash
pytest tests/test_quest_models.py -v
```

This file is **not modified** by the feature. It must pass unchanged. If anything in it fails, FR-036 is violated and the change must be reverted/fixed before merge.

---

## 5. Running the full test suite

```bash
pytest -q
```

Specifically, the new test files added by this feature:

```bash
pytest tests/test_adventure_models.py \
       tests/test_adventure_graph_unlock.py \
       tests/test_adventure_routes_teacher.py \
       tests/test_adventure_routes_student.py \
       tests/test_adventure_rewards.py -v
```

All must pass before any Adventures slice is considered done (see plan.md Constitution gate G-2 and `.cursor/rules/database-management.mdc`).

---

## 6. Useful one-liners

### Dump the adventure graph for an adventure id

```bash
sqlite3 instance/legends.db "
  SELECT n.slug, n.node_type, n.x, n.y, n.is_start, n.is_end
    FROM adventure_nodes n
   WHERE n.adventure_id = 1
   ORDER BY n.id;
"
sqlite3 instance/legends.db "
  SELECT e.from_node_id, e.to_node_id, e.condition_type, e.unlock_semantics
    FROM adventure_edges e
   WHERE e.adventure_id = 1
   ORDER BY e.id;
"
```

### Run the integrity scanner (Phase 1+)

```bash
python scripts/check_adventure_graph_integrity.py
```

Surfaces:
- Orphan non-optional nodes.
- End-flagged nodes unreachable from any start.
- `character_node_progress` rows pointing at deleted nodes.
- `character_adventure_progress.current_node_id` rows pointing at deleted nodes.

### Reset only adventure data, keep legacy data

```bash
sqlite3 instance/legends.db "
  DELETE FROM character_node_progress;
  DELETE FROM character_adventure_progress;
  DELETE FROM adventure_assignments;
  DELETE FROM node_consequences;
  DELETE FROM node_rewards;
  DELETE FROM adventure_edges;
  DELETE FROM adventure_nodes;
  DELETE FROM adventures;
"
```

> Legacy `quests`, `quest_logs`, `rewards`, `consequences` tables remain untouched. Verify with a manual `SELECT count(*) FROM quests;` before and after if you want belt-and-braces proof of FR-036.

---

## 7. Where to find what

| Want to read about... | Look at |
|---|---|
| What we're building and why | `spec.md` |
| Decisions and trade-offs | `research.md` |
| Tables, columns, FKs, indexes, enums | `data-model.md` |
| HTTP/JSON contracts for the editor | `contracts/teacher-api.md` |
| HTTP/JSON contracts for the player | `contracts/student-api.md` |
| Phases / scope / project structure / constitution gates | `plan.md` |
| Running the thing | this file |
| Source roadmap (the deep dive) | `../../Ideas/Adventures Quest Map System - Roadmap.md` |

---

## 8. Definition of "Smoke OK"

The smoke is considered green for any given Adventures change if **all** of the following are true on a fresh clone:

- [x] `alembic upgrade head` reports "Reached head" (see migration caveats for pytest).
- [ ] `python run.py` starts cleanly with no template/Jinja errors (manual).
- [ ] Steps 4.2–4.3 above complete without console or server errors (manual browser smoke).
- [x] `pytest tests/test_quest_models.py` — 31/32 pass; 1 pre-existing failure (`test_quest_availability`) unchanged and unrelated to Adventures.
- [x] `pytest tests/test_adventure_*.py` — **55 passed** (2026-05-22 final phase run).
- [ ] The student character's XP and gold reflect the configured rewards after node completion (manual).
- [ ] The teacher progress view (`/teacher/adventures/<id>/progress`) shows the smoke-test student transitioning through `not_started → in_progress → completed` (manual).
- [x] `python scripts/check_adventure_graph_integrity.py` reports OK on a clean DB.
