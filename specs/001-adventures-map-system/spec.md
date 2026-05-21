# Feature Specification: Adventures Quest Map System

**Feature Branch**: `001-adventures-map-system`

**Created**: 2026-05-21

**Status**: Draft

**Input**: User description: "Adventures Quest Map System — a new, parallel map-based quest system where teachers visually author branching quest maps (background image + drag-and-drop nodes + connecting paths) and assign them to classes/clans/individual students; students play through the adventure on a map with a character marker, completing typed nodes (battle / quiz / story / choice / reward / milestone / boss / end) to earn rewards and unlock the next path. Coexists alongside the legacy Quest/QuestLog system without modifying it."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Teacher visually authors a linear adventure and assigns it to a class (Priority: P1)

A teacher opens the Adventure Editor, picks a background image (e.g. a fantasy map), and visually places quest nodes on it — a starting node, a sequence of tasks (battle, quiz, story), and an end node. They draw connecting lines (paths) between nodes to define the order, fill in each node's title, description and rewards in a side panel, save, publish, and then assign the adventure to one of their classes. Students in that class can immediately see and start it.

**Why this priority**: This is the entire MVP. Without visual authoring + a playable student map for at least linear progressions, the feature delivers no incremental value over the legacy Quest system. Everything else (branching, choices, snapshots, sharing) is layered on top of this core loop.

**Independent Test**: Can be fully tested end-to-end by a teacher creating a 3-node linear adventure (start → battle → end), assigning it to a test class, then logging in as a student in that class, walking through the three nodes, and confirming rewards land on the student's character.

**Acceptance Scenarios**:

1. **Given** a logged-in teacher with at least one class, **When** they open the Adventures area and click "New Adventure", **Then** they are taken to an editor with a blank canvas and a background image picker.
2. **Given** a teacher in the editor, **When** they pick a background and click on the canvas after selecting a node type from the toolbar, **Then** a node of that type appears at the click position.
3. **Given** a teacher with two placed nodes, **When** they draw a connection from one node to another, **Then** a directed path is recorded and visualised between them.
4. **Given** a draft adventure with a start node, an intermediate task, and an end node all connected, **When** the teacher clicks "Publish", **Then** the adventure becomes eligible for assignment.
5. **Given** a published adventure, **When** the teacher chooses "Assign" and selects one of their classes, **Then** every student in that class can see the adventure in their Adventures list.
6. **Given** an assigned adventure, **When** a student opens it, **Then** they see the teacher's background and node layout, the starting node is marked as available, and downstream nodes are marked as locked.
7. **Given** a student looking at an available node, **When** they open it and complete its task (e.g. finish the battle, finish the story), **Then** the node is marked as completed, any rewards configured for that node land on their character, and the next connected node becomes available.
8. **Given** a student who has completed every node along a path to an end node, **When** they finish that end node, **Then** the adventure is marked complete for that student and any adventure-completion rewards/feedback are shown.

---

### User Story 2 - Branching paths and student choices (Priority: P2)

A teacher authors an adventure where, after a certain node, the student is presented with a choice ("Side with the orcs" vs "Side with the elves"). Each option leads to a different sub-path on the map. After both sub-paths re-converge at a shared node, the journey continues. Students live with the consequences of their choice — the not-chosen branch stays locked. Optional side nodes can also be placed off the main route so students can earn bonus rewards without being required to do so.

**Why this priority**: Branching, choices and optional nodes are the central differentiator of this system over the legacy single-parent, linear-only quest model. They unlock narrative-driven and self-paced learning experiences, which is the explicit motivation for building a new system in parallel rather than continuing to extend the old one. They are not, however, required to demonstrate end-to-end value (P1 already does that), so they sit one priority below the core loop.

**Independent Test**: Can be tested by authoring a single adventure containing one choice node with two outbound paths that re-converge, plus one optional side node off the main route. A test student picks the "left" option and confirms only the left sub-path unlocks, then continues through the re-convergence to the end. A second test student picks "right" and confirms the mirror behaviour. Both students can ignore the optional side node and still complete the adventure; a third student completes the optional side node and confirms its bonus rewards land.

**Acceptance Scenarios**:

1. **Given** a node placed as a "choice" node with two outgoing paths labelled "left" and "right", **When** a student completes the choice node by selecting "left", **Then** only the "left" path's next node becomes available; the "right" path's next node remains locked.
2. **Given** two parallel paths that re-converge at a single downstream node, **When** the convergence node is configured to require ANY inbound path to be completed, **Then** completing either inbound path unlocks it.
3. **Given** two parallel paths that re-converge at a single downstream node, **When** the convergence node is configured to require ALL inbound paths to be completed, **Then** the student must complete both upstream branches before the convergence node unlocks.
4. **Given** a node marked as "optional", **When** the student does not complete it, **Then** the adventure can still be marked as complete; **When** the student does complete it, **Then** they receive its rewards.
5. **Given** a student who has made a choice, **When** they revisit the choice node, **Then** their previous selection is preserved and the not-chosen branch is not retroactively unlocked.

---

### User Story 3 - Live student progress visibility for teachers (Priority: P3)

A teacher wants to know, at a glance, how each student in an assigned class is progressing through an adventure — who is stuck on which node, who has failed an attempt, who has finished early. They open a progress view for the adventure and see a roster of students with their current node, status and recent activity.

**Why this priority**: This is high operational value for teachers running a class, but is not part of the minimum end-to-end loop — teachers could survive on the legacy progress view temporarily. It's prioritised P3 so that it can be added once the authoring + playing loop is proven without blocking the MVP.

**Independent Test**: With three test students at different states (one not started, one in progress at a specific node, one completed), open the teacher progress view and confirm the roster shows each student's status, current node, and last activity timestamp.

**Acceptance Scenarios**:

1. **Given** an adventure assigned to a class with multiple students, **When** the teacher opens its progress view, **Then** every assigned student is listed with their current status (not started / in progress / completed / abandoned), current node title and last-active timestamp.
2. **Given** a student who has failed a node enough times that consequences applied, **When** the teacher views progress, **Then** that failure is visible in the student's row (e.g. status flag or recent-event entry).

---

### User Story 4 - Reuse the same adventure across classes and terms (Priority: P3)

A teacher who built "The Lost Library" adventure for one class wants to use it again next term with a different class, without re-authoring. They open their list of adventures, pick "The Lost Library", and assign it to the new class. Both classes' progress is tracked independently.

**Why this priority**: Reuse is a major efficiency win that compounds over time, but isn't required to ship the first working version. Without it, each teacher would have to recreate maps every term, which is acceptable for a single-term pilot.

**Independent Test**: Create one adventure, assign it to Class A and have a student complete a node. Then assign the same adventure to Class B and confirm a student in Class B starts at the beginning with their own independent progress, while Class A's student's progress remains intact and visible.

**Acceptance Scenarios**:

1. **Given** an adventure already assigned to Class A with at least one student mid-flight, **When** the teacher assigns the same adventure to Class B, **Then** Class B students start at the beginning with their own progress records, and Class A students' existing progress is unaffected.
2. **Given** the same adventure is assigned to two classes, **When** the teacher opens the progress view, **Then** they can scope the view to a single class.

---

### User Story 5 - Mid-flight edits do not disrupt students already playing (Priority: P3)

A teacher discovers a typo or a tuning issue (e.g. a node's reward is too high) in an already-assigned, in-progress adventure. They edit the adventure. Students who are already mid-flight continue to see the version they started on, so unlock logic and rewards stay consistent. Students who start the adventure for the first time after the edit see the updated version.

**Why this priority**: Without this guarantee, every authoring change risks corrupting in-progress students' state, which would erode teacher trust in the editor. It's P3 rather than P1 because the legacy system has the same flaw today, so we can ship the MVP without it and add the safeguard before the system is widely used.

**Independent Test**: Have a student begin an adventure. As the teacher, edit the adventure (e.g. rename a node, add a new node, change a reward amount). Confirm the in-progress student still sees the original node layout and rewards. Have a new student start the same adventure and confirm they see the edited version.

**Acceptance Scenarios**:

1. **Given** a student has started an adventure, **When** the teacher edits its structure or rewards, **Then** the student's view, unlock logic and pending rewards continue to reflect the version they started on.
2. **Given** the same adventure has been edited since assignment, **When** a different student starts it for the first time after the edit, **Then** they see the updated version.

---

### User Story 6 - Share adventures with other teachers (Priority: P4)

A teacher who has built a high-quality adventure wants to make it available for other teachers in the same school to assign or clone (and then modify their own copy without affecting the original).

**Why this priority**: This drives content propagation across the staff and amplifies the value of every adventure built, but is not required for any single teacher's classroom to use the system. It's deferred until the core authoring and playing experience is stable.

**Independent Test**: Teacher A marks an adventure as shareable. Teacher B sees it in a "shared by colleagues" list, clones it, edits the title of the clone, and assigns the clone to their own class. Teacher A's original is unaffected.

**Acceptance Scenarios**:

1. **Given** Teacher A has an adventure marked as shareable, **When** Teacher B browses available adventures, **Then** Teacher A's adventure appears in a section labelled as shared/public.
2. **Given** Teacher B clones Teacher A's adventure, **When** Teacher B edits the clone, **Then** only the clone changes; the original remains untouched and still owned by Teacher A.

---

### Edge Cases

- **No start node, or no path from any start to any end node**: publish must be blocked with a clear, specific error message identifying the broken structure.
- **A node has no incoming connection and is not marked as a start or optional node (orphan)**: publish must be blocked.
- **A choice node has fewer than two outgoing paths**: warn at publish time; at runtime treat the single option as auto-selected.
- **A battle or quiz node has no question set / monster configured**: warn at publish time; the node is not playable until configured.
- **Background image upload is unreasonably large**: enforce a per-file size limit and reject larger uploads with a user-friendly message.
- **Two paths form a cycle (A → B → A)**: allowed but warned at publish time; the unlock logic must not loop infinitely on revisits.
- **A node is dragged off the visible canvas (negative or out-of-bounds coordinates)**: the system clamps to canvas bounds.
- **A student concurrently submits "complete" and "retry" on the same node**: these operations must be idempotent; the second request returns the same final state rather than double-distributing rewards or corrupting attempts.
- **A teacher deletes a node that has student progress against it**: the teacher is warned with a count of affected students before the deletion proceeds, and progress is cleaned up consistently afterwards.
- **A character is deleted while in-flight**: that character's progress rows are cleaned up; no orphan rows are left behind.
- **An adventure assignment's `ends_at` date has passed**: students see a clear "this adventure has ended" indication and cannot start new nodes, but can still review their completed history.
- **An adventure assignment's `starts_at` date is in the future**: students see a countdown / locked indication and cannot start the adventure yet.
- **A student fails a node up to the maximum allowed attempts**: configured consequences (e.g. XP/gold/HP penalties) are applied once, and the student cannot retry that node without teacher intervention.
- **A student fails a non-optional node max times such that the adventure is no longer completable**: the teacher has a manual "force complete" / unblock action available.
- **Two students complete the same node concurrently**: each student's reward distribution is isolated and atomic; one student's failure does not roll back the other's rewards.
- **A battle that was started inside an adventure node is completed**: completion of that battle must reliably propagate to mark the bound node complete, even if the student leaves the page in between.
- **Self-loop attempt (a node connected to itself)**: rejected at authoring time.

## Requirements *(mandatory)*

### Functional Requirements

#### Authoring (teachers)

- **FR-001**: Teachers MUST be able to create, view, edit, archive, and clone Adventures from a dedicated area distinct from the legacy Quests area.
- **FR-002**: Teachers MUST be able to pick a background image for an Adventure, either from a built-in library of seed images or by uploading one of their own.
- **FR-003**: Teachers MUST be able to place nodes on the map by selecting a node type (start, story, battle, quiz, choice, reward, milestone, boss, end) and clicking a position on the canvas.
- **FR-004**: Teachers MUST be able to drag nodes to reposition them, and the new position MUST persist.
- **FR-005**: Teachers MUST be able to draw a directed connection (path) from one node to another and delete connections.
- **FR-006**: Teachers MUST be able to edit each node's title, description, optional lore/flavour text, and type-specific verification settings (e.g. monster for a battle node, question set for a quiz node, pass threshold).
- **FR-007**: Teachers MUST be able to add and remove rewards on any node (XP, gold, equipment, ability, clan XP, special currency, badge) and to mark a reward as conditional on the node's outcome (e.g. minimum score, first-try success, completed within a time limit).
- **FR-008**: Teachers MUST be able to add penalties (consequences) that apply when a node is failed beyond its retry limit.
- **FR-009**: Teachers MUST be able to mark a node as optional (does not block adventure completion).
- **FR-010**: Teachers MUST be able to mark a node explicitly as a start or end node, in addition to implicit detection by lack of inbound/outbound connections.
- **FR-011**: For each connection, teachers MUST be able to choose a condition: always taken, taken only if a specific choice was made on the upstream choice node, or taken only if a numeric criterion was met (e.g. score above a threshold).
- **FR-012**: For nodes with multiple inbound connections, teachers MUST be able to choose per-connection whether the connection counts toward an "all required" (AND) or "any required" (OR) unlock rule, so that re-join nodes after a branch can be configured.
- **FR-013**: The system MUST validate an Adventure in real time while authoring and again at publish time, surfacing errors that block publish and warnings that do not. At minimum, missing start node, unreachable end nodes, orphan non-optional nodes, and zero-node adventures MUST block publish.
- **FR-014**: Teachers MUST be able to save changes (with auto-save) and explicitly publish a draft Adventure; publishing makes it eligible for assignment.
- **FR-015**: Teachers MUST be able to preview an adventure as a student would see it, in a sandboxed mode that does not create real progress records.
- **FR-016**: Teachers MUST be able to assign a published Adventure to one of their classes; later phases MUST add the ability to assign to a clan or to an individual student (see Out of Scope).
- **FR-017**: Teachers MUST be able to set an optional start date and end date on an assignment, outside of which the Adventure is not playable.
- **FR-018**: Teachers MUST be able to deactivate or remove an assignment without deleting the Adventure itself.
- **FR-019**: Teachers MUST be able to clone any Adventure they own (and, when sharing is enabled, any Adventure shared with them) into a new editable copy.
- **FR-020**: Teachers MUST be able to view per-student progress for an assigned Adventure, including current node, status, attempts, recent events and timestamps.
- **FR-021**: Teachers MUST be able to manually mark a stuck student's node or whole adventure as complete (a "force complete" override), with the action recorded for audit.

#### Playing (students)

- **FR-022**: Students MUST see a list of Adventures assigned to them (directly, via their class, or via their clan) with a per-Adventure progress summary.
- **FR-023**: Students MUST be able to open an assigned Adventure and see it rendered as a map using the teacher's background image and node layout, with their character marker showing their last position.
- **FR-024**: Each node MUST display a clearly distinct visual state for: locked, available, in progress, completed, failed, and skipped/optional.
- **FR-025**: Students MUST be able to click any non-locked node to open a detail panel showing the node's title, type, description, objectives, configured rewards, and a clear primary action button whose label matches the node type (e.g. "Enter Battle", "Take Quiz", "Read", "Make Your Choice", "Open Chest").
- **FR-026**: Starting a battle node MUST connect the resulting battle to the node such that completing that battle propagates completion to the node automatically.
- **FR-027**: Starting a quiz node MUST run a quiz against the node's configured question set and use the configured pass threshold to determine pass/fail.
- **FR-028**: For story, reward, milestone and end nodes, a single explicit student action MUST complete the node.
- **FR-029**: For choice nodes, a student MUST be presented with one option per outgoing connection; selecting one option MUST complete the node and propagate only along the selected option's connection.
- **FR-030**: When a node is completed, the system MUST atomically distribute the node's configured rewards (including any conditional rewards whose conditions are met) and re-evaluate downstream unlock state in a single transaction; partial reward distribution on failure is not permitted.
- **FR-031**: When a node is failed and a configured retry limit is reached, the system MUST atomically apply the configured consequences once and prevent further automatic retries on that node.
- **FR-032**: When a student completes a node, any downstream nodes whose unlock conditions are now satisfied (considering choice paths, criteria paths, and AND/OR semantics on inbound connections) MUST move from locked to available.
- **FR-033**: The student-facing operations for starting, completing and retrying a node MUST be idempotent: repeated submissions for the same state transition MUST NOT double-distribute rewards or corrupt attempt counts.
- **FR-034**: When the student completes any end node (or all non-optional end nodes, per Adventure configuration), the system MUST mark the Adventure as complete for that student and record completion in audit history.
- **FR-035**: Students MUST see a clear "not yet started" indication for assignments whose start date is in the future, and a clear "ended" indication for assignments whose end date has passed.

#### Coexistence and scoping

- **FR-036**: The Adventures system MUST be strictly additive with respect to the existing Quest / QuestLog system: no observable behaviour, stored data, or visible UI of the legacy Quests area changes as a result of this feature, except for additive navigation entries that point teachers and students to the new Adventures area.
- **FR-037**: Adventures MUST be ownership-scoped by default: only the authoring teacher can edit or assign their Adventures; other teachers MUST NOT see them unless explicitly shared.
- **FR-038**: The system MUST record an audit trail for every node start, node completion, node failure with consequences applied, choice made, and Adventure completion event, including the student, character, node, score (where applicable) and rewards distributed.
- **FR-039**: Editing or deleting an Adventure that has students mid-flight MUST NOT corrupt those students' in-progress experience (see User Story 5).
- **FR-040**: The system MUST enforce, on every authoring and play action, that students only act on Adventures assigned to them (directly, via their class, or via their clan) and that teachers only edit Adventures they own (or have explicit permission for).

### Key Entities *(include if feature involves data)*

- **Adventure**: A reusable, teacher-authored map template. Has a title, description, background image, owner (teacher), draft/published status, sharing visibility, and a version number that increments when its structure changes after publish.
- **Adventure Node**: A single task placed on the map. Has a stable identifier within its Adventure, a position, a type (start / story / battle / quiz / choice / reward / milestone / boss / end), an optional/required flag, a description, type-specific verification settings (e.g. monster, question set, pass threshold), completion rules (retry limits, score thresholds), and a list of attached rewards and consequences.
- **Adventure Connection (Edge)**: A directed link from one node to another within the same Adventure. Has a condition (always / depends on a specific choice key / depends on a numeric criterion), an unlock-semantics flag (counts toward AND vs OR at the target node), and a sort order for presentation when it represents one option of a choice.
- **Node Reward**: A reward tied to a node, configurable per type (XP, gold, equipment, ability, clan XP, special currency, badge) and amount, with an optional condition (e.g. minimum score) under which the reward is granted.
- **Node Consequence**: A penalty applied when a node is failed beyond its retry limit (e.g. XP, gold, HP penalty, plus room for future penalty types).
- **Adventure Assignment**: A binding of an Adventure to a target — a class, a clan, or an individual student — by a specific teacher, with optional start and end dates and an active flag.
- **Adventure Progress (per character)**: A character's overall standing in an Adventure: status (not started / in progress / completed / abandoned), current node, started/completed/last-active timestamps, and a link to the assignment that created it.
- **Node Progress (per character per node)**: A character's standing on a single node: status (locked / available / in progress / completed / failed / skipped), number of attempts, last score, the choice they made if applicable, and timestamps.
- **Audit Event**: A record of a significant Adventure event (node start, node completion, node failure with consequences, Adventure completion), with enough payload to reconstruct what happened, who it happened to, and what rewards were granted.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A teacher with no prior exposure can place 5 nodes, connect them, configure rewards on at least one, and publish a valid linear Adventure within 10 minutes on first use.
- **SC-002**: A teacher with prior exposure can assign an existing published Adventure to a new class in under 60 seconds.
- **SC-003**: A student opening an assigned Adventure sees the rendered map (background plus current node states) within 2 seconds on a typical school-network connection.
- **SC-004**: Completing a node visually reflects its new "completed" state and any newly unlocked downstream nodes within 2 seconds of the student's action.
- **SC-005**: Across a typical class of 30 students all working through the same Adventure simultaneously, no student observes incorrect rewards, missing unlocks, or duplicated reward distributions.
- **SC-006**: 0 incidents of legacy Quest / QuestLog data corruption or behavioural regression are observed during and after rollout, verified by the legacy regression test suite continuing to pass unchanged.
- **SC-007**: In a teacher-feedback survey after one term of use, at least 80% of participating teachers rate the visual map editor as easier and faster to use than the legacy Quest form for authoring branching content.
- **SC-008**: At least 80% of students who start an Adventure can independently identify their next available step on the map without teacher intervention (measured by a short usability study or in-product survey).
- **SC-009**: The teacher progress view loads and displays the roster for an assigned Adventure of up to 60 students in under 3 seconds.
- **SC-010**: Reuse rate: in a school running the system for a full term, at least 50% of assignments after the first month are reuses (assigning an existing Adventure to a new target) rather than newly authored Adventures.
- **SC-011**: 100% of mid-flight edits to a published, in-use Adventure leave in-progress students' visible structure and rewards unchanged for the duration of their current run (verified by automated tests once snapshotting is in place).
- **SC-012**: The audit trail allows a teacher (or admin) to fully reconstruct what happened in any student's Adventure run — every node attempt, outcome, choice and reward — without ambiguity.

## Assumptions

- The legacy Quest / QuestLog system stays in place indefinitely during and after rollout of Adventures, and is not in scope to be migrated, deprecated, or removed by this feature. Coexistence is the explicit design choice.
- Visibility of Adventures defaults to private (only the authoring teacher sees them); cross-teacher sharing is opt-in via an explicit "shareable / public" flag set by the author.
- Adventure completion semantics default to "all non-optional end nodes must be completed", with the option to switch to "any one end node completes the Adventure" configurable per Adventure.
- Mid-flight stability is achieved by pinning each student's run to the Adventure version that was in effect when they were assigned (a snapshot of the structure they started on); deeper per-character snapshot serialisation is out of scope for v1 and only added if version pinning proves insufficient.
- The map graph is a directed acyclic graph by intent. Cycles are technically possible but warned against at publish time and are not optimised for.
- Connections from a node to itself are explicitly disallowed.
- A node with multiple inbound connections defaults to AND semantics (all upstream paths required) unless any individual inbound connection is set to OR, which is the mechanism for re-join nodes after branching.
- Choice nodes that have only one outbound connection treat that single option as auto-selected at runtime, but generate an authoring-time warning.
- The student's character marker animation, mini-map and other polish features are nice-to-have and not on the critical path for shipping the core loop; their absence does not invalidate FR-022..FR-034.
- Background image uploads are stored under the application's static asset path so they are served like other static images; uploaded files are size-limited (a sensible default — e.g. a few megabytes — applied at upload).
- Reusing an Adventure across classes results in independent per-character progress; no shared/team progress mode exists in v1.
- The school's existing identity model (users, classrooms, clans, students, characters) is reused as-is for ownership, assignment scoping and reward delivery. No new user roles or organisational structures are introduced.
- "Sharing across teachers in the same school" is supported at the level of all teachers visible in the existing teacher directory; a more formal multi-school separation is not introduced by this feature.
- The MVP scope (User Story 1) covers class-level assignment only; clan-level and individual-student assignment may be added in later milestones without changing the data model commitments above.
- Standard reasonable defaults apply for unspecified details: friendly user-facing error messages with fallbacks; the project's existing authentication and session model is reused for both teacher and student access; standard web-app performance expectations; no offline mode.

## Out of Scope

The following are intentionally not part of v1 of this feature and may be considered later:

- Clan-shared progress (multiple students collaboratively progressing through a single shared run of an Adventure).
- Cross-school sharing of Adventures outside of the school's own teacher directory.
- Time-limited individual nodes (a per-node "must complete within X seconds" rule).
- Analytics dashboards highlighting class-wide or school-wide difficulty hotspots, drop-off rates, etc.
- A tool to convert existing legacy Quests into starter Adventures.
- Retirement, deprecation, or any visible change to the legacy Quest / QuestLog system.
- Consequences (penalties) for branches the student did *not* choose at a choice node (i.e. losing rewards on the road not taken).
- A mobile-native or offline-capable mode for either authoring or playing Adventures.
