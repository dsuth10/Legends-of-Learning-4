# Phase 0 - Research & Decisions: Student UI Remaining Gaps

**Feature**: 004-student-ui-gaps
**Date**: 2026-09-21
**Status**: Decisions finalised; no NEEDS CLARIFICATION items remain.

This feature unifies student chrome and finishes leftover redesign gaps. It does not introduce a frontend framework, a JS build step, or new database tables.

---

## R1 - One shared shell, not copy-paste chrome

**Decision**: Put identity bar, clan/classroom strip, stats, and destination list in one student shell. Pages in scope extend `student/base_student.html` and fill a main-content block (plus an optional page-specific sidebar block). Reuse `_student_header.html` and `_student_sidebar.html` as the only includes. Stop duplicating nav markup in Character / Shop / Equipment / Quests. Delete or leave unused `_student_layout.html` (nothing includes it today).

**Rationale**:

- Character, Shop, Equipment, and Quests each inline a different destination list. That is the FR-002 / FR-020 / FR-021 failure.
- `_student_sidebar.html` already exists but is not used by those pages. Completing it is smaller than a new layout system.
- Leftover pages (`progress.html`, `clan.html`, `profile.html`, `character_create.html`) still extend Bootstrap `base.html`. Switching them to `base_student.html` is the P1 fix.
- Powers already extends `base_student.html` but omits the shell. Adventures list includes the header only.

**Alternatives considered**:

- Flask `context_processor` that injects chrome on every request. Rejected: it would run on teacher routes and add hidden DB work. A student-only helper called from student routes is enough.
- Keep per-page copy-paste and only “make the labels match.” Rejected: the spec requires one chrome, and four copies already drifted.

---

## R2 - Chrome context helper, thin routes

**Decision**: Add `app/services/student_chrome.py` with `student_chrome_context(user)` returning `student_profile`, `main_character`, ordered clan members (current character first), classroom, and display fields for bars. Student HTML routes and the Adventures list route call it and pass the dict into templates. Do not grow `app/routes/student_main.py` with more duplicated profile lookups.

**Rationale**:

- Profile, Clan, Create character, and Adventures list do not pass `main_character` / `student_profile` today, so they cannot render the strip even after a template switch.
- Constitution: business logic in services; keep files under 500 lines when possible. `student_main.py` is already far over that; this feature must not add more copy-paste lookups there.
- One helper also precomputes `party_members` (up to three other clan characters) so Character does not rely on a Jinja `{% set %}` counter, which does not persist across loop iterations.

**Alternatives considered**:

- A Jinja macro that queries the ORM. Rejected: templates should not load clan members.
- Refactor all of `student_main.py` into smaller blueprints. Valuable later, out of scope for this UI pass.

---

## R3 - No schema change; power pictures from type marks

**Decision**: Do not add `abilities.icon` or any other column. Character power slots show each equipped power’s name plus a Material Icon chosen from `Ability.type` (and `special_effect` when set). Names remain the unique label (SC-004). Empty slots stay labelled empty.

**Rationale**:

- `Ability` has no icon or image field. Mapping mentioned `ability.icon`, which does not exist.
- Spec forbids new game systems and prefers no migration. Type marks are distinct from the current generic bolt on every slot.
- Powers page also has no pictures today; giving Character type marks does not require changing learn/equip APIs.

**Alternatives considered**:

- Add `icon` on `abilities` and seed art. Rejected: migration plus content pack for a chrome-unification feature.
- Keep the bolt for all powers. Rejected: FR-017 and SC-004.

**Type → icon map** (implementation may adjust ligatures, not the rule):

| Ability type / effect | Icon intent |
|------------------------|-------------|
| attack | swords |
| defense | shield |
| heal | favorite |
| buff | upgrade |
| debuff | trending_down |
| utility | auto_fix |
| special_effect revive / cheat death | emergency / health_and_safety |

---

## R4 - Truthful resource bars; do not redefine combat properties

**Decision**: Shared chrome displays:

- HP current = `character.health`; HP max = `character.max_health` plus equipped `health_bonus` (computed in the chrome helper).
- Power current = `character.power`; Power max = `character.max_power` (activation resource).
- Power Points = `character.power_points` as a number, not a bar.
- XP = `character.experience` versus the existing next-level amount already used on Character (`level * 1000`).
- Gold = `character.gold` as a number. No decorative fill (remove the hardcoded 85% gold bar).

Do **not** change `Character.total_health` / `total_power` in this feature. Those properties return current value plus bonuses, which is the wrong maximum for a bar and is used elsewhere.

Clan strip HP fill today uses `health / max_health` while some sidebars use `health / total_health`. Unify on the helper’s current/max pair.

**Rationale**:

- FR-007 and FR-019 require live values and proportional fills, not a fake gold percentage.
- Character page already split activation Power from spendable Power Points; Shop/Equipment still label Power as “pp” and use `total_power`. The shared sidebar must use the Character meaning.
- Changing `total_health` semantics would be a combat/display regression risk outside this spec.

**Alternatives considered**:

- Fix `total_health` to `max_health + bonuses` globally. Deferred; needs its own tests and is not required to ship chrome.
- Hide Power Points from leftover pages. Rejected: FR-007 lists them on shared stats.

---

## R5 - Honest controls: hide unfinished chrome

**Decision**: Remove, do not implement:

- Shop “Special Offer” banner
- Equipment Auto Equip and Save Loadout buttons
- Quests “Filter Quests” button
- “Click to Rotate” portrait hint
- Documents/article icon in the identity bar

Clan-mate strip tabs are non-interactive awareness (`role="group"` / not links). They must not impersonate. The clan *name* in the strip may link to `/student/clan`.

**Rationale**: Spec FR-010–FR-016. Mapping already called these future. Showing disabled primary buttons fails SC-002.

**Alternatives considered**:

- Build auto-equip / loadouts / offers / filters now. Rejected: explicit out of scope.
- Grey-out with “coming soon.” Rejected: still looks like a broken action on a classroom screen.

---

## R6 - Leftover pages keep their tasks; only the frame changes

**Decision**: Progress, Powers, Clan, Profile, and Create character keep their current information and POST/JSON behaviour. Wrap them in the shell. Style inner content only enough to sit on the student visual language (fonts, background, cards), not a full redesign without comps.

Adventures **list** joins the shell. Adventure **map** and battle screens stay as they are (spec FR-003 / out of scope).

Login and Welcome are not touched (SC-008).

Unused legacy templates (`student/character.html`, `student/shop.html`) are not routed today; leave them unrouted. Do not resurrect them.

**Rationale**: Spec assumption: leftover pages restyle only enough to sit in shared chrome.

**Create-character**: no character yet, so omit stats bars and clan tabs; show identity (class name if the student has a classroom) plus a short explanation. Successful create still redirects to Character.

**Profile / Clan**: include Character and the rest of the destination list; highlight via a current-page indicator even if those items are not in the seven-button grid (SC-003). Add Clan and Profile as text links in the identity bar (logout already lives there) so they remain reachable.

---

## R7 - Small screens: stack, do not overlay

**Decision**: Add `static/css/student_shell.css`. Below a ~768px breakpoint: clan strip stays horizontal-scroll; stats/destination column stacks above main content (or collapses behind a labelled “Character stats” disclosure) so Shop purchase and Equipment slot actions remain on screen. Non-interactive clan tabs are not in tab order (`tabindex="-1"` unnecessary if they are not `<button>`/`<a>`). Destination links stay real links.

**Rationale**: FR-025–FR-028. The redesign is `h-screen` + `w-80` sidebar, which hides main actions on a phone if the sidebar stays a left column.

**Alternatives considered**:

- Separate mobile templates. Rejected: one shell with CSS is enough for a responsive pass.
- Hide the clan strip on small screens. Rejected: FR-026 requires scroll access to other members.

---

## R8 - Tests: HTML chrome contracts plus existing shop/equip/quest/power tests

**Decision**: New `tests/test_student_ui_shell.py` using the pytest client:

- Each in-scope GET contains shared chrome markers (destination labels, identity class/clan, stats labels when a character exists).
- Character/Shop/Equipment/Quests responses do not contain Special Offer, Auto Equip, Save Loadout, Filter Quests, Click to Rotate, or a clickable article icon.
- Clan-less student: classroom name, single strip tab.
- No-character student: create-character uses the student visual language without fabricated HP numbers.
- Equipped power name appears on Character with a type icon, not a lone generic bolt for every slot.
- Party portraits omitted when the student has no clan-mates.

Keep running existing `tests/test_shop_api.py`, `tests/test_powers.py`, and quest/character tests so FR-022–FR-024 do not regress.

Manual smoke in `quickstart.md` for phone-width and keyboard tab order (hard to assert in pytest without a browser).

**Rationale**: Constitution requires pytest for new features. Chrome is mostly HTML, so response-body assertions are the right automated gate.

---

## Summary of resolved items

| Topic | Resolution |
|-------|------------|
| Shared chrome mechanism | One `base_student.html` shell + two includes |
| Route data | `student_chrome_context` service; no global processor |
| Schema | None |
| Power pictures | Type/special-effect Material Icons + names |
| Resource bars | Helper current/max; gold is an amount; do not change `total_health` |
| Placeholders | Remove unfinished controls |
| Leftover pages | Shell wrap; keep existing tasks |
| Small screens | CSS stack + scrollable clan strip |
| Tests | New shell HTML tests + existing shop/equip/quest/power tests |
