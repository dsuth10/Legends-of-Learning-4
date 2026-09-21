# Feature Specification: Student UI Remaining Gaps

**Feature Branch**: `004-student-ui-gaps`

**Created**: 2026-09-21

**Status**: Draft

**Input**: User description: "Start another spec-kit project for the student UI remaining-gaps audit."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - One student shell on every student destination (Priority: P1)

A student signed in with a character moves among Character, Quests, Shop, Equipment, Adventures, Progress, Powers, Clan, and Profile and always sees the same surrounding chrome: class or clan identity, the clan (or solo) strip with HP and power, character stats, and a destination list that highlights the current page. They never drop into a different, older-looking page for those destinations. A student who still needs to create a character sees the same visual language on the create-character screen, with stats and clan details omitted until a character exists.

**Why this priority**: The redesign already exists on Character, Quests, Shop, and Equipment, but several everyday destinations still use a separate layout. That split is the largest remaining gap and the one students hit as soon as they leave the four rebuilt pages.

**Independent Test**: Starting from Character, visit Quests, Shop, Equipment, Adventures list, Progress, Powers, Clan, and Profile. Confirm each uses the same header, clan strip, stats (when a character exists), and destination list, with the current destination highlighted. Repeat with a student who has no character yet on create-character.

**Acceptance Scenarios**:

1. **Given** a student with an active character, **When** they open Character, Quests, Shop, Equipment, Adventures list, Progress, Powers, Clan, or Profile, **Then** each screen shows the shared student chrome (identity bar, clan or classroom strip, stats, destination list) and highlights the current destination.
2. **Given** a student is on any of those screens, **When** they use the destination list, **Then** they can reach Character, Quests, Shop, Equipment, Adventures, Progress, and Powers without hunting for a different menu style.
3. **Given** a student with a character but no clan, **When** they open any of those screens, **Then** the strip shows their classroom name and only their own tab with their HP and power.
4. **Given** a student with no character yet, **When** they open create-character, **Then** the page uses the same visual language as the rest of the student area, and missing stats or clan details are explained rather than shown as empty or broken bars.
5. **Given** a student returns to Character after visiting Progress or Powers, **When** the Character page loads, **Then** it still uses the redesigned layout (the older character layout is not shown).

---

### User Story 2 - Controls that look real actually work (Priority: P2)

A student only sees actions they can take. Decorative or unfinished ideas from the design comps (special shop offers, auto-equip, save loadout, quest filters, character rotate, a documents icon with no destination) are either working features or not presented as clickable primary actions. Clan-mate tabs in the strip show teammates’ HP and power for awareness; they do not pretend to switch the signed-in student into another student.

**Why this priority**: Unfinished chrome is already on the rebuilt pages. It trains students to ignore buttons and makes the app feel broken even where the redesign is furthest along.

**Independent Test**: Walk Character, Quests, Shop, and Equipment and attempt every control that looks interactive. Each either completes a real action with feedback or is absent / clearly not an action. Clan-mate tabs do not change whose account is signed in.

**Acceptance Scenarios**:

1. **Given** a student is on Shop, **When** there is no real limited-time offer, **Then** no “special offer” message is shown as if a sale were active.
2. **Given** a student is on Equipment, **When** auto-equip and save-loadout are not available, **Then** those controls are not shown as the primary actions on the page.
3. **Given** a student is on Quests, **When** quest filtering is not available, **Then** no disabled filter control is presented as a page action.
4. **Given** a student is on Character or Equipment, **When** rotating the portrait is not available, **Then** no “click to rotate” hint is shown.
5. **Given** a student is looking at the top identity bar, **When** a documents or reports control has no destination, **Then** it is not shown as a clickable icon.
6. **Given** a student is in a clan, **When** they select another member’s tab in the clan strip, **Then** they are not signed in as that member; the tab is either non-interactive awareness or opens a permitted clan view of that member without impersonation.

---

### User Story 3 - Finish the four redesigned pages (Priority: P3)

On Character, Quests, Shop, and Equipment, the remaining design intent from the comps is present and truthful: the identity bar names the class (and clan when the student is in one), equipped powers show their real names and pictures, clan-mate portraits appear on Character when the student has clan-mates, gold and resource bars reflect actual amounts, and Equipment is reachable from Character as a first-class destination.

**Why this priority**: These pages are already the redesign. Closing leftover mismatches avoids a second partial pass later. This is independent of bringing leftover pages onto the shell.

**Independent Test**: Compare Character, Quests, Shop, and Equipment against the design comps for identity, powers, party portraits, resource bars, and destination coverage. Confirm each leftover mismatch from the audit is resolved without adding the out-of-scope placeholder systems.

**Acceptance Scenarios**:

1. **Given** a student with a classroom, **When** they open Character, Quests, Shop, or Equipment, **Then** the top identity bar shows the class name (and clan name when they belong to a clan), not a comma-separated list of member names as the primary identity.
2. **Given** a student has equipped powers, **When** they open Character, **Then** each equipped power shows its name and its own picture (not a generic bolt for every power), and empty power slots are labelled as empty.
3. **Given** a student is in a clan with other members, **When** they open Character, **Then** portraits for other clan members are visible; if they have no clan-mates, no empty party cluster is shown.
4. **Given** a student has gold, health, power, and experience, **When** they view the stats on Character, Shop, or Equipment, **Then** the filled portion of each bar matches the current value versus the maximum (gold may be shown as an amount without a fake fill).
5. **Given** a student is on Character, **When** they look at destinations, **Then** they can open Equipment without leaving the shared destination list, and the current page (Character) is the one highlighted.
6. **Given** a student is on Quests, Shop, or Equipment, **When** they look at destinations, **Then** Character and Adventures are reachable from that same list.

---

### User Story 4 - The shell still works on a small screen (Priority: P4)

A student on a phone-sized screen can read their HP and gold, switch destinations, and complete the primary task on Character, Quests, Shop, and Equipment without the clan strip or stats column covering the main action or requiring sideways hunting for essential controls.

**Why this priority**: The redesign was composed for a wide classroom display. Small screens are a real classroom device class, but they do not block shipping a consistent desktop shell first.

**Independent Test**: Using a phone-sized viewport, open Character, Quests, Shop, and Equipment. Confirm stats, destinations, and the page’s primary action remain reachable, and that clan-mate tabs can be scrolled rather than overflowing off-screen with no way to reach them.

**Acceptance Scenarios**:

1. **Given** a phone-sized viewport, **When** a student opens Character, Quests, Shop, or Equipment, **Then** they can see current HP and gold and open another destination without essential controls sitting off-screen with no way to reach them.
2. **Given** a clan with more members than fit on a phone-width strip, **When** the student views the strip, **Then** they can scroll to other members; the current student’s tab remains identifiable.
3. **Given** a phone-sized viewport on Equipment or Shop, **When** the student equips or buys an item they can afford, **Then** the confirm action is reachable and not covered by the clan strip or stats column.
4. **Given** a student uses a keyboard on a wide screen, **When** they tab through the shared chrome, **Then** destination links and primary page actions are reachable in a sensible order, and non-interactive clan tabs are not in the tab order as buttons.

---

### Edge Cases

- Student has a character but no classroom: identity bar still identifies the student; clan strip does not invent classmates.
- Student has a classroom but no clan: classroom name is shown; only the current student’s tab appears.
- Student has a clan with one member (themselves): no party portraits; strip shows only their tab.
- Character name is a single word: name display does not leave a blank second line that looks like missing data.
- Character has zero equipped powers: empty slots are shown, not a broken grid.
- Character has more equipped powers than the grid shows: the student can still reach the rest from Powers.
- Gold, HP, or power is zero: bars show empty/zero, not a decorative partial fill.
- HP or power exceeds the displayed maximum (temporary bonus): the bar is full and the numeric values remain truthful.
- Student is fallen (0 HP) or a clan-mate is fallen: existing rescue messaging still appears on Character and Powers inside the shared shell.
- Shop has no items in a category: the student sees an empty state, not leftover offer copy.
- Inventory is empty or full: empty slots or a full-inventory message remain understandable on small screens.
- Create-character after the shell change: submitting a valid character still lands the student in the redesigned Character page.
- Adventures list with zero assignments: empty state uses the shared shell, not the old generic page.
- Teacher-facing screens and the adventure map are unchanged by this feature.

## Requirements *(mandatory)*

### Functional Requirements

#### Shared student chrome

- **FR-001**: Authenticated student destinations in scope MUST present one shared chrome: identity bar, clan or classroom strip, character stats (when a character exists), and a destination list.
- **FR-002**: The destination list MUST include Character, Quests, Shop, Equipment, Adventures, Progress, and Powers, and MUST visually indicate the current destination.
- **FR-003**: In-scope destinations are Character, Quests, Shop, Equipment, Adventures list, Progress, Powers, Clan, Profile, and Create character. The adventure map and battle screens are excluded.
- **FR-004**: The identity bar MUST show the student’s class name when they have a classroom, and MUST show the clan name when they belong to a clan.
- **FR-005**: The clan strip MUST show the current student first, highlighted, with current HP and power, then other clan members’ names with their HP and power when a clan exists.
- **FR-006**: Students without a clan MUST see a classroom-labelled strip containing only themselves.
- **FR-007**: Character stats in the shared chrome MUST show current and maximum HP, current and maximum power, experience toward the next level, spendable power points, and gold, using the student’s live values.
- **FR-008**: Students without a character MUST still see the student visual language on Create character, without fabricated stats.
- **FR-009**: Existing fallen-student and fallen-clan-mate notices MUST remain visible on Character and Powers after the chrome is unified.

#### Honest controls

- **FR-010**: The product MUST NOT present a control as an available action if that action cannot be completed.
- **FR-011**: Shop MUST NOT show a limited-time offer unless a real offer exists (none is in scope for this feature, so the offer banner MUST NOT appear).
- **FR-012**: Equipment MUST NOT show Auto Equip or Save Loadout as page actions in this feature.
- **FR-013**: Quests MUST NOT show a Filter Quests action in this feature.
- **FR-014**: Character and Equipment MUST NOT claim the portrait can be rotated.
- **FR-015**: The identity bar MUST NOT show a documents/reports icon unless it opens a real student destination.
- **FR-016**: Clan-mate strip tabs MUST NOT sign the student in as another student.

#### Redesigned page completeness

- **FR-017**: Equipped powers on Character MUST display each power’s own name and picture; empty slots MUST be labelled empty.
- **FR-018**: Character MUST show portraits of other clan members when they exist, and MUST hide the party cluster when they do not.
- **FR-019**: Resource bars MUST fill in proportion to current versus maximum values. Gold MUST display the true amount and MUST NOT use a decorative fill unrelated to a maximum.
- **FR-020**: Character MUST treat Equipment as a first-class destination in the shared list.
- **FR-021**: Quests, Shop, and Equipment MUST treat Character and Adventures as destinations in the shared list.
- **FR-022**: Shop category browsing (weapon, armour, accessory, all) and purchase of affordable items MUST continue to work after chrome changes.
- **FR-023**: Equipment equip and unequip MUST continue to work after chrome changes.
- **FR-024**: Quest log selection, objectives, rewards, start, and turn-in MUST continue to work after chrome changes.

#### Small screens and access

- **FR-025**: On a phone-sized viewport, students MUST be able to read HP and gold and reach the primary action on Character, Quests, Shop, and Equipment.
- **FR-026**: Clan strips that overflow the viewport MUST be scrollable, with the current student still identifiable.
- **FR-027**: Non-interactive chrome MUST NOT appear in keyboard tab order as buttons.
- **FR-028**: Interactive destination links and primary actions MUST be reachable by keyboard.

### Key Entities

- **Student chrome**: The repeating frame around student pages — identity bar, clan or classroom strip, stats, and destination list — so those pages feel like one place.
- **Student destination**: A signed-in page a student is meant to live in day to day (Character, Quests, Shop, Equipment, Adventures list, Progress, Powers, Clan, Profile, Create character).
- **Clan strip tab**: A compact view of one clan member’s name, HP, and power. It is awareness, not account switching.
- **Design comp**: The agreed Character, Quest, Shop, Equipment, Login, and Welcome mock screens. Login and Welcome already match; this feature closes remaining gaps against the four student comps and extends the same chrome to leftover destinations.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A tester who starts on Character can open Quests, Shop, Equipment, Adventures list, Progress, and Powers in one continuous session and report that all six use the same surrounding chrome, with no return to the older generic student layout.
- **SC-002**: On Character, Quests, Shop, and Equipment, a first-time tester finds zero controls that look like primary actions but do nothing.
- **SC-003**: 100% of in-scope student destinations highlight the current destination in the shared list (or an equivalent current-page indicator on Clan, Profile, and Create character).
- **SC-004**: A student with equipped powers can name each power from the Character page using the picture and label shown there, without opening Powers, for every power shown in the grid.
- **SC-005**: After chrome changes, a student can still buy an affordable shop item, equip an inventory item, and start or turn in an assigned quest on the first attempt.
- **SC-006**: On a phone-sized viewport, a student can move from Character to Shop and complete a purchase (when they can afford an item) without an essential control being unreachable.
- **SC-007**: Students without a clan, without clan-mates, or without a character can complete their available tasks without seeing empty party portraits, invented classmates, or fabricated stat bars.
- **SC-008**: Login and the public welcome screen remain usable and visually consistent with their existing redesign; this feature does not regress sign-in.

## Assumptions

- An audit of the live student area against the redesign comps and mapping was done as part of writing this spec. Remaining gaps are: leftover pages still on the old generic layout (Progress, Clan, Profile, Create character), Powers and Adventures list only partly on the new look, duplicated and inconsistent destination lists, and several non-functional controls on the four rebuilt pages.
- Character, Quests, Shop, and Equipment already use the redesign as their main screens. This feature finishes those pages and brings leftover destinations onto the same chrome rather than redesigning them from scratch.
- Login (“Portal Access”) and the public Welcome screen already match their comps and are not rebuild targets.
- Progress, Powers, Clan, Profile, and Create character keep their current information and tasks; they are restyled only enough to sit in the shared chrome. No new Progress, Clan, or Profile comps are required.
- Placeholder systems called out in the mapping as future (special offers, auto-equip, save loadout, quest filters, portrait rotation) stay out of this feature. Unfinished chrome for those ideas is removed rather than implemented.
- Clan-strip awareness of teammates’ HP and power is intentional (classroom visibility). Impersonating another student is not.
- Adventures map play and battle screens stay on their own layouts from the Adventures work. Only the Adventures *list* joins the shared chrome.
- Teacher screens are unchanged.
- Phone-sized use is a responsive web pass, not a native app.
- Existing authentication, character creation rules, shop pricing, equipment slot rules, quest assignment, powers spending, and behaviour/fallen rules are unchanged.

## Out of Scope

- Rebuilding Login or Welcome (already aligned with comps).
- Adventure map play, mini-map, travel animation, and battle arena or results screens.
- Teacher dashboard, teacher shop, assignment, and editor screens.
- Building a special-offer / sale engine, auto-equip, saved loadouts, quest filtering, or 3D/rotating character portraits.
- New student game systems (new stats, new destinations, new reward types).
- Clan-shared progress, public adventure sharing, or other Adventures Phase 6 items.
- Dark-mode as a new product setting beyond whatever the current student screens already do.
- Pixel-perfect recreation of stock photos from the comps; local classroom art may be used as long as layout and information match.
