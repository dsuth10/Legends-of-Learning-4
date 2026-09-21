# Now / Next

**This is the product-direction source of truth.** When someone asks what to work on next, read this file first. Do not invent a new backlog, and do not treat older planning docs as current unless this file points at them.

Last reviewed: 2026-09-21

---

## How to use this file

- **Humans:** update the Current / Next / Later sections whenever a feature ships or the direction changes.
- **Agents:** start here for "what's next", then open only the spec or plan named below. After shipping work, mark the current item done and promote the next candidate — do not leave this file stale.
- **Speckit** (`specs/<id>-*/`) remains the implementation source for the *active* feature. This file decides *which* feature is active.
- Keep this short. Detail belongs in the linked spec, roadmap, or idea note.

---

## Current

**No active feature.** Spec 004 (student UI remaining gaps) is shipped: one student shell on Character, Quests, Shop, Equipment, Adventures list, Progress, Powers, Clan, Profile, and Create character; unfinished placeholder controls removed; small-screen stack in `student_shell.css`.

---

## Next

Stay on Adventures only if original roadmap Phase 6 is explicitly chosen.

1. **Adventures optional later** — cross-teacher clone, public sharing, clan-shared progress, time-limited nodes, difficulty analytics, legacy-quest migration. Source: [Ideas/Adventures Quest Map System - Roadmap.md](../Ideas/Adventures%20Quest%20Map%20System%20-%20Roadmap.md) §17 Phase 6.

---

## Later / parked

These are real ideas, not the current queue:

| Item | Where | Notes |
|------|--------|--------|
| Adventures original roadmap | `Ideas/Adventures Quest Map System - Roadmap.md` | Vision doc for 001. Foundation + MVP are shipped. Use for later phases only. |
| Editor three-feature plan | `Ideas/Adventure-editor-three-features-plan.md` | Became spec 002. Keep as background, not as a task list. |
| Student UI redesign comps | `Ideas/Student UI redesign/` | Mock HTML/screens; mapping in `docs/student-ui-redesign-mapping.md`. |
| Classcraft Powers research | `Ideas/Give me a detailed rundown of the Powers system —.md` | Research dump. In-game powers/behavior already exist in code. |
| Classcraft Consequence research | `Ideas/Consequence_Sentence system — points deducted for.md` | Research dump. Classroom behavior + Cursed Die already shipped. |

---

## Planning systems in this repo (what each is for)

Use this table instead of creating another tool.

| System | Location | Role | Status |
|--------|----------|------|--------|
| **Now / Next (this file)** | `docs/now.md` | What to work on *now* | **Use this** |
| **Speckit** | `specs/001-adventures-map-system/`, `specs/002-adventure-editor-enhancements/`, `specs/003-adventure-player-polish/`, `specs/004-student-ui-gaps/`, `.specify/` | Spec → plan → tasks for one feature | 001 complete (103/103). 002 complete including Phase 6 polish. 003 implemented (player polish, assignment targets, icons). **004 is shipped** (shared student chrome, honest controls, leftover pages wrapped). No next Speckit feature is queued. |
| **Constitution** | `constitution.md` | Coding/architecture gates for Speckit plans | Active |
| **Adventures roadmap** | `Ideas/Adventures Quest Map System - Roadmap.md` | Product vision and later phases | Draft; 001 implemented most of Phases 0–4 |
| **BMAD brownfield docs** | `docs/index.md`, `docs/project-overview.md`, `docs/architecture.md`, … | Codebase snapshot for onboarding | Generated 2025-01-27; useful background, not a backlog |
| **BMAD workflow status** | `docs/bmm-workflow-status.yaml` | Method track: next workflow = PRD | Stalled. `docs/prd.md` is an empty shell. Do not resume unless choosing BMAD over Speckit. |
| **Project analysis** | `PROJECT_ANALYSIS_AND_RECOMMENDATIONS.md` | Old prioritized backlog | **Stale.** Quest/shop fixes, teacher shop, powers, and behavior have since shipped. Do not follow its "start here" order. |
| **Quest/shop fix plan** | `app/routes/QUEST_SHOP_FIX_PLAN.md` | Historical bug plan | Likely done (see commits around shop/quest error handling). Keep as archaeology. |
| **Older planning notes** | `.planning_docs/` | Pre-Adventures quest assignment notes | Historical |
| **Taskmaster** | `.taskmaster/` | Config + PRD template only | Unused (no `tasks.json`). Do not start using it unless replacing Speckit. |
| **Root spec** | `spec.md` | High-level product description | Generic "future enhancements"; not a queue |

**Recommended default:** Speckit for implementation, this file for direction. Do not run BMAD, Taskmaster, and Speckit as parallel backlogs.

---

## Shipped recently (so we do not re-plan them)

- Student UI remaining gaps (spec 004): one shared student shell, leftover pages off Bootstrap `base.html`, unfinished placeholder controls removed, truthful stats/power icons, small-screen stack.
- Adventures map system (spec 001): models, teacher editor, student play, branching, assignment, rewards.
- Adventure editor enhancements (spec 002): quiz question-set picker, in-editor settings, drag-to-reposition, Phase 6 polish.
- Adventures player/editor polish (spec 003): travel animation, mini-map, keyboard/undo/zoom, clan and individual assignment, node icon library.
- Classroom behavior: infractions, fallen events, Cursed Die (`app/models/behavior.py`).
- Powers / abilities as in-game character skills.
- Teacher shop configuration UI.
