# API Contracts - Legends of Learning

**Generated:** 2025-01-27  
**Authentication:** Flask-Login (sessions) and Flask-JWT-Extended (tokens)

## Authentication Endpoints

### POST `/login`
- **Description:** User login (creates session)
- **Auth:** None (public)
- **Returns:** Redirect or login form

### POST `/logout`
- **Description:** User logout
- **Auth:** Session required
- **Returns:** Redirect to home

### POST `/signup`
- **Description:** User registration
- **Auth:** None (public)
- **Returns:** Redirect or signup form

## Student Endpoints

### GET `/student/profile`
- **Description:** Student profile page
- **Auth:** `@login_required`, `@student_required`

### GET `/student/quests`
- **Description:** Quest board listing
- **Auth:** `@login_required`, `@student_required`

### POST `/student/quests/start/<int:quest_id>`
- **Description:** Start a quest
- **Auth:** `@login_required`, `@student_required`
- **Returns:** JSON response

### POST `/student/quests/complete/<int:quest_id>`
- **Description:** Complete a quest and receive rewards
- **Auth:** `@login_required`, `@student_required`
- **Returns:** JSON response

### GET `/student/clan`
- **Description:** Clan dashboard
- **Auth:** `@login_required`, `@student_required`

### GET `/student/character`
- **Description:** Character management page
- **Auth:** `@login_required`, `@student_required`

### POST `/student/character/create`
- **Description:** Create new character
- **Auth:** `@login_required`, `@student_required`

### POST `/student/character/gain_xp`
- **Description:** Award XP to character
- **Auth:** `@login_required`, `@student_required`

### GET `/student/shop`
- **Description:** Equipment shop page
- **Auth:** `@login_required`, `@student_required`

### POST `/student/shop/buy`
- **Description:** Purchase equipment
- **Auth:** `@login_required`, `@student_required`
- **Returns:** JSON response

### PATCH `/student/equipment/equip`
- **Description:** Equip an item
- **Auth:** `@login_required`, `@student_required`
- **Returns:** JSON response

### PATCH `/student/equipment/unequip`
- **Description:** Unequip an item
- **Auth:** `@login_required`, `@student_required`
- **Returns:** JSON response

### GET `/student/api/clan`
- **Description:** Get clan data (API)
- **Auth:** `@login_required`, `@student_required`
- **Returns:** JSON

### POST `/student/abilities/use`
- **Description:** Use an ability
- **Auth:** `@login_required`, `@student_required`
- **Returns:** JSON response

### GET `/student/abilities/history`
- **Description:** Get ability usage history
- **Auth:** `@login_required`, `@student_required`
- **Returns:** JSON

### GET `/student/battle/`
- **Description:** Battle arena page
- **Auth:** `@login_required`, `@student_required`

### POST `/student/battle/start`
- **Description:** Start a battle
- **Auth:** `@login_required`, `@student_required`
- **Returns:** JSON response

### GET `/student/battle/<int:battle_id>`
- **Description:** Battle detail page
- **Auth:** `@login_required`, `@student_required`

### POST `/student/battle/<int:battle_id>/attack`
- **Description:** Perform attack in battle
- **Auth:** `@login_required`, `@student_required`
- **Returns:** JSON response

### POST `/student/battle/<int:battle_id>/flee`
- **Description:** Flee from battle
- **Auth:** `@login_required`, `@student_required`
- **Returns:** JSON response

## Teacher Endpoints

### GET `/teacher/dashboard`
- **Description:** Teacher dashboard
- **Auth:** `@login_required`, `@teacher_required`

### GET `/teacher/classes`
- **Description:** Class management page
- **Auth:** `@login_required`, `@teacher_required`

### POST `/teacher/classes`
- **Description:** Create new class
- **Auth:** `@login_required`, `@teacher_required`

### GET `/teacher/students`
- **Description:** Student list
- **Auth:** `@login_required`, `@teacher_required`

### GET `/teacher/quests/`
- **Description:** Quest management page
- **Auth:** `@login_required`, `@teacher_required`

### POST `/teacher/quests/create`
- **Description:** Create new quest
- **Auth:** `@login_required`, `@teacher_required`

### POST `/teacher/quests/assign`
- **Description:** Assign quest to students
- **Auth:** `@login_required`, `@teacher_required`
- **Returns:** JSON response

### GET `/teacher/analytics`
- **Description:** Analytics dashboard
- **Auth:** `@login_required`, `@teacher_required`

### GET `/teacher/analytics/data`
- **Description:** Analytics data (API)
- **Auth:** `@login_required`, `@teacher_required`
- **Returns:** JSON

### GET `/teacher/clans`
- **Description:** Clan management page
- **Auth:** `@login_required`, `@teacher_required`

## JWT API Endpoints

### GET `/clans/<int:clan_id>/metrics`
- **Description:** Get clan metrics
- **Auth:** `@jwt_required()`
- **Returns:** JSON

### GET `/clans/<int:clan_id>/history`
- **Description:** Get clan progress history
- **Auth:** `@jwt_required()`
- **Returns:** JSON

### GET `/classes/<int:class_id>/clan-leaderboard`
- **Description:** Get class clan leaderboard
- **Auth:** `@jwt_required()`
- **Returns:** JSON

### GET `/api/teacher/student/<int:student_id>/stats`
- **Description:** Get student statistics
- **Auth:** `@login_required`, `@teacher_required`
- **Returns:** JSON

### POST `/api/teacher/student/<int:student_id>/award-gold`
- **Description:** Award gold to student
- **Auth:** `@login_required`, `@teacher_required`
- **Returns:** JSON

### POST `/api/teacher/student/<int:student_id>/award-xp`
- **Description:** Award XP to student
- **Auth:** `@login_required`, `@teacher_required`
- **Returns:** JSON

## Notes

- Most endpoints use Flask-Login session authentication
- JWT endpoints use Flask-JWT-Extended token authentication
- Student routes are prefixed with `/student`
- Teacher routes are prefixed with `/teacher`
- API routes return JSON, page routes return HTML templates

