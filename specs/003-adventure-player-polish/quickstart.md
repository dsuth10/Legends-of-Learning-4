# Quickstart - Adventures Player and Editor Polish

**Feature**: 003-adventure-player-polish
**Date**: 2026-09-21
**Audience**: developers implementing or verifying Phase 5 polish.

This quickstart assumes specs 001 and 002 are already present in the codebase.

---

## 1. Prerequisites

| Tool | Version | Notes |
|---|---|---|
| Python | 3.8+ | project constitution |
| pip | latest | install project dependencies |
| SQLite | bundled with Python | local `instance/legends.db` |
| Browser | Chrome / Firefox / Edge / Safari | player travel, mini-map, keyboard, reduced motion |

No Node install or JS build step is required. No new Alembic migration is expected.

---

## 2. Setup

```bash
# from repo root
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt -r requirements-dev.txt

alembic upgrade head
```

If implementation discovers a missing CHECK or column (it should not), add a migration and run `alembic upgrade head` before testing.

---

## 3. Run Route Tests

Focused tests after implementation:

```bash
pytest tests/test_adventure_routes_teacher.py tests/test_adventure_routes_student.py -q
```

Expected new coverage:

- Teacher can assign a published adventure to a clan in their class and to a character in their class.
- Duplicate active assignment to the same clan or character returns `CONFLICT`.
- Other-teacher clan/character is `FORBIDDEN`.
- Class assignment still succeeds and student play is unchanged (SC-008).
- Assignment list JSON includes clan and character rows with `target_type` / `target_label`.
- Progress `?assignment_id=` returns the clan or individual roster.
- Student who started under a clan assignment can still load the map after `character.clan_id` is cleared; a classmate who never started cannot.
- Node `icon_url` save, clear (`null`), and student state echo the stored value.
- Icon catalog lists every `node_type` exactly once as a default.

Broader graph/unlock smoke if assignment matching changes:

```bash
pytest tests/test_adventure_graph_unlock.py tests/test_adventure_routes_student.py tests/test_adventure_routes_teacher.py -q
```

Legacy quests must still pass:

```bash
pytest tests/test_quest_models.py -q
```

---

## 4. Run The App

```bash
python run.py
```

Open `http://127.0.0.1:5000/`. Log in as a teacher and as a student (separate browsers or profiles).

Seed if needed:

```bash
flask --app run:app seed-db
```

---

## 5. Manual Smoke - Travel (P1)

1. Assign a linear adventure (start → story → end) to a class and open it as a student.
2. Complete the start/story node on the map. Confirm a marker travels to the newly available node in under 1.5s.
3. Complete the end node. Confirm no travel and the marker stays.
4. Open DevTools → Rendering → emulate CSS `prefers-reduced-motion: reduce`. Complete a node. Confirm states update with no motion.
5. Start a battle node, win the battle, return to the map. Confirm travel toward newly unlocked successors plays once.

---

## 6. Manual Smoke - Mini-map (P2)

1. Open an adventure whose nodes do not fit in one screen (or temporarily shrink the window).
2. Confirm the overview appears, shows the current view, and shows the marker.
3. Click a distant region: main view jumps there within one second.
4. Tab to an overview node mark and press Enter: main view jumps to that node.
5. Narrow to a phone width. Confirm the primary node action is not covered by the overview.

---

## 7. Manual Smoke - Keyboard (P3)

**Editor**

1. Tab to a node, Enter to inspect, Esc to deselect.
2. Delete a node with Delete (confirm). Ctrl+Z restores it; Ctrl+Y (or Ctrl+Shift+Z) deletes again.
3. `+` / `-` zoom the canvas. Drag still saves the correct coordinates after zoom.

**Player**

1. Tab among unlocked nodes only. Enter opens details. Complete a story node from the keyboard.
2. Locked nodes are not in the tab order. A screen reader or the node name includes status.

---

## 8. Manual Smoke - Clan / individual assignment (P4)

1. On Assign, switch target from class to a clan. Assign. Only that clan's students see the adventure.
2. Assign the same published adventure to one student in another class. Only that student sees it from the new assignment.
3. Existing class assignment still lists and plays.
4. Deactivate the clan assignment. Those students cannot start new nodes from it.
5. Progress filter includes the clan and individual targets by name.

---

## 9. Manual Smoke - Icons (P5)

1. Select a battle node, pick a non-default icon, save. Reopen the editor: same icon.
2. Open the student map: same icon on that node.
3. Clear override: both views show the battle default.
4. Change node type with an override still set: picker still shows the stored icon versus the new type default.

---

## 10. Done when

- Route tests above pass.
- Manual smokes for P1–P5 pass on desktop and one phone-sized window.
- `pytest tests/test_quest_models.py` still passes.
- No new JS build step was added.
