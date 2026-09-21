# Phase 0 - Research & Decisions: Adventures Player and Editor Polish

**Feature**: 003-adventure-player-polish
**Date**: 2026-09-21
**Status**: Decisions finalised; no NEEDS CLARIFICATION items remain.

This feature polishes the shipped Adventures loop from specs 001 and 002. It does not introduce a new frontend framework, a JS build step, or new database tables.

---

## R1 - Travel animation source of truth

**Decision**: Drive travel from the existing `next_unlocked` payload on complete/choose, and on map load infer pending travel from the most recently completed node plus currently available successors. Persist a "already seen" key in `sessionStorage` so battle/quiz returns replay once. Honor `prefers-reduced-motion: reduce` by skipping motion.

**Rationale**:

- Complete, choose, and quiz already return `next_unlocked`. On-map completions can animate immediately without a schema change.
- Battle and quiz finish on another page. Inferring from latest `completed_at` plus available successors covers FR-006 without new columns.
- `sessionStorage` keyed by adventure id + completed node id + `completed_at` prevents replaying travel on every refresh in the same tab, while a new tab/session can still show it once.
- Reduced motion is a platform preference, matching the spec's assumption that there is no separate skip setting.

**Alternatives considered**:

- Add `pending_travel_json` on `character_adventure_progress`. Rejected because it requires a migration for a visual cue and needs a "mark seen" write on every map load.
- Animate only when `next_unlocked` is in the same page response. Rejected because it fails FR-006 for battles and quizzes.
- Always replay travel from the last completed node on every load. Rejected because it would annoy returning students.

**Fork behaviour**: After one successor, the marker ends on that successor. After two or more, copies travel along each path and fade; the main marker remains on the completed node (the student has not chosen a next node yet). Interrupted travel jumps to the final state.

---

## R2 - Mini-map and camera

**Decision**: Keep the existing scrollable `#map-container` as the camera. Add a student-only mini-map that scales the full adventure into a corner overlay, draws a viewport rectangle from `scrollLeft`/`scrollTop`, and jumps by setting those scroll offsets. Keyboard users jump by focusing mini-map node marks (unlocked nodes) rather than aiming at coordinates.

**Rationale**:

- The player already uses overflow scroll rather than a pan/zoom engine. Reusing scroll avoids a new camera model.
- Click/tap on empty mini-map space pans the main view to that coordinate (FR-010, under one second).
- Focusable marks on unlocked nodes satisfy FR-011 without requiring precise pointer aiming.
- Teacher-editor mini-map stays out of scope per the spec assumption.

**Alternatives considered**:

- CSS/SVG transform pan-zoom on the student map. Rejected for v1; scroll already works and mini-map jump is then just `scrollTo`.
- Hide the mini-map unless the map overflows. Accepted as optional de-emphasis: still render it when the layout exceeds the visible area; tiny maps may collapse it.

---

## R3 - Editor keyboard, zoom, and undo

**Decision**: Add keyboard handling in a dedicated editor helper. Shortcuts: Tab/arrows among nodes, Enter to inspect, Esc to deselect or close overlay, Delete/Backspace to delete with existing confirm, `+`/`=` and `-` to zoom the canvas wrapper, Ctrl/Cmd+Z undo, Ctrl/Cmd+Shift+Z or Ctrl/Cmd+Y redo. Undo is an in-memory command stack of successful place/move/connect/delete operations for the current page session.

**Rationale**:

- The editor has no zoom or keydown map today; labels exist but nodes are not a keyboard widget.
- Session-only undo matches the spec and avoids a new history table.
- Commands wrap the existing node/edge APIs so undo/redo stay consistent with the server. A failed save does not push a command; a failed undo reports through the existing `aria-live` banner and leaves the last successful save visible.
- Extracting keyboard/undo out of `adventure_editor.js` (already ~1100 lines) respects the constitution's "keep files under 500 lines when possible" guidance.

**Alternatives considered**:

- Persist undo across reloads. Rejected; spec explicitly says session-only.
- Zoom via SVG `viewBox` only. Acceptable alternative; CSS transform on the canvas wrap is simpler to keep node pointer math aligned with the existing `svgPoint` helper if zoom is applied to a wrapper around the SVG, not the SVG itself. Implementation should pick one and keep drag coordinates correct.

---

## R4 - Clan and individual assignment

**Decision**: Remove the teacher route's "not yet supported" rejection. Generalise assignment creation in a new `app/services/adventure_assignment.py`. Student matching already supports class, clan (`character.clan_id`), and direct character targets. Extend "still assigned" so a student who already has `character_adventure_progress` for an *active* assignment can continue after leaving the clan; students with no progress do not newly receive it.

**Rationale**:

- `AssignmentCreateSchema` already requires exactly one of `classroom_id` / `clan_id` / `character_id`.
- `_resolve_roster_characters` already walks clan and character assignments.
- `_active_assignments_for_character` already matches those targets. The gap is teacher create/list UI plus progress filters that currently list classroom rows only.
- Spec FR for leaving a clan: keep started runs, do not grant new access. That requires a progress-row fallback in `student_is_assigned` / `require_student_assignment`, which 001 did not implement because clan assignment was unused.

**Authorisation**:

- Clan: clan's `class_id` must be a classroom owned by the teacher (`require_teacher_classroom`).
- Character: character's student must belong to a classroom owned by the teacher.
- Duplicate active assignment to the same adventure + same target → `CONFLICT`.
- Empty clan: allow create; include a warning in the JSON `data` (not an error).

**Alternatives considered**:

- Keep create logic in `adventure_graph.py`. Rejected because that module is already far over the size guideline; assignment create/list/target-auth is a coherent service.
- Shared clan progress. Rejected; out of scope.
- Change target type in place. Rejected; spec says deactivate and create a new assignment.

---

## R5 - Node icon library

**Decision**: Ship a curated catalog of Material Icon ligatures (already used on student pages). Store an override in existing `adventure_nodes.icon_url` as the ligature name (for example `swords`). `null` means "use the default for this `node_type`". Changing node type keeps the override; the picker shows current vs type default so the teacher is not surprised. No file uploads.

**Rationale**:

- `icon_url` already exists on the node and is already serialized to both teacher and student payloads.
- Student maps do not currently draw icons; they draw labelled circles. The catalog plus ligature rendering is enough for FR-031..FR-034 without binary assets.
- Teacher dashboard uses Font Awesome, student pages use Material Icons. The player page must include the Material Icons stylesheet. The editor picker can use the same stylesheet for consistency with the student map.
- Paths beginning with `/` remain valid if a later feature adds file icons; this feature does not.

**Default ligatures** (starting set; labels may be tuned at implementation):

| node_type | default icon |
|-----------|----------------|
| start | `flag` |
| story | `auto_stories` |
| battle | `swords` |
| quiz | `quiz` |
| choice | `alt_route` |
| reward | `redeem` |
| milestone | `emoji_events` |
| boss | `cruelty_free` |
| end | `sports_score` |

**Alternatives considered**:

- PNG library under `static/images/adventure_node_icons/`. Optional later; the directory already exists. Rejected as required work because there is no art set ready and ligatures match the student UI.
- Custom uploads. Rejected; spec out of scope.

---

## R6 - Accessibility and small screens

**Decision**: Treat this as markup and CSS on the existing editor and player, not a redesign. Locked student nodes stay `tabindex="-1"` and `aria-disabled`. Unlocked/completed nodes are buttons with names `{title}, {type}, {status}`. Editor nodes get `{title}, {type}`. Selection, validation, and save outcomes continue to use one `aria-live` region per page. Phone layouts stack the detail/inspector below or in a sheet so the mini-map and primary action do not overlap.

**Rationale**:

- Student player already has Enter/Space on unlocked nodes and an sr-only keyboard hint; the gap is travel announcements, mini-map names, locked-node discoverability, and editor keyboard.
- One live region per page avoids duplicate chatter (lesson from spec 002).
- Responsive stacking is cheaper and more reliable than a second mobile map.

**Alternatives considered**:

- Native apps or a new player shell. Rejected; spec is a web pass.
