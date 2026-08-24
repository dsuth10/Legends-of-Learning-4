# Legends of Learning — Project Completion Roadmap

**Repository:** `dsuth10/Legends-of-Learning-4`  
**Document date:** 24 August 2026  
**Purpose:** Consolidate the original project vision, the current implementation state, known architectural risks, and a practical staged plan to deliver a stable classroom-ready `v1.0.0` release.

---

## 1. Executive Summary

Legends of Learning is no longer an early prototype. The project has evolved into a substantial local-first Flask application with teacher and student interfaces, persistent game state, character progression, powers, clans, equipment, a shop, behaviour consequences, battles, analytics, classroom tools, and a sophisticated graph-based Adventure system.

The most important conclusion from the current audit is that the project does **not** primarily need another large round of feature development. The shortest route to completion is now:

1. **Repair release-critical infrastructure**, especially database migrations.
2. **Consolidate duplicate sources of truth** for student/character state and classroom membership.
3. **Centralise game rules** so quests, adventures, battles, behaviour, powers, and teacher tools all modify state consistently.
4. **Make Adventures the canonical learning-path system** and treat real classroom activities as first-class Adventure nodes.
5. **Build a Live Classroom control centre** so teachers can actually run the gamification system while teaching.
6. **Finish local/offline deployment**, backup/restore, end-to-end testing, and classroom pilot work.
7. **Freeze scope and release `v1.0.0`** only when the entire classroom workflow is reproducible from a fresh install.

The project should now be treated as **late alpha**. It has already proved that the core product can be built. The main remaining challenge is to make the systems coherent, reproducible, robust, and easy to operate in a real classroom.

> **Strategic shift:** Stop measuring progress by the number of features added. Start measuring progress by complete classroom workflows that cannot break.

---

## 2. Original Product Direction

The original design was a local Classcraft-style gamified classroom web application running on a teacher-controlled machine and accessed by students through web browsers over the local network.

The early project plan emphasised:

- RPG-style characters and classes.
- XP, HP, and a spendable power/action resource.
- Positive behaviour rewards and negative behaviour consequences.
- Teams/clans and cooperative powers.
- Classroom quests linked to real learning activities.
- A teacher administrative role.
- Multiple teacher-created classes.
- A student-first-login character creation flow.
- Gold and a shop for cosmetic/gameplay equipment.
- Local persistence rather than dependence on an external cloud service.
- A browser-based interface that works on classroom devices.

The project initially considered local JSON persistence, but the implemented application evolved into a more appropriate Flask + SQLAlchemy + SQLite architecture. That change should be retained. The current relational data model is now too rich for a return to JSON storage to be beneficial.

---

## 3. Original Build Schedule Compared with Current State

The original build schedule can still be used as a useful high-level progress indicator.

| Original stage | Original intent | Current project state | Assessment |
|---|---|---|---|
| **1. Core mechanics** | Character classes, XP, HP, power/action points, rewards and consequences | XP, levels, HP, Gold, Powers, Power Points, class-specific abilities, Fallen state, consequences, equipment and battles exist | **Substantially built; rules need consolidation** |
| **2. Data/backend** | Local persistence and game-state management | Flask, SQLAlchemy, SQLite, models, services, migrations, audit logs, backups and WAL support exist | **Strong foundation; migration history is currently a release blocker** |
| **3. Basic frontend** | Browser UI for teacher/student workflows | Extensive Jinja/Bootstrap/JavaScript teacher and student interfaces exist | **Well beyond basic** |
| **4. Teams** | Student teams/clans and cooperation | Clans, clan metrics, team powers, Fallen rescues and cascade mechanics exist | **Mostly built** |
| **5. Teacher tools** | Class/student/quest management and classroom control | Classes, students, quests, Adventures, shop settings, behaviour, analytics, backup and classroom tools exist | **Mostly built** |
| **6. Polish/deployment** | Robustness, deployment, testing, documentation | Partial | **This is now the main project phase** |

The original roadmap has therefore done its job. The project now requires a **completion roadmap**, not another expansion roadmap.

---

# Part I — Verified Current State

## 4. Current Technical Architecture

### 4.1 Backend

The application is a monolithic Flask web application using:

- Python
- Flask
- Flask-Login
- Flask-JWT-Extended
- Flask-SQLAlchemy
- SQLAlchemy
- Alembic / Flask-Migrate
- SQLite
- Pydantic
- Pytest

The application uses the Flask application-factory pattern and feature-oriented Blueprints.

### 4.2 Frontend

The user interface is primarily:

- Server-rendered Jinja templates
- Bootstrap 5
- Bootstrap Icons
- Vanilla JavaScript
- Selective AJAX/`fetch()` interactions
- Chart.js for some analytics

There is no React/Vue/Angular application and no Node build pipeline required for normal development.

### 4.3 Persistence

SQLite is the default database. The database configuration enables:

- foreign-key enforcement;
- WAL journal mode;
- connection timeouts;
- SQLAlchemy connection pooling for file-based databases.

For a teacher machine serving one classroom over a local network, this remains a sensible architecture.

### 4.4 Major Implemented Domains

The current model registry includes systems for:

- users;
- teachers;
- students;
- classrooms;
- characters;
- clans;
- equipment and inventory;
- powers/abilities;
- shop configuration and purchases;
- quests and quest logs;
- question sets;
- monsters and battles;
- achievement badges;
- behaviour incidents;
- Fallen events and Cursed Die outcomes;
- classroom tools;
- audit logging;
- Adventures, Adventure nodes and edges;
- Adventure assignments and progress.

This is already a substantial application domain.

---

## 5. Major Existing Product Capabilities

### 5.1 Teacher workflows

The application currently provides substantial support for:

- creating and managing multiple classes;
- creating and managing students;
- importing students;
- managing character information;
- organising clans;
- assigning rewards and game resources;
- creating and assigning quests;
- creating Adventure maps;
- monitoring Adventure progress;
- configuring shop items;
- managing behaviour consequences;
- using classroom tools;
- viewing analytics;
- creating database backups and exporting table data.

### 5.2 Student workflows

Students can currently interact with systems including:

- character creation;
- class selection;
- avatar selection;
- character stats;
- powers;
- Power Points;
- equipment;
- inventory;
- Gold;
- the shop;
- clans;
- quests;
- Adventures;
- battles;
- progress and activity history;
- Fallen/rescue mechanics.

### 5.3 Character classes and powers

The current application uses three primary classes:

- **Warrior**
- **Sorcerer**
- **Druid**

The current seeded power data includes class-specific and universal powers across basic, advanced and elite tiers.

Examples include:

- Warrior defensive and team-protection abilities;
- Sorcerer power/focus transfer and utility abilities;
- Druid healing and revival abilities;
- universal real-world classroom privileges.

The system also supports:

- prerequisites;
- level requirements;
- Power Point costs;
- equipped powers;
- power costs;
- cooldowns;
- status effects;
- single-self, single-ally and all-allies targeting.

### 5.4 Behaviour system

The newer behaviour system includes:

- classroom-specific behaviour settings;
- teacher-defined infractions;
- configurable HP deductions;
- recorded behaviour incidents;
- Fallen state when HP reaches zero;
- a rescue window;
- clanmate rescue interactions;
- configurable Cursed Die outcomes;
- team/cascade damage;
- audit logging.

This is a strong implementation of the negative-consequence side of the classroom RPG loop.

### 5.5 Adventure system

The Adventures system is one of the most advanced pieces of the current codebase.

It supports node types including:

- Start
- Story
- Battle
- Quiz
- Choice
- Reward
- Milestone
- Boss
- End

It also supports:

- directed graph authoring;
- branching choices;
- AND/OR unlock semantics;
- conditional edges;
- optional nodes;
- rewards and consequences;
- reusable Adventures across classes;
- progress tracking;
- teacher force-complete controls;
- snapshots/version pinning for students already in progress;
- public/shared Adventures;
- cross-teacher cloning;
- accessibility additions;
- integrity checking;
- performance tests.

The Adventure task specification records **103 completed implementation tasks**.

The final recorded Adventure test report in the repository documented:

- **55 Adventure tests passing**;
- **203 tests passing overall**;
- **2 known pre-existing failures**;
- several manual browser smoke checks still outstanding.

This recorded result should be treated as historical evidence, not as proof that the current repository still reproduces that state. Reproducibility must be re-established during Stage 0 of the new roadmap.

---

# Part II — Critical Findings

## 6. Release Blocker: Alembic Migration History Is Not Reliably Version-Controlled

### 6.1 Current problem

The current application model registry describes a much larger schema than the migration history currently visible in `main`.

The current `.gitignore` contains a rule that ignores migration files:

```gitignore
# Migration versions
migrations/versions/*
!migrations/versions/.gitkeep
```

This is incompatible with a reliable Alembic workflow.

Migration scripts are not disposable build artefacts. They are source code that describes how one valid version of the database becomes the next valid version.

The Adventure quickstart documentation refers to migrations such as:

- `001_adventure_tables`
- `002_battle_adventure_node`

while those migrations are not present in the current migration directory on `main`.

The one visible migration also references an earlier `down_revision` that is not present in the same directory.

### 6.2 Risk

A developer can have a working existing database while a fresh installation fails because their local database already contains tables created by historical migrations or `create_all()` fallbacks that a new clone cannot reproduce.

This means the project cannot currently treat:

```bash
alembic upgrade head
```

as a reliable fresh-install contract.

### 6.3 Required decision

**Alembic migration files must be committed to Git.**

The project should remove the ignore rule for `migrations/versions/*.py`.

### 6.4 Recovery options

#### Option A — Clean V1 baseline migration

Recommended if there is no irreplaceable live classroom database that must preserve its historic migration lineage.

1. Freeze the canonical ORM schema.
2. Back up all development databases.
3. Generate a clean V1 baseline migration representing the canonical schema.
4. Verify that a completely empty database reaches the correct schema using Alembic alone.
5. Seed default data separately.
6. Commit the migration and future migrations to Git.

#### Option B — Reconstruct historical chain

Required if important live databases already exist and must migrate without reset.

1. Recover missing revisions from Git history or developer machines.
2. Reconstruct the exact migration chain.
3. Verify upgrades from representative older database snapshots.
4. Commit the entire chain.

### 6.5 Stage 0 release gate

A clean clone must be able to run:

```bash
python -m venv .venv
pip install -r requirements.txt -r requirements-dev.txt
alembic upgrade head
flask --app run:app seed-db
pytest -q
python run.py
```

without relying on a pre-existing database.

---

## 7. Duplicate RPG State: `Student` and `Character`

### 7.1 Current problem

The `Student` model currently contains game-state fields such as:

- `xp`
- `level`
- `health`
- `power`
- `gold`

The `Character` model also stores the equivalent gameplay state:

- `experience`
- `level`
- `health`
- `max_health`
- `power`
- `max_power`
- `gold`
- `power_points`

This creates two potential sources of truth.

A concrete example already exists in the teacher API:

- the XP award endpoint modifies the **Character**;
- the student stats endpoint can read game values from **Student**.

Therefore two screens can theoretically display different values for the same student.

### 7.2 Required V1 rule

> **Student represents identity and enrolment. Character represents RPG/game state.**

### 7.3 Proposed canonical ownership

#### `Student`

Keep:

- user relationship;
- current classroom relationship;
- student status;
- non-game enrolment metadata.

#### `Character`

Own:

- class;
- avatar/gender presentation;
- XP;
- level;
- HP;
- max HP;
- Focus Points;
- max Focus Points;
- Power Points;
- Gold;
- clan membership;
- equipment;
- powers;
- status effects;
- game progression.

### 7.4 Migration approach

1. Identify every read/write of `Student.xp`, `Student.level`, `Student.health`, `Student.power`, `Student.gold`.
2. Replace runtime reads with Character queries or DTO/service results.
3. Migrate legacy data where Character values are missing.
4. Add regression tests proving teacher and student screens return the same character values.
5. Remove duplicated columns only after all code has been migrated.

---

## 8. Duplicate Classroom Membership Models

The codebase currently has both:

- a many-to-many `class_students` association between users and classrooms;
- a direct `Student.class_id` relationship.

Most current application logic assumes a student belongs to one active classroom.

For the classroom context targeted by V1, supporting multiple simultaneous classroom memberships creates unnecessary complexity.

### Recommended V1 decision

> **One Student profile has one active Classroom. One teacher may manage many Classrooms.**

The project should choose `Student.class_id` as the canonical relationship for V1 and remove or constrain the duplicate association once all dependent code is migrated.

Multi-class enrolment can be revisited in a later major version if a genuine requirement emerges.

---

## 9. Clan Membership Should Also Have One Authority

Clan membership has historically appeared at both student and character layers.

The RPG nature of clans makes Character the more coherent owner.

### Recommended V1 rule

> **Clan membership is Character state.**

Teacher/student queries should derive clan state from the active Character.

---

## 10. Game Rule Drift Across Subsystems

The project has grown feature-by-feature. Several systems now perform their own calculations directly rather than using one game-rules engine.

This creates inconsistencies in:

- XP thresholds;
- level-up logic;
- HP changes;
- Gold changes;
- power/focus consumption;
- reward distribution;
- auditing;
- transaction boundaries.

### 10.1 Example: level progression

The Character model uses the progression rule:

```text
level = experience // 1000 + 1
```

However the Battle code contains a different level threshold check based on:

```text
level * 100
```

and can call the Character level-up method with an incompatible signature.

This demonstrates why individual routes should not independently implement progression rules.

### 10.2 Required architectural rule

> **No route or feature subsystem should calculate levels directly.**

The same principle should apply to Gold, HP, Focus Points, and rewards.

---

## 11. `power` Is Doing More Than One Job

The current code uses `Character.power` as the spendable resource required to activate classroom Powers.

The Battle system also uses `Character.power` as base combat damage.

This means spending classroom power can directly reduce battle attack strength.

That coupling may not be intended and is not clearly defined in the project rules.

### Recommended separation

#### Classroom game resources

- XP
- Level
- HP
- Focus Points (FP)
- Power Points (PP)
- Gold

#### Combat attributes

- Attack
- Defence
- Battle HP or battle-state health
- Equipment bonuses

The exact combat design can remain simple, but it should not silently reuse the same field as the classroom Powers economy unless this becomes an explicit game rule.

---

## 12. Transaction Boundaries Are Inconsistent

`Base.save()` currently commits immediately.

Newer Quest/Adventure code has already moved toward an atomic style where rewards and progress updates can be applied with `commit=False` and then committed together.

The newer approach is safer.

### Risk

If a use case includes:

1. mark activity complete;
2. award XP;
3. award Gold;
4. add equipment;
5. add audit event;

and one model method commits after step 2, then a failure during step 4 can leave a partially applied event.

### Required V1 transaction rule

> **Routes/use-case services own transactions. Domain entities and low-level services mutate state but do not unexpectedly commit.**

A typical application use case should become:

```text
HTTP route
   ↓
Authorisation / validation
   ↓
Domain service(s)
   ↓
Audit event(s)
   ↓
ONE COMMIT
   ↓
Response
```

---

## 13. Quest and Adventure Systems Overlap

The application currently contains two overlapping learning-content systems.

### Legacy Quest system

Supports:

- quests;
- quest logs;
- rewards;
- consequences;
- prerequisites;
- question-set links;
- monster links;
- map coordinates.

### Adventure system

Supports:

- graph authoring;
- branching;
- choice nodes;
- criteria edges;
- reusable maps;
- assignments;
- snapshots;
- teacher progress monitoring;
- story, quiz, battle, boss, reward and milestone nodes;
- rewards/consequences;
- sharing and cloning.

The Adventure system is the more capable long-term content platform.

### Required product decision

> **Adventure becomes the canonical learning-path system for V1 and beyond.**

The existing Quest system should enter compatibility/maintenance mode and eventually be retired after migration tooling exists.

---

## 14. Offline Operation Is Not Yet Complete

The application is designed as a local classroom web application, but base templates currently load some front-end dependencies from external CDNs.

This means that a classroom network without internet connectivity may lose styling/icons or other front-end functionality.

### Required V1 offline rule

> **Normal application use must make zero external network requests.**

Vendor required front-end assets into the repository, for example:

```text
static/vendor/bootstrap/
static/vendor/bootstrap-icons/
static/vendor/chartjs/
```

A browser test should run with internet access disabled.

---

## 15. LAN Deployment Is Not Yet Productised

The README describes access from other devices on the local network, but the current development entry point defaults to loopback (`127.0.0.1`) and uses Flask's built-in development server.

For V1 classroom use, deployment should become an explicit supported workflow.

### Recommended Windows V1 runtime

Use **Waitress** as the local WSGI server.

Example target workflow:

```text
start_legends.bat
      ↓
Check Python/runtime
      ↓
Check configuration
      ↓
Create safety backup
      ↓
Run migration check/upgrade
      ↓
Start Waitress on 0.0.0.0:5000
      ↓
Display teacher URL
      ↓
Display LAN student URL
```

A future standalone installer is optional and should not block initial V1 delivery.

---

## 16. Backup Exists; Restore Must Be Proven

The repository already includes a substantial SQLite backup service that:

- checkpoints WAL;
- copies the database;
- exports tables to CSV;
- exports tables to JSON.

The next requirement is **tested restore**.

### V1 restore workflow

1. Teacher selects backup file.
2. System validates that it is a recognised Legends database.
3. System creates an automatic backup of the current database.
4. System verifies migration/schema compatibility.
5. Teacher confirms restoration.
6. Database is replaced/restored.
7. Integrity checks run.
8. Application reports success or restores the safety copy on failure.

A backup feature should not be considered complete until a round-trip restore test is automated.

---

## 17. Planning Documents Have Multiple Competing Authorities

The repository contains planning or agent-control information across areas such as:

- `.planning_docs`
- `specs`
- `Ideas`
- `PROJECT_ANALYSIS_AND_RECOMMENDATIONS.md`
- Cursor rules
- BMAD assets
- various agent-specific files

Some older planning documents describe features as unfinished even though newer code has implemented them.

### Required governance improvement

Create four canonical top-level project documents:

```text
docs/PRODUCT.md
docs/GAME_RULES.md
docs/ARCHITECTURE.md
docs/ROADMAP.md
```

This document should either become `docs/ROADMAP.md` later or feed directly into it.

Feature-level specifications under `specs/` remain authoritative for the implementation contract of that feature.

Older research and brainstorming files can remain, but should be clearly labelled as historical/non-authoritative where appropriate.

---

# Part III — Target V1 Architecture

## 18. Canonical Domain Model

The following conceptual model is recommended for V1.

```text
User
 ├── Teacher
 │    └── Classroom(s)
 │
 └── Student
      └── active Classroom
           └── active Character
                ├── Character Class
                ├── XP / Level
                ├── HP
                ├── Focus Points
                ├── Power Points
                ├── Gold
                ├── Clan
                ├── Equipment / Inventory
                ├── Learned Powers
                ├── Status Effects
                ├── Adventure Progress
                └── Audit/Game Events
```

### Important authority rules

- `User` owns authentication identity.
- `Student` owns enrolment/profile identity.
- `Classroom` owns the teacher's class context.
- `Character` owns all RPG state.
- `Adventure` owns structured learning-path content.
- `AuditLog`/game events record changes.
- Domain services own game rules.

---

## 19. Proposed Game Domain Services

Create or consolidate the following service boundaries.

### 19.1 `ProgressionService`

Responsibilities:

- `grant_xp()`
- calculate resulting level;
- handle multi-level gains;
- grant Power Points on level-up;
- update max resources;
- write XP/level audit events.

### 19.2 `HealthService`

Responsibilities:

- damage;
- healing;
- HP clamping;
- Fallen initiation;
- rescue;
- restoration after consequence;
- behaviour-linked damage;
- audit events.

### 19.3 `FocusService`

Responsibilities:

- Focus Point regeneration;
- spending Focus Points;
- restoring Focus Points;
- maximum Focus Points;
- power activation validation.

### 19.4 `EconomyService`

Responsibilities:

- grant Gold;
- spend Gold;
- purchase validation;
- shop transactions;
- refunds where permitted;
- audit logging.

### 19.5 `RewardService`

Responsibilities:

Apply a consistent reward bundle containing any combination of:

- XP;
- Gold;
- equipment;
- powers;
- clan XP;
- badges;
- future special currencies.

Both Quest compatibility and Adventures should use the same reward service.

### 19.6 `GameEventService`

Responsibilities:

- record teacher/student game actions;
- provide reliable activity history;
- support Live Classroom activity feeds;
- support undo for reversible teacher actions.

---

# Part IV — Product Direction

## 20. Adventures Become the Learning Backbone

Adventures should become the central learning-content model.

An Adventure represents a reusable learning journey.

An Adventure contains Activities represented as graph nodes.

The existing node system already supports many useful activity types. V1 should add one particularly important type.

---

## 21. New Adventure Node: `CLASSROOM_ACTIVITY`

This should explicitly represent real-world classroom work.

Examples:

- complete a science investigation;
- finish today's maths problem set;
- contribute to group research;
- complete a writing draft;
- demonstrate a practical skill;
- present a group product;
- participate successfully in a classroom activity.

### Proposed lifecycle

```text
LOCKED
  ↓ prerequisites satisfied
AVAILABLE
  ↓ student opens activity
IN_PROGRESS
  ↓ student indicates completion / teacher observes completion
AWAITING_TEACHER_VERIFICATION
  ↓ teacher approves
COMPLETED
  ↓
REWARDS APPLIED + NEXT NODE(S) UNLOCKED
```

Teacher rejection can return the node to `IN_PROGRESS` with optional feedback.

### Why this matters

The project should remain a **classroom gamification system**, not gradually become only an online quiz/battle game.

A first-class classroom-activity node ties Adventure progression directly to real teaching and learning.

---

## 22. Legacy Quest Migration Strategy

Do not delete the Quest system in one large change.

Use a controlled compatibility approach.

### Example conversion

```text
Legacy Quest
     ↓ converter
Adventure
     ↓
Start → Classroom Activity → Reward → End
```

### Migration phases

1. Freeze new feature development on legacy Quest models.
2. Build a Quest-to-Adventure conversion service.
3. Convert representative quests and verify rewards/progress.
4. Hide legacy Quest creation from new classroom workflows.
5. Maintain read-only/support compatibility for existing data.
6. Remove legacy models/routes only in a later migration after data has been converted.

---

## 23. Live Classroom Should Become the Main Teacher Runtime Screen

The most valuable major feature after stabilisation is a **Live Classroom** control centre.

The goal is to let a teacher operate the gamification system while actually teaching, without moving through multiple administration pages.

### 23.1 Roster view

Each student card could show:

```text
[Avatar]  Student Name
Warrior • Level 7

HP  ███████░░  82/100
FP  █████░░░░  14/25
XP  3,450
Gold 820

Clan: The Dragons
Current Adventure: Bushfire Mission
```

### 23.2 Single-student quick actions

Selecting a student should provide immediate controls for:

- positive behaviour reward;
- HP consequence;
- XP;
- Gold;
- heal;
- Focus restore;
- view current powers;
- view current Adventure node;
- view recent activity.

### 23.3 Multi-select actions

Teacher can select:

- several students;
- one clan;
- the whole class.

Bulk actions could include:

- +XP;
- +Gold;
- heal;
- Focus restoration;
- assign activity/adventure;
- trigger class event.

### 23.4 Undo

The interface should prominently support:

> **Undo last teacher action**

Only reversible event types should be eligible.

This should be implemented through auditable event records rather than by attempting to reverse arbitrary database transactions.

---

## 24. Positive Behaviour Needs First-Class Configuration

The negative behaviour/Fallen system is currently more structured than positive behaviour rewards.

V1 should introduce a teacher-configurable positive reward catalogue.

Example:

| Reward | Default value |
|---|---:|
| Great effort | +25 XP |
| Helping someone | +20 XP |
| Ready to learn | +10 XP |
| Excellent teamwork | +25 XP |
| Persistence | +20 XP |
| Quality work | +30 XP |
| Custom | Teacher-defined |

Teachers should be able to edit names and values per classroom.

The classroom loop becomes:

```text
Positive classroom behaviour → XP / Gold / recognition
Negative classroom behaviour → HP consequence
```

---

## 25. Random Events

Random Events are a relatively low-cost feature with strong classroom identity value.

They should be configurable and teacher-controlled rather than automatically imposed.

Example events:

- **Treasure Everywhere** — everyone receives Gold.
- **Heroic Morning** — XP rewards are increased for the lesson.
- **Second Wind** — everyone restores Focus Points.
- **Peace Treaty** — HP loss is disabled for a period.
- **Lucky Clan** — one random clan receives a reward.
- **Mysterious Benefactor** — the lowest-level student receives a bonus.
- purely humorous events with no game-state effect.

Teacher controls should include:

- draw;
- preview;
- reroll;
- accept;
- cancel.

---

## 26. Boss Battles as Formative Assessment

The application already contains individual question-based battles.

A higher-value classroom extension is a teacher-led Boss Battle designed for formative assessment.

### Proposed flow

```text
Teacher starts Boss Battle
       ↓
Select classroom/clans + question set
       ↓
Boss appears on projector/live screen
       ↓
Question displayed
       ↓
Students/clans answer
       ↓
Correct response damages boss
       ↓
Battle continues
       ↓
Boss defeated
       ↓
Class/clan reward bundle
```

The existing Adventure `BOSS` node should be able to launch this mode.

---

# Part V — Completion Roadmap

## 27. Stage 0 — Recovery and Reproducible Baseline

### Objective

Make the repository reproducible from an empty machine/database and establish a trusted baseline before further feature work.

### Required work

1. Remove migration-version ignore rule from `.gitignore`.
2. Decide baseline-migration vs historical-chain recovery strategy.
3. Restore/commit complete Alembic history.
4. Verify empty-database `alembic upgrade head`.
5. Verify seeded database creation.
6. Run the complete test suite.
7. Fix all known test failures rather than retaining accepted failures for V1.
8. Complete the outstanding manual Adventure smoke flow.
9. Add a clean-install automated test.
10. Introduce baseline GitHub Actions CI.
11. Document the exact supported Python version(s).
12. Record a stable baseline commit/tag.

### Completion gate

A fresh checkout must satisfy:

- dependencies install successfully;
- migrations reach head;
- seed completes;
- application starts;
- all automated tests pass;
- Adventure manual smoke succeeds;
- database integrity scan succeeds.

### Deliverable

**`v1-stabilisation-baseline`** development tag or equivalent stable baseline commit.

---

## 28. Stage 1 — Domain Consolidation

### Objective

Create one authoritative game-state model and one set of game rules.

### Required work

1. Make Character authoritative for RPG stats.
2. Migrate every Student-stat read/write.
3. Decide and enforce one-class-per-student V1 model.
4. Make Character authoritative for clan membership.
5. Add `ProgressionService`.
6. Add `HealthService`.
7. Add `FocusService`.
8. Add `EconomyService`.
9. Consolidate rewards through `RewardService`.
10. Fix battle XP/level-up behaviour.
11. Separate classroom Focus Points from combat Attack if required by approved `GAME_RULES.md`.
12. Standardise transaction boundaries.
13. Update audit logging for all resource mutations.
14. Add cross-feature integration tests.

### Completion gate

- All XP changes go through one progression path.
- All Gold changes go through one economy path.
- All HP changes go through one health path.
- All Focus spending/restoration goes through one focus path.
- No teacher/student UI can show conflicting RPG values.
- Battle, Powers, Behaviour, Quest and Adventure tests all pass together.

---

## 29. Stage 2 — Content Unification

### Objective

Establish Adventures as the canonical learning-path platform.

### Required work

1. Approve Adventure as canonical content architecture.
2. Add `CLASSROOM_ACTIVITY` node type.
3. Add teacher-verification lifecycle.
4. Reuse canonical RewardService.
5. Reuse canonical Health/Economy/Progression services.
6. Add activity feedback/notes.
7. Build Quest-to-Adventure converter.
8. Prevent new functionality being added to legacy Quest paths.
9. Update teacher navigation to prefer Adventures.
10. Add Adventure end-to-end tests that include a real classroom activity node.

### Completion gate

A teacher can:

1. create an Adventure;
2. add real classroom work;
3. assign it to a class;
4. see student progress;
5. verify work;
6. automatically award rewards;
7. unlock the next learning step.

---

## 30. Stage 3 — Live Classroom

### Objective

Give the teacher one operational screen for running classroom gamification.

### Required work

1. Live roster cards.
2. HP/FP/XP/Gold status display.
3. clan and character-class display.
4. current Adventure status.
5. positive reward catalogue.
6. behaviour consequence controls.
7. single-student actions.
8. clan actions.
9. whole-class actions.
10. real-time-ish refresh/polling without requiring WebSockets.
11. recent event feed.
12. undo reversible teacher actions.
13. Random Event system.
14. projector/fullscreen mode where useful.
15. keyboard/touch-friendly controls.

### Completion gate

A teacher can run a normal gamified lesson without navigating away from Live Classroom for routine rewards, consequences, class state and current learning-path monitoring.

---

## 31. Stage 4 — Assessment and Battle Integration

### Objective

Use existing game mechanics to improve formative assessment rather than create isolated mini-games.

### Required work

1. Repair and test individual battle progression.
2. Separate combat stats from classroom resources where required.
3. Build teacher-led Boss Battle flow.
4. Add class/clan response modes.
5. Connect question sets to Boss Battles.
6. Connect Adventure Battle/Boss nodes.
7. Apply canonical rewards.
8. Add teacher battle summary/report.
9. Add accessibility alternatives for students unable to participate in fast-response modes.

### Completion gate

A teacher can launch a question-set Boss Battle from an Adventure and return to the Adventure with progress/rewards correctly recorded.

---

## 32. Stage 5 — UX Consolidation

### Objective

Remove legacy duplication and create one coherent teacher and student experience.

### Required work

1. Audit `_new` vs legacy templates.
2. Select one canonical template per workflow.
3. Remove dead navigation paths.
4. Simplify teacher sidebar structure.
5. Simplify student navigation around:
   - Character
   - Adventures
   - Powers
   - Clan
   - Shop/Inventory
   - Progress
6. Standardise terminology:
   - Focus Points
   - Power Points
   - Adventure
   - Activity
   - Clan
7. Review mobile browser layouts.
8. Review touch targets.
9. Complete keyboard accessibility.
10. Review colour contrast and non-colour state indicators.
11. Add consistent error/empty/loading states.

### Completion gate

Every major workflow has one canonical interface and no student/teacher needs to understand legacy vs new systems.

---

## 33. Stage 6 — Local Production Deployment

### Objective

Make the application dependable on a Windows teacher computer and classroom LAN with no external internet requirement.

### Required work

1. Vendor all runtime front-end dependencies locally.
2. Add Waitress or equivalent production WSGI server.
3. Add classroom-server launcher script.
4. Bind LAN server explicitly.
5. Detect/display local network address.
6. Add first-run configuration.
7. Add migration/version preflight.
8. Create automatic startup safety backup.
9. Complete restore workflow.
10. Add LAN diagnostic page.
11. Document Windows Firewall configuration.
12. Test multiple classroom browsers concurrently.
13. Test application with internet disconnected.
14. Define log rotation/support bundle process.
15. Add graceful shutdown documentation.

### Completion gate

On a supported Windows machine:

1. install/launch the application;
2. open teacher interface locally;
3. open student interface from another LAN device;
4. perform classroom workflows with internet disabled;
5. back up and restore successfully.

---

## 34. Stage 7 — Release Engineering

### Objective

Turn project quality into repeatable automated gates.

### Required CI suites

#### Unit tests

- models;
- services;
- utility functions;
- game-rule calculations.

#### Integration tests

- authentication;
- teacher ownership/authorisation;
- class/student lifecycle;
- rewards;
- shop purchase;
- behaviour/Fallen/rescue;
- powers;
- battles;
- Adventures;
- backup/restore.

#### Migration tests

At minimum:

- blank DB → head;
- known previous release DB → head;
- schema matches ORM expectations.

#### Browser end-to-end tests

Recommended tool: Playwright.

Critical flows:

1. teacher creates class;
2. teacher adds student;
3. student first-login character creation;
4. teacher rewards behaviour;
5. student levels up;
6. student learns/uses power;
7. teacher applies HP consequence;
8. Fallen/rescue flow;
9. teacher creates Adventure;
10. teacher assigns Adventure;
11. student completes/teacher verifies classroom activity;
12. rewards arrive;
13. student purchases/equips item;
14. teacher runs Boss Battle;
15. backup → mutate data → restore → verify original data.

### Completion gate

Every merge to `main` has a reproducible green test result and migrations cannot be accidentally omitted.

---

## 35. Stage 8 — Classroom Pilot and V1 Release

### Objective

Validate the system with actual classroom use and freeze a stable V1 scope.

### Pilot questions

Measure practical friction rather than adding speculative features.

Observe:

- How many clicks does a teacher need to reward a student?
- Can the teacher operate Live Classroom while speaking/teaching?
- Do students understand XP, HP, FP and PP?
- Are class roles meaningfully distinct?
- Does Gold remain valuable?
- Are shop prices balanced?
- Do powers get used or merely collected?
- Does the Fallen system produce cooperation without disrupting lessons?
- Do Adventures make classroom work clearer or create extra administration?
- Are Boss Battles instructionally useful?
- Does the app remain responsive with a full class connected?
- Can backup/restore be performed confidently?

### Release work

1. Fix pilot blockers.
2. Balance XP/Gold/FP progression.
3. Finalise default behaviour values.
4. Finalise default powers.
5. Finalise default shop catalogue.
6. Finalise teacher guide.
7. Finalise student quick-start guide.
8. Freeze schema.
9. Create final V1 migration.
10. Tag `v1.0.0`.
11. Preserve known-good release artefacts/documentation.

### V1 completion definition

V1 is complete when the system can reliably support this classroom loop:

```text
Teacher creates class
      ↓
Students log in and create characters
      ↓
Teacher runs Live Classroom
      ↓
Positive behaviour → XP/Gold
Negative behaviour → HP
      ↓
Students use class powers and support clans
      ↓
Teacher assigns an Adventure containing real classroom work
      ↓
Students complete activities/quizzes/battles
      ↓
Teacher verifies real-world activities
      ↓
Rewards update Character state consistently
      ↓
Students level, learn powers and use Gold in the shop
      ↓
Teacher monitors progress
      ↓
Data is backed up and can be restored
```

---

# Part VI — Detailed Milestone 0 Backlog

## 36. Milestone: `V1 Stabilisation`

No major new feature should begin until these items are complete.

### Issue 1 — Repair and commit Alembic migration history

**Goal:** `alembic upgrade head` works from a blank database using source-controlled migrations.

**Acceptance criteria:**

- migration Python files are not ignored;
- migration chain has no missing revision references;
- Adventure/Behaviour/Battle schema is represented;
- migration files are committed;
- clean upgrade reaches head.

---

### Issue 2 — Add clean-database installation test

**Goal:** Prevent future commits from working only on developer databases.

**Acceptance criteria:**

CI can:

1. create empty database;
2. run migrations;
3. seed required defaults;
4. import/start application;
5. run smoke query/tests.

---

### Issue 3 — Fix all known failing tests

Historic Adventure documentation recorded two pre-existing failures.

**V1 rule:** no permanently accepted red tests.

**Acceptance criteria:**

```bash
pytest -q
```

returns success with zero failures.

---

### Issue 4 — Make Character the single source of RPG state

**Acceptance criteria:**

- no teacher/student endpoint reports RPG values from obsolete Student fields;
- Character owns XP, level, HP, FP, PP and Gold;
- tests verify consistent values across views.

---

### Issue 5 — Resolve duplicate classroom membership

**Acceptance criteria:**

- V1 relationship is documented;
- all enrolment queries use the canonical relationship;
- duplicate association is removed or made non-authoritative.

---

### Issue 6 — Resolve duplicate clan membership

**Acceptance criteria:**

- Character owns clan membership;
- all APIs/templates read canonical membership;
- migration preserves existing clan assignments.

---

### Issue 7 — Create canonical ProgressionService

**Acceptance criteria:**

- one XP-to-level formula;
- battle, quest, Adventure, behaviour rewards and teacher XP awards use it;
- multi-level gains work;
- PP awards work;
- audit events are consistent.

---

### Issue 8 — Create canonical Health/Fallen service

**Acceptance criteria:**

- all HP damage/healing flows pass through service;
- zero HP triggers Fallen rules consistently where appropriate;
- behaviour, powers and teacher actions use same path;
- test rescue/cascade edge cases.

---

### Issue 9 — Create canonical Focus Point service

**Acceptance criteria:**

- spend/regenerate/restore rules exist in one location;
- Powers use the service;
- classroom UI displays canonical values;
- no negative or over-max resource state.

---

### Issue 10 — Create canonical Economy/Reward service

**Acceptance criteria:**

- one Gold mutation path;
- one reward bundle path;
- Quest/Adventure/shop/teacher actions use common services;
- reward transactions are atomic.

---

### Issue 11 — Remove unexpected model-level commits from domain workflows

**Acceptance criteria:**

- critical use cases have explicit transaction boundaries;
- partial reward completion cannot persist;
- service tests deliberately inject failure and verify rollback.

---

### Issue 12 — Fix Battle XP and level-up rules

**Acceptance criteria:**

- Battle calls ProgressionService;
- no duplicate XP threshold formula;
- battle victory causing a level-up is tested;
- Adventure battle hook still completes the correct node.

---

### Issue 13 — Add Behaviour/Fallen integration test suite

Cover:

- infraction damage;
- zero HP;
- rescue window;
- revive;
- Cheat Death;
- Cursed Die;
- clan cascade;
- audit events;
- transaction rollback.

---

### Issue 14 — Add Battle integration test suite

Cover:

- start;
- correct answer;
- incorrect answer;
- victory;
- defeat;
- flee;
- reward;
- level-up;
- Adventure integration.

---

### Issue 15 — Verify Adventure schema against current ORM

**Acceptance criteria:**

- current migrations create every Adventure table/column/index;
- graph integrity scanner passes;
- current 55-test Adventure suite passes;
- manual browser smoke passes.

---

### Issue 16 — Add GitHub Actions baseline CI

Minimum jobs:

- dependency install;
- migration test;
- pytest;
- lint/format check if retained;
- Adventure integrity test.

---

### Issue 17 — Create canonical project documentation

Create:

- `docs/PRODUCT.md`
- `docs/GAME_RULES.md`
- `docs/ARCHITECTURE.md`
- `docs/ROADMAP.md`

Add headers to older planning documents explaining whether they are historical, supporting research, or feature-specific specifications.

---

# Part VII — Release Gates

## 37. Gate A — Repository Reproducibility

Required:

- clean clone;
- migration succeeds;
- seed succeeds;
- app starts;
- test suite passes.

## 38. Gate B — Game-State Consistency

Required:

- one authority for RPG state;
- one XP formula;
- one HP mutation path;
- one Gold mutation path;
- one Focus mutation path;
- atomic rewards.

## 39. Gate C — Core Classroom Loop

Required:

- teacher can reward positive behaviour;
- teacher can apply consequences;
- Fallen/rescue works;
- Powers work;
- Live Classroom supports routine operation.

## 40. Gate D — Learning Loop

Required:

- teacher can author Adventure;
- Adventure can include real classroom activity;
- teacher verification works;
- quiz/battle nodes work;
- rewards/progression work;
- teacher progress reporting works.

## 41. Gate E — Offline/LAN Operation

Required:

- no CDN/network dependency;
- classroom devices connect over LAN;
- supported Windows launcher;
- server remains stable with representative concurrent clients.

## 42. Gate F — Data Safety

Required:

- backup succeeds;
- restore succeeds;
- migration from previous V1 candidate succeeds;
- integrity checks succeed after restore.

## 43. Gate G — V1 Release

Required:

- all gates A–F green;
- classroom pilot completed;
- no release-blocking defects;
- teacher/student documentation complete;
- version tagged `v1.0.0`.

---

# Part VIII — Explicit Non-Goals Before V1

## 44. Do Not Rewrite the Frontend

Do **not** migrate the application to React/Vue/Angular merely for architectural fashion.

The Flask/Jinja/vanilla-JS architecture is sufficient for the target local classroom product.

## 45. Do Not Replace SQLite Without Evidence

Do **not** move to PostgreSQL/Supabase before V1 unless classroom concurrency testing proves SQLite inadequate.

Current local-first requirements strongly favour SQLite's simplicity.

## 46. Do Not Add More Character Classes Before Rules Are Stable

Warrior/Sorcerer/Druid already provide enough complexity to validate the design.

Balance and use-rate matter more than adding classes.

## 47. Do Not Build a Third Learning-Path System

New learning content should be implemented within Adventures.

## 48. Do Not Expand the Item Catalogue Before the Economy Is Balanced

A larger shop does not solve an unstable Gold economy.

## 49. Do Not Introduce WebSockets Unless Polling Is Proven Inadequate

Live Classroom can initially use modest polling/refetch patterns and stay operationally simple.

## 50. Do Not Make a Complex Installer a V1 Blocker

A reliable documented Windows launch process is enough for the initial classroom release.

---

# Part IX — Intended Finished Product Loop

## 51. Core System Diagram

```text
                         REAL CLASSROOM
                              │
                              ▼
                   ┌─────────────────────┐
                   │   LIVE CLASSROOM    │
                   │ Teacher Control Hub │
                   └──────────┬──────────┘
                              │
                   ┌──────────┼──────────┐
                   ▼          ▼          ▼
               + XP/Gold    - HP      Random Event
                   │          │          │
                   ▼          ▼          ▼
               Level Up     Fallen      Class Effect
                   │          │
                   ▼          ▼
                PP + FP    Team Rescue
                   │          │
                   └────┬─────┘
                        ▼
                  Character Powers
                        │
                        ▼
             ┌──────────────────────┐
             │      ADVENTURES      │
             │ branching class work │
             └──────────┬───────────┘
                        │
               ┌────────┼─────────┐
               ▼        ▼         ▼
            Activity   Quiz    Boss Battle
               │        │         │
               └────────┼─────────┘
                        ▼
                     Rewards
                        │
                ┌───────┴────────┐
                ▼                ▼
              Gold              XP
                │                │
                ▼                ▼
               Shop           Level Up
                │
                ▼
          Character / Gear
                │
                ▼
           Clan Identity
```

The important design principle is that all systems reinforce classroom participation and learning rather than existing as unrelated mini-games.

---

# Part X — Project Management Approach

## 52. Use GitHub as the Execution System

The repository currently has extensive planning material but has historically lacked a sufficiently concrete issue/PR backlog.

From this point forward:

- each roadmap item becomes a GitHub issue;
- issues contain acceptance criteria;
- issues are grouped by milestone;
- code changes occur through focused branches/PRs where practical;
- tests and migration gates are required before merge;
- closed issues link to implementing commits/PRs;
- the roadmap records outcomes, not detailed implementation chatter.

### Suggested milestones

1. `V1 Stabilisation`
2. `V1 Domain Consolidation`
3. `V1 Adventure Unification`
4. `V1 Live Classroom`
5. `V1 Assessment Integration`
6. `V1 UX Consolidation`
7. `V1 Local Production`
8. `V1 Release Candidate`

---

## 53. Definition of Done for Future Issues

A feature/bug should not be marked complete only because code exists.

A normal issue is complete when:

- implementation is present;
- database migration is present where required;
- automated tests are present;
- affected legacy tests still pass;
- documentation is updated where behaviour/contracts changed;
- error paths are handled;
- authorisation is verified;
- browser/manual smoke is completed for UI-critical changes;
- feature is merged into the target branch.

---

# 54. Immediate Next Action

The next implementation block should be **Stage 0 — Recovery and Reproducible Baseline**.

The first technical action should be:

> **Repair Alembic migration version control and prove a completely fresh database can be created from the repository.**

Do not begin Live Classroom, Random Events, Boss Battles, or another major feature until this baseline exists.

After Stage 0, proceed directly to **Stage 1 — Domain Consolidation**, because the current duplication of RPG state and game-rule logic will otherwise make every future feature more expensive and fragile.

Once those two stages are green, the project is ready to move from late alpha toward a controlled beta/classroom pilot.

---

# 55. Final Project Assessment

Legends of Learning has already crossed the most difficult conceptual threshold: the application proves that the classroom RPG idea can be implemented as a local browser-based system.

The codebase contains considerably more functionality than the original MVP required.

The project is therefore not blocked by a lack of ambition or capability. It is blocked by the normal problems that emerge when a prototype becomes a product:

- migration reproducibility;
- duplicated state;
- duplicated content systems;
- independently implemented game rules;
- inconsistent transaction boundaries;
- deployment assumptions;
- incomplete release gates;
- multiple planning authorities.

These are solvable engineering problems.

The path to completion is to **consolidate first, then integrate, then pilot**.

The recommended product destination is a teacher-operated local classroom RPG in which:

- classroom behaviour affects characters;
- character classes create meaningful cooperation;
- Adventures organise real learning;
- formative assessment can become game events;
- students progress visibly;
- Gold and equipment provide long-term motivation;
- teachers retain complete control;
- the application works locally without internet;
- school data remains on the teacher-controlled machine;
- the entire system can be installed, backed up, restored and upgraded predictably.

That is the target for `v1.0.0`.
