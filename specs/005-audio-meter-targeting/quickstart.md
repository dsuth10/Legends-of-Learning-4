# Quickstart: Audio Meter Targeting

**Feature**: 005-audio-meter-targeting
**Date**: 2026-09-21
**Plan**: [plan.md](plan.md) | **Contracts**: [contracts/audio-meter-api.md](contracts/audio-meter-api.md)

How to set up, run, and verify this feature during development.

---

## 1. Schema setup

The feature adds one table. After the model and migration land:

```powershell
alembic upgrade head
```

Per the repository's database-management rule, do this before starting Flask, or the app logs a DB version mismatch warning. Never substitute `db.create_all()`.

Verify the table exists:

```powershell
python -c "from app import create_app; from app.models import db; app=create_app(); ctx=app.app_context(); ctx.push(); print(db.engine.table_names() if hasattr(db.engine,'table_names') else db.inspect(db.engine).get_table_names())"
```

`audio_meter_sessions` should be in the list.

No data migration is needed for the new `hp_damage_enabled` setting: `_merge_volume_config` backfills it as `False` for every existing classroom row on the next read.

---

## 2. Run the app

```powershell
python run.py
```

Sign in as a teacher who owns at least one active classroom containing two clans and a few students with active characters. If you need such data, the `scripts/` directory holds the seeding utilities this repo already uses.

---

## 3. Configure the meter

1. Go to **Classroom Tools** in the teacher sidebar (`/teacher/classroom-tools`).
2. Pick the class.
3. For fast manual testing, set:
   - Timer: `1` minute (the shortest allowed)
   - Threshold: around `20%` so a normal voice trips it
   - Breach duration: `1` second
   - Breach cooldown: `2` seconds
   - Base XP: `1000`, Base gold: `100` (matches the spec's worked example)
   - HP damage on trigger: **off** (this is the default)
4. Save, then use **Launch display**.

---

## 4. Verify the reward tiers

On the display, choose participants and press Start. Allow microphone access.

| Steps | Expected per-participant award |
|-------|-------------------------------|
| Stay quiet for the full minute | 1000 XP, 100 gold |
| Make noise once, then stay quiet | 500 XP, 50 gold |
| Make noise twice | 250 XP, 25 gold |
| Make noise three times | 125 XP, **13** gold |

The third-trigger gold value is the point of the feature: 12.5 rounds **up** to 13. Seeing 12 means the ceiling formula is not being applied.

Check the displayed potential reward updates the moment each trigger fires, and that the number shown comes from the trigger response rather than a local multiplier.

---

## 5. Verify targeting

1. Start a session with only **one clan** selected.
2. Complete it quietly.
3. Confirm every member of that clan gained the full reward, and that students in the other clan and unclanned students are unchanged in XP, gold, and HP.
4. Repeat selecting **two individual students**, and again selecting **one clan plus a student who is already in that clan** — that student must be rewarded exactly once, not twice.

Quick check from a shell:

```powershell
python -c "from app import create_app; from app.models import db; from app.models.character import Character; app=create_app(); ctx=app.app_context(); ctx.push(); [print(c.id, c.name, c.experience, c.gold, c.health) for c in Character.query.filter_by(is_active=True).all()]"
```

---

## 6. Verify the trust requirement

This is the security-relevant check. With a session running, from the display's devtools console:

```js
await fetch(location.origin + '/teacher/api/classroom-tools/17/audio-meter/sessions/12/complete', {
  method: 'POST',
  credentials: 'same-origin',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ xp_amount: 100000, gold_amount: 100000, paused_ms: 0 }),
}).then(r => r.json());
```

Substitute the real class and session ids. Expected outcomes:

- Before the timer has elapsed: HTTP 409 and no XP or gold change anywhere.
- After the timer has elapsed: success, but `xp_awarded_each` and `gold_awarded_each` equal the derived tier. The 100000 values are ignored entirely.

---

## 7. Verify HP is optional

1. With HP damage off (default), trigger the meter and confirm no participant's `health` changes while the reward tier halves.
2. Turn HP damage on in settings, save, start a **new** session (settings are locked at start, so an already-running session keeps the old flag), trigger it, and confirm only snapshot participants lose the configured HP.
3. Confirm no `behavior_incidents` row was created by the audio meter:

```powershell
python -c "from app import create_app; from app.models import db; from app.models.behavior import BehaviorIncident; app=create_app(); ctx=app.app_context(); ctx.push(); print(BehaviorIncident.query.count())"
```

The count must not increase because of audio meter activity.

---

## 8. Verify student visibility

Sign in as a rewarded student and open **Progress**. The recent activity feed should include an entry like:

> Classroom tool reward — Quiet-time reward: 250 XP and 25 gold (halved twice after 2 noise triggers)

This works because the feed queries `AuditLog.character_id == character.id` and renders `event_data['description']`, and this feature writes one reward row per character rather than only a batch row.

---

## 9. Session lifecycle checks

| Action | Expected |
|--------|----------|
| Pause mid-session, wait, resume | Countdown and listening resume; trigger count and tier unchanged |
| Press Reset before the timer ends | Session becomes `abandoned`, nothing awarded |
| Reload the display mid-session | Nothing awarded; starting again creates a new session and returns `superseded_session_id` for the stale one |
| Start a second session while one is active | First becomes `abandoned` with no award |
| Deny microphone permission | Clear message, no session started, no award or penalty |
| Select a student with no active character | Session starts, that student appears in `skipped_student_ids`, others still rewarded |
| Select all students who have no characters | 400 `NO_PARTICIPANTS`, no session row |

---

## 10. Run the tests

```powershell
pytest tests/test_audio_meter.py -v
```

Then the full suite before committing:

```powershell
pytest
```

---

## Troubleshooting

| Symptom | Likely cause |
|---------|--------------|
| Gold shows 12 instead of 13 at the third tier | Floor rounding still in play; check `tier_amount` is used server-side and that the display renders the trigger response |
| DB version mismatch warning on startup | `alembic upgrade head` not run after the migration landed |
| Meter shows "Missing class or API URLs" | Display page did not receive the new session URLs; check `classroom_tools_display.html` and `buildToolConfig` in `classroom_tools_display.js` |
| Microphone never registers level | Page not served over a secure context or permission blocked at the browser level; `getUserMedia` requires localhost or HTTPS |
| Completion always 409 | Elapsed-time check failing; confirm `timer_seconds` on the session row and the `paused_ms` the client reports |
| Non-participants also rewarded | Award loop iterating the classroom instead of `participant_character_ids` |
