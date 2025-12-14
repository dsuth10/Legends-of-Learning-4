# Student UI Redesign - API Endpoint Mapping

This document maps the new UI design elements to existing API endpoints and data models.

## Design Overview

The redesign includes 4 main pages:
1. **Character Page** - Stats display, powers, character model
2. **Shop Page** - Item marketplace with rarity colors and filters
3. **Equipment Page** - Equipment slots and inventory management
4. **Quest Page** - Quest log and active quest details

## Shared Components

### Header (Top Bar)
- **Class Name**: `student_profile.classroom.name` or `student_profile.classroom.class_name`
- **Teacher Avatar**: `student_profile.classroom.teacher.avatar_url` or similar
- **Class Icon**: Clan icon or default

### Clan Bar (Student Tabs)
- **Student List**: All students in the same classroom/clan
- **HP Bar**: `character.health` / `character.max_health` or `character.total_health`
- **PP Bar**: `character.power` / `character.max_power` or `character.total_power`
- **Active Student Indicator**: Blue border on top of active student's tab

### Sidebar Stats Panel
- **Character Name**: `main_character.name`
- **Level & Class**: `main_character.level` + `main_character.character_class`
- **HP Bar**: `main_character.health` / `main_character.total_health` (max with bonuses)
- **PP Bar**: `main_character.power` / `main_character.total_power` (max with bonuses)
- **XP Bar**: `main_character.experience` / `next_level_xp`
- **GP Display**: `main_character.gold`

## Page 1: Character Page

### Route
- `GET /student/character` (existing)
- Template: `app/templates/student/character.html`

### Data Mappings

#### Character Display
- **Name**: `main_character.name` → Display in sidebar
- **Level**: `main_character.level` → "Level {level} {class}"
- **Class**: `main_character.character_class`

#### Stat Bars (Sidebar)
- **HP** (Health Points):
  - Current: `main_character.health`
  - Max: `main_character.total_health` (includes equipment bonuses)
  - Percentage: `(health / total_health) * 100`
  - Color: `#ef4444` (hp-red)

- **PP** (Power Points):
  - Current: `main_character.power` 
  - Max: `main_character.total_power` (includes equipment bonuses)
  - Percentage: `(power / total_power) * 100`
  - Color: `#3b82f6` (ap-blue)

- **XP** (Experience):
  - Current: `main_character.experience`
  - Next Level: Calculate based on level formula
  - Color: `#f59e0b` (xp-yellow)

- **GP** (Gold):
  - Amount: `main_character.gold`
  - Color: `#d97706` (gp-gold)

#### Navigation Buttons
- **Quests**: Link to `/student/quests`
- **Shop**: Link to `/student/shop`
- **Progress**: Link to `/student/progress`
- **Character**: Current page (highlighted)

#### Powers Grid
- **Data Source**: `main_character.abilities.filter_by(is_equipped=True).all()`
- **Display**: 
  - Icon: `ability.icon` or default
  - Name: `ability.name`
  - Grid: 3 columns
- **Learn Powers Button**: Link to shop or abilities page

#### Character Model
- **Avatar Image**: `main_character.avatar_url`
- **Position**: Center of main area
- **Background**: Fantasy landscape image (from design)

#### Party Members (Small cards at bottom right)
- **Data**: Clan members (exclude current character)
- **Source**: `main_character.clan.members` if clan exists

### API Endpoints Used
- `GET /student/character` - Page load
- `POST /student/abilities/use` - Use power (existing)
- `GET /student/abilities/history` - Power usage history (existing)

## Page 2: Shop Page

### Route
- `GET /student/shop` (existing)
- `POST /student/shop/buy` (existing)
- Template: `app/templates/student/shop.html`

### Data Mappings

#### Sidebar Stats
- Same as Character page (HP, PP, GP)

#### Category Filters
- **Weapon**: Filter by `equipment.type == 'weapon'` or `equipment.slot == 'MAIN_HAND'`
- **Armor**: Filter by `equipment.type == 'armor'` or `equipment.slot in ['CHEST', 'HEAD', 'LEGS', 'FEET']`
- **Accessory**: Filter by `equipment.type == 'accessory'` or `equipment.slot in ['NECK', 'RING']`

#### Item Cards
- **Data Source**: `items` list from route (Equipment + Abilities)
- **Rarity Colors**:
  - Common: `#9ca3af` (rarity-common)
  - Rare: `#3b82f6` (rarity-rare)
  - Epic: `#a855f7` (rarity-epic)
  - Legendary: `#eab308` (rarity-legendary)
- **Item Display**:
  - Image: `item.image` or `equipment.image_url`
  - Name: `item.name`
  - Type & Level: `item.category` + "Lvl {level_requirement}"
  - Stats: 
    - Equipment: `health_bonus`, `power_bonus`, `defense_bonus`
    - Or damage ranges, crit rates, etc.
  - Price: `item.price` in GP (gold)
  - Purchase Button: Enable/disable based on `item.can_buy`

#### Special Offer Banner
- Placeholder for future feature
- Could show discounted items or special events

#### Wallet Info (Bottom of sidebar)
- **Current Gold**: `main_character.gold`
- **Total Spent**: Calculate from `ShopPurchase.query.filter_by(character_id=character.id).all()`

### API Endpoints Used
- `GET /student/shop` - Page load
- `POST /student/shop/buy` - Purchase item
  - Request: `{item_id, item_type: 'equipment'|'ability'}`
  - Response: `{success, character: {gold}, item, inventory, abilities}`

## Page 3: Equipment Page

### Route
- `GET /student/character` (reuse character route or create `/student/equipment`)
- `PATCH /student/equipment/equip` (existing)
- `PATCH /student/equipment/unequip` (existing)
- Template: `app/templates/student/equipment.html` (new)

### Data Mappings

#### Sidebar Stats
- Same as Character page (HP, PP, GP)
- **Equipment button highlighted**

#### Inventory Grid
- **Data Source**: `main_character.inventory_items.filter_by(is_equipped=False).all()`
- **Display**: 4-column grid
- **Item Display**:
  - Image: `item.equipment.image_url`
  - Count badge: If stackable (show quantity)
  - Rarity border: Based on `equipment.rarity`
- **Empty Slots**: Dashed border placeholders

#### Character Model (Center)
- **Avatar**: `main_character.avatar_url`
- **Equipment Slots** (overlay on character):
  - **Weapon** (left side): 
    - Check `main_character.inventory_items.filter_by(is_equipped=True, equipment.slot=='MAIN_HAND').first()`
    - Show equipment icon/image
  - **Armor** (right side):
    - Check `main_character.inventory_items.filter_by(is_equipped=True, equipment.slot=='CHEST').first()`
  - **Accessory** (right side):
    - Check `main_character.inventory_items.filter_by(is_equipped=True, equipment.slot=='RING').first()`

#### Equipment Slot Hover Tooltips
- Show equipment stats:
  - Name: `equipment.name`
  - Type: `equipment.type`
  - Stats: `health_bonus`, `power_bonus`, `defense_bonus`

#### Stat Changes Panel (Bottom of sidebar)
- **Attack**: Sum of `power_bonus` from all equipped items
- **Defense**: Sum of `defense_bonus` from all equipped items
- Calculate from: `main_character.inventory_items.filter_by(is_equipped=True).all()`

#### Action Buttons
- **Auto Equip**: Future feature (placeholder)
- **Save Loadout**: Future feature (placeholder)

### API Endpoints Used
- `GET /student/character` - Load character and inventory data
- `PATCH /student/equipment/equip` - Equip item
  - Request: `{inventory_id, slot}`
  - Response: `{success}`
- `PATCH /student/equipment/unequip` - Unequip item
  - Request: `{inventory_id}`
  - Response: `{success}`

## Page 4: Quest Page

### Route
- `GET /student/quests` (existing)
- `POST /student/quests/start/<quest_id>` (existing)
- `POST /student/quests/complete/<quest_id>` (existing)
- Template: `app/templates/student/quests.html`

### Data Mappings

#### Quest Log Sidebar
- **Data Source**: `assigned_quests` list (quest + QuestLog)
- **Quest Cards**:
  - Name: `quest.name`
  - Description: `quest.description`
  - Status Badge:
    - "Active" (yellow) if `log.status == 'in_progress'`
    - "Ready" (green) if `log.status == 'completed'` but not turned in
    - "New" (gray) if `log.status == 'not_started'`
  - Progress Bar: Calculate from quest objectives
  - Progress %: Display percentage

#### Active Quest Display (Main area)
- **Selected Quest**: Based on active/selected quest
- **Quest Header**:
  - Type Badge: `quest.quest_type` or "Story Quest"
  - Time Remaining: Calculate from `quest.deadline` if exists
  - Title: `quest.name`
  - Description: `quest.description` (italic, with quote styling)

#### Objectives List
- **Data Source**: `quest.objectives` or parse from quest structure
- **Display**:
  - Checkmark (green) for completed objectives
  - Number badge for in-progress objectives
  - Gray for not started
- **Objective Text**: Parse from quest data

#### Rewards Section
- **Data Source**: `quest.rewards` (Reward model)
- **Display**:
  - XP: `reward.amount` where `reward.type == 'xp'`
  - Gold: `reward.amount` where `reward.type == 'gold'`
  - Items: `reward.item_id` if `reward.type == 'item'`

#### Quest Giver Info
- **Name**: From quest data or default "Master Archivist"
- **Avatar**: Quest giver image (placeholder)
- **Location**: From quest data

#### Action Buttons
- **Continue Quest**: If `status == 'in_progress'`, link to quest activity
- **Abandon**: If allowed, remove quest log entry

### API Endpoints Used
- `GET /student/quests` - Load quests and logs
- `POST /student/quests/start/<quest_id>` - Start quest
- `POST /student/quests/complete/<quest_id>` - Complete quest

## Stats Calculation Notes

### Equipment Bonuses
- `total_health = base_health + sum(equipped_items.health_bonus)`
- `total_power = base_power + sum(equipped_items.power_bonus)`
- `total_defense = base_defense + sum(equipped_items.defense_bonus)`

### Current Implementation
- Character model has `@property` methods: `total_health`, `total_power`, `total_defense`
- These already calculate bonuses from equipped items
- Use these properties for display, not base stats

### Stat Display Changes
- **HP** instead of "Health"
- **PP** instead of "Power" (Power Points)
- Show both current and max values
- Display as progress bars with percentages

## Color Scheme

From Tailwind config in design files:
- Primary: `#4f46e5` (indigo)
- HP Red: `#ef4444`
- AP/PP Blue: `#3b82f6`
- XP Yellow: `#f59e0b`
- GP Gold: `#d97706`
- Background Light: `#f3f4f6`
- Background Dark: `#111827`
- Rarity Common: `#9ca3af`
- Rarity Rare: `#3b82f6`
- Rarity Epic: `#a855f7`
- Rarity Legendary: `#eab308`

## Fonts

- Display Font: Cinzel (serif, for headings)
- Body Font: Lato (sans-serif, for body text)
- Material Icons: For iconography

## Shared Layout Structure

```
<div class="h-8">Top bar (class name, teacher avatar)</div>
<div class="h-16">Clan bar (student tabs with HP/PP)</div>
<div class="flex-1 flex">
  <aside class="w-80">Sidebar (stats, navigation, page-specific)</aside>
  <main class="flex-1">Main content area</main>
</div>
```
