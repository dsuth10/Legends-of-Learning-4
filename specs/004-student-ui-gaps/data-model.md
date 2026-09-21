# Phase 1 - Data Model: Student UI Remaining Gaps

**Feature**: 004-student-ui-gaps
**Date**: 2026-09-21
**Status**: Planning final; no schema migration expected.

This feature is a view composition over existing student, character, clan, and ability records. No new tables or columns.

---

## View composition (not stored)

### Student chrome

Repeating frame around in-scope student pages.

**Inputs** (assembled by `student_chrome_context`):

- Signed-in user → `Student` profile (may be missing in corrupt data; pages already handle that)
- Active `Character` (`is_active=True`) or none
- `Classroom` via `student.classroom` when present
- `Clan` via `character.clan` when present
- Ordered clan member characters: current character first, then other `is_active` members

**Displayed fields**:

| Chrome region | Source |
|---------------|--------|
| Identity class name | `classroom.name` or `classroom.class_name` |
| Identity clan name | `clan.name` when the character is in a clan |
| Strip tab name | `character.name` |
| Strip HP | current `health`, max = `max_health` + equipped health bonuses |
| Strip power | current `power`, max = `max_power` |
| Sidebar HP / Power / XP / GP / PP | same current/max rules as research R4 |
| Destination current | Flask `request.endpoint` (plus Create character / Clan / Profile indicators) |

**Validation rules**:

- Do not invent classmates when `clan` is missing.
- Do not render numeric HP/power bars when `character` is missing.
- Clan tabs are awareness only; they are not an account-switch entity.

**State transitions**: none. Chrome is derived per request.

---

## Existing entities used

### Student

Classroom membership for the identity bar.

**Fields used**: `user_id`, `class_id` / `classroom` relationship.

### Classroom

**Fields used**: `name` or `class_name`, `teacher` (avatar already shown in the identity bar).

### Character

**Fields used**:

- `id`, `name`, `level`, `character_class`, `avatar_url`
- `health`, `max_health`, `power`, `max_power`, `power_points`, `experience`, `gold`
- `clan_id`, `is_active`

**Derived for chrome only** (not columns):

- `hp_max_display` = `max_health` + sum of equipped `equipment.health_bonus`
- `xp_next` = existing Character page rule (`level * 1000`)
- `party_members` = up to three other active clan characters

Do not change `total_health` / `total_power` property semantics in this feature.

### Clan

**Fields used**: `name`, `members` (characters).

**Rules**:

- Strip shows current student first.
- Party portraits on Character use other members only; hide the cluster when the list is empty.

### Ability / CharacterAbility

**Fields used**: equipped abilities’ `name`, `type`, `special_effect`.

**Rules**:

- Character grid shows up to six equipped powers; overflow remains on Powers.
- Picture is a type/effect icon map (see research R3), not a stored file.

### Equipment / Inventory

Unchanged. Equipment page still lists unequipped inventory and equipped slots (`main_hand`, `chest`, `ring`/`neck`). Shop purchase and equip/unequip APIs stay as they are.

### Quest / QuestLog

Unchanged. Quest log, start, and turn-in stay on existing routes.

---

## Page coverage (destinations)

| Destination | Route endpoint (current) | Chrome |
|-------------|--------------------------|--------|
| Character | `student.character` | Full shell |
| Quests | `student.quests` | Full shell |
| Shop | `student.shop` | Full shell |
| Equipment | `student.equipment` | Full shell |
| Adventures list | `adventures_student.list_adventures` | Full shell |
| Progress | `student.progress` | Full shell |
| Powers | `student.powers` | Full shell |
| Clan | `student.clan` | Full shell; Clan indicated current |
| Profile | `student.profile` | Full shell; Profile indicated current |
| Create character | `student.character_create` | Visual language, no fabricated stats |
| Adventure map | `adventures_student.adventure_map_page` | **Excluded** |
| Battle | student battle routes | **Excluded** |

---

## State transitions

None for chrome. Existing character-create POST still creates a `Character` and redirects to Character. Existing shop, equip, quest, and powers POSTs are unchanged.

```
no character
  --[successful create]--> Character page with full chrome
```
