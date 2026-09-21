# Feature Specification: Audio Meter Targeting

**Feature Branch**: `005-audio-meter-targeting`

**Created**: 2026-09-21

**Status**: Draft

**Input**: User description: "Audio meter that can target whole class, individual clans, or individual students. Measures classroom audio; if it triggers beyond a preset amount, the reward for completing the full time without triggering is halved (ceil rounding). Example: 1000 XP / 100 gold → 500/50 → 250/25 → 125/13."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Run a quiet-time session for selected participants (Priority: P1)

A teacher opens the classroom audio meter, chooses who is in the session (whole class, one or more clans, and/or individual students), sets a noise threshold, timer length, and base XP and gold rewards, then starts a session on the projector display. The meter listens to the room microphone. When the session timer completes without (or despite) noise triggers, only the selected participants receive the current reward tier. Students not selected receive nothing from that session.

**Why this priority**: Targeting is the core gap versus today’s whole-class-only tool. Without it, the feature cannot support clan competitions or small-group quiet work.

**Independent Test**: Configure a class with at least two clans and several students. Select one clan only, run a short session to completion with zero triggers, and confirm only that clan’s active characters receive the full base XP and gold. Confirm non-selected students’ XP and gold are unchanged.

**Acceptance Scenarios**:

1. **Given** a teacher owns an active classroom with students who have active characters, **When** they select the whole class as participants and complete a session with zero triggers, **Then** every active character in that class receives the full configured base XP and base gold.
2. **Given** a classroom with two clans, **When** the teacher selects only Clan A as participants and completes a zero-trigger session, **Then** only Clan A members with active characters receive the reward; Clan B members and unclanned students receive nothing from that session.
3. **Given** a classroom with several students, **When** the teacher selects two individual students as participants and completes a zero-trigger session, **Then** only those two students’ active characters receive the reward.
4. **Given** the teacher mixes clans and individual students in the participant list, **When** the session completes, **Then** every unique active character covered by any selected clan or student is rewarded exactly once (no double award).
5. **Given** a selected student has no active character, **When** the session completes, **Then** that student is skipped for awards and the remaining participants still receive their reward; the teacher is informed how many characters were actually rewarded.

---

### User Story 2 - Noise triggers halve the remaining reward (Priority: P1)

During a running session, if room noise stays above the teacher’s threshold long enough to count as a trigger, the potential reward for all participants is halved (rounded up). The projector clearly shows the current potential XP and gold and how many times the meter has triggered. When the timer ends, participants receive that reduced amount—not the original base.

**Why this priority**: Halved rewards are the primary classroom consequence the teacher asked for; without correct tiering the meter does not change behaviour.

**Independent Test**: Set base rewards to 1000 XP and 100 gold, run a session, force one trigger, complete the timer, and confirm each participant receives 500 XP and 50 gold. Repeat with a second trigger before completion and confirm 250 XP and 25 gold. Force a third trigger and confirm 125 XP and 13 gold.

**Acceptance Scenarios**:

1. **Given** base rewards of 1000 XP and 100 gold and zero triggers so far, **When** the session completes, **Then** each participant receives 1000 XP and 100 gold.
2. **Given** the same base and one trigger during the session, **When** the session completes, **Then** each participant receives 500 XP and 50 gold.
3. **Given** the same base and two triggers, **When** the session completes, **Then** each participant receives 250 XP and 25 gold.
4. **Given** the same base and three triggers, **When** the session completes, **Then** each participant receives 125 XP and 13 gold (gold rounded up from 12.5).
5. **Given** any positive base reward and many triggers, **When** the award is calculated, **Then** XP and gold never drop below 1 while the corresponding base was greater than zero (unbounded halving with a floor of 1, not zero).
6. **Given** a running session, **When** a trigger occurs, **Then** the projector immediately updates the displayed potential reward and trigger count before the timer ends.

---

### User Story 3 - HP damage is optional and off by default (Priority: P2)

The teacher can optionally enable HP damage on each noise trigger. When the option is off (the default), a trigger only halves the reward. When the option is on, each trigger also applies the configured HP damage to participant characters only—not to students outside the session.

**Why this priority**: Today’s tool always deals HP on breach. Making HP optional keeps the audio meter aligned with “quiet for reward” while still allowing teachers who want both consequences.

**Independent Test**: Run a session with HP damage disabled, force a trigger, and confirm no participant loses HP while the reward multiplier halves. Enable HP damage, force a trigger, and confirm only participants lose the configured HP amount.

**Acceptance Scenarios**:

1. **Given** HP damage is disabled (default), **When** a noise trigger fires, **Then** participants’ HP is unchanged and the reward tier halves.
2. **Given** HP damage is enabled with a configured damage amount, **When** a noise trigger fires, **Then** each participant with an active character loses that amount of HP (subject to existing health floors) and the reward tier halves.
3. **Given** HP damage is enabled and the session targets one clan, **When** a trigger fires, **Then** non-participant characters’ HP is unchanged.
4. **Given** the teacher opens the tool settings for a class that has never configured HP damage, **When** they view the setting, **Then** HP damage is off unless they turn it on.

---

### User Story 4 - Session controls and honest completion (Priority: P2)

The teacher can start, pause, resume, and reset a session from the display. Completing the timer awards the current tier to participants using the teacher’s saved settings and the recorded trigger count—not an amount invented on the display. If the teacher resets or abandons before the timer ends, no reward is granted for that incomplete session. Participants can later see that they earned XP/gold from the quiet-time tool and, when reduced, that noise triggers caused the reduction.

**Why this priority**: Reliable session control and trustworthy awards are required for classroom use; a projector page that can be tampered with to inflate rewards is unacceptable.

**Independent Test**: Complete a session normally and confirm awards match ceil(base / 2^triggers). Attempt to force a larger award from the display and confirm the granted amount still matches the saved base and recorded triggers. Reset mid-session and confirm no award is granted until a later full completion.

**Acceptance Scenarios**:

1. **Given** a running session, **When** the teacher pauses and later resumes, **Then** listening and the countdown continue from the remaining time without resetting the trigger count or reward tier.
2. **Given** a running session, **When** the teacher resets before the timer reaches zero, **Then** no XP or gold is awarded for that attempt and the display returns to a ready state.
3. **Given** a completed session, **When** awards are granted, **Then** each participant’s XP and gold change by amounts derived from the saved base rewards and the session’s trigger count (ceil division by two per trigger), not from an arbitrary client-supplied total.
4. **Given** someone alters the display’s proposed reward numbers before completion, **When** the session completes, **Then** participants still receive only the amount implied by saved settings and the recorded trigger count.
5. **Given** a student who participated and received a reduced reward, **When** they view their recent rewards or character activity related to the tool, **Then** they can tell they received a quiet-time reward and that it was reduced because of noise triggers.

---

### User Story 5 - Configure once, reopen with the same preferences (Priority: P3)

A teacher sets threshold, breach duration, timer length, base XP, base gold, optional HP damage, and (optionally) a remembered participant-selection style for a classroom. When they return later, those preferences are still available so they can start another session quickly.

**Why this priority**: Speeds repeated classroom use but is not required for the first successful targeted session.

**Independent Test**: Save settings for a class, leave the page, reopen classroom tools for that class, and confirm the same numeric settings and HP-toggle state load. Confirm participant selection can be re-chosen each session even if a prior selection is suggested.

**Acceptance Scenarios**:

1. **Given** a teacher saves audio meter settings for a classroom, **When** they reopen the tools page for that class, **Then** threshold, timer, base rewards, and HP-damage toggle match what they saved.
2. **Given** saved settings, **When** the teacher starts a new session, **Then** they can still change the participant selection for that session before starting.

---

### Edge Cases

- Microphone permission denied or unavailable: the session does not start listening; the teacher sees a clear message and no reward or penalty is applied.
- No active characters among the selected participants: the teacher cannot complete an award meaningfully; they are told there are no eligible characters before or at completion, and no silent “success” with zero awards is presented as a full win.
- Selected student has no active character: skipped for HP and rewards; others still proceed.
- Student joins or leaves the class, or changes clan, mid-session: participants are resolved at session start (or at award time in a documented consistent way); late joiners are not silently added mid-flight without teacher intent. Spec assumption: roster is fixed at session start.
- Overlapping sessions for the same classroom: only one active audio meter session per classroom at a time; starting another is blocked or replaces the previous incomplete session without awarding it.
- Teacher does not own the classroom: they cannot configure, start, penalize, or reward for that class.
- Base XP or gold is zero: awards stay zero; trigger halving does not invent rewards.
- Very many triggers: amounts remain at least 1 when the base was greater than zero.
- Page reload mid-session: the incomplete session does not auto-award; the teacher must start a new session (or resume only if the product later supports durable resume—out of scope to invent durable resume here; treat reload as abandoned unless plan adds durable sessions).
- Pause during a rising noise level: breach timing does not continue while paused.
- Behavior / Cursed Die systems are unchanged by this feature.

## Requirements *(mandatory)*

### Functional Requirements

#### Participant targeting

- **FR-001**: Teachers MUST be able to select participants for an audio meter session as: the whole class, one or more clans in that class, one or more individual students in that class, or a combination of clans and individuals.
- **FR-002**: Only selected participants’ active characters MUST be eligible for session rewards and for optional HP damage on triggers.
- **FR-003**: Characters not covered by the participant selection MUST be unaffected by that session’s rewards and optional HP damage.
- **FR-004**: If a character would be included more than once (e.g. selected both via clan and individually), they MUST still receive at most one reward and at most one HP application per trigger event.
- **FR-005**: Only teachers who own the classroom MUST be able to configure or run the audio meter for that classroom.

#### Listening and triggers

- **FR-006**: The meter MUST measure ambient classroom audio via the device microphone while a session is running and not paused.
- **FR-007**: A trigger MUST occur when measured level stays above the configured threshold for at least the configured sustained duration (and after any configured cooldown between triggers).
- **FR-008**: Each trigger MUST advance the session’s trigger count by one and halve the potential reward relative to the previous tier.
- **FR-009**: While paused, the countdown MUST freeze, listening MUST not accumulate toward a new trigger, and the trigger count MUST NOT reset.

#### Rewards

- **FR-010**: Potential and final awards MUST use ceiling division by two per trigger: after n triggers, each of XP and gold is `ceil(base / 2^n)`, with a minimum of 1 whenever the corresponding base is greater than zero.
- **FR-011**: Completing the full session timer MUST award the current tier’s XP and gold to each eligible participant character.
- **FR-012**: Resetting or abandoning a session before the timer completes MUST NOT award XP or gold for that attempt.
- **FR-013**: The granted XP and gold amounts MUST be determined from the teacher’s saved (or session-locked) base rewards and the session’s recorded trigger count, such that tampering with the display cannot inflate awards above that amount.
- **FR-014**: Award events MUST be attributable in teacher/student-visible history as quiet-time / audio meter rewards, including enough information to explain a reduction when triggers occurred.

#### Optional HP damage

- **FR-015**: HP damage on trigger MUST be a teacher-configurable option that defaults to off.
- **FR-016**: When HP damage is on, each trigger MUST apply the configured damage only to eligible participant characters.
- **FR-017**: When HP damage is off, triggers MUST NOT change participant HP.

#### Configuration and session lifecycle

- **FR-018**: Teachers MUST be able to configure at least: noise threshold, sustained breach duration, timer length, base XP, base gold, optional HP damage on/off and damage amount when on, and participant selection before start.
- **FR-019**: Teachers MUST be able to start, pause, resume, and reset a session from the display.
- **FR-020**: At most one active audio meter session MUST run per classroom at a time.
- **FR-021**: Classroom-level numeric preferences (threshold, timer, bases, HP toggle) MUST persist so the teacher can reopen them later.
- **FR-022**: Students outside the participant set MUST NOT receive XP, gold, or optional HP effects from the session.

#### Non-goals (out of scope)

- **FR-023**: The system MUST NOT attempt to attribute which student made the noise (single shared room reading only).
- **FR-024**: The system MUST NOT run multiple concurrent audio meter sessions for the same classroom in this feature.
- **FR-025**: This feature MUST NOT change Cursed Die or classroom behavior-infraction HP workflows.

### Key Entities

- **Audio Meter Settings**: Per-classroom preferences for threshold, breach duration, cooldown, timer length, base XP, base gold, and whether trigger HP damage is enabled (and how much).
- **Audio Meter Session**: A single timed run for a classroom: participant set, start state, remaining time concept, trigger count, optional HP flag, and completion/abandon outcome.
- **Participant Set**: The resolved list of student/character identities included via whole-class, clan, and/or individual selection for one session.
- **Trigger Event**: A counted noise breach during a session that advances the tier and may apply optional HP damage.
- **Session Award**: Per-character XP and gold granted on successful completion, derived from base rewards and trigger count.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A teacher can select participants (class, clan(s), and/or students), start a session, and finish an award in under 2 minutes of setup for a familiar class (excluding the session timer itself).
- **SC-002**: In acceptance tests with base 1000 XP / 100 gold, completed awards match 1000/100, 500/50, 250/25, and 125/13 after 0–3 triggers respectively, for every eligible participant.
- **SC-003**: In a mixed classroom, 100% of non-participant characters show unchanged XP, gold, and HP after a completed session that awarded and (if enabled) damaged participants.
- **SC-004**: With HP damage left at default, 100% of trigger events in test runs change only the reward tier (no HP change).
- **SC-005**: Attempts to submit inflated completion amounts from the display fail to grant more than the amount implied by base rewards and recorded triggers in 100% of tested cases.
- **SC-006**: After a reduced award, a participating student can identify within one minute that the quiet-time reward was reduced because of noise triggers (via in-app history or equivalent feedback).

## Assumptions

- This feature extends the existing classroom audio / volume meter tool rather than introducing a separate competing product surface.
- A single shared room microphone cannot identify who spoke; “scope” means who participates in consequences and rewards, not who caused the noise.
- Participant roster for a session is fixed when the session starts; mid-session join/leave does not expand or shrink the set unless the teacher resets and starts again.
- Page reload mid-session abandons the in-progress attempt without awarding; durable cross-reload resume is not required for this version.
- Ceiling (round-up) applies independently to XP and gold after each halving step from the original bases (equivalent to `ceil(base / 2^n)`).
- Existing character health rules (e.g. floors at zero HP) still apply when optional HP damage is enabled.
- Teachers run the meter on a trusted classroom device for microphone access; students are not required to grant mic permission.
- Quest assignment’s mental model of class / clan / student targets is the vocabulary teachers already understand for “who is included.”
- Behavior and Cursed Die remain the primary systems for formal behavior incidents; the audio meter stays a classroom tool.
