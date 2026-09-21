# Phase 1 - Data Model: Adventure Editor Enhancements

**Feature**: 002-adventure-editor-enhancements
**Date**: 2026-05-22
**Status**: Planning final; no schema migration expected.

This feature reuses the existing Adventures and Education data model. It adds editor behavior around existing fields rather than introducing new persisted entities.

---

## Existing Entities Used

### Adventure

Teacher-authored map metadata displayed and edited from the Adventure Editor.

**Existing fields used by this feature**:

- `id`: stable adventure identifier.
- `title`: editable display title.
- `description`: editable teacher/student-facing summary.
- `background_image_url`: editable background reference, updated by upload flow.
- `theme`: editable visual theme string.
- `is_public`: editable sharing visibility, subject to existing draft/publish restrictions.
- `end_semantics`: editable completion rule, `all` or `any`.
- `width`, `height`: logical map bounds used to clamp dragged node coordinates.
- `status`: determines whether sharing can be enabled and whether updates bump version.
- `version`: existing published-edit version counter.
- `teacher_id`: owner `User.id`, used by current Adventures authorization.

**Validation rules**:

- `title` must be non-empty and no more than 128 characters.
- `width` and `height` must remain at least 100 when changed by any future settings UI.
- `end_semantics` must be `all` or `any`.
- Draft adventures cannot be shared publicly.
- Only the owning teacher can edit settings.

**State transitions**:

- No new adventure status transitions.
- Existing route behavior increments `version` when a published adventure is updated.

---

### Adventure Node

Map item that can be selected in the inspector, configured as a quiz node, or repositioned by drag.

**Existing fields used by this feature**:

- `id`: stable node identifier used for update calls.
- `adventure_id`: parent adventure.
- `slug`: existing editor label and stable node slug.
- `title`: existing inspector field.
- `node_type`: determines whether quiz-specific question-set controls appear.
- `x`, `y`: logical map coordinates updated after drag.
- `question_set_id`: selected question set for quiz nodes.
- `monster_id`: existing battle-node selector pattern that quiz-node selection mirrors.

**Validation rules**:

- `x` and `y` must be greater than or equal to 0.
- Editor drag must clamp final `x` and `y` to the adventure's `width` and `height`.
- `question_set_id` may be empty while a teacher is drafting, but publish readiness continues to warn when a quiz node lacks a valid question set.
- A question set attached through the editor must belong to the current teacher's available question sets.

**State transitions**:

- Repositioning changes only coordinates.
- Quiz question-set assignment changes only `question_set_id`.
- Existing published-edit version bump behavior applies to node updates.

---

### Question Set

Legacy education content collection that can be attached to an adventure quiz node.

**Existing fields used by this feature**:

- `id`: selected by quiz nodes.
- `title`: displayed in editor dropdowns.
- `teacher_id`: references legacy `Teacher.id`, not `User.id`.
- `is_active`: filters available editor options.
- `questions`: dynamic relationship used to show question count.

**Validation rules**:

- Only active question sets for the current teacher are shown as selectable.
- If the current user has no corresponding legacy `Teacher` row, the available list is empty.
- Inactive or other-teacher question sets are not returned by the option source and should be treated as unavailable in the editor.

---

### Question Set Option

Read-only view model for editor dropdowns. This is not a database table.

**Fields**:

- `id`: question set id.
- `title`: question set title.
- `question_count`: number of questions in the set.

**Relationships**:

- Derived from `QuestionSet`.
- Used by quiz-node inspector controls.

---

## No New Tables

No Alembic migration is planned. Existing columns already satisfy the feature:

- Adventure settings: `adventures.title`, `description`, `background_image_url`, `theme`, `is_public`, `end_semantics`.
- Quiz configuration: `adventure_nodes.question_set_id`.
- Drag persistence: `adventure_nodes.x`, `adventure_nodes.y`.

If implementation discovers that question-set availability needs richer data, prefer extending the read-only option view first. Add schema only if a persisted concept cannot be represented by existing tables.
