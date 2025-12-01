# Legends of Learning

A gamified learning platform where students complete quests, earn gold, and upgrade their characters, while teachers manage classes and track progress.

## Features

### 👨‍🏫 Teacher Dashboard
*   **Class Management**: Create and manage multiple classes.
*   **Student Management**: Add students manually or import them in bulk. Track student progress.
*   **Quest Management**: Create educational quests with specific rewards (XP, Gold).
*   **Clan Management**: Oversee student clans and monitor clan performance.
*   **Analytics**: View real-time statistics on student engagement and performance.

### 👨‍🎓 Student Dashboard
*   **Quest Board**: View and complete assigned quests to earn rewards.
*   **Character Progression**: Earn XP to level up and improve stats (Health, Strength, Defense).
*   **Shop**: Spend earned Gold on equipment (Weapons, Armor, etc.) to boost stats.
*   **Clans**: Join clans, contribute to clan goals, and compete with others.
*   **Inventory**: Manage equipped items and inventory.

### 🎮 Gamification Elements
*   **XP & Levels**: Progress through levels by completing tasks.
*   **Gold Economy**: Earn currency to purchase in-game items.
*   **Equipment System**: Items with specific stats, rarities, and level requirements.
*   **Clans**: Collaborative groups for students.

## Tech Stack

*   **Backend**: Python, Flask
*   **Database**: SQLAlchemy (ORM), SQLite (Development), Flask-Migrate (Alembic)
*   **Authentication**: Flask-Login, Flask-JWT-Extended
*   **Forms**: Flask-WTF
*   **Testing**: Pytest

## Setup

### 1. Prerequisites
*   Python 3.8+
*   pip

### 2. Installation

1.  **Clone the repository** (if applicable) or navigate to the project directory.

2.  **Create and activate a virtual environment**:
    ```bash
    python -m venv venv
    # Windows
    .\venv\Scripts\activate
    # macOS/Linux
    source venv/bin/activate
    ```

3.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

### 3. Configuration

Create a `.env` file in the root directory with the following variables:
```env
SECRET_KEY=your-secret-key-here
TEACHER_ACCESS_CODE=your-secure-teacher-code
# Optional: Database URI (defaults to SQLite local.db)
# SQLALCHEMY_DATABASE_URI=sqlite:///instance/local.db
```

### 4. Database Initialization

1.  **Apply Migrations**:
    ```bash
    flask db upgrade
    ```

2.  **Seed Initial Data** (Equipment, etc.):
    ```bash
    flask seed-db
    ```

### 5. Running the Application

Start the development server:
```bash
python run.py
```
The application will be available at `http://127.0.0.1:5000`.

## Testing

Run the test suite using `pytest`:
```bash
pytest
```
