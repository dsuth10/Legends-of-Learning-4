# Data Models - Legends of Learning

**Generated:** 2025-01-27  
**ORM:** SQLAlchemy 2.0+  
**Database:** SQLite (Development), PostgreSQL-ready

## Core Models

### User (`users`)
**Purpose:** Authentication and user management

| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key |
| username | String(64) | Unique username |
| email | String(120) | Unique email |
| password_hash | String(256) | Hashed password |
| role | Enum(UserRole) | TEACHER, STUDENT, or ADMIN |
| is_active | Boolean | Account status |
| first_name | String(64) | User's first name |
| last_name | String(64) | User's last name |
| display_name | String(64) | In-game display name |
| avatar_url | String(255) | Avatar image path |

**Relationships:**
- Many-to-many with `Classroom` via `class_students` association
- One-to-many with `AuditLog`

### Student (`students`)
**Purpose:** Student game profile linked to User

| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key |
| user_id | Integer | Foreign key to `users.id` |
| class_id | Integer | Foreign key to `classrooms.id` |
| created_at | DateTime | Creation timestamp |

**Relationships:**
- One-to-one with `User` (via user_id)
- Many-to-one with `Classroom`
- One-to-many with `Character`
- One-to-many with `ShopPurchase`

### Character (`characters`)
**Purpose:** Student's game avatar with stats and progression

| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key |
| name | String(64) | Character name |
| level | Integer | Current level (default: 1) |
| experience | Integer | Current XP (default: 0) |
| health | Integer | Current health (default: 100) |
| max_health | Integer | Maximum health (default: 100) |
| power | Integer | Power stat (default: 10) |
| defense | Integer | Defense stat (default: 10) |
| gold | Integer | Gold currency (default: 0) |
| character_class | String(32) | Character class |
| gender | String(16) | Character gender |
| avatar_url | String(256) | Avatar image URL |
| is_active | Boolean | Active status |
| student_id | Integer | Foreign key to `students.id` |
| clan_id | Integer | Foreign key to `clans.id` (nullable) |

**Relationships:**
- Many-to-one with `Student`
- Many-to-one with `Clan` (optional)
- Many-to-many with `Ability` via `character_abilities`
- Many-to-many with `Equipment` via `inventories`
- One-to-many with `QuestLog`
- One-to-many with `ShopPurchase`
- One-to-many with `AuditLog`

### Classroom (`classrooms`)
**Purpose:** Teacher-managed classes

| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key |
| name | String(128) | Class name |
| teacher_id | Integer | Foreign key to `users.id` |
| created_at | DateTime | Creation timestamp |
| is_archived | Boolean | Archive status |

**Relationships:**
- Many-to-one with `User` (teacher)
- One-to-many with `Student`
- One-to-many with `Clan`
- Many-to-many with `User` (students) via `class_students`

### Quest (`quests`)
**Purpose:** Educational quests/tasks

| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key |
| title | String(128) | Quest title |
| description | Text | Quest description |
| type | Enum(QuestType) | STORY, DAILY, WEEKLY, ACHIEVEMENT, EVENT |
| level_requirement | Integer | Minimum level required |
| requirements | JSON | Quest requirements (flexible) |
| completion_criteria | JSON | Completion criteria |
| parent_quest_id | Integer | Foreign key for quest chains |
| created_at | DateTime | Creation timestamp |

**Relationships:**
- One-to-many with `Reward` (quest rewards)
- One-to-many with `Consequence` (quest consequences)
- One-to-many with `QuestLog` (student quest progress)

### QuestLog (`quest_logs`)
**Purpose:** Tracks student quest progress

| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key |
| quest_id | Integer | Foreign key to `quests.id` |
| character_id | Integer | Foreign key to `characters.id` |
| status | Enum(QuestStatus) | NOT_STARTED, IN_PROGRESS, COMPLETED, FAILED |
| started_at | DateTime | Quest start time |
| completed_at | DateTime | Quest completion time |

**Relationships:**
- Many-to-one with `Quest`
- Many-to-one with `Character`

### Equipment (`equipment`)
**Purpose:** Purchasable items (weapons, armor, accessories)

| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key |
| name | String(128) | Item name |
| description | Text | Item description |
| type | Enum(EquipmentType) | WEAPON, ARMOR, ACCESSORY |
| slot | Enum(EquipmentSlot) | Weapon/Armor slot type |
| cost | Integer | Gold cost |
| level_requirement | Integer | Minimum level to equip |
| health_bonus | Integer | Health stat bonus |
| power_bonus | Integer | Power stat bonus |
| defense_bonus | Integer | Defense stat bonus |
| rarity | String(32) | Item rarity |
| image_url | String(256) | Item image URL |
| class_restriction | String(32) | Character class restriction (nullable) |

**Relationships:**
- Many-to-many with `Character` via `inventories`

### Inventory (`inventories`)
**Purpose:** Character equipment inventory (junction table)

| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key |
| character_id | Integer | Foreign key to `characters.id` |
| equipment_id | Integer | Foreign key to `equipment.id` |
| is_equipped | Boolean | Equipped status |
| quantity | Integer | Item quantity |

### Clan (`clans`)
**Purpose:** Student teams/groups

| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key |
| name | String(128) | Clan name |
| class_id | Integer | Foreign key to `classrooms.id` |
| leader_id | Integer | Foreign key to `characters.id` (nullable) |
| created_at | DateTime | Creation timestamp |

**Relationships:**
- Many-to-one with `Classroom`
- One-to-many with `Character` (members)
- Many-to-many with `AchievementBadge` via `clan_badges`
- One-to-many with `ClanProgressHistory`

### Ability (`abilities`)
**Purpose:** Character skills/powers

| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key |
| name | String(128) | Ability name |
| description | Text | Ability description |
| type | Enum(AbilityType) | Ability type |
| cooldown_seconds | Integer | Cooldown duration |
| effect_data | JSON | Ability effects |

**Relationships:**
- Many-to-many with `Character` via `character_abilities`
- One-to-many with `AssistLog`

### ShopPurchase (`shop_purchases`)
**Purpose:** Tracks equipment/ability purchases

| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key |
| character_id | Integer | Foreign key to `characters.id` |
| student_id | Integer | Foreign key to `students.id` |
| purchase_type | Enum(PurchaseType) | EQUIPMENT or ABILITY |
| item_id | Integer | Equipment or Ability ID |
| cost | Integer | Purchase cost |
| purchased_at | DateTime | Purchase timestamp |

### AuditLog (`audit_log`)
**Purpose:** Tracks important game events

| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key |
| user_id | Integer | Foreign key to `users.id` |
| character_id | Integer | Foreign key to `characters.id` (nullable) |
| event_type | Enum(EventType) | Event type |
| description | Text | Event description |
| metadata | JSON | Additional event data |
| created_at | DateTime | Event timestamp |

## Association Tables

- `class_students`: User ↔ Classroom (many-to-many)
- `character_abilities`: Character ↔ Ability (many-to-many)
- `inventories`: Character ↔ Equipment (many-to-many)
- `clan_badges`: Clan ↔ AchievementBadge (many-to-many)
- `character_badges`: Character ↔ AchievementBadge (many-to-many)

## Key Relationships Summary

```
User ⟷ Student ⟶ Character ⟶ (Ability, Equipment, QuestLog, AchievementBadge, ShopPurchase, AuditLog)
User ⟷ Classroom ⟶ Clan ⟶ Character
Quest ⟶ (Reward, Consequence, QuestLog)
Clan ⟶ ClanProgressHistory
Ability ⟶ AssistLog
```

## Database Migrations

- Managed via Alembic
- Migration files in `migrations/versions/`
- Run `alembic upgrade head` to apply migrations

