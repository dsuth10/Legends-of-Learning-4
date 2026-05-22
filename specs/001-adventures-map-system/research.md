# Phase 0 — Research & Decisions: Adventures Quest Map System

**Feature**: 001-adventures-map-system
**Date**: 2026-05-22
**Owner**: implementation team
**Status**: Decisions finalised; no NEEDS CLARIFICATION items remain.

This document records every design decision required to start Phase 1 of the Adventures feature. Each decision lists the choice taken, the reason it was chosen, and the alternatives that were evaluated and rejected. All open questions from the source roadmap and the Spec's Assumptions section have been resolved.

---

## R1 — Editor & Player frontend technology

**Decision**: **Vanilla JS + SVG + Tailwind utility classes** for both the teacher editor and the student map player.

**Rationale**:
- The existing project is server-rendered Flask + Jinja + Tailwind with no JS build pipeline. Introducing a React + bundler (Vite/esbuild) only for this feature would add a permanent operational burden and a new mental model to the codebase.
- The editor and player are both bounded in scope: place / move / connect / inspect / save (editor), render / hover / click / animate marker (player). All of these are tractable in 1–2 kLOC of plain JS each.
- The API surface is JSON-first (see `contracts/`), so if Phase 5+ ever requires a richer editor (auto-layout, mini-map fidelity, multi-select drag), only the editor page needs rewriting — the backend doesn't change.
- SVG is a natural fit for edges (cheap, sharp, easy to style with CSS), and absolutely-positioned `<div>`s on top of a background `<img>` are a natural fit for nodes.

**Alternatives considered**:
- **React Flow**. Excellent DX, drag/zoom/edge routing/mini-map all built in. Rejected because it forces a JS build pipeline, a Node toolchain in CI, and a React mental model that no other page in the project uses.
- **JointJS**. Mature diagramming library, no React dependency. Rejected because its API surface is large, styling it to match Tailwind requires substantial CSS overrides, and its commercial-friendly license has caveats worth not introducing for a v1.
- **Cytoscape.js**. Powerful graph-layout library. Rejected because it is overkill for ≤ 100 nodes and its built-in styling is opinionated and clashes with the Tailwind look.

**Escape hatch**: The contract between server and client is purely JSON (`GET /teacher/adventures/<id>/graph`, `GET /student/adventures/<id>/state`). If Phase 2 reveals that hand-rolled SVG edge routing is painful, the editor page alone can be migrated to React Flow without touching anything else.

---

## R2 — Snapshot strategy (mid-flight stability, FR-039, US-5)

**Decision**: **Version pinning on assignment** for v1. Each `adventure_assignment` row records the `adventure_version` at the moment of assignment. Each per-character progress row references that assignment. Mid-flight teacher edits bump `adventures.version` but DO NOT bump existing assignments' pinned version; new assignments capture the new version.

A nullable `snapshot_json` column is included on `character_adventure_progress` from day 1 (DDL is cheap to add now and impossible to add cleanly later). It is left NULL in v1. Phase 4 of the feature roadmap can populate it with a full JSON snapshot of `{nodes, edges}` if version-pinning proves insufficient (e.g. if teachers regularly edit live and we observe student-visible drift in spite of pinning).

**Rationale**:
- Simplest model that passes US-5 acceptance scenarios: in-progress students see the version they started on; new students see the latest.
- No duplicated structural data in v1 — keeps the schema lean.
- DDL-now, populate-later is much cheaper than altering tables once they have prod rows.

**Alternatives considered**:
- **Full JSON snapshot per character at start**. Strongest correctness guarantee but doubles write volume and storage on every adventure start, with no observed need yet.
- **Schema-level versioned tables (`adventure_nodes_v1`, `_v2` ...)**. Hugely over-engineered; rejected immediately.
- **No snapshot at all**. Rejected — would silently corrupt in-progress students on any teacher edit, violating FR-039.

---

## R3 — Battle / quiz completion propagation to nodes

**Decision**: **Explicit one-line hook** in the existing battle-resolution code path: `adventure_hooks.on_battle_resolved(battle)`. The hook is a no-op when the battle is not bound to an adventure node. The same pattern applies to quiz nodes via `adventure_hooks.on_quiz_resolved(...)` once the quiz pipeline reaches the equivalent resolution point.

**Rationale**:
- Atomic with the battle's own commit — no race window between "battle won" and "node completed".
- Single, narrow, audited legacy edit (one call), which the spec explicitly permits as the only legacy seam.
- Trivially testable — the hook returns immediately for unbound battles, so legacy tests are not perturbed.

**Alternatives considered**:
- **Polling on student page load**. Simpler but laggy (student would refresh and *then* see the node complete and rewards arrive). Also forces idempotency complexity into a different layer. Rejected.
- **Database trigger on `battles` table**. Couples ORM behaviour to DB-vendor-specific trigger semantics. Rejected to keep the project portable across SQLite (dev) and Postgres-like backends in the future.
- **Celery / background job**. No async infrastructure exists in the project today. Rejected for v1.

---

## R4 — Audit log integration (FR-038)

**Decision**: Add three new application-level `EventType` enum values to `app/models/audit.py`:
- `ADVENTURE_NODE_START`
- `ADVENTURE_NODE_COMPLETE`
- `ADVENTURE_COMPLETE`

Update the `EVENT_TYPES` dict in the same module to register them. No schema migration is required because `audit_log.event_type` is a `VARCHAR(50)` with application-level validation only.

**Rationale**:
- Cleanest, smallest possible change. The existing `AuditLog.log_event(EventType.X, event_data=..., user_id=..., character_id=..., commit=False)` API already supports flush-with-current-transaction (via `commit=False`), which is exactly what `adventure_rewards.distribute_node_rewards` needs to remain atomic.
- Event payload is JSON, so we can record adventure_id, node_id, node_slug, node_type, score, attempts, rewards distributed, and `next_unlocked` (see Appendix B.4 of the source roadmap) without any schema change.

**Alternatives considered**:
- **Separate `adventure_audit_log` table**. Splits audit data; complicates cross-system reporting. Rejected.
- **Promote `event_type` to a DB-level enum**. Forces a migration on legacy data and removes the easy-extension property. Rejected.

---

## R5 — JSON response envelope shape

**Decision**: Use the project constitution's mandated shape: `{"success": bool, "data": object|null, "errors": [{"code": str, "message": str}, ...]}`.

**Rationale**:
- The project constitution at `/constitution.md` explicitly defines this shape under "API Patterns" and is the binding standard. Consistency across the codebase matters more than the slightly more compact `{"ok": true}` shape suggested in the source roadmap.
- All Pydantic response models in `app/forms/adventure_schemas.py` will inherit from a small `ApiResponse[T]` base that enforces this shape.

**Alternatives considered**:
- The roadmap-suggested `{"ok": true, "data": ..., "errors": [...]}` shape. Rejected because it would introduce inconsistency with the rest of the API surface and violate the constitution. Migrating the entire project to a new shape is out of scope.

---

## R6 — DAG unlock semantics (FR-012, FR-032)

**Decision**: Per-edge `unlock_semantics` column with values `and` (default) / `or`. When recomputing unlocks for a target node:

1. Fetch all inbound edges to that node.
2. Partition them into the AND group (all edges with `unlock_semantics = 'and'`) and the OR group (all edges with `unlock_semantics = 'or'`).
3. The node unlocks iff (every edge in the AND group has its source node completed AND its edge condition satisfied) AND (the OR group is empty OR at least one edge in the OR group has its source node completed AND its edge condition satisfied).
4. Edge "condition satisfied" rules: `always` → true; `choice` → the source node's `choice_made` equals `condition_data.choice_key`; `criteria` → the source node's `score` / `progress_data` satisfies `condition_data` (e.g. `min_score_percent >= 80`).

**Rationale**:
- Per-edge OR/AND is the simplest mechanism that supports re-join nodes after a branch: the two re-converging branches each get `or` semantics, while any extra "must also have done the side quest" inbound stays `and`.
- Default `and` matches teacher intuition for a linear chain (every prerequisite must be done).
- The (AND-all + OR-any) split is robust to mixed groups and avoids the ambiguity of a single boolean per node.

**Alternatives considered**:
- **A single `unlock_mode` on the *node*** (`all` vs `any`). Cleaner per-node but blocks mixed semantics — e.g. "must complete A AND (B OR C)". Rejected.
- **Boolean expression DSL on the node**. Over-engineered for the use cases observed in the spec.
- **Always AND**. Rejected — explicitly forbids the re-join pattern that US-2 (P2) requires.

---

## R7 — End-of-adventure completion semantics

**Decision**: Per-Adventure configurable: `adventures.end_semantics` ENUM(`all`, `any`), default `all`. "Adventure complete" means:
- `all`: every non-optional `is_end=True` node is completed.
- `any`: any one `is_end=True` node is completed.

**Rationale**:
- The source roadmap's Open Question #2 recommended this; the spec adopted "all non-optional end nodes" as the default and allowed a per-Adventure switch. This decision codifies it.
- Authoring UI exposes a single dropdown on the Adventure settings panel.

**Alternatives considered**:
- **Hard-coded `all`**. Rejected — narratively-branching adventures sometimes want "any one true ending counts".
- **Hard-coded `any`**. Rejected — defeats teachers who want a "must complete every path" guarantee.

---

## R8 — Quiz node implementation

**Decision**: **Option Q2 — direct quiz route, not via Battle.** Quiz nodes link to a `question_set_id` and are resolved through a new student route `/student/adventures/<id>/nodes/<slug>/quiz` that renders questions, accepts answers, scores, and posts to `/complete` with the score.

**Rationale**:
- Cleaner mental model: a quiz is not a fight.
- Avoids creating phantom `Battle` rows for quiz attempts, which would pollute battle analytics.
- The shared scoring code is small and lives in `app/services/adventure_quiz.py` (a thin wrapper around the existing question-set utilities, no new logic).

**Alternatives considered**:
- **Option Q1 — reuse Battle pipeline with `question_set_id`**. Acceptable as a Phase 3 fallback if the dedicated quiz path slips, but rejected as the long-term home because it conflates two different game concepts.

---

## R9 — Background image storage (Spec Assumption + Open Q #7)

**Decision**: Store uploaded backgrounds under `static/images/adventure_backgrounds/<adventure_id>/<filename>`. Seed/library images stay in their existing static paths (`static/images/quest_maps/`, `static/images/Backgrounds/Core Level Backgrounds/`).

Enforce upload constraints at the route layer:
- Max file size: 5 MB (configurable via env var, default 5 MB).
- MIME whitelist: `image/png`, `image/jpeg`, `image/webp`.
- Sanitised filename (strip path components, normalise extension).
- On reject: return HTTP 413 (Payload Too Large) or 400 with a friendly error message.

**Rationale**:
- Consistent with how every other image is served in this project (no behind-the-scenes file API or signed URLs).
- The `<adventure_id>` subfolder isolates uploads per adventure for easy cleanup on delete.
- Keeping it inside `static/` means no separate web-server configuration is needed in production.

**Alternatives considered**:
- **`instance/` folder**. Per-environment but not served by Flask's static handler by default; would require adding a custom route. Rejected for v1.
- **S3 / external object storage**. Out of scope for a v1 inside an existing single-host Flask app.

---

## R10 — Adventure visibility default (Spec Assumption + Open Q #1)

**Decision**: Adventures default to `is_public=False` (private to the authoring teacher). A teacher must explicitly toggle "share with other teachers in this school" to set `is_public=True`. Cross-school visibility is out of scope (per spec Out of Scope).

**Rationale**:
- Matches the recommendation from the source roadmap's Open Q #1 and the spec's Assumptions section.
- Avoids accidental cross-teacher visibility of incomplete drafts.

**Alternatives considered**: discussed in spec.

---

## R11 — Concurrency & idempotency (FR-033, edge cases for double-submit)

**Decision**: Idempotency is enforced inside the service layer via state-check + UPDATE-conditional-on-current-status, using a SQL transaction per request. Specifically:

- `complete_node(character, node)` does:
  1. `SELECT … FOR UPDATE` (or `BEGIN IMMEDIATE` on SQLite) on `character_node_progress` row.
  2. If status is already `completed`, return the existing state (no reward redistribution, no audit duplication).
  3. Otherwise, transition to `completed`, distribute rewards, recompute unlocks, log audit — all in the same transaction.
- `retry_node` is similarly guarded: only resets from `failed` (within retry budget) → `available`. A repeat `retry` call after the reset is a no-op.

**Rationale**:
- Mirrors the proven `Reward.distribute()` no-premature-commit pattern from `app/models/quest.py`.
- Simple, correct, transaction-scoped — no need for distributed locks or queues.

**Alternatives considered**:
- **Application-level Idempotency-Key header**. Standard but heavy for a per-classroom-scale system. Deferred.
- **Optimistic concurrency with version columns on every progress row**. Reasonable but more complex than the row-locking approach for an SQLite-and-Postgres-friendly v1.

---

## R12 — Cycles and self-loops

**Decision**:
- **Self-loops** (`from_node_id == to_node_id`) are rejected at the DB layer (`CHECK (from_node_id != to_node_id)`) and at the API layer (defensive guard, returns HTTP 400).
- **Cycles** (`A → B → A`) are allowed but produce a publish-time warning. Unlock recomputation tracks an in-call visited-set to prevent infinite recursion on revisit.

**Rationale**: Spec and source roadmap both call this out explicitly. Self-loops have no pedagogical use; cycles occasionally do (e.g. "revisit the village", although those are usually modelled as branched re-joins).

---

## R13 — Database engine / portability

**Decision**: Target SQLite for development (`instance/legends.db`, already in place) and any future Postgres-compatible engine in production. Avoid SQL features that don't work on both:

- Use `CHECK (from_node_id != to_node_id)` on `adventure_edges` (works on both).
- Use SQLAlchemy enums (Python-side validators + VARCHAR column on disk) rather than DB-native enum types.
- Avoid `SELECT … FOR UPDATE` syntactic constructs that vary between engines; instead, rely on SQLAlchemy's `with_for_update()` which gracefully degrades on SQLite.
- All DDL routed through Alembic.

**Rationale**: The project's `tests/conftest.py` already uses SQLite-on-disk for tests, and the production target is fully agnostic.

---

## R14 — Per-character UNIQUE constraints (preventing duplicate progress rows)

**Decision**:
- `character_adventure_progress`: `UNIQUE (character_id, adventure_id)` — a character has at most one "run" of a given Adventure. (Reassignment to a new class shouldn't create a duplicate row for the same character; if a character is in two classes both assigned the same Adventure, we deduplicate to the first.)
- `character_node_progress`: `UNIQUE (character_id, node_id)` — at most one progress row per character per node.

**Rationale**:
- Eliminates a whole class of "which row is canonical?" bugs.
- The cross-class-assignment case (the same Adventure assigned to Class A and Class B with a student in both) is a corner case explicitly handled by US-4 — the student gets one run, and progress is shared across both assignments (the second assignment is treated as a no-op for that character).

**Alternatives considered**:
- **`UNIQUE (character_id, adventure_id, assignment_id)`**. Would allow per-assignment progress rows, but introduces ambiguity about which one drives the player UI. Rejected.

---

## R15 — Migration sequencing & ordering

**Decision**: Adventure tables ship in **one** Alembic migration `<ts>_add_adventure_tables.py` that:
1. Creates `adventures`.
2. Creates `adventure_nodes` (FK → `adventures`).
3. Creates `adventure_edges` (FKs → `adventures`, `adventure_nodes` × 2, plus CHECK).
4. Creates `node_rewards` (FK → `adventure_nodes` and SET-NULL FKs into `equipment`, `abilities`, `achievement_badge`).
5. Creates `node_consequences` (FK → `adventure_nodes`).
6. Creates `adventure_assignments` (FKs → `adventures`, `classrooms`, `clans`, `characters`, `users`).
7. Creates `character_adventure_progress` (FKs → `characters`, `adventures`, `adventure_nodes`, `adventure_assignments`).
8. Creates `character_node_progress` (FKs → `characters`, `adventure_nodes`).

All indexes and CHECK constraints are part of the same migration. `down_revision` is the current head as of branching.

**Rationale**: All-in-one keeps the cognitive overhead low and `alembic upgrade head` deterministic in any environment. SQLite's CREATE TABLE happily takes the constraints inline; Postgres handles them identically.

---

## R16 — Naming alignment with existing models

**Decision**: Reuse existing naming conventions:

- Plural lowercase table names: `adventures`, `adventure_nodes`, etc. (matches `quests`, `characters`, `classrooms`, ...).
- Enum classes named in PascalCase (`NodeType`, `EdgeConditionType`, `UnlockSemantics`, `AdventureStatus`, `AdventureProgressStatus`, `NodeProgressStatus`, `RewardType` (re-exported with `BADGE` added), `EndSemantics`).
- Mirror the `RewardType` enum from `quest.py` (existing: `EXPERIENCE`, `GOLD`, `EQUIPMENT`, `ABILITY`, `CLAN_EXPERIENCE`, `SPECIAL_CURRENCY`) and add a new value `BADGE`.

**Rationale**: Onboarding new contributors is easier if the new domain "rhymes" with the existing one.

---

## R17 — Test data fixtures

**Decision**: Provide a small fixture factory in `tests/conftest.py` (or a new `tests/fixtures/adventure_factories.py` to avoid bloating `conftest.py`) that builds:

- A "linear-3-node" adventure (start → battle → end).
- A "branching-choice" adventure (start → quiz → choice → {left, right} → end).
- An "AND/OR re-join" adventure (start → A and B → C(AND) → D(OR-with-side) → end).
- An "optional side path" adventure (start → main → (optional reward) → end).
- A "cycle" adventure (start → A → B → A → end via flag).
- A "max-attempts failure" scenario.

These fixtures are reused across `test_adventure_graph_unlock.py`, `test_adventure_routes_student.py`, and `test_adventure_rewards.py`.

**Rationale**: Centralised fixtures avoid divergent test setup and keep coverage of the unlock algorithm tight and discoverable.

---

## Resolved open questions from spec / source roadmap

| Source-roadmap Q # | Question | Resolution |
|---|---|---|
| Q1 | Default visibility | Private; opt-in public (R10) |
| Q2 | End-node completion semantics | Configurable per Adventure, default `all` (R7) |
| Q3 | Clan-shared progress | Out of scope for v1 (spec Out of Scope) |
| Q4 | Snapshot strategy | Version pinning v1 + optional JSON snapshot column for later (R2) |
| Q5 | Editor frontend stack | Vanilla JS + SVG + Tailwind (R1) |
| Q6 | Max adventures per teacher | No soft cap (per spec assumption) |
| Q7 | Background upload storage | `static/images/adventure_backgrounds/<id>/` (R9) |
| Q8 | Non-chosen branch consequences | Out of scope for v1 (spec Out of Scope) |

**No NEEDS CLARIFICATION items remain.** Phase 1 (data model + contracts + quickstart) can begin.
