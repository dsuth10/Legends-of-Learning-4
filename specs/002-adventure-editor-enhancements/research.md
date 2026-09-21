# Phase 0 - Research & Decisions: Adventure Editor Enhancements

**Feature**: 002-adventure-editor-enhancements
**Date**: 2026-05-22
**Status**: Decisions finalised; no NEEDS CLARIFICATION items remain.

This document records the implementation decisions required before design. The feature enhances an existing Adventures implementation rather than creating new infrastructure.

---

## R1 - Quiz question-set ownership and option source

**Decision**: Build question-set options from the current teacher's legacy `Teacher` row, not directly from `User.id`. Render options into the editor on first page load and expose the same data through a teacher-scoped JSON route for refresh/future use.

**Rationale**:

- `QuestionSet.teacher_id` references `teachers.id`, while `Adventure.teacher_id` references `users.id`. Looking up `Teacher.query.filter_by(user_id=current_user.id)` is required for correct ownership filtering.
- Server-rendering options mirrors the existing monster picker and avoids an extra fetch before the inspector can render.
- A JSON route keeps the contract explicit and allows later "refresh after creating a question set" behavior without changing the editor again.

**Alternatives considered**:

- Filter question sets by `current_user.id`. Rejected because it uses the wrong key and would leak or omit records.
- Fetch options only after selecting a quiz node. Rejected because it adds latency to a common inspector action and duplicates state handling.

---

## R2 - Adventure settings UI placement

**Decision**: Add a settings modal opened from the existing editor action toolbar.

**Rationale**:

- The current editor uses the canvas and inspector for map-building. A modal keeps adventure-level settings separate from node/edge editing.
- One deliberate save aligns with the existing partial update schema and avoids accidental updates while teachers type.
- The share toggle already lives near the toolbar; moving or mirroring it in the modal lets settings feel cohesive while preserving the existing publish-first rule.

**Alternatives considered**:

- Inline accordion above the canvas. Acceptable but rejected for v1 because it consumes vertical space in the map editor.
- Inline title editing in the header. Rejected because it introduces another save surface for the same field and complicates validation feedback.

---

## R3 - Settings persistence and background flow

**Decision**: Use existing adventure metadata update and background upload routes. Save changed metadata fields in one JSON update, upload background files through the existing background route, then reflect the returned background URL in the editor preview and final metadata save state.

**Rationale**:

- `AdventureUpdateSchema` already accepts `title`, `description`, `theme`, `background_image_url`, `is_public`, and `end_semantics`.
- The background upload route already performs extension, MIME, magic-byte, and size validation.
- Keeping upload and metadata save behavior in existing routes preserves current status codes, ownership checks, and response envelopes.

**Alternatives considered**:

- Add a separate settings-specific route. Rejected because it duplicates validation and ownership logic already present.
- Auto-save every changed field. Rejected because it increases request volume and makes recovery from partial validation failures harder.

---

## R4 - Drag implementation

**Decision**: Implement drag with pointer events on SVG node groups, live transform updates during movement, live connected-edge endpoint updates, and one node-position update when the pointer is released.

**Rationale**:

- Pointer events support mouse, pen, and touch through one code path.
- Moving the existing SVG group during drag avoids a full graph re-render on every pointer move.
- Updating connected lines during drag prevents visual detachment between nodes and paths.
- One update on drop protects the server from excessive requests and keeps published version bumps to one per completed reposition.

**Alternatives considered**:

- Re-render the whole graph on every pointer move. Rejected as likely janky and unnecessarily complex.
- Save on every pointer move. Rejected because it hammers the server and can create many published-version bumps.
- Mouse-only events. Rejected because the spec requires consistent pointer behavior across supported input types.

---

## R5 - Click versus drag threshold

**Decision**: Treat movement below a small threshold as a click and movement at or above the threshold as a drag. Recommended threshold: 4 logical pixels.

**Rationale**:

- Current node selection and connect-mode behavior are click-driven. A threshold preserves those behaviors for normal hand jitter.
- The source plan recommends 4px, which is a common threshold for distinguishing intentional drag from click.

**Alternatives considered**:

- No threshold. Rejected because tiny pointer movement would make node selection unreliable.
- Large threshold (10px+). Rejected because it makes short corrections feel unresponsive.

---

## R6 - Validation and recovery UX

**Decision**: Centralize editor request error display through the existing validation banner plus concise local recovery behavior: failed metadata saves preserve form values, failed background uploads keep the prior background, and failed drags snap the node back to its last saved position.

**Rationale**:

- The current editor already has `#editor-validation` with `aria-live`; extending it avoids creating multiple competing error surfaces.
- Each feature has an obvious safe recovery state that does not require a full page reload.
- This supports both keyboard/screen-reader feedback and visual teacher workflows.

**Alternatives considered**:

- Browser alerts for all failures. Rejected because alerts interrupt the workflow and are inconsistent with current validation-panel behavior.
- Silent rollback on failed drag. Rejected because teachers need to know their layout was not saved.
