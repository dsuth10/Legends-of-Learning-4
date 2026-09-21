# API Contracts - Teacher Assignment Targets

**Feature**: 003-adventure-player-polish
**Date**: 2026-09-21
**Blueprint**: `adventures_teacher_bp` (`url_prefix="/teacher/adventures"`)
**Auth**: Logged-in teacher. Mutations require ownership of the adventure and of the target.

## Conventions

All JSON responses use the existing Adventures envelope:

```json
{
  "success": true,
  "data": {},
  "errors": []
}
```

Common error codes: `VALIDATION_ERROR` (400), `FORBIDDEN` (403), `NOT_FOUND` (404), `CONFLICT` (409).

---

## Create assignment

### `POST /teacher/adventures/<int:adventure_id>/assignments`

Exactly one of `classroom_id`, `clan_id`, `character_id` is required (existing `AssignmentCreateSchema`).

**Request** (clan example):

```json
{
  "clan_id": 4,
  "starts_at": null,
  "ends_at": null
}
```

**Request** (individual example):

```json
{
  "character_id": 33
}
```

Class assignment request shape is unchanged.

**201 response data**:

```json
{
  "assignment": {
    "id": 32,
    "adventure_id": 42,
    "adventure_version": 3,
    "classroom_id": null,
    "clan_id": 4,
    "character_id": null,
    "target_type": "clan",
    "target_label": "Team Oak",
    "assigned_by_user_id": 7,
    "starts_at": null,
    "ends_at": null,
    "is_active": true,
    "progress_url": "/teacher/adventures/42/progress?assignment_id=32"
  },
  "warnings": []
}
```

Empty clan:

```json
{
  "assignment": { "id": 33, "clan_id": 5, "target_type": "clan", "target_label": "Empty Wolves" },
  "warnings": ["This clan has no members yet, so no students will see the adventure until someone joins."]
}
```

**Errors**:

| Code | HTTP | When |
|------|------|------|
| `CONFLICT` | 409 | Adventure is not published, or an active assignment already exists for this adventure + target |
| `VALIDATION_ERROR` | 400 | Zero or more than one target field; invalid dates |
| `FORBIDDEN` | 403 | Teacher does not own the classroom / clan's class / character's class |
| `NOT_FOUND` | 404 | Adventure, clan, or character does not exist |

Clan and individual targets MUST no longer return "not yet supported".

---

## List assignments

### `GET /teacher/adventures/<int:adventure_id>/assignments`

HTML page by default. JSON when `Accept: application/json` or `?format=json`.

**200 response data**:

```json
{
  "assignments": [
    {
      "id": 31,
      "target_type": "classroom",
      "target_label": "Year 5",
      "classroom_id": 17,
      "clan_id": null,
      "character_id": null,
      "adventure_version": 3,
      "is_active": true,
      "progress_url": "/teacher/adventures/42/progress?classroom_id=17"
    },
    {
      "id": 32,
      "target_type": "clan",
      "target_label": "Team Oak",
      "classroom_id": null,
      "clan_id": 4,
      "character_id": null,
      "is_active": true,
      "progress_url": "/teacher/adventures/42/progress?assignment_id=32"
    }
  ]
}
```

Must include active classroom, clan, and character assignments (not classroom-only).

---

## Assignment target options

### `GET /teacher/adventures/<int:adventure_id>/assignment-targets`

Teacher-owned classrooms, clans in those classrooms, and active characters of students in those classrooms. Used by the assignment form.

**200 response data**:

```json
{
  "classrooms": [
    { "id": 17, "name": "Year 5", "already_assigned": true }
  ],
  "clans": [
    { "id": 4, "name": "Team Oak", "class_id": 17, "class_name": "Year 5", "member_count": 5, "already_assigned": false }
  ],
  "characters": [
    {
      "id": 33,
      "name": "Ada the Druid",
      "student_name": "Ada L.",
      "class_id": 17,
      "class_name": "Year 5",
      "already_assigned": false
    }
  ]
}
```

`already_assigned` is true when this adventure has an active assignment to that exact target. The form may still list them as disabled.

---

## Deactivate

### `DELETE /teacher/adventures/<int:adventure_id>/assignments/<int:assignment_id>`

Unchanged: sets `is_active=false`. Applies to clan and individual rows as well as class rows. Students cannot start new nodes from a deactivated assignment.

---

## Progress roster

### `GET /teacher/adventures/<int:adventure_id>/progress`

Existing `?classroom_id=` remains. Add `?assignment_id=` to scope to one assignment of any target type.

- Omit both: combined roster of every student covered by any active assignment (deduped by character).
- `classroom_id`: existing class-scoped behaviour.
- `assignment_id`: roster for that assignment's members only; 404 if not an assignment of this adventure.

JSON and HTML both show `target_type` / `target_label` for each active assignment in the filter list.
