# API Contracts — Adventures: Student Endpoints

**Feature**: 001-adventures-map-system
**Date**: 2026-05-22
**Blueprint**: `adventures_student_bp` (`url_prefix="/student/adventures"`)
**Auth**: All endpoints require `@login_required` with the student role (mirroring the existing `/student/*` blueprints, e.g. `app/routes/student_main.py` and `app/routes/student/battle.py`).

## Conventions

All endpoints use the same `{"success", "data", "errors"}` envelope and the same canonical error-code list as the teacher API (see `teacher-api.md` § Conventions). Student-specific errors are listed below.

### Student-specific error codes

| Code | HTTP | Meaning |
|---|---|---|
| `NOT_ASSIGNED` | 403 | The student is not assigned this adventure (directly, via class, or via clan). |
| `NODE_LOCKED` | 409 | The requested node is not currently available for this student. |
| `NODE_ALREADY_COMPLETED` | 200 (success path) | Repeated `/complete` call — service returns success with the existing completion data (idempotent). |
| `NODE_MAX_ATTEMPTS_REACHED` | 409 | The student has exceeded the configured retry limit for this node. |
| `ADVENTURE_NOT_STARTED_YET` | 409 | Current time is before `assignment.starts_at`. |
| `ADVENTURE_ENDED` | 409 | Current time is after `assignment.ends_at`. |
| `CHOICE_REQUIRED` | 400 | `/complete` was called on a choice node without `/choose` first. |

---

## Resource: Student adventure list

### `GET /student/adventures/`

List every adventure assigned to the calling student — directly, via their class, or via their clan — with a per-adventure progress summary.

**200 response data**:

```json
{
  "adventures": [
    {
      "id": 42,
      "title": "The Lost Library",
      "background_image_url": "/static/images/quest_maps/quest_map.png",
      "theme": "fantasy",
      "node_count": 12,
      "edge_count": 14,
      "my_progress": {
        "status": "in_progress",
        "current_node": { "id": 88, "slug": "wizard_riddle", "title": "The Wizard's Riddle" },
        "node_counts": { "completed": 4, "available": 1, "locked": 7, "failed": 0, "skipped": 0 },
        "started_at": "2026-05-21T16:00:00Z",
        "last_active_at": "2026-05-22T15:08:00Z"
      },
      "assignment": {
        "id": 31,
        "starts_at": "2026-06-01T00:00:00Z",
        "ends_at": "2026-08-31T23:59:59Z",
        "window_status": "not_started_yet"
      }
    }
  ]
}
```

`assignment.window_status` is one of:
- `active` — current time is between `starts_at` and `ends_at` (or both are null).
- `not_started_yet` — current time is before `starts_at`.
- `ended` — current time is after `ends_at`.

---

## Resource: Adventure map page

### `GET /student/adventures/<int:adventure_id>`

Returns the HTML player page (Jinja template `student/adventure_map.html`). The page hydrates client state via the JSON endpoint below.

**Authorisation**: caller is assigned this adventure (any of the three channels). 403 `NOT_ASSIGNED` otherwise.

---

### `GET /student/adventures/<int:adventure_id>/state`

JSON snapshot drives the client renderer.

**200 response data**:

```json
{
  "adventure": {
    "id": 42,
    "title": "The Lost Library",
    "background_image_url": "/static/images/quest_maps/quest_map.png",
    "theme": "fantasy",
    "width": 2000,
    "height": 1500,
    "version": 3,
    "end_semantics": "all"
  },
  "nodes": [
    {
      "id": 86, "slug": "start", "node_type": "start", "title": "Begin",
      "x": 100, "y": 100, "is_optional": false, "is_start": true, "is_end": false,
      "icon_url": null
    },
    {
      "id": 88, "slug": "wizard_riddle", "node_type": "quiz", "title": "The Wizard's Riddle",
      "x": 540, "y": 320, "is_optional": false, "is_start": false, "is_end": false,
      "icon_url": null,
      "description": "...", "lore": "..."
    }
  ],
  "edges": [
    {
      "id": 1, "from_node_id": 86, "to_node_id": 87,
      "label": null, "condition_type": "always", "condition_data": {},
      "unlock_semantics": "and", "sort_order": 0
    }
  ],
  "my_progress": {
    "adventure_status": "in_progress",
    "current_node_id": 88,
    "started_at": "2026-05-21T16:00:00Z",
    "last_active_at": "2026-05-22T15:08:00Z",
    "nodes": [
      { "node_id": 86, "status": "completed", "attempts": 1, "score": null,
        "choice_made": null, "started_at": "...", "completed_at": "..." },
      { "node_id": 87, "status": "completed", "attempts": 1, "score": null,
        "choice_made": null, "started_at": "...", "completed_at": "..." },
      { "node_id": 88, "status": "available", "attempts": 0, "score": null,
        "choice_made": null, "started_at": null, "completed_at": null }
    ]
  },
  "assignment": {
    "id": 31,
    "starts_at": null,
    "ends_at": null,
    "window_status": "active"
  }
}
```

The `nodes` list reflects the version pinned by the assignment (per snapshot strategy R2). When the assignment row's `adventure_version` differs from `adventures.version`, the student continues to see the pinned version (v1 behaviour) — see data-model.md "Cross-cutting invariants" #5 for the v1 limitation.

**Errors**: `NOT_ASSIGNED`, `ADVENTURE_NOT_STARTED_YET`, `ADVENTURE_ENDED`.

---

## Resource: Node detail (read-only)

### `GET /student/adventures/<int:adventure_id>/nodes/<slug>`

Returns one node's payload including rewards visible to the student (so they can decide whether to attempt it).

**200 response data**:

```json
{
  "node": {
    "id": 88, "slug": "wizard_riddle", "node_type": "quiz", "title": "The Wizard's Riddle",
    "description": "Answer three riddles to prove your wit.",
    "lore": "An old wizard greets you.",
    "completion_rules": { "min_score_percent": 80, "max_attempts": 3 },
    "rewards_preview": [
      { "type": "experience", "amount": 150, "is_conditional": false },
      { "type": "gold", "amount": 50, "is_conditional": false },
      { "type": "badge", "badge_id": 12, "badge_name": "Riddle Master",
        "is_conditional": true, "condition_summary": "Score 100%." }
    ],
    "consequences_preview": [
      { "description": "Drained by the puzzle.", "xp_penalty": 25, "gold_penalty": 10, "hp_penalty": 0 }
    ],
    "my_progress": { "status": "available", "attempts": 0, "score": null }
  },
  "outgoing_choices": null
}
```

For a choice node:

```json
"outgoing_choices": [
  { "choice_key": "left",  "label": "Trust the wizard" },
  { "choice_key": "right", "label": "Walk away" }
]
```

---

## Resource: Node lifecycle (mutating)

All four mutating endpoints below are **idempotent** in the strong sense — repeating the same call against the same final state returns the same response without side effects. This is the explicit FR-033 contract and the implementation is documented in research.md (R11).

### `POST /student/adventures/<int:adventure_id>/nodes/<slug>/start`

Marks the node as `in_progress`, increments `attempts`. For battle/quiz nodes, also creates the verification artifact and returns a redirect URL.

**Request body**: empty.

**200 response data — story/reward/milestone/end node**:

```json
{ "node": { "id": 88, "slug": "...", "status": "in_progress", "attempts": 1 } }
```

**200 response data — battle node**:

```json
{
  "node": { "id": 87, "slug": "goblin", "status": "in_progress", "attempts": 1 },
  "redirect_url": "/student/battle/12345",
  "battle_id": 12345
}
```

**200 response data — quiz node**:

```json
{
  "node": { "id": 88, "slug": "wizard_riddle", "status": "in_progress", "attempts": 1 },
  "redirect_url": "/student/adventures/42/nodes/wizard_riddle/quiz"
}
```

**200 response data — choice node**:

```json
{
  "node": { "id": 90, "slug": "trust_wizard", "status": "in_progress", "attempts": 1 },
  "outgoing_choices": [
    { "choice_key": "left",  "label": "Trust the wizard" },
    { "choice_key": "right", "label": "Walk away" }
  ]
}
```

**Errors**: `NODE_LOCKED` (the node is not currently `available` for this student), `NODE_MAX_ATTEMPTS_REACHED`.

---

### `POST /student/adventures/<int:adventure_id>/nodes/<slug>/complete`

Completes the node. Only valid for nodes that complete without external verification — `story`, `reward`, `milestone`, `end`. For `battle` nodes, completion is propagated by `adventure_hooks.on_battle_resolved`. For `quiz` nodes, the dedicated quiz endpoint (below) drives completion. For `choice` nodes, use `/choose`.

**Request body**: empty.

**200 response data**:

```json
{
  "node": { "id": 88, "slug": "wizard_riddle", "status": "completed", "attempts": 1, "score": null,
            "started_at": "...", "completed_at": "..." },
  "rewards_distributed": [
    { "type": "experience", "amount": 150 },
    { "type": "gold", "amount": 50 }
  ],
  "next_unlocked": [
    { "id": 90, "slug": "trust_wizard", "title": "Trust the wizard?", "node_type": "choice" }
  ],
  "adventure_complete": false
}
```

**Idempotency contract**: a second call when the node is already `completed` returns 200 with the same `node`/`rewards_distributed`/`next_unlocked` payload — `rewards_distributed` reflects what was distributed *the first time*, NOT a re-distribution.

**Errors**: `NODE_LOCKED`, `CHOICE_REQUIRED` (called on a choice node).

---

### `POST /student/adventures/<int:adventure_id>/nodes/<slug>/choose`

For `choice` nodes only. Records the student's selection, completes the node, propagates unlocks only along the matching outbound edges.

**Request body**:

```json
{ "choice_key": "left" }
```

`choice_key` must match an outgoing edge's `condition_data.choice_key` on this node.

**200 response data**: same shape as `/complete` plus `choice_made`:

```json
{
  "node": { "id": 90, "slug": "trust_wizard", "status": "completed", "choice_made": "left",
            "attempts": 1, "started_at": "...", "completed_at": "..." },
  "rewards_distributed": [],
  "next_unlocked": [
    { "id": 91, "slug": "ally_village", "title": "Ally village", "node_type": "story" }
  ],
  "adventure_complete": false
}
```

**Idempotency contract**: a second `/choose` with the **same** `choice_key` is a no-op (returns the previous state). A second `/choose` with a **different** `choice_key` after the first one already locked in is rejected with `CONFLICT` (`code: "CHOICE_ALREADY_MADE"`).

**Errors**: `NODE_LOCKED`, `VALIDATION_ERROR` (unknown `choice_key`), `CONFLICT` (`CHOICE_ALREADY_MADE`).

---

### `POST /student/adventures/<int:adventure_id>/nodes/<slug>/retry`

Resets a `failed` node back to `available` provided the retry budget allows it.

**Request body**: empty.

**200 response data**:

```json
{ "node": { "id": 87, "slug": "goblin", "status": "available", "attempts": 2, "score": null } }
```

**Idempotency contract**: calling `/retry` on a node that is already `available` returns the same state (no-op).

**Errors**: `NODE_LOCKED` (not in `failed` state), `NODE_MAX_ATTEMPTS_REACHED`.

---

## Resource: Quiz (dedicated quiz pipeline — R8)

### `GET /student/adventures/<int:adventure_id>/nodes/<slug>/quiz`

HTML page that renders the question set for a quiz node. Requires the node to be in `in_progress` status (set by `/start`).

### `POST /student/adventures/<int:adventure_id>/nodes/<slug>/quiz/submit`

Submits answers, computes score, calls the same atomic completion path as `/complete`.

**Request body**:

```json
{ "answers": { "1": "B", "2": "A", "3": "C" } }
```

**200 response data** (passed `min_score_percent`):

```json
{
  "node": { "id": 88, "slug": "wizard_riddle", "status": "completed", "score": 92,
            "attempts": 1, "started_at": "...", "completed_at": "..." },
  "rewards_distributed": [
    { "type": "experience", "amount": 150 },
    { "type": "gold", "amount": 50 }
  ],
  "conditional_rewards_distributed": [],
  "next_unlocked": [{ "id": 90, "slug": "trust_wizard", "title": "Trust the wizard?" }],
  "adventure_complete": false
}
```

**200 response data** (failed `min_score_percent`, attempts remain):

```json
{
  "node": { "id": 88, "slug": "wizard_riddle", "status": "failed", "score": 60,
            "attempts": 1, "started_at": "...", "completed_at": null },
  "rewards_distributed": [],
  "next_unlocked": []
}
```

**200 response data** (failed `min_score_percent`, max attempts reached — consequences applied once):

```json
{
  "node": { "id": 88, "slug": "wizard_riddle", "status": "failed", "score": 50,
            "attempts": 3, "started_at": "...", "completed_at": null },
  "rewards_distributed": [],
  "consequences_applied": [
    { "xp_penalty": 25, "gold_penalty": 10, "hp_penalty": 0, "description": "Drained by the puzzle." }
  ],
  "next_unlocked": [],
  "adventure_blocked": false
}
```

`adventure_blocked` is `true` when the failed node is non-optional AND the adventure can no longer satisfy its `end_semantics` rule. In that case, the student is shown a message and the teacher's progress view surfaces the block so they can use the force-complete override (FR-021).

---

## Battle integration (R3) — informational

There is no student-facing Adventures endpoint for completing battles. The existing battle pipeline calls `adventure_hooks.on_battle_resolved(battle)` as part of its commit. The hook:

1. Reads `battle.metadata` (or a dedicated `battle.adventure_node_id` field added in the hook migration) to find the bound node.
2. If absent, returns immediately (no-op).
3. If present, calls `adventure_rewards.distribute_node_rewards(...)` and `adventure_graph.recompute_unlocks_for_character(...)` with `commit=False`, so all the side effects flush in the battle's own transaction.

This means a student who completes a battle bound to an adventure node:
- Sees their normal battle-results screen (no change).
- On returning to the adventure map (`GET /state` or a websocket-less periodic refresh), sees the node now `completed` and downstream nodes unlocked.

---

## Authorisation summary (per FR-040)

| Action | Allowed when |
|---|---|
| List adventures | Always (returns empty list if none assigned). |
| Read adventure / state / node detail | An active assignment exists (direct, class, or clan) AND `window_status='active'` — except for read-only state which is allowed in `ended` so students can review their history. |
| Mutate (`start`, `complete`, `choose`, `retry`, `quiz/submit`) | Assignment exists AND `window_status='active'` AND node lifecycle preconditions met. |

All checks live in a single `_authorise_student(student, adventure, action)` helper in `adventure_graph.py`.

---

## Performance contract

| Endpoint | SLA |
|---|---|
| `GET /student/adventures/<id>/state` | ≤ 2 s end-to-end (SC-003). Single grouped query for nodes + edges + progress; no N+1. |
| `POST .../complete` / `/choose` / `/quiz/submit` | ≤ 2 s end-to-end including reward distribution and unlock recomputation (SC-004). |
| `GET /student/adventures/` | ≤ 2 s for up to 30 assigned adventures. |
