# Implementation Plan: Student UI Remaining Gaps

**Branch**: `004-student-ui-gaps` | **Date**: 2026-09-21 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/004-student-ui-gaps/spec.md`

**Note**: Git may still be on `003-adventure-player-polish`; Speckit locates this feature via `.specify/feature.json`. Create or switch to `004-student-ui-gaps` when implementation starts if you want the branch name to match the spec directory.

## Summary

Close remaining student-UI redesign gaps: one shared chrome on every in-scope student destination, remove unfinished controls that look clickable, finish Character / Quests / Shop / Equipment against the comps, and keep the shell usable on a phone-sized screen. Implementation stays on Flask + Jinja + Tailwind-in-template + a small CSS file. No new tables, no new student JSON APIs, no frontend build step.

**Technical approach** (validated in Phase 0 — see `research.md`):

- One `base_student.html` shell using `_student_header.html` and `_student_sidebar.html`; leftover pages stop extending Bootstrap `base.html`.
- `app/services/student_chrome.py` builds profile, character, clan-member order, bar maxes, and party members so routes stay thin.
- Power slot pictures are Material Icons from `Ability.type` / `special_effect`; no `abilities.icon` column.
- Resource bars use helper current/max (HP includes equipment health bonus on max; gold is an amount). Do not change `Character.total_health` / `total_power`.
- Delete unfinished chrome (special offer, auto-equip, loadout, quest filter, rotate hint, dead article icon). Clan tabs are non-interactive awareness.

## Technical Context

**Language/Version**: Python 3.8+ for backend code; JavaScript only where Shop/Equipment/Quests/Powers already use it; Jinja2 templates.

**Primary Dependencies**: Flask, Flask-Login, Flask-SQLAlchemy, Jinja2, Tailwind via CDN on `base_student.html` (already in use). No new Python packages.

**Storage**: Existing Student / Character / Clan / Ability / Inventory / Quest tables. No migration. Chrome is request-derived.

**Testing**: pytest with `tests/conftest.py`; new `tests/test_student_ui_shell.py` for HTML chrome contracts. Regression: `tests/test_shop_api.py`, `tests/test_powers.py`, `tests/test_equipment_data_integration.py`, `tests/test_character_management.py`, `tests/test_adventure_routes_student.py`. Browser smoke in `quickstart.md`.

**Target Platform**: Existing Flask web app; modern desktop browsers plus a phone-sized responsive pass. No native app.

**Project Type**: Single Flask web application with server-rendered templates.

**Performance Goals**:

- Chrome helper does one student + active character lookup and, when clanned, one member list (no per-tab queries in the template).
- In-scope GETs remain ordinary server-rendered pages (no extra round trips for the frame).

**Constraints**:

- No new JavaScript build pipeline or frontend framework.
- No schema changes.
- Existing shop / equip / quest / powers request shapes stay the same.
- Adventure map and battle layouts are unchanged.
- Login and Welcome are unchanged.
- `student_main.py` must not gain another copy of profile/character loading; use the chrome service.
- JSON responses for existing student APIs keep their current envelopes.

**Scale/Scope**: One signed-in student at a time. Ten in-scope HTML destinations. Clan strip sized for a typical classroom clan (horizontal scroll if larger). Power grid shows at most six equipped abilities.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

The constitution at `/constitution.md` defines gates for code style, testing, architecture, database practices, security, error handling, documentation, project structure, API patterns, and service layering.

| # | Gate | Requirement | Plan adherence | Status |
|---|------|-------------|----------------|--------|
| G-1 | Code Style | Python 3.8+, PEP 8, readable focused functions | Chrome assembly in a dedicated service; type-to-icon map as a small function, not inline in templates. | PASS |
| G-2 | Testing | pytest coverage for new features and errors | HTML chrome tests for presence/absence; keep shop/equip/quest/power tests. Manual smoke for phone and keyboard. | PASS |
| G-3 | Architecture | Routes / models / services separated | `student_chrome.py` for context; routes only call it and render; no ORM in Jinja. | PASS |
| G-4 | Database / Migrations | SQLAlchemy + Alembic for schema changes | No schema changes. | PASS |
| G-5 | Authentication / Authorization | Flask-Login and role checks | Existing `@login_required` / `@student_required`; clan tabs cannot switch user. | PASS |
| G-6 | Templates / Static Files | Jinja2 by role, static under `/static` | Student templates only; new `static/css/student_shell.css`. | PASS |
| G-7 | Security | Validate input, no secrets | No new inputs. Create-character and profile POSTs keep existing validation. | PASS |
| G-8 | Error Handling | Status codes and meaningful errors | Existing flash/JSON errors unchanged. Missing character on chrome pages already has create-character paths. | PASS |
| G-9 | API Patterns | Pydantic + envelope where JSON exists | No new JSON endpoints. Existing student APIs untouched. | PASS |
| G-10 | Project Structure | Established directories | Files under `app/`, `static/`, `tests/`, `specs/`. | PASS |

**Initial gate decision**: PASS — no constitution violations, no Complexity Tracking entries required.

**Re-check after Phase 1 design**: PASS — data model is view composition over existing entities; the only contract is HTML chrome plus “do not break existing POSTs.” No new architecture, migration, or API envelope.

## Project Structure

### Documentation (this feature)

```text
specs/004-student-ui-gaps/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── student-chrome.md
├── checklists/
│   └── requirements.md
├── spec.md
└── tasks.md             # Phase 2 output, not created by /speckit-plan
```

### Source Code (repository root)

```text
app/
├── services/
│   └── student_chrome.py              # NEW — context, bar maxes, party members, power icon map
├── routes/
│   ├── student_main.py                # Pass chrome context; do not add more lookups
│   └── adventures/
│       └── student.py                 # Pass chrome context into adventures_list.html
└── templates/
    └── student/
        ├── base_student.html          # Own the shell (header + strip + optional sidebar slot)
        ├── _student_header.html       # Identity + clan strip (class/clan names; no article icon)
        ├── _student_sidebar.html      # Stats + destination list (single source)
        ├── character_new.html         # Use shell; real power icons; party_members from view
        ├── shop_new.html              # Use shell; drop special offer
        ├── equipment_new.html         # Use shell; drop auto-equip/loadout/rotate
        ├── quests_new.html            # Use shell; drop filter button
        ├── powers.html                # Wrap in shell
        ├── progress.html              # Switch from base.html to shell
        ├── clan.html                  # Switch from base.html to shell
        ├── profile.html               # Switch from base.html to shell
        ├── character_create.html      # Student visual language, no fake stats
        └── adventures_list.html       # Full shell, not header-only

static/
└── css/
    └── student_shell.css              # NEW — small-screen stack, strip scroll, tab-order-safe tabs

tests/
└── test_student_ui_shell.py           # NEW — chrome HTML contracts
```

**Structure Decision**: Stay in the existing single-app Flask layout. Prefer a chrome service and one shell over duplicating nav in each template. Do not add a frontend package or a new blueprint. Unused `_student_layout.html` and unrouted `character.html` / `shop.html` are not implementation targets.

## Complexity Tracking

> No constitution violations were identified. This section is intentionally empty.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| *(none)* | *(n/a)* | *(n/a)* |
