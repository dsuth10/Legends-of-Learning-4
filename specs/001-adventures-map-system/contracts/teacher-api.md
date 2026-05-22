# API Contracts — Adventures: Teacher Endpoints

**Feature**: 001-adventures-map-system
**Date**: 2026-05-22
**Blueprint**: `adventures_teacher_bp` (`url_prefix="/teacher/adventures"`)
**Auth**: All endpoints require `@login_required` + `@teacher_required` (Flask-Login session OR Flask-JWT-Extended bearer token, mirroring existing teacher routes). Ownership is enforced per endpoint as noted.

## Conventions

### Response envelope (constitution-mandated)

Every JSON response — success or failure — uses this shape:

```json
{
  "success": true,
  "data": { ... } | null,
  "errors": []
}
```

On error:

```json
{
  "success": false,
  "data": null,
  "errors": [
    { "code": "NODE_NOT_FOUND", "message": "Node 42 does not exist." }
  ]
}
```

### Error codes (canonical list)

| Code | HTTP | Meaning |
|---|---|---|
| `VALIDATION_ERROR` | 400 | Request body failed Pydantic validation. `errors[].message` contains field-level detail. |
| `AUTH_REQUIRED` | 401 | Missing/invalid session or JWT. |
| `FORBIDDEN` | 403 | Caller is not the owner / does not have permission. |
| `NOT_FOUND` | 404 | Target resource doesn't exist (or caller can't see it). |
| `CONFLICT` | 409 | State-machine collision (e.g. publish-with-validation-errors, slug already taken). |
| `PAYLOAD_TOO_LARGE` | 413 | Upload exceeds `MAX_BACKGROUND_UPLOAD_BYTES`. |
| `INTERNAL_ERROR` | 500 | Unhandled exception (logged server-side). |

### Pydantic schemas (live in `app/forms/adventure_schemas.py`)

All request and response payloads are validated by Pydantic v2 models. Discriminated unions are used for the `condition_data`-by-`condition_type` shape and the `reward.type`-by-required-FK shape.

---

## Resource: Adventure (teacher-side)

### `GET /teacher/adventures/`

List all adventures the teacher owns plus any `is_public=True` adventures owned by other teachers in the same school directory.

**Query params**:
- `status=draft|published|archived` (optional, repeatable)
- `mine=true|false` (optional, default true; set false to show only shared/public)
- `q=<string>` (optional, fuzzy title match)

**200 response data**:

```json
{
  "adventures": [
    {
      "id": 42,
      "title": "The Lost Library",
      "description": "...",
      "status": "published",
      "is_public": false,
      "version": 3,
      "owner": { "id": 7, "name": "Mr. Smith" },
      "node_count": 12,
      "edge_count": 14,
      "assignment_count": 2,
      "created_at": "2026-05-21T12:00:00Z",
      "updated_at": "2026-05-22T09:14:00Z"
    }
  ]
}
```

---

### `POST /teacher/adventures/`

Create a new draft adventure.

**Request body**:

```json
{
  "title": "The Lost Library",
  "description": "A mystery in three acts.",
  "background_image_url": "/static/images/quest_maps/quest_map.png",
  "theme": "fantasy",
  "width": 2000,
  "height": 1500,
  "end_semantics": "all"
}
```

All fields except `title` are optional (sensible defaults applied).

**201 response data**:

```json
{ "adventure": { "id": 42, "title": "...", "status": "draft", "version": 1, ... } }
```

**Errors**: `VALIDATION_ERROR` (e.g. title empty).

---

### `GET /teacher/adventures/<int:adventure_id>`

Read-only summary. Authorisation: teacher must own OR adventure is `is_public=True`.

**200 response data**: same shape as the per-item shape in the list endpoint.

---

### `GET /teacher/adventures/<int:adventure_id>/graph`

Returns the full graph for the editor: adventure + nodes + edges + rewards + consequences.

**200 response data**:

```json
{
  "adventure": { /* full adventure object */ },
  "nodes": [
    {
      "id": 88,
      "slug": "wizard_riddle",
      "title": "The Wizard's Riddle",
      "description": "...",
      "lore": "...",
      "icon_url": null,
      "node_type": "quiz",
      "x": 540.0,
      "y": 320.0,
      "is_optional": false,
      "is_start": false,
      "is_end": false,
      "question_set_id": 7,
      "monster_id": null,
      "completion_rules": { "min_score_percent": 80, "max_attempts": 3 },
      "on_complete_actions": {},
      "rewards": [
        { "id": 1, "type": "experience", "amount": 150, "is_conditional": false, "condition_json": {} }
      ],
      "consequences": [
        { "id": 1, "xp_penalty": 25, "gold_penalty": 10, "hp_penalty": 0, "description": "Drained by the puzzle." }
      ]
    }
  ],
  "edges": [
    {
      "id": 1,
      "from_node_id": 86,
      "to_node_id": 87,
      "label": null,
      "condition_type": "always",
      "condition_data": {},
      "unlock_semantics": "and",
      "sort_order": 0
    }
  ],
  "validation": {
    "ok_to_publish": true,
    "errors": [],
    "warnings": [
      { "code": "CHOICE_FEW_OUTBOUND", "node_slug": "trust_wizard", "message": "Choice node has fewer than 2 outbound edges." }
    ]
  }
}
```

---

### `PATCH /teacher/adventures/<int:adventure_id>`

Update adventure metadata (NOT structural — for that, use the nodes/edges endpoints).

**Request body** (any subset):

```json
{
  "title": "...",
  "description": "...",
  "background_image_url": "...",
  "theme": "scifi",
  "width": 2400,
  "height": 1600,
  "is_public": true,
  "end_semantics": "any"
}
```

**Authorisation**: owner only. Cannot set `is_public=true` while `status=draft` (the UI nudges teachers to publish first).

**200 response data**: `{ "adventure": { ... } }`.

---

### `POST /teacher/adventures/<int:adventure_id>/publish`

Transition `status: draft → published`. Validates via `adventure_graph.validate_for_publish`; if there are blocking errors, returns `409 CONFLICT` with a structured error list.

**200 response data**:

```json
{ "adventure": { "id": 42, "status": "published", "version": 2, ... } }
```

**409 response errors**:

```json
[
  { "code": "NO_START_NODE", "message": "Adventure must have at least one start node." },
  { "code": "END_UNREACHABLE", "message": "Node 'end_final' is not reachable from any start.", "node_slug": "end_final" }
]
```

---

### `DELETE /teacher/adventures/<int:adventure_id>`

Soft-delete (archive). Sets `status='archived'`. Existing assignments stay readable, but no new assignments can be created.

**200 response data**: `{ "adventure": { "status": "archived", ... } }`.

---

### `POST /teacher/adventures/<int:adventure_id>/clone`

Duplicates an adventure into a new draft owned by the calling teacher. Permitted on own adventures and on `is_public=True` adventures from other teachers.

**Request body** (optional):

```json
{ "title": "The Lost Library (copy)" }
```

**201 response data**: `{ "adventure": { "id": 99, "title": "...", "version": 1, "status": "draft", ... } }`.

---

## Resource: AdventureNode (teacher-side)

### `POST /teacher/adventures/<int:adventure_id>/nodes`

**Request body**:

```json
{
  "slug": "wizard_riddle",
  "title": "The Wizard's Riddle",
  "description": "Answer three riddles.",
  "lore": "An old wizard greets you.",
  "icon_url": null,
  "node_type": "quiz",
  "x": 540.0,
  "y": 320.0,
  "is_optional": false,
  "is_start": false,
  "is_end": false,
  "question_set_id": 7,
  "monster_id": null,
  "completion_rules": { "min_score_percent": 80, "max_attempts": 3 },
  "on_complete_actions": {},
  "rewards": [
    { "type": "experience", "amount": 150 },
    {
      "type": "badge",
      "badge_id": 12,
      "is_conditional": true,
      "condition_json": { "min_score_percent": 100 }
    }
  ]
}
```

`rewards` is optional; rewards may also be added later via the rewards endpoint.

**201 response data**: `{ "node": { /* full node */ } }`.
**Errors**: `VALIDATION_ERROR` (bad type-specific FK), `CONFLICT` (slug taken), `NOT_FOUND` (adventure).

---

### `PATCH /teacher/adventures/<int:adventure_id>/nodes/<int:node_id>`

Update any subset of node fields. Changing `slug`, `node_type`, `is_start`, `is_end`, or the graph topology bumps `adventures.version` if the adventure is published.

**200 response data**: `{ "node": { ... } }`.

---

### `DELETE /teacher/adventures/<int:adventure_id>/nodes/<int:node_id>`

Cascades inbound/outbound edges. If the adventure has student progress, the response includes an `affected_students` count and the request requires `?confirm=true` to proceed.

**409 response** (without `confirm=true`):

```json
{
  "code": "AFFECTS_STUDENT_PROGRESS",
  "message": "8 students have progress on this node. Re-issue with ?confirm=true.",
  "affected_students": 8
}
```

**200 response data**: `{ "deleted_node_id": 88, "affected_students": 8, "cleaned_progress_rows": 8 }`.

---

## Resource: AdventureEdge (teacher-side)

### `POST /teacher/adventures/<int:adventure_id>/edges`

**Request body**:

```json
{
  "from_node_id": 88,
  "to_node_id": 91,
  "label": "Trust the wizard",
  "condition_type": "choice",
  "condition_data": { "choice_key": "left" },
  "unlock_semantics": "and",
  "sort_order": 0
}
```

`condition_data` is validated by a Pydantic discriminated union against `condition_type`:
- `always`: must equal `{}`.
- `choice`: requires `choice_key` (non-empty string).
- `criteria`: requires at least one of `min_score_percent` (1–100), `completed_within_seconds` (positive int), `no_failed_attempts` (bool).

**201 response data**: `{ "edge": { ... } }`.
**Errors**: `VALIDATION_ERROR` (self-loop, bad condition_data, duplicate edge).

---

### `PATCH /teacher/adventures/<int:adventure_id>/edges/<int:edge_id>`

Update any subset (excluding `from_node_id` and `to_node_id` — to repoint an edge, delete and recreate).

---

### `DELETE /teacher/adventures/<int:adventure_id>/edges/<int:edge_id>`

Idempotent. Returns 200 even if already deleted.

---

## Resource: NodeReward (teacher-side)

### `POST /teacher/adventures/<int:adventure_id>/nodes/<int:node_id>/rewards`

**Request body**: same shape as rewards-element in node create.

**201 response data**: `{ "reward": { ... } }`.

### `DELETE /teacher/adventures/<int:adventure_id>/nodes/<int:node_id>/rewards/<int:reward_id>`

---

## Resource: NodeConsequence (teacher-side)

### `POST /teacher/adventures/<int:adventure_id>/nodes/<int:node_id>/consequences`

**Request body**:

```json
{
  "description": "Drained by the puzzle.",
  "xp_penalty": 25,
  "gold_penalty": 10,
  "hp_penalty": 0,
  "custom_json": {}
}
```

### `DELETE /teacher/adventures/<int:adventure_id>/nodes/<int:node_id>/consequences/<int:consequence_id>`

---

## Resource: AdventureAssignment (teacher-side)

### `POST /teacher/adventures/<int:adventure_id>/assignments`

**Request body** (exactly one of classroom_id / clan_id / character_id required; clan and individual are Phase 5):

```json
{
  "classroom_id": 17,
  "clan_id": null,
  "character_id": null,
  "starts_at": "2026-06-01T00:00:00Z",
  "ends_at": "2026-08-31T23:59:59Z"
}
```

The server snapshots `adventures.version` into `adventure_assignments.adventure_version` automatically.

**201 response data**:

```json
{
  "assignment": {
    "id": 31,
    "adventure_id": 42,
    "adventure_version": 3,
    "classroom_id": 17,
    "clan_id": null,
    "character_id": null,
    "assigned_by_user_id": 7,
    "starts_at": "...",
    "ends_at": "...",
    "is_active": true
  }
}
```

**Errors**: `CONFLICT` if adventure is not `published`; `VALIDATION_ERROR` if more than one target is set; `FORBIDDEN` if teacher doesn't own the target classroom.

---

### `PATCH /teacher/adventures/<int:adventure_id>/assignments/<int:assignment_id>`

Update `starts_at`, `ends_at`, `is_active` only.

### `DELETE /teacher/adventures/<int:adventure_id>/assignments/<int:assignment_id>`

Deactivates (`is_active=false`). Does not delete the row, preserving FK from in-progress students.

---

## Resource: Progress view (teacher-side)

### `GET /teacher/adventures/<int:adventure_id>/progress`

Per-student roster for an assigned adventure. Supports `?classroom_id=<id>` to scope to one assigned classroom.

**200 response data**:

```json
{
  "students": [
    {
      "user_id": 17,
      "character_id": 33,
      "name": "Ada L.",
      "classroom_id": 17,
      "status": "in_progress",
      "current_node": { "id": 88, "slug": "wizard_riddle", "title": "The Wizard's Riddle", "node_type": "quiz" },
      "node_counts": { "completed": 4, "available": 1, "locked": 7, "failed": 0, "skipped": 0 },
      "last_active_at": "2026-05-22T15:08:00Z",
      "recent_events": [
        { "event_type": "ADVENTURE_NODE_COMPLETE", "node_slug": "goblin", "score": null, "timestamp": "..." }
      ]
    }
  ],
  "summary": {
    "total_students": 28,
    "not_started": 2,
    "in_progress": 21,
    "completed": 5
  }
}
```

**Performance constraint (SC-009)**: ≤ 3 s for up to 60 students. Implementation must use a single grouped query plus an aggregated `node_counts` subquery; no per-student N+1.

---

### `POST /teacher/adventures/<int:adventure_id>/progress/<int:character_id>/force-complete`

Teacher override per FR-021. Marks the student's adventure complete; audit-logged as an explicit teacher action.

**Request body** (optional):

```json
{ "reason": "Student fell ill, manual completion." }
```

**200 response data**:

```json
{ "adventure_progress": { "character_id": 33, "status": "completed", "completed_at": "...", "forced_by": 7 } }
```

---

## Background image upload

### `POST /teacher/adventures/<int:adventure_id>/background`

Multipart form upload. `Content-Type: multipart/form-data` with field name `file`.

- Max size: `MAX_BACKGROUND_UPLOAD_BYTES` (default 5 MB, env-configurable).
- MIME whitelist: `image/png`, `image/jpeg`, `image/webp`.
- Storage path: `static/images/adventure_backgrounds/<adventure_id>/<sanitised-filename>`.
- Sets `adventures.background_image_url` to the new path on success.

**200 response data**: `{ "background_image_url": "/static/images/adventure_backgrounds/42/library.png" }`.
**Errors**: `PAYLOAD_TOO_LARGE`, `VALIDATION_ERROR` (bad MIME).

---

## Authorisation summary (per FR-037, FR-040)

| Action | Allowed when |
|---|---|
| List own + public adventures | Always for any teacher |
| Read an adventure | Teacher owns it OR it is `is_public=True` |
| Edit / publish / archive / assign | Teacher owns it |
| Clone | Teacher owns it OR it is `is_public=True` |
| Read progress view | Teacher owns it AND the target classroom is theirs |
| Force-complete a student | Teacher owns the adventure AND the student is in their classroom |
| Upload background | Teacher owns the adventure |

All checks live in a single `_authorise(teacher, adventure, action)` helper in `adventure_graph.py` so they are testable in isolation.
