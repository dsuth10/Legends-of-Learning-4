# UI Contract - Student Chrome

**Feature**: 004-student-ui-gaps
**Date**: 2026-09-21

This is a page-composition contract. Shop buy, equipment equip/unequip, quest start/complete, and powers learn/equip/use keep their existing endpoints. This feature adds no student JSON APIs.

---

## In-scope HTML destinations

| Page | Method | Path |
|------|--------|------|
| Character | GET | `/student/character` |
| Quests | GET | `/student/quests` |
| Shop | GET | `/student/shop` |
| Equipment | GET | `/student/equipment` |
| Progress | GET | `/student/progress` |
| Powers | GET | `/student/powers` |
| Clan | GET | `/student/clan` |
| Profile | GET | `/student/profile` |
| Create character | GET | `/student/character/create` |
| Adventures list | GET | existing student adventures list path |

Excluded: adventure map HTML, battle HTML, login, welcome, all teacher pages.

---

## Shared chrome landmarks

Every in-scope GET (except Create character, which omits stats/strip numbers) MUST include:

1. **Identity bar** — class name when the student has a classroom; clan name when in a clan; teacher avatar when present; logout. MUST NOT include a documents/article control with no destination.
2. **Clan or classroom strip** — current character first and highlighted, with HP and power; other clan members after, HP and power, not focusable as buttons. Classroom-only students: one tab, classroom label.
3. **Stats column** (when a character exists) — HP, Power, Power Points, XP, Gold using live values (research R4).
4. **Destination list** — links to Character, Quests, Shop, Equipment, Adventures, Progress, Powers. The current destination is indicated (active class, `aria-current="page"`, or equivalent). Clan and Profile use an equivalent current indicator when those pages are open.

Create character MUST use the same visual language and MUST NOT render invented HP/power numbers.

---

## Forbidden chrome (must be absent)

These strings/controls MUST NOT appear as available actions on Character, Quests, Shop, or Equipment:

| Forbidden | Where it is today |
|-----------|-------------------|
| Special Offer / wandering merchant sale copy | Shop sidebar |
| Auto Equip | Equipment |
| Save Loadout | Equipment |
| Filter Quests | Quests |
| Click to Rotate | Character / Equipment |
| Clickable article / documents icon with no href | Identity bar |

Clan-mate tabs MUST NOT submit a login or character-switch request.

---

## Character-specific chrome

- Equipped powers: up to six slots; each filled slot shows `ability.name` and a type/effect icon; empty slots labelled Empty.
- Party portraits: other clan members only; omit the cluster when there are none.
- Equipment is a destination in the shared list (not Character-only via a one-off button).

---

## Behaviour that must still work (existing contracts)

Unchanged request/response shapes:

- `POST /student/shop/buy` — JSON `{item_id, item_type}`
- `PATCH /student/equipment/equip` — JSON `{inventory_id, slot}`
- `PATCH /student/equipment/unequip` — JSON `{inventory_id}`
- `POST /student/quests/start/<quest_id>` and complete — existing form/redirect
- Powers learn / equip / use — existing JSON routes

After the shell change, these MUST still succeed for a student who could succeed before (FR-022–FR-024, SC-005).

---

## Small screens and keyboard

- Viewport ~390×844: HP, gold, destination links, and the page primary action (buy / equip / selected quest action / character portrait) MUST be reachable without an overlay covering them.
- Overflowing clan strips: horizontal scroll; current student remains identifiable.
- Destination links are `<a>` (or equivalent) in tab order.
- Clan-mate awareness tabs are not buttons and are not in tab order.

---

## Adventures list context

`list_adventures` HTML MUST receive the same chrome context as other student pages (`main_character`, `student_profile`, or the helper’s dict) so the shell can render. JSON `format=json` for that route is unchanged and does not include chrome.
