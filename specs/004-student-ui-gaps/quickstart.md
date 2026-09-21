# Quickstart - Student UI Remaining Gaps

**Feature**: 004-student-ui-gaps
**Date**: 2026-09-21
**Audience**: developers implementing or verifying the student chrome unification.

This quickstart assumes specs 001–003 are already present. No new Alembic migration is expected.

---

## 1. Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| Python | 3.8+ | project constitution |
| pip | latest | install project dependencies |
| SQLite | bundled with Python | local `instance/legends.db` |
| Browser | Chrome / Firefox / Edge / Safari | desktop plus a phone-sized window |

No Node install or JS build step is required.

---

## 2. Setup

```bash
# from repo root
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt -r requirements-dev.txt

alembic upgrade head
```

---

## 3. Run tests

Chrome contract:

```bash
pytest tests/test_student_ui_shell.py -q
```

Expected coverage:

- In-scope student GETs include destination labels Character, Quests, Shop, Equipment, Adventures, Progress, Powers.
- Current destination is indicated on Character, Quests, Shop, and Equipment.
- Shop/Equipment/Quests/Character HTML does not include Special Offer, Auto Equip, Save Loadout, Filter Quests, or Click to Rotate.
- Identity bar shows class name (and clan name when the fixture character is in a clan), not a comma-separated member list as the primary identity.
- Clan-less student: classroom label and a single strip tab.
- No-character student: create-character page has no fabricated HP value.
- Equipped ability name is visible on Character.
- Party portrait cluster absent when there are no clan-mates.

Regression (must still pass):

```bash
pytest tests/test_shop_api.py tests/test_powers.py tests/test_equipment_data_integration.py tests/test_character_management.py -q
```

Adventures list still lists assignments:

```bash
pytest tests/test_adventure_routes_student.py -q
```

---

## 4. Run the app

```bash
python run.py
```

Open `http://127.0.0.1:5000/`. Log in as a student who has a character.

---

## 5. Manual smoke

### Shared chrome (SC-001, SC-003)

1. Open Character. Confirm class (and clan) in the identity bar, strip with HP/power, stats, and destinations.
2. Visit Quests, Shop, Equipment, Adventures list, Progress, Powers, Clan, Profile. Each uses that frame; the current destination is obvious.
3. Confirm you never land on the old generic Bootstrap student layout for those pages.

### Honest controls (SC-002)

4. On Shop, there is no fake sale banner.
5. On Equipment, Auto Equip and Save Loadout are gone.
6. On Quests, Filter Quests is gone.
7. No rotate hint on the portrait; no dead documents icon in the identity bar.
8. Clicking another clan-mate tab does not sign you in as them.

### Finished redesigned pages (SC-004, SC-005, SC-007)

9. Equipped powers on Character show distinct names and type icons.
10. With clan-mates, portraits appear; without, they do not.
11. Gold shows a real amount; HP/power fills match current versus max.
12. Buy an affordable shop item, equip something, start or turn in a quest.

### Small screen (SC-006)

13. Narrow the window to phone width (~390px). Read HP and gold, open Shop, complete a purchase if you can afford an item. Clan tabs scroll rather than overflowing with no access.

### Create character / login (SC-007, SC-008)

14. As a student with no character, open Create character: same visual language, no fake stat bars. Submit still reaches Character.
15. Log out. Login and Welcome still match their existing redesign.

---

## 6. Out of scope checks (do not “fix” these in 004)

- Adventure map travel, mini-map, and battle screens.
- Teacher pages.
- Implementing special offers, auto-equip, loadouts, or quest filters.
