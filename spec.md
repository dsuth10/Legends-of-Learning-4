# Project Specification

## Overview

Legends of Learning is a gamified learning platform where students complete educational quests, earn rewards, and progress through character levels, while teachers manage classes and track student performance.

## Core Features

### Teacher Dashboard
- Class Management: Create and manage multiple classes
- Student Management: Add students manually or import in bulk via CSV
- Quest Management: Create educational quests with XP and Gold rewards
- Clan Management: Oversee student clans and monitor performance
- Analytics: Real-time statistics on student engagement and performance

### Student Dashboard
- Quest Board: View and complete assigned quests to earn rewards
- Character Progression: Earn XP to level up and improve stats (Health, Strength, Defense)
- Shop: Spend earned Gold on equipment (Weapons, Armor, Accessories) to boost stats
- Clans: Join clans, contribute to clan goals, and compete with others
- Inventory: Manage equipped items and inventory

## Technical Stack

- **Backend**: Python 3.8+, Flask
- **Database**: SQLAlchemy ORM, SQLite (Development), PostgreSQL (Production-ready)
- **Migrations**: Alembic
- **Authentication**: Flask-Login, Flask-JWT-Extended
- **Forms**: Flask-WTF
- **Testing**: Pytest
- **Frontend**: Jinja2 templates, vanilla JavaScript, CSS

## Key Models

- User (authentication and roles)
- Student (game profile linked to User)
- Classroom (teacher-managed classes)
- Character (student's game avatar)
- Clan (student teams)
- Quest (educational tasks)
- Equipment (purchasable items)
- AchievementBadge (earnable badges)

## Current Status

The project is in active development with core features implemented:
- User authentication and role management
- Student and teacher dashboards
- Quest system
- Character progression
- Equipment shop
- Clan system
- Battle system

## Future Enhancements

- Enhanced analytics and reporting
- More quest types and rewards
- Social features
- Mobile responsiveness improvements
- API documentation
- Performance optimizations









