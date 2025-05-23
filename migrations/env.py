from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Import our models and db instance
from app.models import db
from app.models.db_config import get_database_url

# Import all models to ensure they are registered with SQLAlchemy
from app.models.user import User
from app.models.classroom import Classroom
from app.models.character import Character
from app.models.clan import Clan
from app.models.equipment import Equipment
from app.models.ability import Ability
from app.models.shop import ShopPurchase
from app.models.quest import Quest, QuestLog
from app.models.audit import AuditLog
from app.models.student import Student
from app.models.assist_log import AssistLog
from app.models.base import Base
from app.models.db_maintenance import *  # If this file contains models
from app.models.classroom import class_students  # Association table

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Set the SQLAlchemy URL in the alembic config
# config.set_main_option("sqlalchemy.url", get_database_url())  # Commented out to allow test fixture to set DB URL

# Debug: Print the DB URL being used
print("Alembic using DB URL:", config.get_main_option("sqlalchemy.url"))

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = db.metadata

# Debug: Print the tables Alembic sees in target_metadata
print("Alembic target_metadata tables:", list(target_metadata.tables.keys()))

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
