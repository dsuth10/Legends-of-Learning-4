# Legends of Learning — current art and integration worklist

**Reviewed:** 23 September 2026 (Australia/Brisbane).
**Scope:** Source-checked asset register and integration handoff. Batch A is merged through PR #4; wiring is under review on `codex/art-integration`.
**Direction:** [Now / Next](../docs/now.md). This file is the detailed asset handoff, not a second project roadmap.
**Evidence baseline:** source and filesystem inspected against local `4251d46` and the Batch A branch. GitHub confirms [PR #3 — Art refresh: Phase 1+2 asset pack](https://github.com/dsuth10/Legends-of-Learning-4/pull/3) merged as `5cbc965`, and [PR #4 — Art Batch A](https://github.com/dsuth10/Legends-of-Learning-4/pull/4) merged as `7bb9f1b`.

This replaces the 21 September estimates. Earlier agent messages, the PR description, `ART_ASSET_WIRING_SUMMARY.md` and `TEST_RESULTS.md` are historical handoffs; their claims of complete wiring and their tier counts are not current acceptance evidence. File presence, catalogue references, database migration and visible rendering are separate checks.

## 1. What is already done

| Category | Verified files | Remaining work |
|---|---:|---|
| Character portraits | All 54 expected options; 54 distinct file hashes | Expose all options, preserve selection across level bands, wire active pages. Visual consistency still needs review. |
| Equipment | 43 PNGs and 43 catalogue entries; every path resolves on disk | Repair duplicate names and safe database synchronisation; verify shop and equip flows. |
| Adventure map symbols | 14 including PR #4 | Nine type defaults, three state badges, and optional Quest/Rest choices are wired on the integration branch. Editor/player browser review remains. |
| Adventure background pack | 3 (forest, castle, arcane) | Add a built-in picker and reuse stored background URL. Two additional files under `adventure_backgrounds/1/` are local adventure content, not pack deliverables. |
| Character backgrounds | Levels 1, 2 and 3 | Active Character is fixed to Level 1; active Equipment uses the quest map. |
| Quest cast and symbols | 12: five givers, four badges, three reward symbols | Reuse in Adventures where meaningful; legacy Quests redirects to Adventures. |
| Class avatars / clan icons / achievement badges | 6 class avatars, 10 clan icons, 6 badges | Reuse; migrate old persisted clan paths and review consistency. No new commission. |
| Power icons | 0 | Retain 33 default powers; resolve effect contract, then commission one per stable key. |
| Battle opponents | 4 in PR #4 | Arena, fight and results wiring is on the integration branch; visual/browser review remains. |

The equipment file tiers are **18 tier 1 + 16 tier 2 + 9 tier 3 = 43**. These are filename tiers, not rarity counts. The current seed contains 24 added entries compared with its original 19-entry group; the old bow already points at a tier-2 filename. Neither “21 all-tier-1 entries” nor “32 new entries” describes this checkout.

Asset compression is largely complete: 48 portraits are 256×256; PR #4 re-exported the six Warrior level-1 portraits to 384×384, about 60–66 kB each, preserving the earlier painted scenes. Their photorealistic style and scene backgrounds still differ visibly from the Sorcerer/Druid cut-outs. This is a visual acceptance choice, not a compression defect. All equipment and quest PNGs are below 200 kB. Backgrounds have a separate size budget.

## 2. Branch and agent coordination

- PR #3 is **already merged**. Its source branch still existing is not evidence of pending work. Do not merge it again.
- PR #4 is **merged**. The local `codex/art-integration` branch includes its artwork and will carry the code and migration in a separate review.
- Local `main` includes the art merge and later interface changes. Its `static/`, equipment catalogue and sync command match the cached art branch exactly.
- The cached `feature/interface-redesign` commit `adf5773` is an ancestor of local main. GitHub confirms the branch still exists; its latest tip was not refreshed. Shell remote-ref lookup failed with a Windows credential error. Refresh remote refs before implementation and inspect any uncommitted work in other agents' checkouts.
- The merge was verified using the GitHub connector. No live database, deployed app, browser session or other agent's uncommitted checkout was inspected.
- Each implementation owner should return: branch + commit, files changed, catalogue/asset counts, checks performed and outstanding user review. One integrator owns migrations, shared model fields and final acceptance.

| Order / owner role | Bounded handoff | Depends on | Acceptance |
|---|---|---|---|
| 0 — Coordinator | Reconcile remote refs and each active agent's actual changes; use this worklist as the asset brief | None | No duplicate seeding or work based on the retired quest UI |
| 1 — Catalogue and rules owner | Equipment identities/sync; approved powers list and effect corrections; stable icon keys | 0 | Existing and fresh database copies converge safely; exact icon manifest is stable |
| 2 — Character and shop owner | Portrait selection/progression, backdrops, equipment cards/slots and clan URL compatibility | 1 for migrations | Correct art for all classes/options/bands and a buy/equip/reload walkthrough |
| 3 — Adventure and battle owner | PNG node rendering/defaults, background picker, selective reuse of quest pack, opponent portraits | 0; 1 for shared schema changes | Editor, saved map and player agree; all opponent images appear |
| 4 — Art owner | Four opponents and five node symbols first; 33 power icons after effect contract | Stable brief below | Files match manifest, small-size readability and style review |
| 5 — Integrator | Review focused follow-up PRs, test a database copy, merge and verify deployed result | 1–4 | No broken paths, no lost inventory/identity, user visual acceptance recorded |

These are proposed roles, not agents dispatched by this planning task. Use a fresh `codex/` branch from refreshed main for follow-up work. Merge the focused fixes, not whole stale feature branches. Existing fonts/CSS fallbacks allow wiring changes to proceed before power art arrives.

## 3. Wiring decisions and defects to resolve

### Equipment and existing databases

Source: `app/models/equipment_data.py`, `app/commands.py`, `app/models/equipment.py`, `app/routes/student_main.py` and the active Shop/Equipment templates.

1. Keep `/static/images/equipment/{class}/{class}_{tier}_{slot}_{slug}.png` unchanged. All 43 catalogue URLs currently match files. `armor` remains the literal filename/API token; use Australian spelling in display copy.
2. Two display names each identify different files: **Sorcerer Cloak II** and **Druid Cloak II** occur in both tier 1 and tier 2. `sync-equipment` matches only names, so it skips the new tier-2 cloak when its old namesake is already present. Introduce stable catalogue keys, explicitly distinguish the older cloak variant, and map existing rows by known legacy identity/path. Preserve equipment IDs referenced by inventories, purchases and shop overrides.
3. Sync currently inserts missing names; it does not update old space-containing image URLs. Plan a dry-run report and an idempotent update migration for known catalogue rows, including old paths and duplicate-name resolution. Preserve teacher-created/custom entries. Test fresh, previously seeded and already partially synced databases; rerunning must make no further changes. Do not run `seed-db` as a substitute on a populated database.
4. **Proposed progression baseline:** keep the implemented visual bands 1–10 / 11–20 / 21+, and current new-gear thresholds 11 / 21 for this integration. The earlier suggestion of levels 4–6 / 8+ is a separate pacing change, not something already applied. Resolve the tier-2 Warrior Bow at level 2 explicitly before catalogue acceptance; do not silently rewrite owned items.
5. Keep escalating costs (new tier-2 entries 300–500 gold; tier-3 600–1000), pending gameplay balance review. Separate visual tier, rarity and unlock level in the manifest. The model documents rarity 2 as uncommon while Shop labels 2 as rare; agree one shared display mapping. Do not bake rarity frames or numbers into artwork.
6. Verify all 43 items through class/level/teacher shop filters and purchase → equip → reload. File-path coverage alone cannot prove they appear in an existing shop.

### Character identity

- The route renders `character_new.html`; the refresh changed the older `character.html`. Use the active route/template pair.
- Character and Equipment currently render `avatar_url`; the helper `portrait_url` always uses option 1. Character creation offers six compact avatars, not the 18 level-1 portrait choices.
- Store a stable appearance choice (class-compatible visual set and option 1–3), with explicit mapping for existing selections. Keep that choice through level bands. Do not infer a different gender from the user's identity: allow a visual choice independently, including for the existing “Other” option; remove the helper's silent male fallback in the planned wiring.
- Render the same resolved portrait and level background on Character and Equipment; use compact variants where appropriate in shared chrome. Check boundaries 1, 10, 11, 20 and 21 and options 1–3 for all six visual sets.
- Missing/invalid legacy selections need an existing neutral fallback or a code-rendered silhouette. No additional raster fallback commission is required.

### Adventures, quest assets and battle art

- Actual `NodeType` values are **start, story, battle, quiz, choice, reward, milestone, boss, end**. `quest` and `rest` are not current node types. Do not add gameplay types just to use images.
- `adventure_icons.py` supplies font ligatures. Editor resolves a stored `/...` image path back to a font default; player returns null for that path but still creates SVG text. Implement an explicit image/ligature renderer in both, plus a shared default catalogue and a fallback on image failure. Retain custom overrides.
- Suggested defaults: story → `node_story.png`; battle → `node_battle.png`; reward → `node_treasure.png`; boss → `node_boss.png`; use the five new symbols below for the other types. `node_quest.png` and `node_rest.png` can remain optional decorations.
- Use `node_locked.png`, `node_complete.png` and `node_current.png` as state overlays/markers, not additional node types. Keep available/in-progress/completed states readable by shape/text as well as colour; preserve keyboard focus and activation.
- The three background files exist, but the current upload endpoint saves per-adventure files. Add a built-in selection using `background_image_url`; preserve existing uploads and map coordinates. Check editor, player and mini-map alignment.
- Five quest-giver portraits, four quest badges and three reward images already exist under `static/images/quests/`. The Archivist reference is in a retired template. Reuse the givers as optional Adventure/story presenters with the teacher as fallback; this needs an explicit selection field or catalogue mapping. Reuse XP/gold/item symbols in Adventure reward displays. Keep story/daily/clan/challenge badges parked until they describe real metadata; they must not invent new quest modes.
- `scripts/seed_monsters.py` defines Goblin, Orc Warrior, Dark Wizard and Dragon and points at missing `/static/monsters/*.png` files. Arena/fight/results templates currently show text/font symbols rather than `Monster.image_url`. Use the four seed opponents as the proposed initial portrait roster, without adding enemies or changing battle stats. Wire the portrait field with an existing code fallback. Reconcile deployed/custom monsters separately.

## 4. Powers retained for the art brief

**User decision, 23 September:** retain all **33 default powers**: Warrior 9, Sorcerer 10, Druid 9, universal 5. Keep their current names, class assignments and prerequisite graph. The old examples “Strike / Guard / Rally”, “Bolt / Shield / Focus” and “Heal / Entangle / Renew” are not the seeded list and must not drive commissions.

The following is a catalogue/name freeze for planning, not a claim that current runtime behaviour or balance is accepted. Proposed stable keys are `{class}_{snake_case_name}` (use `universal` for shared powers, omit apostrophes). Store the key independently of editable display names; use it in an icon manifest. The current Ability model has neither a stable slug nor an image field. Backfill known defaults without replacing IDs or teacher edits. Existing `sync-powers` is additive by name and will not apply corrected effects to existing rows.

Before commissioning this pack, resolve these concrete effect contracts:

- **Unbreakable:** description says +15 defence to the clan, but type `buff` creates a power status effect. Recommended correction: retain the name and shield concept, make it a defence effect.
- **Last Stand:** currently a timed defence effect, not an automatic rescue from 0 HP. Retain that effect and make wording truthful; use shield imagery rather than resurrection imagery. Any interception mechanic would need separate implementation.
- **Battle Cry, Arcane Spark, Mana Transfer, Power Surge, Arcane Mastery:** currently create timed `power` status effects; they do not refill the spendable power pool. Recommended baseline: describe them as temporary power bonuses and test their actual consumers. Fountain of Mana is the explicit refill. Avoid commissioning contradictory “resource refill” art before this is settled.
- **Classroom privileges:** ordinary utility powers return generic success; there is no privilege redemption/approval state in that executor. Define whether activation is a request or an already teacher-authorised use, when power is charged/refunded, and how fulfilment is recorded. Do not imply automatic permission to change seats, use notes or take a pass.
- **Revive / Cheat Death / Rejuvenation:** verify fallen-event integration and rescue semantics. Revive restores 1 HP; Cheat Death selects the better of two Cursed Die outcomes, not a direct resurrection. Ordinary healing at 0 HP and full healing need a consistent policy before sign-off.
- Verify target rules, prerequisites, four equipped slots, learning PP versus activation power, cooldowns, effect duration and stacking. Current default PP cost is 1 each; cooldown is 0 except Cheat Death at 60 seconds. Do not use equipment tiers as power tiers: powers have basic / advanced / elite and their own unlock levels.
- Teacher-created powers can keep type-based Material Icon fallbacks. They do not expand the default commissioned pack indefinitely.

Each row below becomes `static/images/powers/{filename}`. Level, activation cost and prerequisite are the current source snapshot, not new balance changes. PNGs contain no text, level numbers or rarity borders. Use distinct silhouettes: warrior steel/red, sorcerer purple/blue, druid green/brown, universal neutral gold/teal.

| Power | Class | Level | Activation power | Prerequisite | Filename | Art concept |
|---|---|---:|---:|---|---|---|
| Shield Wall | Warrior | 1 | 2 | — | `warrior_shield_wall.png` | Single shield forming a wall |
| Battle Cry | Warrior | 2 | 3 | — | `warrior_battle_cry.png` | Horn with an outward rally wave |
| Seat Swap | Warrior | 3 | 3 | — | `warrior_seat_swap.png` | Two chairs with exchange arrows |
| Protect Ally | Warrior | 4 | 4 | Shield Wall | `warrior_protect_ally.png` | Shield sheltering an ally |
| Fortify | Warrior | 6 | 5 | Protect Ally | `warrior_fortify.png` | Linked shields surrounding a team |
| Frontal Assault | Warrior | 8 | 6 | Fortify | `warrior_frontal_assault.png` | Team banner and rolled assignment pass |
| Iron Will | Warrior | 10 | 4 | Battle Cry | `warrior_iron_will.png` | Steel helm and steady flame |
| Last Stand | Warrior | 13 | 8 | Fortify | `warrior_last_stand.png` | Shield braced against impact |
| Unbreakable | Warrior | 16 | 10 | Last Stand | `warrior_unbreakable.png` | Unbroken ring of linked shields |
| Arcane Spark | Sorcerer | 1 | 2 | — | `sorcerer_arcane_spark.png` | Bright arcane spark |
| Mana Transfer | Sorcerer | 2 | 4 | — | `sorcerer_mana_transfer.png` | Energy ribbon linking two hands |
| Teleport | Sorcerer | 3 | 3 | — | `sorcerer_teleport.png` | Small doorway portal |
| Invisibility | Sorcerer | 5 | 4 | Arcane Spark | `sorcerer_invisibility.png` | Fading cloak silhouette |
| Power Surge | Sorcerer | 7 | 6 | Mana Transfer | `sorcerer_power_surge.png` | Concentrated arcane burst |
| Mana Shield | Sorcerer | 9 | 5 | Arcane Spark | `sorcerer_mana_shield.png` | Shield formed from runes |
| Time Warp | Sorcerer | 11 | 7 | Power Surge | `sorcerer_time_warp.png` | Hourglass with a circular trail |
| Cheat Death | Sorcerer | 12 | 8 | Power Surge | `sorcerer_cheat_death.png` | Two dice and a protective charm |
| Arcane Mastery | Sorcerer | 14 | 9 | Power Surge | `sorcerer_arcane_mastery.png` | Several linked glowing runes |
| Fountain of Mana | Sorcerer | 17 | 12 | Arcane Mastery | `sorcerer_fountain_of_mana.png` | Overflowing magical fountain |
| Minor Heal | Druid | 1 | 2 | — | `druid_minor_heal.png` | Leaf and small healing glow |
| Snack Time | Druid | 2 | 2 | — | `druid_snack_time.png` | Apple and small lunch pouch |
| Nature's Touch | Druid | 3 | 3 | Minor Heal | `druid_natures_touch.png` | Hand cupping a leaf |
| Herbal Remedy | Druid | 4 | 3 | Snack Time | `druid_herbal_remedy.png` | Herbal sprig beside an open notebook |
| Greater Heal | Druid | 6 | 5 | Minor Heal | `druid_greater_heal.png` | Large leaf with strong healing glow |
| Healing Circle | Druid | 9 | 7 | Greater Heal | `druid_healing_circle.png` | Ring of leaves around a team |
| Revive | Druid | 11 | 8 | Healing Circle | `druid_revive.png` | Sprout rising in a warm light |
| Nature's Blessing | Druid | 14 | 10 | Greater Heal | `druid_natures_blessing.png` | Bloom and protective open hands |
| Rejuvenation | Druid | 17 | 12 | Healing Circle | `druid_rejuvenation.png` | Tree canopy radiating renewal |
| Quick Rest | Universal | 5 | 3 | — | `universal_quick_rest.png` | Cup of water and restful leaf |
| Study Buddy | Universal | 7 | 4 | Quick Rest | `universal_study_buddy.png` | Two learners with an open book |
| Music Pass | Universal | 10 | 5 | Study Buddy | `universal_music_pass.png` | Headphones with a musical note |
| Late Pass | Universal | 13 | 6 | Music Pass | `universal_late_pass.png` | Assignment sheet with a clock |
| Teacher's Pet | Universal | 16 | 8 | Late Pass | `universal_teachers_pet.png` | Teacher star and positive message card |

## 5. Updated image production queue

### Batch A — delivered in PR #4 (9)

| File | Subject / purpose | Display surface |
|---|---|---|
| `static/monsters/goblin.png` | Playful goblin opponent; level 1 seed | Arena opponent picker, fight, results |
| `static/monsters/orc.png` | Orc warrior; level 3 seed | Same |
| `static/monsters/wizard.png` | Dark Wizard; level 5 seed; clearly distinct from student Sorcerer portraits | Same |
| `static/monsters/dragon.png` | Fantasy dragon; level 10 seed; no gore/horror | Same |
| `static/images/adventure_node_icons/node_start.png` | Trailhead flag / beginning | Start node |
| `static/images/adventure_node_icons/node_quiz.png` | Scroll and question symbol | Quiz node |
| `static/images/adventure_node_icons/node_choice.png` | Forked path / signpost | Choice node |
| `static/images/adventure_node_icons/node_milestone.png` | Trophy or summit marker | Milestone node |
| `static/images/adventure_node_icons/node_end.png` | Finish arch / destination flag, distinct from completed overlay | End node |

These five node symbols complete a consistent raster set; the application can continue using existing font fallbacks until they are ready. Opponent files match existing seed paths deliberately.

### Batch B — after power effect contract is accepted (33)

Create exactly the 33 power PNGs listed in section 4. Names and roster are retained by user decision; generation is deferred until descriptions, effect semantics and the stable-key mapping are settled. No power artwork was generated during this planning task.

### Optional, not in the required queue (2)

- `static/images/adventure_node_icons/node_failed.png`: only if a distinct retry state is chosen. Keep current CSS/text feedback otherwise.
- `static/images/adventure_backgrounds/adventure_bg_classroom_fantasy.png`: optional fourth map theme.

### Existing art to reuse or re-export — do not commission again

- All 54 character options, including the six compressed Warrior level-1 exports in PR #4.
- All 43 equipment icons, all three character backgrounds and all three pack map backgrounds.
- Nine existing map symbols, twelve quest assets, six compact class avatars, ten clan icons, six achievement badges, app icon and welcome background.
- Keep `quest_map.png` available; assigning the level backdrops removes the need for it as an Equipment default.
- No new gear variants, badges, class-tinted backgrounds, animated sprites or 3D models are part of this plan. Extra equipment art requires an approved catalogue entry first.

**Production count: 9 Batch A images delivered + 33 power icons deferred = 42 selected new images.** Two optional images are excluded. Six Warrior level-1 portraits were re-exported, not newly commissioned. This is the source-defined roster, not an audit of teacher-created database content.

## 6. Delivery and acceptance

- Icons: transparent PNG, 256×256 delivery; strong silhouette readable at 48–64 px. Opponent portraits: 512×512 master, 256×256 transparent web export. Match existing illustrative art and use school-appropriate fantasy.
- Aim below 200 kB per web icon/portrait (prefer below 100 kB where quality allows). Retain larger masters outside served web assets. Backgrounds: 1920×1080 or 1600×900, compressed separately.
- Keep exact lowercase filenames, underscores and existing path contracts. Do not rename historical files without updating persisted URLs. Track source/licence and master/export location in the handoff.
- Before integration: confirm all files decode, dimensions and transparency are correct, filenames are unique, manifest paths exist and no accidental exact duplicate exports were delivered.
- Before merging follow-up fixes: test catalogue sync twice on a disposable database copy, preserve inventory/purchases/teacher overrides, and validate default power IDs and prerequisites after migration. Current test evidence is historical; this planning audit did not run application tests or database commands.
- Browser acceptance: character creation and option retention; level boundaries; all three classes in Shop; buy/equip/unequip/reload; clan icons; all nine Adventure types in editor/player; overrides and backgrounds; reward displays; all four battle opponents; power fallbacks and custom powers; small screens and keyboard use. Inspect actual images and network requests, not only response status codes.
- After merge: confirm the deployment contains both assets and code, apply the reviewed database migration to the intended environment with a recoverable backup, then repeat the key walkthrough there. A merged PR is not evidence of deployment or a successful database update.

## 7. Immediate next checkpoint

Finish integration review: include the ignored equipment migration explicitly in Git, check active pages in a browser, and review/merge the follow-up wiring PR. The combined integration suite passed 145 tests; the full suite passed 335 and failed two unrelated classroom/legacy quest tests. Both failures were reproduced against baseline source `4251d46` with its historical ignored migration files restored for test setup. Verify the migrated database on a recoverable copy before production use. Batch B waits for the effect contract. Decide whether the six Warrior level-1 scenes should be regenerated to match the newer cut-out style after visual review.
