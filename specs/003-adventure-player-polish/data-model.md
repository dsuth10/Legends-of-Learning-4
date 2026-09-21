# Phase 1 - Data Model: Adventures Player and Editor Polish

**Feature**: 003-adventure-player-polish
**Date**: 2026-09-21
**Status**: Planning final; no schema migration expected.

This feature reuses the Adventures data model from spec 001. Player travel, mini-map, and keyboard behaviour are client-side. Assignment and icons use columns that already exist.

---

## Existing Entities Used

### Adventure Node

Map item shown on the teacher editor and student player.

**Fields used by this feature**:

- `id`, `slug`, `title`, `node_type`, `x`, `y`
- `icon_url`: optional override. `NULL` means the type default from the icon catalog. Non-null stores a Material Icon ligature (for example `swords`). Values starting with `/` are treated as static image paths for forward compatibility.
- `adventure_id`: parent adventure for save/load.

**Validation rules**:

- `icon_url`, when set, must be a catalog ligature or a path beginning with `/`. Unknown ligatures fall back to the type default at render time; the stored value is still shown in the picker.
- Changing `node_type` does not clear `icon_url`.
- Clearing the override persists `icon_url = NULL`.

**State transitions**:

- None. Icon changes are field updates; existing published-edit version bump still applies.

---

### Adventure Assignment

Binding of a published adventure to exactly one target.

**Fields used by this feature**:

- `id`, `adventure_id`, `adventure_version`
- `classroom_id`, `clan_id`, `character_id` — exactly one non-null (already enforced by `AssignmentCreateSchema` and a CHECK where supported)
- `assigned_by_user_id`, `starts_at`, `ends_at`, `is_active`

**Validation rules**:

- Adventure must be `published`.
- Teacher must own the target: classroom they teach; clan whose `class_id` is one of those classrooms; character whose student is in one of those classrooms.
- No second *active* assignment for the same adventure and same target.
- Start/end window rules unchanged (`ends_at > starts_at` when both set).
- Empty clan is allowed; the create response includes a warning.

**State transitions**:

```
created (is_active=true)
  --[teacher deactivate]--> is_active=false
```

Target type cannot change in place. Teachers deactivate and create a new assignment.

**Derived view fields** (not columns):

- `target_type`: `classroom` | `clan` | `character`
- `target_label`: class name, clan name, or student/character name
- `member_count` for clan targets (may be 0)
- `progress_url` for the scoped roster

---

### Character Adventure Progress

Per-character standing, already unique on `(character_id, adventure_id)`.

**Fields used by this feature**:

- `character_id`, `adventure_id`, `assignment_id`
- `current_node_id`: last node the student opened; used as the default marker position
- `status`, `last_active_at`

**Assignment-after-leaving-clan rule**:

- If the character still matches an active class/clan/direct assignment, they can play.
- Else if they have a progress row whose `assignment_id` points at an *active* assignment for this adventure, they can continue or review (they already started).
- Else they are not assigned. They do not newly receive a clan assignment after leaving the clan.

Deactivated assignments still block *new* node starts via existing window/active checks.

---

### Character Node Progress

Per-node status used by travel inference.

**Fields used by this feature**:

- `node_id`, `status`, `completed_at`

**Travel inference** (not persisted):

- On-map complete/choose: `next_unlocked` from the response is the destination set; origin is the completed node.
- On map load: origin = node with latest non-null `completed_at`; destinations = currently `available` successors of that node that have not been marked seen in `sessionStorage`.

**Marker position**:

- Prefer `current_node_id` if that node exists.
- Else last completed node.
- Else the start node that is `available`.

---

### Clan / Character / Classroom (identity, unchanged)

Used only to authorise and label assignment targets.

- `Classroom.teacher_id` must equal the assigning teacher.
- `Clan.class_id` → that classroom.
- `Character.student_id` → `Student.class_id` → that classroom.
- Clan membership for *receiving* an assignment is `Character.clan_id` (already used by `_active_assignments_for_character`).

---

## Client-only concepts (not tables)

### Character marker

Visible token on the student map. Position is derived from progress as above. Travel duration ≤ 1.5s. Copies used only for forked unlocks.

### Mini-map

Scaled overview of nodes/edges plus a viewport rectangle bound to `#map-container` scroll. Not stored.

### Editor command stack

In-memory list of `{do, undo}` for place, move, connect, delete in the current editor page. Cleared on reload. Not stored.

### Icon catalog

Read-only list of `{ id, label, ligature, default_for: [node_type...] }`. Served to the editor; player uses the same default map in JS.

---

## No New Tables

No Alembic migration is planned.

| Need | Existing representation |
|------|-------------------------|
| Clan / individual assignment | `adventure_assignments.clan_id` / `character_id` |
| Node icon override | `adventure_nodes.icon_url` |
| Marker position | `character_adventure_progress.current_node_id` + node progress |
| Pending travel | `sessionStorage` + `completed_at` / `next_unlocked` |
| Undo history | editor session memory |

Add a migration only if implementation proves `icon_url` cannot hold ligature names (it can; VARCHAR 512) or if assignment CHECKs are missing on a target database. Prefer app-level validation first.
