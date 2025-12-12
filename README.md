# Legends of Learning

A gamified learning platform where students complete quests, earn gold, and upgrade their characters, while teachers manage classes and track progress.

## Quick Start

If you're setting up the project for the first time:

```bash
# 1. Create and activate virtual environment (recommended)
python -m venv venv
source venv/Scripts/activate  # Windows Git Bash/PowerShell
# OR: venv\Scripts\activate  # Windows Command Prompt
# OR: source venv/bin/activate  # macOS/Linux

# 2. Install dependencies (REQUIRED - do this first!)
pip install -r requirements.txt

# 3. Set up database
alembic upgrade head  # Apply database migrations (REQUIRED)
flask seed-db  # Seed initial data (optional, only needed once)

# 4. Run the application
python run.py
```

Then open `http://127.0.0.1:5000` or `http://localhost:5000` in your browser.

**Important Notes**: 
- **Always install dependencies first**: If you see `ModuleNotFoundError` (e.g., "No module named 'flask_login'"), run `pip install -r requirements.txt` before starting the server
- **Virtual environment is recommended** but not strictly required if dependencies are installed globally
- **If you see "Connection refused"**: Make sure the server is actually running in a terminal window and you see "Running on http://127.0.0.1:5000" in the output
- **After database changes**: Always run `alembic upgrade head` to ensure your database schema is up to date

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

2.  **Create a virtual environment**:
    ```bash
    python -m venv venv
    ```

3.  **Activate the virtual environment**:
    ```bash
    # Windows (Git Bash / PowerShell)
    source venv/Scripts/activate
    # Windows (Command Prompt)
    venv\Scripts\activate
    # macOS/Linux
    source venv/bin/activate
    ```
    
    **Note**: You should see `(venv)` at the beginning of your command prompt when activated. You must activate the virtual environment every time you open a new terminal session.

4.  **Install dependencies**:
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

**Note**: Make sure your virtual environment is activated (if using one) before running these commands.

1.  **Apply Migrations**:
    ```bash
    alembic upgrade head
    ```
    This ensures your database schema is up to date with the latest migrations. **Always run this after:**
    - Setting up the project for the first time
    - Pulling new code that includes database changes
    - Resetting or modifying the database schema
    - Seeing version mismatch warnings in the application logs

2.  **Seed Initial Data** (Equipment, etc.):
    ```bash
    flask seed-db
    ```
    This populates the database with initial equipment data. You only need to run this once, or if you've reset the database.

### 5. Running the Application

**IMPORTANT**: Ensure dependencies are installed before running the application.

1. **Verify dependencies are installed** (if you're unsure):
   ```bash
   pip install -r requirements.txt
   ```
   This ensures all required packages (Flask, Flask-Login, Flask-WTF, etc.) are installed.

2. **Activate the virtual environment** (recommended):
   ```bash
   # Windows (Git Bash / PowerShell)
   source venv/Scripts/activate
   
   # Windows (Command Prompt)
   venv\Scripts\activate
   
   # macOS/Linux
   source venv/bin/activate
   ```
   
   You should see `(venv)` at the beginning of your command prompt when activated.
   
   **Note**: If dependencies are installed globally, you can skip this step, but using a virtual environment is strongly recommended.

3. **Verify the database is up to date** (recommended before first run or after schema changes):
   ```bash
   alembic upgrade head
   ```
   This applies all pending database migrations and ensures your database schema matches the latest version.

4. **Start the development server**:
   ```bash
   python run.py
   ```
   
   You should see output indicating the server is running, such as:
   ```
   * Running on http://127.0.0.1:5000
   * Running on http://0.0.0.0:5000
   ```

5. **Access the application**:
   - **Recommended**: Open your browser and navigate to: `http://127.0.0.1:5000` or `http://localhost:5000`
   - The server is also accessible on your network IP (e.g., `http://192.168.0.45:5000`) if you need to access it from other devices on your local network
   - The server will run until you stop it

6. **Stop the server**:
   - Press `Ctrl+C` in the terminal where the server is running
   - The server will shut down gracefully

**Troubleshooting**:

- **`ModuleNotFoundError` (e.g., "No module named 'flask_login'")**: 
  - **Solution**: Run `pip install -r requirements.txt` to install all required dependencies
  - This is the most common issue when starting the application for the first time or on a new machine
  - You don't necessarily need to activate the virtual environment if dependencies are installed globally, but it's recommended

- **Database errors or version mismatch warnings**: 
  - Run `alembic upgrade head` to apply all pending migrations
  - This ensures your database schema is up to date with the latest code changes
  - Always run this after pulling new code or resetting the database

- **Port 5000 already in use**: 
  - Change the port in `run.py` (modify the `port=5000` parameter) or stop the other process using that port
  - On Windows, you can find the process using: `netstat -ano | findstr ":5000"`

- **Connection refused / ERR_CONNECTION_REFUSED**: 
  - Make sure the server is actually running (you should see "Running on http://127.0.0.1:5000" in the terminal output)
  - Try accessing `http://127.0.0.1:5000` or `http://localhost:5000` instead of the network IP
  - If accessing from another device on your network, Windows Firewall may be blocking the connection. You may need to allow Python through the firewall or add a firewall rule for port 5000
  - Verify the server process is running: `netstat -ano | findstr ":5000.*LISTENING"` (Windows) or `netstat -tuln | grep 5000` (Linux/macOS)

- **Server not starting or crashes immediately**: 
  - Check that all dependencies are installed: `pip install -r requirements.txt`
  - Verify the database exists and is accessible (check `instance/legends.db`)
  - Look for error messages in the terminal output when starting the server
  - Ensure Python 3.8+ is being used: `python --version`

## Testing

Run the test suite using `pytest`:
```bash
pytest
```
