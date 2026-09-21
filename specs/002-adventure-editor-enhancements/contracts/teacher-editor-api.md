# API Contracts - Adventure Editor Enhancements

**Feature**: 002-adventure-editor-enhancements
**Date**: 2026-05-22
**Blueprint**: `adventures_teacher_bp` (`url_prefix="/teacher/adventures"`)
**Auth**: All endpoints require a logged-in teacher. Adventure-specific mutations require ownership/edit permission.

## Conventions

All JSON responses use the existing Adventures envelope:

```json
{
  "success": true,
  "data": {},
  "errors": []
}
```

On error:

```json
{
  "success": false,
  "data": null,
  "errors": [
    { "code": "VALIDATION_ERROR", "message": "Field-level detail." }
  ]
}
```

Common error codes: `VALIDATION_ERROR` (400), `FORBIDDEN` (403), `NOT_FOUND` (404), `CONFLICT` (409), `PAYLOAD_TOO_LARGE` (413).

---

## Question Set Options

### `GET /teacher/adventures/question-sets`

Returns active question sets available to the current teacher for quiz-node configuration.

**Authorization**: current user must be a teacher. Results are filtered through the legacy `Teacher` row linked to `current_user.id`.

**200 response data**:

```json
{
  "question_sets": [
    {
      "id": 12,
      "title": "Fractions Review",
      "question_count": 15
    }
  ]
}
```

**Empty state**:

```json
{
  "question_sets": []
}
```

If the current teacher has no legacy `Teacher` row or no active question sets, return an empty list rather than an error.

---

## Editor Page Bootstrap Data

### `GET /teacher/adventures/<int:adventure_id>`

Default response is the HTML editor page. JSON is returned when the request `Accept` type is `application/json` or `?format=json` is present:

```json
{
  "success": true,
  "data": { "adventure": { "id": 42, "title": "The Lost Library" } },
  "errors": []
}
```

The HTML editor bootstraps question-set options and current settings in `AdventureEditor.init`.

**Template bootstrap shape**:

```javascript
AdventureEditor.init({
  adventureId: 42,
  canEdit: true,
  monsters: [{ id: 5, name: "Goblin" }],
  questionSets: [{ id: 12, title: "Fractions Review", question_count: 15 }],
  adventureSettings: {
    title: "The Lost Library",
    description: "Explore a ruined library and solve riddles.",
    theme: "fantasy",
    end_semantics: "any",
    is_public: false,
    background_image_url: "/static/images/adventure_backgrounds/42/map.png",
    status: "draft"
  }
});
```

For shared/view-only adventures, `canEdit` remains `false` and `questionSets` is an empty array because controls are not editable. The JSON adventure object is the existing `adventure_summary` payload (includes `status`, `width`, `height`, `owner`, counts, and timestamps in addition to the settings fields).

---

## Attach Question Set To Quiz Node

### `PATCH /teacher/adventures/<int:adventure_id>/nodes/<int:node_id>`

Existing node update endpoint. The editor uses it to save quiz question-set selection and drag coordinates.

**Quiz question-set request body**:

```json
{
  "question_set_id": 12
}
```

**Clear selection request body**:

```json
{
  "question_set_id": null
}
```

**200 response data**: existing `node_dict` payload. Fields used by this feature:

```json
{
  "node": {
    "id": 88,
    "slug": "wizard-riddle",
    "node_type": "quiz",
    "question_set_id": 12,
    "x": 540.0,
    "y": 320.0
  }
}
```

The same object also includes title, description, lore, icon, flags, monster id, completion rules, rewards, and consequences.

**Validation**:

- Owner/editor permission required.
- If `question_set_id` is non-null, it must refer to an active question set owned by the current teacher (legacy `Teacher` profile). Inactive or other-teacher ids return `VALIDATION_ERROR` (400).
- Other node fields not included in the request remain unchanged.
- Published adventures increment `version` after a successful node PATCH.

---

## Reposition Node

### `PATCH /teacher/adventures/<int:adventure_id>/nodes/<int:node_id>`

Existing node update endpoint used after drag release.

**Request body**:

```json
{
  "x": 725,
  "y": 410
}
```

**200 response data**:

```json
{
  "node": {
    "id": 88,
    "slug": "wizard-riddle",
    "x": 725.0,
    "y": 410.0
  }
}
```

**Validation**:

- `x` and `y` must be greater than or equal to 0 (Pydantic `NodeUpdateSchema`).
- The editor clamps coordinates to the current adventure width/height before saving. The API does not re-clamp to width/height.
- If save fails, the client restores the previous saved position.
- Published adventures increment `version` after a successful coordinate PATCH.

---

## Save Adventure Settings

### `PATCH /teacher/adventures/<int:adventure_id>`

Existing adventure update endpoint. The settings modal sends only fields changed by the teacher.

**Request body**:

```json
{
  "title": "The Lost Library",
  "description": "Explore a ruined library and solve riddles.",
  "theme": "fantasy",
  "end_semantics": "any",
  "is_public": true,
  "background_image_url": "/static/images/adventure_backgrounds/42/map.webp"
}
```

All fields are optional. Omitted fields are preserved.

**200 response data**: existing `adventure_summary` payload, including the settings fields plus `status`, `width`, `height`, `owner`, counts, and timestamps.

```json
{
  "adventure": {
    "id": 42,
    "title": "The Lost Library",
    "description": "Explore a ruined library and solve riddles.",
    "theme": "fantasy",
    "background_image_url": "/static/images/adventure_backgrounds/42/map.png",
    "is_public": true,
    "end_semantics": "any",
    "version": 3,
    "status": "published"
  }
}
```

**Validation**:

- `title` must be non-empty.
- `end_semantics` must be `all` or `any`.
- Draft adventures cannot be made public (`VALIDATION_ERROR`: publish first).
- Published adventures increment `version` after a successful settings PATCH.

---

## Upload Background Image

### `POST /teacher/adventures/<int:adventure_id>/background`

Existing upload endpoint used by the settings modal.

**Request**: `multipart/form-data` with file field `file`.

**200 response data**:

```json
{
  "background_image_url": "/static/images/adventure_backgrounds/42/map.png"
}
```

The URL uses the sanitized original filename. This endpoint persists `adventure.background_image_url` immediately; the settings modal does not wait for a later metadata PATCH to keep the new background.

**Validation**:

- Allowed content: PNG, JPEG, WebP (`.png`, `.jpg`, `.jpeg`, `.webp`).
- File extension, MIME type, and file signature must agree.
- Default max size is 5 MB (`MAX_BACKGROUND_UPLOAD_BYTES`); oversized files return `PAYLOAD_TOO_LARGE` (413).
- Owner/editor permission required.
