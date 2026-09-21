# API Contracts - Node Icon Catalog

**Feature**: 003-adventure-player-polish
**Date**: 2026-09-21
**Blueprint**: `adventures_teacher_bp` (`url_prefix="/teacher/adventures"`)
**Auth**: Logged-in teacher for the catalog route. Node updates require edit permission.

## Conventions

Existing Adventures JSON envelope. Error codes: `VALIDATION_ERROR` (400), `FORBIDDEN` (403), `NOT_FOUND` (404).

---

## Icon catalog

### `GET /teacher/adventures/node-icons`

Read-only curated library. Same list is the source of type defaults.

**200 response data**:

```json
{
  "icons": [
    { "id": "flag", "label": "Flag", "ligature": "flag", "default_for": ["start"] },
    { "id": "auto_stories", "label": "Story", "ligature": "auto_stories", "default_for": ["story"] },
    { "id": "swords", "label": "Swords", "ligature": "swords", "default_for": ["battle"] },
    { "id": "quiz", "label": "Quiz", "ligature": "quiz", "default_for": ["quiz"] },
    { "id": "alt_route", "label": "Branch", "ligature": "alt_route", "default_for": ["choice"] },
    { "id": "redeem", "label": "Reward", "ligature": "redeem", "default_for": ["reward"] },
    { "id": "emoji_events", "label": "Milestone", "ligature": "emoji_events", "default_for": ["milestone"] },
    { "id": "cruelty_free", "label": "Boss", "ligature": "cruelty_free", "default_for": ["boss"] },
    { "id": "sports_score", "label": "Finish", "ligature": "sports_score", "default_for": ["end"] }
  ]
}
```

The catalog MAY include extra ligatures that are not type defaults so teachers can override. Each `node_type` MUST appear in exactly one `default_for` list.

The editor MAY also bootstrap this list into the page to avoid an extra fetch; the JSON route remains the contract for tests and refresh.

---

## Save / clear override

### `PATCH /teacher/adventures/<int:adventure_id>/nodes/<int:node_id>`

Existing node update. This feature uses:

```json
{ "icon_url": "swords" }
```

Clear override:

```json
{ "icon_url": null }
```

**200**: existing node payload, including `icon_url` after save.

**Validation**:

- If `icon_url` is a string not starting with `/`, it SHOULD be a known catalog ligature. Unknown ligatures are accepted but rendered with the type default plus a picker note that the stored value is not in the library.
- Empty string is treated as `null`.

Student `GET /student/adventures/<id>/state` already includes `icon_url` per node. No student API change is required; the player resolves `null` to the type default locally.
