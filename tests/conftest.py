import sys
import os
import tempfile
import pytest
from alembic.config import Config
from alembic import command
import sqlite3
from sqlalchemy import text
import uuid
import sqlalchemy

# Do NOT import app/db until after Alembic runs!


def drop_all_tables(db_path):
    print(f"[DEBUG] Dropping all tables in {db_path} before Alembic migration...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    for (table_name,) in tables:
        if table_name != "sqlite_sequence":
            cursor.execute(f"DROP TABLE IF EXISTS {table_name};")
            print(f"[DEBUG] Dropped table: {table_name}")
    conn.commit()
    conn.close()


def run_alembic_upgrade(database_uri):
    alembic_cfg_path = os.path.join(
        os.path.dirname(__file__), "..", "migrations", "alembic.ini"
    )
    print(f"[DEBUG] Alembic config: {alembic_cfg_path}")
    alembic_cfg = Config(alembic_cfg_path)
    alembic_cfg.set_main_option("sqlalchemy.url", database_uri)
    script_location = alembic_cfg.get_main_option("script_location")
    print(f"[DEBUG] Alembic script_location: {script_location}")
    print(f"[DEBUG] Alembic DB URI: {database_uri}")
    import glob

    migration_files = glob.glob(
        os.path.join(os.path.dirname(__file__), "..", "migrations", "versions", "*.py")
    )
    print(f"[DEBUG] Migration files: {migration_files}")
    if migration_files:
        with open(migration_files[-1], "r") as f:
            print(f"[DEBUG] Last migration file contents:\n{f.read(1000)}")
    # Drop all tables before running Alembic
    if database_uri.startswith("sqlite:///"):
        db_path = database_uri.replace("sqlite:///", "")
        drop_all_tables(db_path)
    try:
        from alembic.script import ScriptDirectory

        script = ScriptDirectory.from_config(alembic_cfg)
        print(f"[DEBUG] Alembic heads before upgrade: {script.get_heads()}")
        command.upgrade(alembic_cfg, "head")
        print(f"[DEBUG] Alembic heads after upgrade: {script.get_heads()}")
    except Exception as e:
        print(f"[DEBUG] Alembic upgrade exception: {e}")
        raise

    # Fallback: if Alembic created no tables, initialize via SQLAlchemy models
    engine = sqlalchemy.create_engine(database_uri)
    inspector = sqlalchemy.inspect(engine)
    tables = [t for t in inspector.get_table_names() if t != "alembic_version"]
    if not tables:
        print("[DEBUG] No tables created by Alembic. Falling back to create_all().")
        from app import create_app, db

        app = create_app({"SQLALCHEMY_DATABASE_URI": database_uri})
        with app.app_context():
            db.create_all()
    engine.dispose()


def check_equipment_cost_column(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(equipment);")
    columns = cursor.fetchall()
    print(f"[DEBUG] equipment table columns: {columns}")
    has_cost = any(col[1] == "cost" for col in columns)
    if not has_cost:
        raise RuntimeError(
            "[SCHEMA ERROR] 'cost' column missing from equipment table after Alembic migration!"
        )
    conn.close()


@pytest.fixture(scope="function")
def test_db_file():
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)
    db_uri = f"sqlite:///{db_path}"
    # Ensure the test DB file is deleted before running Alembic
    try:
        os.remove(db_path)
    except FileNotFoundError:
        pass
    print(f"[DEBUG] Creating new test DB at {db_path}")
    run_alembic_upgrade(db_uri)
    # Print tables after Alembic
    conn = sqlite3.connect(db_path)
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table';"
    ).fetchall()
    print(f"[DEBUG] Tables after Alembic: {tables}")
    if not tables:
        raise RuntimeError(
            "Alembic migration did not create any tables! Check env.py and model imports."
        )
    # Print alembic_version table contents if it exists
    if any(t[0] == "alembic_version" for t in tables):
        version = conn.execute("SELECT version_num FROM alembic_version;").fetchall()
        print(f"[DEBUG] alembic_version table: {version}")
    else:
        print("[DEBUG] alembic_version table does not exist.")
    # Print clan_progress_history schema
    try:
        schema = conn.execute("PRAGMA table_info(clan_progress_history);").fetchall()
        print(f"[DEBUG] clan_progress_history schema: {schema}")
    except Exception as e:
        print(f"[DEBUG] Error fetching clan_progress_history schema: {e}")
    conn.close()
    # Check for cost column in equipment
    check_equipment_cost_column(db_path)
    yield db_uri
    try:
        os.remove(db_path)
    except FileNotFoundError:
        pass


@pytest.fixture(scope="function")
def app(test_db_file):
    import os

    os.environ["SQLALCHEMY_DATABASE_URI"] = test_db_file  # Set before importing app
    from app import create_app, db

    app = create_app()
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False  # Disable CSRF for tests
    app.config["SQLALCHEMY_DATABASE_URI"] = test_db_file
    print(
        f"[DEBUG] Flask app SQLALCHEMY_DATABASE_URI: {app.config['SQLALCHEMY_DATABASE_URI']}"
    )
    # Confirm Alembic and SQLAlchemy URIs match
    if test_db_file != app.config["SQLALCHEMY_DATABASE_URI"]:
        print(
            f"[ERROR] Alembic DB URI and SQLAlchemy DB URI do not match! {test_db_file} != {app.config['SQLALCHEMY_DATABASE_URI']}"
        )
    with app.app_context():
        from app.models.equipment import Equipment
        from app.models.equipment_data import EQUIPMENT_DATA

        if Equipment.query.count() == 0:
            for item in EQUIPMENT_DATA:
                type_value = (
                    item["type"].value
                    if hasattr(item["type"], "value")
                    else item["type"]
                )
                slot_value = (
                    item["slot"].value
                    if hasattr(item["slot"], "value")
                    else item["slot"]
                )
                eq = Equipment(
                    name=item["name"],
                    description=item["description"],
                    type=type_value,
                    slot=slot_value,
                    cost=item["cost"],
                    level_requirement=item["level_requirement"],
                    health_bonus=item["health_bonus"],
                    strength_bonus=item["strength_bonus"],
                    defense_bonus=item["defense_bonus"],
                    rarity=item["rarity"],
                    image_url=item["image_url"],
                    class_restriction=item.get("class_restriction"),
                )
                db.session.add(eq)
            db.session.commit()
    with app.app_context():
        db.session.remove()
        db.engine.dispose()
        db.Model.metadata.reflect(bind=db.engine)
        db.session.expire_all()
        yield app
        db.session.remove()
        db.engine.dispose()


@pytest.fixture(scope="function")
def db_session(app):
    from app import db

    yield db.session
    db.session.rollback()


@pytest.fixture
def client(app):
    return app.test_client()


# Add a fixture to truncate all tables before each test for full isolation
@pytest.fixture(autouse=True, scope="function")
def truncate_tables(db_session):
    from app import db

    meta = db.metadata
    engine = db.engine
    # Disable foreign key checks for SQLite
    if engine.dialect.name == "sqlite":
        db.session.execute(text("PRAGMA foreign_keys=OFF"))
    try:
        for table in reversed(meta.sorted_tables):
            try:
                db.session.execute(table.delete())
            except sqlalchemy.exc.OperationalError as e:
                print(f"[WARN] Could not delete from table {table.name}: {e}")
        # --- Repopulate Equipment table from EQUIPMENT_DATA ---
        from app.models.equipment import Equipment
        from app.models.equipment_data import EQUIPMENT_DATA

        for item in EQUIPMENT_DATA:
            type_value = (
                item["type"].value if hasattr(item["type"], "value") else item["type"]
            )
            slot_value = (
                item["slot"].value if hasattr(item["slot"], "value") else item["slot"]
            )
            eq = Equipment(
                name=item["name"],
                description=item["description"],
                type=type_value,
                slot=slot_value,
                cost=item["cost"],
                level_requirement=item["level_requirement"],
                health_bonus=item["health_bonus"],
                strength_bonus=item["strength_bonus"],
                defense_bonus=item["defense_bonus"],
                rarity=item["rarity"],
                image_url=item["image_url"],
                class_restriction=item.get("class_restriction"),
            )
            db.session.add(eq)
    finally:
        # Re-enable foreign key checks for SQLite
        if engine.dialect.name == "sqlite":
            db.session.execute(text("PRAGMA foreign_keys=ON"))
    db.session.commit()


@pytest.fixture
def test_user(db_session):
    from app.models.user import User, UserRole

    unique = uuid.uuid4().hex[:8]
    user = User(
        username=f"student_{unique}",
        email=f"student_{unique}@example.com",
        role=UserRole.STUDENT,
    )
    user.set_password("password")
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def test_classroom(db_session, test_user):
    from app.models.classroom import Classroom

    unique = uuid.uuid4().hex[:8]
    classroom = Classroom(
        name=f"Test Class {unique}",
        teacher_id=test_user.id,
        join_code=f"TEST{unique[:5]}",
    )
    db_session.add(classroom)
    db_session.commit()
    return classroom


@pytest.fixture
def test_student(db_session, test_user, test_classroom):
    from app.models.student import Student

    student = Student(
        user_id=test_user.id, class_id=test_classroom.id, level=1, gold=200
    )
    db_session.add(student)
    db_session.commit()
    return student


@pytest.fixture
def test_character(db_session, test_student):
    from app.models.character import Character
    from app.models.clan import Clan

    # Create a clan for the character
    clan = Clan(name="Test Clan", class_id=test_student.class_id)
    db_session.add(clan)
    db_session.commit()
    character = Character(
        name="Hero",
        student_id=test_student.id,
        character_class="Warrior",
        level=1,
        experience=0,
        health=100,
        max_health=100,
        strength=10,
        defense=10,
        is_active=True,
        clan_id=clan.id,
    )
    db_session.add(character)
    db_session.commit()
    return character


@pytest.fixture
def test_inventory(db_session, test_character):
    from app.models.equipment import Inventory, Equipment

    # Use an existing equipment item or create a simple placeholder
    eq = db_session.query(Equipment).first()
    if eq is None:
        eq = Equipment(name="Test Item", type="weapon", slot="main_hand", cost=0)
        db_session.add(eq)
        db_session.commit()
    inv = Inventory(character_id=test_character.id, item_id=eq.id, is_equipped=True)
    db_session.add(inv)
    db_session.commit()
    return inv
