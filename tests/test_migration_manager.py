"""Tests for the migration manager module."""

import os
import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, text

from app.models.migration_manager import MigrationManager
from app.models.db_config import get_database_url

@pytest.fixture
def migration_manager(tmp_path):
    """Create a MigrationManager instance with a temporary project root."""
    # Create mock alembic.ini in temp directory
    alembic_ini = tmp_path / "alembic.ini"
    alembic_ini.write_text("[alembic]\nsqlalchemy.url = sqlite:///test.db\n")
    
    return MigrationManager(project_root=tmp_path)

@pytest.fixture
def mock_engine():
    """Create a mock SQLAlchemy engine."""
    engine = create_engine("sqlite:///:memory:")
    yield engine
    engine.dispose()

def test_init_with_project_root(tmp_path):
    """Test initialization with explicit project root."""
    manager = MigrationManager(project_root=tmp_path)
    assert manager.project_root == tmp_path
    assert isinstance(manager.alembic_cfg, Config)

def test_init_without_project_root():
    """Test initialization without project root defaults to cwd."""
    manager = MigrationManager()
    assert manager.project_root == Path.cwd()
    assert isinstance(manager.alembic_cfg, Config)

@patch("app.models.migration_manager.command")
def test_create_migration_autogenerate(mock_command, migration_manager):
    """Test creating a migration with autogenerate=True."""
    mock_rev = Mock(revision="abc123")
    mock_command.revision.return_value = mock_rev
    
    revision = migration_manager.create_migration("test migration")
    
    mock_command.revision.assert_called_once_with(
        migration_manager.alembic_cfg,
        "test migration",
        autogenerate=True
    )
    assert revision == "abc123"

@patch("app.models.migration_manager.command")
def test_create_migration_manual(mock_command, migration_manager):
    """Test creating a migration with autogenerate=False."""
    mock_rev = Mock(revision="def456")
    mock_command.revision.return_value = mock_rev
    
    revision = migration_manager.create_migration("test migration", autogenerate=False)
    
    mock_command.revision.assert_called_once_with(
        migration_manager.alembic_cfg,
        "test migration"
    )
    assert revision == "def456"

@patch("app.models.migration_manager.command")
def test_upgrade(mock_command, migration_manager):
    """Test upgrading to a specific revision."""
    migration_manager.upgrade("abc123")
    mock_command.upgrade.assert_called_once_with(migration_manager.alembic_cfg, "abc123")

@patch("app.models.migration_manager.command")
def test_upgrade_to_head(mock_command, migration_manager):
    """Test upgrading to head revision."""
    migration_manager.upgrade()
    mock_command.upgrade.assert_called_once_with(migration_manager.alembic_cfg, "head")

@patch("app.models.migration_manager.command")
def test_downgrade(mock_command, migration_manager):
    """Test downgrading to a specific revision."""
    migration_manager.downgrade("abc123")
    mock_command.downgrade.assert_called_once_with(migration_manager.alembic_cfg, "abc123")

@patch("app.models.migration_manager.create_engine")
def test_get_current_revision(mock_create_engine, migration_manager, mock_engine):
    """Test getting current revision."""
    mock_create_engine.return_value = mock_engine
    mock_context = Mock()
    mock_context.get_current_revision.return_value = "abc123"
    
    with patch("app.models.migration_manager.MigrationContext") as mock_migration_context:
        mock_migration_context.configure.return_value = mock_context
        revision = migration_manager.get_current_revision()
    
    assert revision == "abc123"
    mock_create_engine.assert_called_once_with(get_database_url())

@patch("app.models.migration_manager.ScriptDirectory")
def test_check_history(mock_script_directory, migration_manager):
    """Test checking migration history."""
    mock_script = Mock()
    mock_script_directory.from_config.return_value = mock_script
    
    mock_rev1 = Mock(revision="abc123", doc="First migration")
    mock_rev2 = Mock(revision="def456", doc="Second migration")
    mock_script.walk_revisions.return_value = [mock_rev1, mock_rev2]
    
    with patch.object(migration_manager, "get_current_revision") as mock_get_current:
        mock_get_current.return_value = "def456"
        history = migration_manager.check_history()
    
    assert history == [
        ("abc123", "First migration", False),
        ("def456", "Second migration", True)
    ]

@patch("app.models.migration_manager.create_engine")
def test_verify_pending_migrations_up_to_date(mock_create_engine, migration_manager, mock_engine):
    """Test verifying pending migrations when up to date."""
    mock_create_engine.return_value = mock_engine
    
    mock_context = Mock()
    mock_context.get_current_revision.return_value = "abc123"
    
    mock_script = Mock()
    mock_script.get_current_head.return_value = "abc123"
    
    with patch("app.models.migration_manager.MigrationContext") as mock_migration_context, \
         patch("app.models.migration_manager.ScriptDirectory") as mock_script_directory:
        mock_migration_context.configure.return_value = mock_context
        mock_script_directory.from_config.return_value = mock_script
        
        result = migration_manager.verify_pending_migrations()
    
    assert result is True

@patch("app.models.migration_manager.create_engine")
def test_verify_pending_migrations_outdated(mock_create_engine, migration_manager, mock_engine):
    """Test verifying pending migrations when outdated."""
    mock_create_engine.return_value = mock_engine
    
    mock_context = Mock()
    mock_context.get_current_revision.return_value = "abc123"
    
    mock_script = Mock()
    mock_script.get_current_head.return_value = "def456"
    
    with patch("app.models.migration_manager.MigrationContext") as mock_migration_context, \
         patch("app.models.migration_manager.ScriptDirectory") as mock_script_directory:
        mock_migration_context.configure.return_value = mock_context
        mock_script_directory.from_config.return_value = mock_script
        
        result = migration_manager.verify_pending_migrations()
    
    assert result is False 