# Feature Specification: Adventure Editor Enhancements

**Feature Branch**: `002-adventure-editor-enhancements`

**Created**: 2026-05-22

**Status**: Draft

**Input**: User description: "@Ideas/Adventure-editor-three-features-plan.md"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Attach Question Sets to Quiz Nodes (Priority: P1)

A teacher selects a quiz node in the Adventure Editor and chooses one of their available question sets so the quiz node becomes ready for students to play. If the teacher has no question sets, the editor clearly explains that a question set must be created before the quiz node can be completed by students.

**Why this priority**: Quiz nodes are already part of the adventure map concept, but they do not deliver classroom value unless teachers can connect them to real assessment content. This is the smallest improvement that unlocks a currently incomplete node type.

**Independent Test**: Can be tested by creating or opening an adventure with a quiz node, assigning one of the teacher's question sets to that node, saving the node, reopening the adventure, and confirming the selection remains visible and publish validation no longer treats the quiz node as missing content.

**Acceptance Scenarios**:

1. **Given** a teacher has at least one question set, **When** they select a quiz node, **Then** they can choose one of their own question sets for that node.
2. **Given** a teacher chooses a question set for a quiz node and saves, **When** the adventure is reopened, **Then** the same question set remains associated with the quiz node.
3. **Given** a teacher has no available question sets, **When** they select a quiz node, **Then** the editor shows an empty-state message and a clear path to manage question sets.
4. **Given** a quiz node references content the current teacher cannot use, **When** the node is selected, **Then** the editor identifies the content as unavailable and asks the teacher to pick an available question set.
5. **Given** a quiz node has a valid question set, **When** the teacher reviews readiness to publish, **Then** the node is not flagged as missing quiz content.

---

### User Story 2 - Edit Adventure Settings In The Editor (Priority: P2)

A teacher edits adventure-level details without leaving the Adventure Editor. They can update the adventure title, description, visual theme, background image, completion rule, and sharing visibility, then save those settings and immediately see the important visible changes reflected in the editor.

**Why this priority**: Adventure metadata affects how teachers organize maps and how students understand them. Keeping these edits inside the editor reduces context switching and makes the authoring experience feel complete.

**Independent Test**: Can be tested by opening an existing adventure, changing its title, description, theme, background image, and completion rule, saving, refreshing the editor, and confirming the updated settings are still visible and accurate.

**Acceptance Scenarios**:

1. **Given** a teacher is editing an adventure they own, **When** they open adventure settings, **Then** they can view the current title, description, theme, background image, completion rule, and sharing visibility.
2. **Given** a teacher changes one or more adventure settings and saves, **When** the save succeeds, **Then** the editor confirms the save and updates visible title and background information without requiring the teacher to leave the page.
3. **Given** a teacher uploads a valid background image, **When** the upload succeeds, **Then** the editor shows a preview and uses that image as the adventure background.
4. **Given** a teacher provides invalid or incomplete settings, **When** they attempt to save, **Then** the editor explains what must be corrected and preserves the teacher's entered values.
5. **Given** a teacher opens settings but makes no changes, **When** they close the settings area, **Then** the adventure remains unchanged.

---

### User Story 3 - Reposition Nodes By Dragging (Priority: P3)

A teacher moves existing adventure nodes directly on the map by dragging them to better align with the background image and narrative flow. The new positions are saved so the layout remains the same when the adventure is reopened.

**Why this priority**: Dragging nodes is a major usability improvement for visual map authoring, but teachers can still build adventures with the existing placement controls. It is prioritized after quiz configuration and settings because it is more interaction-heavy and benefits from the simpler editor improvements being stable first.

**Independent Test**: Can be tested by dragging an existing node to a new location, confirming connected paths visually follow the node, refreshing the editor, and confirming the node remains at the new location.

**Acceptance Scenarios**:

1. **Given** a teacher can edit an adventure, **When** they drag a node to a new spot on the map, **Then** the node moves with the pointer and connected paths remain visually attached during the move.
2. **Given** a teacher releases a dragged node within the map area, **When** the move is saved, **Then** the node remains at the new location after the adventure is reopened.
3. **Given** a teacher starts a tiny pointer movement that is effectively a click, **When** they release the node, **Then** the editor treats the action as node selection rather than a reposition.
4. **Given** a teacher tries to drag a node outside the map area, **When** they release it, **Then** the final position stays within visible map bounds.
5. **Given** the editor is in a mode intended for connecting nodes or the adventure cannot be edited, **When** the teacher attempts to drag a node, **Then** the node does not move.
6. **Given** saving a new node position fails, **When** the editor reports the failure, **Then** the node returns to its previous saved position and the teacher can retry.

---

### Edge Cases

- A teacher has no question sets available: quiz nodes show a helpful empty state and remain clearly incomplete until a question set is chosen.
- A quiz node references a question set the current teacher cannot use: the editor shows the unavailable state and requires a replacement before the node is considered ready.
- A background image is invalid, too large, or unsupported: the editor rejects it with a user-friendly message and keeps the previous background.
- A settings save only changes some fields: unchanged adventure settings remain intact.
- A teacher loses permission to edit while viewing the editor: editable controls no longer save changes and the user sees a clear permission message.
- A node is dragged beyond map boundaries: the saved position is constrained to the visible map.
- A node drag is cancelled or fails to save: the visible layout returns to the last saved position.
- A teacher uses touch, pen, or mouse input: repositioning behaves consistently across supported pointer types.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Teachers MUST be able to assign one of their available question sets to a quiz node from within the Adventure Editor.
- **FR-002**: Teachers MUST only see question sets that are available for their own use when configuring a quiz node.
- **FR-003**: The editor MUST show a clear empty state when no question sets are available for the teacher.
- **FR-004**: The editor MUST identify when a quiz node's saved question set is unavailable to the current teacher.
- **FR-005**: The system MUST preserve a quiz node's selected question set after saving and reopening the adventure.
- **FR-006**: Adventure readiness checks MUST treat quiz nodes with valid question sets as configured for quiz content.
- **FR-007**: Teachers MUST be able to edit adventure title, description, theme, background image, completion rule, and sharing visibility from within the editor.
- **FR-008**: The editor MUST show current adventure settings before the teacher changes them.
- **FR-009**: The system MUST save only the teacher's intended adventure setting changes while preserving settings they did not change.
- **FR-010**: The editor MUST confirm successful settings saves in a way that is perceivable without interrupting the teacher's workflow.
- **FR-011**: Visible editor information MUST update after successful settings saves when the changed setting affects the current view.
- **FR-012**: The editor MUST preview a successfully selected background image before or immediately after the teacher saves it.
- **FR-013**: The system MUST reject invalid background images and explain the problem in plain language.
- **FR-014**: Teachers MUST be able to drag editable nodes to new positions on the adventure map.
- **FR-015**: Connected paths MUST remain visually attached to nodes while nodes are being repositioned.
- **FR-016**: The system MUST save the final node position after a completed drag.
- **FR-017**: The editor MUST preserve node positions after the adventure is reopened.
- **FR-018**: The editor MUST distinguish normal node selection from intentional repositioning.
- **FR-019**: The system MUST keep node positions within the map's visible bounds.
- **FR-020**: Node dragging MUST be disabled when the teacher is connecting nodes or when the adventure is not editable.
- **FR-021**: If saving a dragged node position fails, the editor MUST return that node to its last saved position and notify the teacher.
- **FR-022**: All validation and save failures for these editor actions MUST be shown in the editor with enough detail for the teacher to recover.
- **FR-023**: These enhancements MUST preserve existing adventure creation, publishing, assignment, and student play behavior.

### Key Entities *(include if feature involves data)*

- **Adventure**: The teacher-authored map, including its title, description, visual presentation, completion rule, sharing visibility, and background.
- **Adventure Node**: A positioned item on the map that represents a playable or informational step, including quiz nodes and their configured learning content.
- **Question Set**: A teacher-owned collection of quiz content that can be attached to a quiz node.
- **Node Position**: The saved map location of an adventure node, used to render the teacher's intended layout.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 95% of teachers with at least one question set can attach a question set to a quiz node in under 30 seconds during usability testing.
- **SC-002**: 100% of saved quiz-node question set selections remain accurate after reopening the same adventure in test scenarios.
- **SC-003**: Teachers can update adventure title, description, theme, background, completion rule, and sharing visibility without leaving the editor.
- **SC-004**: 95% of successful adventure settings saves show visible confirmation within 2 seconds.
- **SC-005**: 100% of invalid background image attempts in testing produce a clear error and preserve the previous background.
- **SC-006**: 95% of teachers can reposition an existing node and confirm the saved placement after refresh in under 20 seconds.
- **SC-007**: During drag testing, connected paths remain visually attached to moving nodes in all tested maps with up to 50 nodes.
- **SC-008**: No existing adventure publishing, assignment, or student play regression is observed in the adventure smoke test suite after these enhancements.
- **SC-009**: Teacher satisfaction with the adventure editing workflow improves by at least 20% in post-test feedback compared with the current editor.

## Assumptions

- The target users are teachers who already have access to the Adventure Editor and can create or edit adventures.
- The existing adventure authoring model, publish checks, assignment flow, and student play flow remain in place.
- Question sets already exist elsewhere in the product; this feature only makes them selectable for quiz nodes in the Adventure Editor.
- Teachers can only attach question sets they are permitted to use.
- Adventure settings are saved deliberately by the teacher rather than automatically on every keystroke.
- Node repositioning is available only for editable adventures and does not change node content, connections, or student progress by itself.
- Completion rule means whether all ending nodes or any ending node can complete the adventure.
- The recommended implementation sequence is quiz question sets first, adventure settings second, and drag repositioning third because that order unlocks the most value with the least interaction risk first.
