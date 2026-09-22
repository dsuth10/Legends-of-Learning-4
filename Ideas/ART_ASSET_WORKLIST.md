# Legends of Learning — Art & Asset Worklist

**Repo:** `dsuth10/Legends-of-Learning-4`  
**Date:** 21 September 2026 (Australia/Brisbane)  
**Purpose:** Commission / create every outstanding visual asset, with game context, UI placement, naming, and delivery specs.

---

## 1. How the game is structured (so art has a home)

Legends of Learning is a **classroom RPG loop**, not a free-roam action game.

```text
Teacher sets up class → Students create a character (class + look)
        ↓
Students complete Quests / Adventures → earn XP + Gold
        ↓
Level up (character art can progress) → spend Gold in Shop
        ↓
Equip gear (equipment icons on character) → join Clans → earn Badges
```

### Core player surfaces (student)

| Surface | What the student does | Art that shows here |
|---|---|---|
| **Welcome / Login** | Enter the game | App icon, welcome background |
| **Character** | See self, stats (HP/PP/XP/GP), powers | Full-body portrait, class background, power icons |
| **Shop** | Buy weapons / armour / accessories | Item icons, rarity framing, wallet/GP symbol |
| **Equipment** | Equip / unequip on slots | Item icons on paper-doll slots + inventory grid |
| **Quests** | Pick up / continue / turn in work | Quest-giver avatars, type badges, reward icons |
| **Adventure / Quest Map** *(planned)* | Move across a map of nodes | Map background, node icons, state overlays |
| **Clans** | Belong to a group | Clan icons |
| **Progress / Achievements** | See milestones | Badge art, charts (charts are code, not art) |

### Teacher surfaces

| Surface | Art touchpoints |
|---|---|
| Teacher header / class view | Teacher avatar |
| Clan management | Clan icon picker (folder auto-scanned) |
| Shop config *(stub)* | Same equipment icons students see |

### Three character classes (theme the whole set)

| Class | Look & feel | Typical gear |
|---|---|---|
| **Warrior** | Armour, steel, martial | Sword, axe, bow, plate/leather, shield, ring |
| **Sorcerer** | Robes, arcane glow | Staff, wand, cloak, book, ring |
| **Druid** | Nature, organic | Staff, flail, cloak, bracers, pendant |

Rarity colours (UI already coded — art should read clearly against them):

- Common · Rare · Epic · Legendary

---

## 2. Global delivery standards (apply to every new asset)

| Spec | Requirement |
|---|---|
| Format | PNG with transparency (backgrounds may be JPG/PNG opaque) |
| Colour | RGB, school-appropriate fantasy (no gore / horror) |
| Style | Consistent illustrative style across the set (match existing clan/equipment tone) |
| Character portraits | Target **256×256** (or 512×512 master → export 256) |
| Icons (items, nodes, badges) | **128×128** or **256×256** square |
| Backgrounds / maps | **1920×1080** (or 1600×900) landscape |
| File size | Aim **&lt; 100–200 KB** per icon/portrait after export (current assets are often 1–3 MB — compress) |
| Naming | No spaces; use underscores; no “Copy” suffixes |
| Licence | Own / school-cleared; no unlicensed scraped art |

---

## 3. Workstreams (priority order)

### Workstream A — Adventure map pack *(highest priority for new feature)*

**Why:** Folders exist but are empty. Adventure/quest-map system cannot ship without these.

**Paths:**

- `static/images/adventure_node_icons/`
- `static/images/adventure_backgrounds/`
- Existing map plate: `static/images/quest_maps/quest_map.png` (keep or replace)

**Where they sit in the game:** Student **Adventure / Quest Map** screen — a board of nodes on a background. Teacher may preview the same map when assigning adventures.

#### A1. Node icons (required set)

| ID | Filename (suggested) | Purpose | In-game location |
|---|---|---|---|
| N01 | `node_quest.png` | Standard learning quest stop | Map node |
| N02 | `node_battle.png` | Challenge / contest node | Map node |
| N03 | `node_rest.png` | Rest / recovery stop | Map node |
| N04 | `node_boss.png` | Capstone / boss encounter | Map node |
| N05 | `node_treasure.png` | Reward / loot stop | Map node |
| N06 | `node_story.png` | Narrative / dialogue beat | Map node |
| N07 | `node_locked.png` | Not yet unlocked | Overlay or alternate state |
| N08 | `node_complete.png` | Cleared / done | Overlay or alternate state |
| N09 | `node_current.png` | Player’s current position marker | Map marker |
| N10 | `node_failed.png` *(optional)* | Failed attempt / retry | Overlay |

**Count:** 9 required + 1 optional = **10**

**Art notes:** Read clearly at ~48–64 px on screen; strong silhouette; colour-code by type but keep consistent stroke weight.

#### A2. Adventure backgrounds

| ID | Filename (suggested) | Purpose | In-game location |
|---|---|---|---|
| B01 | `adventure_bg_forest.png` | Default / early path | Map canvas behind nodes |
| B02 | `adventure_bg_castle.png` | Mid / martial theme | Map canvas |
| B03 | `adventure_bg_arcane.png` | Magic / endgame feel | Map canvas |
| B04 | `adventure_bg_classroom_fantasy.png` *(optional)* | School-friendly variant | Alternate map |

**Count:** 3 required + 1 optional = **4**

#### A3. Quest map plate

| ID | Action | Purpose |
|---|---|---|
| M01 | Audit/replace `quest_maps/quest_map.png` | Base illustrated map if node layer sits on a painted map (compress if keeping) |

---

### Workstream B — Character portrait set *(largest volume)*

**Why:** Spec requires **54** unique full-body (or bust) options. Repo only fully covers **Warrior level 1**; other classes are partial / poorly named.

**Path:** `static/images/characters/{warrior|sorcerer|druid}/{male|female}/level{1|2|3}/`

**Naming (mandatory):**

```text
{option}_{class}_{gender}_level{level}.png
```

Examples: `1_warrior_male_level1.png`, `3_druid_female_level2.png`

**Where they sit:**

- Character creation picker
- Character page main portrait
- Equipment page centre “paper doll”
- Clan bar / party mini-cards (may use same art scaled down, or the smaller `static/avatars/` set)

#### Matrix (54 total)

| Class | Gender | Level 1 | Level 2 | Level 3 | Subtotal |
|---|---|---|---|---|---|
| Warrior | Male | 3 options | 3 | 3 | 9 |
| Warrior | Female | 3 | 3 | 3 | 9 |
| Sorcerer | Male | 3 | 3 | 3 | 9 |
| Sorcerer | Female | 3 | 3 | 3 | 9 |
| Druid | Male | 3 | 3 | 3 | 9 |
| Druid | Female | 3 | 3 | 3 | 9 |
| **Total** | | | | | **54** |

**Level meaning (visual):**

- **Level 1** — Starter look (basic kit)
- **Level 2** — Clear upgrade (better gear/details)
- **Level 3** — Advanced (glow / prestige details; still age-appropriate)

#### Current gap (from audit)

| Gap | Action |
|---|---|
| Warrior male/female **level 2 & 3** folders missing | Create 12 images (2 genders × 2 levels × 3 options) |
| Sorcerer / Druid files often named `Sorcerer (1) - Copy.png` etc. | Rename to convention; fill any missing level/gender slots to reach 54 |
| Files ~1.5–2 MB | Re-export compressed |

**Also keep (already exist, small set):** `static/avatars/{warrior|sorcerer|druid}_{m|f}.png` — used as compact class icons in headers. Refresh only if style drifts.

**Teacher:** `static/avatars/teacher_1_avatar.png` — optional refresh; not blocking.

---

### Workstream C — Equipment & shop icons

**Why:** Shop + Equipment redesign show an **image on every item card** and on equip slots. Most current art is **tier 1** only; filenames have spaces; files are huge.

**Path:** `static/images/equipment/{warrior|sorcerer|druid}/`

**Suggested naming:**

```text
{class}_{tier}_{slot}_{item_slug}.png
```

Example: `warrior_1_weapon_sword.png`, `sorcerer_2_armor_cloak.png`

**Where they sit:**

- Shop item grid (category filters: Weapon / Armor / Accessory)
- Equipment inventory grid
- Equipment slots on character (weapon / armour / accessory overlays)
- Teacher shop config (same icons)

#### Recommended catalogue to create / complete

Per class, aim for a readable shop depth:

| Slot | Tier 1 | Tier 2 | Tier 3 | Notes |
|---|---|---|---|---|
| Weapon A | ✓ | ✓ | ✓ | Class-themed primary |
| Weapon B | ✓ | ✓ | optional | Alternate weapon type |
| Armor A | ✓ | ✓ | ✓ | |
| Armor B | ✓ | optional | optional | Variant |
| Accessory A | ✓ | ✓ | ✓ | Ring / pendant / etc. |
| Accessory B | ✓ | optional | optional | Shield / book / bracers |

**Minimum viable new commission (if only filling gaps):**

- **Warrior:** Tier 2–3 for sword/axe/bow, plate/leather, ring/shield → ~8–10 new  
- **Sorcerer:** Tier 2–3 staff/wand, cloaks, book/ring → ~8–10 new  
- **Druid:** Tier 2–3 staff/flail, cloaks, bracers/pendant → ~8–10 new  

**Plus:** Re-export / rename existing ~19 tier-1 assets to the naming scheme and compress.

**Count guide:** ~**24–30 new** icons if aiming at a full tier ladder; ~**19 renames/compress** for existing.

**Placeholder to retire:** `static/images/test_sword.png`, `test_armor.png`, `test_ring.png` — replace references with real equipment art.

---

### Workstream D — Scene / level backgrounds

**Why:** Character page uses a background behind the model; only **Level 1** core background exists.

**Path:** `static/images/Backgrounds/Core Level Backgrounds/`

| ID | Filename | Purpose | Where it sits |
|---|---|---|---|
| L1 | `Level 1.png` *(exists — compress)* | Early-game character backdrop | Character / Equipment main stage |
| L2 | `Level 2.png` **create** | Mid progression backdrop | Same, when level band = 2 |
| L3 | `Level 3.png` **create** | Late progression backdrop | Same, when level band = 3 |
| W1 | `welcome_background.jpg` *(exists)* | Login / welcome | Welcome screen |

**Optional:** Class-tinted variants (warrior forge / sorcerer tower / druid grove) if you want stronger identity on Character page.

**Count:** **2 required new** (+ compress L1/welcome)

---

### Workstream E — Quest page cast & symbols

**Why:** Quest redesign specifies quest-giver portrait, type badge, rewards — currently not a dedicated art pack.

**Where they sit:** Student **Quest** page (sidebar list + detail panel).

#### E1. Quest-giver avatars (suggested starter cast)

| ID | Filename | Role in fiction | UI |
|---|---|---|---|
| QG1 | `questgiver_archivist.png` | Master Archivist — story/knowledge quests | Detail panel |
| QG2 | `questgiver_captain.png` | Challenge / PE / competition quests | Detail panel |
| QG3 | `questgiver_sage.png` | Magic / stretch quests | Detail panel |
| QG4 | `questgiver_ranger.png` | Outdoor / exploration quests | Detail panel |
| QG5 | `questgiver_teacher.png` | Generic “your teacher” fallback | Detail panel |

**Count:** **5**

#### E2. Quest type badges

| ID | Filename | Purpose |
|---|---|---|
| QT1 | `badge_story.png` | Story Quest label |
| QT2 | `badge_daily.png` | Daily Quest label |
| QT3 | `badge_clan.png` | Clan Quest label |
| QT4 | `badge_challenge.png` | Challenge / timed |

**Count:** **4**

#### E3. Reward symbols (if not using Material Icons)

| ID | Filename | Purpose |
|---|---|---|
| R1 | `reward_xp.png` | XP reward chip |
| R2 | `reward_gold.png` | Gold reward chip |
| R3 | `reward_item.png` | Item reward chip |

**Count:** **3** (optional if Material Icons remain)

**Existing badges to keep:** `static/images/badges/achieve1.png` … `achieve6.png` — achievement gallery / progress. Optionally redesign for style consistency later (not blocking Shop/Equipment).

---

### Workstream F — Powers / ability icons *(medium)*

**Why:** Character sidebar has a **powers grid**. Backend abilities exist; custom icons beat generic Material Icons for fantasy feel.

**Suggested path:** `static/images/powers/` *(create folder)*

| Class | Example powers to icon | Count guide |
|---|---|---|
| Warrior | Strike, Guard, Rally | 3–6 |
| Sorcerer | Bolt, Shield, Focus | 3–6 |
| Druid | Heal, Entangle, Renew | 3–6 |

**Where they sit:** Character page powers grid; ability-use feedback.

**Count:** **9–18** depending on how many abilities are live in seed data.

*Defer until ability list is frozen in seed DB — then 1:1 icon per ability slug.*

---

### Workstream G — Brand & chrome *(low / polish)*

| Asset | Path | Status | Action |
|---|---|---|---|
| App icon | `static/images/legends_icon.png` (+ root duplicate) | Exists | Compress; drop duplicate root file if unused |
| Clan icons | `static/images/clan_icons/clan_icon (1–10).png` | 10 exist | Compress; rename to `clan_01.png`…`clan_10.png` |
| Nav icons | Material Icons CDN | OK for now | Custom set only if brand pass |

**Where clan icons sit:** Teacher clan create/edit picker; student clan display.

---

## 4. Master production checklist

### Phase 1 — Unblock Adventure + Shop feel (do first)

- [ ] A1 Node icons (9–10)
- [ ] A2 Adventure backgrounds (3–4)
- [ ] C Rename/compress existing equipment; kill `test_*.png` usage
- [ ] C Create tier 2–3 equipment minimum (~24)
- [ ] D Level 2 & 3 backgrounds
- [ ] B Warrior level 2 & 3 (12 portraits)

### Phase 2 — Complete character identity

- [ ] B Audit sorcerer/druid slots → fill to 54
- [ ] B Rename all portraits to convention
- [ ] B Compress all portraits
- [ ] Refresh `static/avatars/*` if style mismatch

### Phase 3 — Quest & powers flavour

- [ ] E1 Quest-giver avatars (5)
- [ ] E2 Quest type badges (4)
- [ ] E3 Reward chips (optional 3)
- [ ] F Power icons after ability list locked (9–18)

### Phase 4 — Hygiene & brand

- [ ] Compress clan icons + badges + app icon
- [ ] Rename clan icons without spaces
- [ ] Remove unused root `Legends of Learning icon..png` if redundant
- [ ] Spot-check every `image_url` in equipment seed data

---

## 5. Counts at a glance

| Workstream | New art (approx.) | Also: rename/compress |
|---|---:|---:|
| A Adventure nodes + BGs | 13–14 | 1 map plate |
| B Character portraits | ~12–40 (depends on what’s already valid) | toward 54 total |
| C Equipment | 24–30 | ~19 existing |
| D Level backgrounds | 2 | 2 existing |
| E Quest cast/badges | 9–12 | 6 achieve badges optional |
| F Powers | 9–18 | — |
| G Brand/clan | 0–10 refreshes | 10 clan + icon |
| **Rough total new** | **~70–120** | **heavy export pass** |

---

## 6. Handoff package for illustrator / generator

For each batch, supply:

1. This worklist section (A–F) as the brief  
2. 2–3 reference screenshots from `Ideas/Student UI redesign/*/screen.png`  
3. Class colour cues (warrior steel/red, sorcerer purple/blue, druid green/brown)  
4. Export checklist: size, PNG, transparency, filename table  
5. “School-safe fantasy” constraint line  

Acceptance: asset opens in UI on the correct surface; filename matches code/seed; file under size budget; no broken image placeholders on Character / Shop / Equipment / Map.

---

## 7. Out of scope (do not commission yet)

- Full animated sprites / walk cycles  
- 3D models  
- Sound effects  
- Custom font files (Cinzel + Lato already via Google Fonts)  
- Replacing Material Icons for every nav button  
- Real student / teacher photos  

---

*Generated from repo audit of `static/images`, `STUDENT-UI-REDESIGN-GUIDE.md`, and character/equipment READMEs.*
