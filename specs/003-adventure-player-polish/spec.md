# Feature Specification: Adventures Player and Editor Polish

**Feature Branch**: `003-adventure-player-polish`

**Created**: 2026-09-21

**Status**: Draft

**Input**: User description: "A new Speckit feature for Adventures player/editor polish (travel animation, mini-map, keyboard/a11y) from the original Phase 5 roadmap: travel animation between nodes, mini-map, mobile responsiveness, accessibility pass (keyboard navigation in editor, screen-reader labels on the map), icon picker library, and clan and individual student assignment targets."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Travel animation after completing a node (Priority: P1)

A student completes a node on an assigned adventure. Their character marker briefly travels from the finished node along the path toward each newly unlocked next step. If more than one next step unlocks at once, the travel forks so the student can see every newly available destination. Completing a node with no newly unlocked successors leaves the marker on the finished node. Students who prefer reduced motion skip the travel and see the updated map immediately.

**Why this priority**: Progress currently updates in place, so students can miss which node just unlocked. A short travel beat is the original player-facing payoff for completing work and is the smallest change that makes the map feel like a journey.

**Independent Test**: Complete a story-style node that unlocks one successor and confirm the marker travels to that successor. Repeat with a branching unlock (two successors) and with an end node (no successors). Repeat with reduced motion enabled and confirm the map updates without travel.

**Acceptance Scenarios**:

1. **Given** a student completes an available node that unlocks exactly one successor, **When** they return to or remain on the map, **Then** a character marker travels from the completed node to the newly unlocked node and that node is visibly available.
2. **Given** a student completes a node that unlocks two or more successors, **When** the map updates, **Then** travel is shown toward each newly unlocked successor so none are easy to miss.
3. **Given** a student completes a node that unlocks no further nodes, **When** the map updates, **Then** the character marker remains on the completed node and no travel is shown.
4. **Given** the student has requested reduced motion, **When** a node is completed, **Then** node states update immediately without travel motion.
5. **Given** a student completes a battle or quiz that finishes off the map, **When** they return to the adventure map, **Then** the same travel behaviour runs for any nodes unlocked by that completion.
6. **Given** travel is in progress, **When** the student interacts with the map (selects a node, uses the mini-map, or starts another action), **Then** travel finishes or is skipped so the map remains usable and the final node states are correct.

---

### User Story 2 - Mini-map for orientation and camera jump (Priority: P2)

A student playing a large adventure sees a small overview of the whole map. Their current position and the visible area are marked on that overview. Selecting a spot on the overview jumps the main view there so they can find distant unlocked nodes without hunting.

**Why this priority**: Large teacher-authored maps already exist; without an overview, students lose their place. The mini-map is independent of travel animation and still valuable if travel ships first.

**Independent Test**: Open an adventure whose nodes extend beyond one screen. Confirm the overview shows the full layout, highlights the current view, and jumping via the overview moves the main map to that region.

**Acceptance Scenarios**:

1. **Given** a student is viewing an adventure map, **When** the map is larger than the visible area, **Then** a mini-map overview of the full adventure is visible without covering primary node labels in the default layout.
2. **Given** the student pans or zooms the main map, **When** the visible area changes, **Then** the mini-map indicates which part of the adventure is on screen and the character’s current position.
3. **Given** a student selects a location on the mini-map, **When** the jump completes, **Then** the main view centres on that location within one second.
4. **Given** a student is using a keyboard or screen reader, **When** they move focus to the mini-map, **Then** they can jump the view without relying on precise pointer aiming, and the control has an accessible name.
5. **Given** a compact (phone-sized) viewport, **When** the student opens the map, **Then** the mini-map remains usable and does not block the node detail panel or the primary action for the selected node.

---

### User Story 3 - Keyboard and screen-reader pass on editor and player (Priority: P3)

A teacher can author a map using the keyboard: move among nodes, select one, inspect it, delete the selected node or connection, deselect, zoom, and undo or redo recent map edits in the current session. A student can move among unlocked nodes, open details, and take the primary action without a pointer. Screen-reader users hear each node’s title, type, and status, and hear live confirmation when the map selection or validation state changes.

**Why this priority**: Both maps currently depend heavily on pointing. Keyboard and labels were only sketched in the foundation work. This pass is required for classroom accessibility and for teachers who prefer shortcuts.

**Independent Test**: Using only the keyboard, a teacher selects a node, opens its details, deletes it, undoes the delete, and zooms. Using only the keyboard, a student tabs to an available node, opens it, and completes a story node. A screen-reader user can identify locked versus available nodes from spoken labels.

**Acceptance Scenarios**:

1. **Given** a teacher is editing an adventure they own, **When** they use the keyboard only, **Then** they can focus the map, move among nodes, select a node, open its inspector, deselect, delete the selection (with the existing confirmation), and zoom in or out.
2. **Given** a teacher has just placed, moved, connected, or deleted a node or connection in this editing session, **When** they undo and then redo, **Then** the map returns to the previous and then the restored state without a page reload.
3. **Given** a student is on an assigned adventure map, **When** they use the keyboard only, **Then** they can move among unlocked nodes, open the detail panel, dismiss or leave it, and activate the primary node action.
4. **Given** a node is locked, **When** a keyboard or screen-reader user explores the map, **Then** the locked node is not presented as an activatable control, and its locked state is still discoverable from the spoken map description or status text.
5. **Given** a teacher or student changes selection, validation, or save outcome, **When** that change happens, **Then** a screen reader is notified of the new selection or message without requiring the user to hunt for it.
6. **Given** a teacher or student is using a phone-sized screen, **When** they open the editor or player, **Then** primary actions (place or select a node, open inspector or details, complete a simple node) remain reachable without essential controls being off-screen or overlapping each other.

---

### User Story 4 - Assign to a clan or an individual student (Priority: P4)

A teacher assigns a published adventure to one of their clans or to one student character, not only to a whole class. Students in that clan, or that individual, see the adventure in their list and can play it. Class-level assignment continues to work as it does today. The teacher can review and deactivate these assignments, and the progress roster lists the students covered by the chosen target.

**Why this priority**: Teachers already need small-group and catch-up assignment. Class-only assignment was an intentional MVP limit; the assignment concept already allows a class, clan, or individual target. This story unlocks that for teachers.

**Independent Test**: Assign a published adventure to a clan and confirm only that clan’s students see it. Assign the same adventure to one student in a different class and confirm only that student sees it. Confirm an existing class assignment is unchanged.

**Acceptance Scenarios**:

1. **Given** a teacher owns a published adventure and has at least one clan in their classes, **When** they assign the adventure to that clan, **Then** students currently in the clan see the adventure, and students outside the clan do not see it from that assignment.
2. **Given** a teacher owns a published adventure, **When** they assign it to one student character who belongs to one of the teacher’s classes, **Then** only that student sees the adventure from that assignment.
3. **Given** a class assignment already exists, **When** the teacher also creates a clan or individual assignment, **Then** class assignment behaviour is unchanged, and each student still sees the adventure at most once.
4. **Given** a teacher tries to assign to a clan or student they do not teach, **When** they submit the assignment, **Then** the assignment is rejected and nothing is created.
5. **Given** an active clan or individual assignment, **When** the teacher opens the assignment list and progress view, **Then** the target is labelled clearly (clan name or student name) and the roster includes the students covered by that target.
6. **Given** an active clan or individual assignment, **When** the teacher deactivates it, **Then** those students can no longer start new nodes from that assignment, matching existing class-assignment deactivation behaviour.

---

### User Story 5 - Choose a node icon from a library (Priority: P5)

A teacher selects a node and picks an icon from a library of adventure node icons. Each node type has a sensible default. The chosen icon appears on the editor map and on the student map. Clearing the override restores the default for that node type.

**Why this priority**: Icons help students scan a map, but they do not change whether an adventure is playable. This ships after movement, orientation, access, and assignment.

**Independent Test**: Change a battle node’s icon, save, reopen the editor, and open the student map. Confirm both show the new icon. Reset to default and confirm both maps return to the type default.

**Acceptance Scenarios**:

1. **Given** a teacher has selected a node, **When** they open the icon picker, **Then** they see a library of icons and can tell which icon is currently used (default or override).
2. **Given** a teacher picks an icon and saves the node, **When** they reopen the editor and a student opens the map, **Then** both views show the chosen icon on that node.
3. **Given** a teacher clears the icon override, **When** the node is saved, **Then** the node displays the default icon for its type.
4. **Given** a teacher changes a node’s type after an icon override, **When** they have not picked a new icon, **Then** the node either keeps the override or falls back to the new type’s default in a way that is visible in the picker so the teacher is not surprised.

---

### Edge Cases

- Completing a node unlocks several successors at once: travel must show every new destination, not only the first.
- Completing a node unlocks nothing: no travel, marker stays put.
- The student has reduced motion enabled: skip travel; still update states and marker position.
- The student acts during travel (opens a node, uses the mini-map, leaves the page): final map state matches the completed node; no stuck mid-travel marker.
- Battle or quiz completion happens on another page: travel runs when the student next sees the map.
- Mini-map on a tiny map that already fits on screen: overview may be hidden or de-emphasised; jumping is still harmless if shown.
- Mini-map on a phone: must not cover the selected node’s primary action.
- Keyboard focus trapped in inspector, detail panel, or modal: Esc returns to the map or closes the overlay.
- Undo/redo after a failed save: the visible map stays consistent with the last successful save; the teacher is told if an undo cannot be applied.
- Assigning the same clan or the same student twice while an assignment is still active: rejected with a clear message.
- A clan with zero members: assignment may be created, but the teacher is warned that nobody will see it yet.
- A student is in both an assigned class and an assigned clan: they see the adventure once and play a single run.
- A student leaves a clan after assignment: they keep in-progress work already started; they do not newly receive the clan assignment after leaving.
- Icon library image missing or unavailable: the type default (or a non-image fallback such as the node type name) is shown; the map remains usable.
- Screen-reader user during travel: an announcement of newly unlocked node titles is enough; they should not have to watch motion.

## Requirements *(mandatory)*

### Functional Requirements

#### Player map

- **FR-001**: After a student completes a node, the student map MUST show a brief character-marker travel from that node toward each newly unlocked successor.
- **FR-002**: If a completed node unlocks no successors, the character marker MUST remain on the completed node and MUST NOT travel.
- **FR-003**: If a completed node unlocks more than one successor, travel MUST indicate every newly unlocked successor.
- **FR-004**: Students who prefer reduced motion MUST receive an immediate map update with no travel motion.
- **FR-005**: Travel MUST NOT block the student from using the map; interrupting travel MUST leave correct final node states and marker position.
- **FR-006**: Completions that finish away from the map (battle or quiz) MUST produce the same travel behaviour the next time the student views the map for that adventure.
- **FR-007**: The student map MUST display a character marker at the student’s current or last completed position whenever progress exists.
- **FR-008**: The student map MUST provide a mini-map overview of the full adventure when the layout extends beyond the visible area.
- **FR-009**: The mini-map MUST show which part of the adventure is currently on screen and the character marker’s position relative to the full map.
- **FR-010**: Selecting a location on the mini-map MUST move the main view to that location so the student can see it within one second.
- **FR-011**: The mini-map MUST have an accessible name and MUST be operable by keyboard, not only by pointer.
- **FR-012**: On a phone-sized viewport, the mini-map, node detail panel, and primary node action MUST remain usable without essential controls covering one another.

#### Keyboard, screen readers, and small screens

- **FR-013**: Teachers MUST be able to focus the editor map and move among nodes using the keyboard.
- **FR-014**: Teachers MUST be able to select a focused node, open its inspector, deselect, and delete the current selection from the keyboard, using the same confirmation already required for destructive deletes.
- **FR-015**: Teachers MUST be able to zoom the editor map from the keyboard.
- **FR-016**: Teachers MUST be able to undo and redo recent map edits (place, move, connect, delete) made in the current editor session from the keyboard.
- **FR-017**: Students MUST be able to move among unlocked nodes, open and leave the detail panel, and activate the primary node action using the keyboard.
- **FR-018**: Locked nodes MUST NOT be presented as activatable controls to keyboard users.
- **FR-019**: Every visible node on the student map MUST expose an accessible name that includes the node title and current status (locked, available, in progress, completed, failed, or skipped).
- **FR-020**: Every visible node on the editor map MUST expose an accessible name that includes the node title and type.
- **FR-021**: Changes to selection, validation messages, and save success or failure MUST be announced to assistive technology.
- **FR-022**: Editor and player layouts MUST keep primary map actions reachable on a phone-sized screen.

#### Assignment targets

- **FR-023**: Teachers MUST be able to assign a published adventure to a clan that belongs to one of their classes.
- **FR-024**: Teachers MUST be able to assign a published adventure to an individual student character who belongs to one of their classes.
- **FR-025**: Existing class assignment MUST continue to work and MUST remain available in the same assignment area.
- **FR-026**: Each assignment MUST have exactly one target: a class, a clan, or an individual student character.
- **FR-027**: Teachers MUST only assign to classes, clans, and students they teach; other targets MUST be rejected.
- **FR-028**: A student MUST see an adventure if they are covered by at least one active assignment (their class, their current clan, or themselves) and MUST see it only once.
- **FR-029**: Teachers MUST be able to list, inspect progress for, and deactivate clan and individual assignments with the same start/end window behaviour already used for class assignments.
- **FR-030**: Creating a second active assignment to the same adventure and the same target MUST be rejected with a clear message.

#### Node icons

- **FR-031**: Each node type MUST have a default icon that appears on both the editor map and the student map when no override is set.
- **FR-032**: Teachers MUST be able to pick an icon for a selected node from a provided library and save that choice on the node.
- **FR-033**: Clearing an icon override MUST restore the default icon for the node’s type.
- **FR-034**: The student map MUST display the teacher’s chosen icon (or the type default) on each node.

### Key Entities

- **Character marker**: The student’s visible position on the adventure map. It sits on the current or last completed node and travels toward newly unlocked nodes after completion.
- **Mini-map**: A small overview of the full adventure used to stay oriented and to jump the main view. It reflects viewport and marker position.
- **Node icon**: The picture used for a node on editor and player maps. Defaults come from the node type; a teacher may override per node from a library.
- **Adventure assignment target**: The audience of an assignment — an entire class, one clan, or one student character — still with optional start and end dates and an active flag. Progress remains per character; this feature does not introduce shared clan progress.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After a student completes a node that unlocks a successor, at least 90% of first-time testers can point to the newly available node within 3 seconds of the map updating (with travel enabled).
- **SC-002**: Travel, when shown, finishes in under 1.5 seconds and never leaves the map in a state that disagrees with the student’s saved progress.
- **SC-003**: On an adventure whose nodes do not fit in one screen, a student can jump to a distant unlocked node via the mini-map in under 5 seconds, including finding the overview control.
- **SC-004**: A teacher who cannot use a pointer can select a node, change its title in the inspector, save, and delete a different node using only the keyboard, in one uninterrupted session.
- **SC-005**: A student who cannot use a pointer can open an assigned adventure, select an available story node, and complete it using only the keyboard.
- **SC-006**: 100% of visible student-map nodes expose a spoken name that includes title and status; locked nodes are not operable.
- **SC-007**: A teacher who already knows class assignment can assign a published adventure to a clan or to one student in under 60 seconds.
- **SC-008**: 0 regressions in class-only assignment: students covered only by a class assignment still see and play the adventure exactly as they do today.
- **SC-009**: After a teacher changes a node icon and saves, both the editor and a student view of that adventure show the new icon the next time each person looks at the map, with no mismatch between the two views.
- **SC-010**: On a phone-sized viewport, a student can complete a story node and a teacher can select and inspect a node without essential controls being unreachable.
- **SC-011**: Users with reduced motion enabled never see travel motion; they still see correct node states and marker position immediately after completion.

## Assumptions

- This feature polishes the already-shipped Adventures authoring and play loop (specs 001 and 002). It does not change node types, unlock rules, rewards, snapshotting, or school-level sharing.
- Class assignment remains the default path; clan and individual assignment are additional targets in the same teacher assignment area.
- A student matched by more than one active assignment still plays a single personal run. This is not clan-shared progress.
- Clan membership is evaluated at the time the student accesses the adventure. Students who already started keep their run if they later leave the clan; they do not newly gain a clan assignment after leaving.
- The character marker is a simple map token, not a new animated character sprite system.
- Travel is a short visual cue, not a timed challenge and not skippable as a separate setting beyond the student’s reduced-motion preference.
- Mini-map is required on the student map. A teacher-editor overview is out of scope unless it falls out of the same player work; the original Phase 5 mini-map is the student overview.
- Keyboard undo/redo applies to map edits in the current editor session only and does not have to survive a full page reload.
- The icon library is a curated set of provided icons. Teachers do not upload arbitrary icon files in this feature.
- Phone-sized use is a responsive web pass, not a native mobile app and not an offline mode.
- Existing start/end windows, publish-before-assign, and deactivation rules apply unchanged to clan and individual assignments.
- Screen-reader support targets the school’s usual browser assistive technology. Custom screen-reader plugins are not required.
- Default icons may be simple type marks if a full illustrated set is not ready; the picker still lets teachers choose among the provided library.

## Out of Scope

- Cross-teacher cloning beyond what already exists, public sharing across schools, and clan-shared (collaborative) progress.
- Time-limited individual nodes, difficulty analytics, and migrating legacy quests into Adventures.
- Auto-layout / “tidy”, snap-to-grid, and live “preview as student” sandbox work, except where keyboard or small-screen fixes touch those screens.
- Custom icon file uploads and per-theme icon packs beyond one shared library plus type defaults.
- Changing an existing assignment’s target type in place (teachers deactivate and create a new assignment).
- New student roles, new teacher roles, or changes to the legacy Quests area.
