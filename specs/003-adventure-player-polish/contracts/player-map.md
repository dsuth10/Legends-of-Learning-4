# UI Contracts - Player Map and Editor Keyboard

**Feature**: 003-adventure-player-polish
**Date**: 2026-09-21

These are client behaviour contracts. They reuse existing student complete/choose/state payloads and existing teacher node/edge APIs. No new student endpoints.

---

## Student complete payload (already shipped)

`POST /student/adventures/<id>/nodes/<slug>/complete` and `/choose` already return:

```json
{
  "node": { "id": 88, "slug": "lore", "status": "completed" },
  "next_unlocked": [
    { "id": 90, "slug": "trust_wizard", "title": "Trust the wizard?", "node_type": "choice" }
  ],
  "adventure_complete": false
}
```

The player MUST use `next_unlocked` as the travel destination set when this response arrives on the map page.

`GET /student/adventures/<id>/state` already includes `my_progress.current_node_id` and per-node `status` / `completed_at`. The player MUST use those to place the marker and to infer pending travel after a battle or quiz.

---

## Travel

| Condition | Behaviour |
|-----------|-----------|
| `prefers-reduced-motion: reduce` | Update states and marker immediately; no motion |
| One newly unlocked successor | Marker travels along the connecting path in ≤ 1.5s and ends on that node |
| Two or more successors | Copies travel along each path and fade; main marker stays on the completed node |
| Zero successors | No travel; marker stays on the completed node |
| User interacts mid-travel | Snap to final state; map remains usable |
| Complete/choose on the map page | Animate from this response before or while refreshing state |
| Return from battle/quiz | Infer origin = latest `completed_at`; destinations = available successors not yet marked seen in `sessionStorage` |
| Screen reader | Announce "Unlocked: {title}, {title}" via the page live region; do not require watching motion |

`sessionStorage` key suggestion: `adventure-travel:{adventureId}:{nodeId}:{completedAt}`.

---

## Mini-map (student only)

- Landmark: `role="navigation"` (or `region`) with accessible name "Adventure overview".
- Visible when the map layout is larger than `#map-container`.
- Viewport rectangle tracks container scroll.
- Marker dot tracks character position.
- Pointer on empty overview: `scrollTo` that map coordinate within 1s.
- Keyboard: focusable marks for unlocked nodes; Enter/Space jumps the main view to that node.
- Phone: overview must not cover the selected node's primary action. Stack or collapse under a toggle named "Overview" if needed.

---

## Student keyboard

| Key | Action |
|-----|--------|
| Tab | Unlocked/in-progress/completed nodes, then detail panel, then mini-map |
| Enter / Space | Open focused node details |
| Esc | Return focus to the map from the detail panel |
| Enter / Space on primary action | Start or complete (existing buttons) |

Locked nodes: `tabindex="-1"`, not a button. Their title and "locked" status remain in a map description or visually, but they are not activatable.

Node accessible name: `{title}, {node_type}, {status}`.

---

## Teacher editor keyboard

| Key | Action |
|-----|--------|
| Tab / Shift+Tab | Cycle nodes (and selected edge if any) |
| Arrow keys | Move focus among nearby nodes |
| Enter | Select focused node and open inspector |
| Esc | Deselect, or close inspector/modal and return to the map |
| Delete / Backspace | Delete selection using existing confirm dialogs |
| `+` / `=` | Zoom in |
| `-` | Zoom out |
| Ctrl/Cmd+Z | Undo last successful place, move, connect, or delete in this session |
| Ctrl/Cmd+Shift+Z or Ctrl/Cmd+Y | Redo |

Editor node accessible name: `{title}, {node_type}`.

Undo after a failed save: do not record the failed command. If undo cannot be applied, announce through `#editor-validation` (`aria-live`) and keep the last successful layout.

View-only / shared preview: shortcuts that mutate the graph are no-ops.

---

## Small screens

Player: map on top, detail panel below (already `lg:flex-row`). Mini-map corner or toggle; primary action always reachable.

Editor: toolbar and inspector wrap; canvas remains the first map region; inspector may stack under the canvas rather than overlapping it.
