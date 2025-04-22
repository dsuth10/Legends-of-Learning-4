"""
Migration management module.

This module provides utilities for managing database migrations using Alembic.
It handles applying migrations, reverting them, and checking migration status.
"""

import logging
from pathlib import Path
from typing import List, Optional, Tuple

from alembic.config import Config
from alembic import command
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, text

from .db_config import get_database_url

logger = logging.getLogger(__name__)

class MigrationManager:
    """Handles database migration operations."""
    
    def __init__(self, project_root: Optional[Path] = None):
        """
        Initialize the migration manager.
        
        Args:
            project_root: Path to the project root directory. If not provided,
                         assumes current directory is project root.
        """
        self.project_root = project_root or Path.cwd()
        self.alembic_cfg = Config(self.project_root / "alembic.ini")
        
    def create_migration(self, message: str, autogenerate: bool = True) -> str:
        """
        Create a new migration revision.
        
        Args:
            message: Description of what the migration does
            autogenerate: Whether to autogenerate migration based on models
            
        Returns:
            str: The revision ID of the new migration
        """
        try:
            if autogenerate:
                rev = command.revision(self.alembic_cfg, message, autogenerate=True)
            else:
                rev = command.revision(self.alembic_cfg, message)
            logger.info(f"Created new migration revision: {rev.revision}")
            return rev.revision
        except Exception as e:
            logger.error(f"Failed to create migration: {str(e)}")
            raise
    
    def upgrade(self, revision: str = "head") -> None:
        """
        Upgrade database to specified revision.
        
        Args:
            revision: Target revision (default: latest/"head")
        """
        try:
            command.upgrade(self.alembic_cfg, revision)
            logger.info(f"Successfully upgraded database to {revision}")
        except Exception as e:
            logger.error(f"Failed to upgrade database: {str(e)}")
            raise
    
    def downgrade(self, revision: str) -> None:
        """
        Downgrade database to specified revision.
        
        Args:
            revision: Target revision to downgrade to
        """
        try:
            command.downgrade(self.alembic_cfg, revision)
            logger.info(f"Successfully downgraded database to {revision}")
        except Exception as e:
            logger.error(f"Failed to downgrade database: {str(e)}")
            raise
    
    def get_current_revision(self) -> Optional[str]:
        """
        Get the current revision of the database.
        
        Returns:
            str: Current revision ID, or None if no migrations applied
        """
        engine = create_engine(get_database_url())
        with engine.connect() as conn:
            context = MigrationContext.configure(conn)
            return context.get_current_revision()
    
    def check_history(self) -> List[Tuple[str, str, bool]]:
        """
        Get the migration history and status.
        
        Returns:
            List of tuples containing (revision_id, description, is_applied)
        """
        script = ScriptDirectory.from_config(self.alembic_cfg)
        current = self.get_current_revision()
        
        history = []
        for rev in script.walk_revisions():
            is_current = rev.revision == current
            history.append((rev.revision, rev.doc, is_current))
        
        return history
    
    def verify_pending_migrations(self) -> bool:
        """
        Check if there are any pending migrations that need to be applied.
        
        Returns:
            bool: True if database is up to date, False if pending migrations exist
        """
        engine = create_engine(get_database_url())
        with engine.connect() as conn:
            context = MigrationContext.configure(conn)
            script = ScriptDirectory.from_config(self.alembic_cfg)
            
            head_revision = script.get_current_head()
            current_revision = context.get_current_revision()
            
            if current_revision != head_revision:
                logger.warning(f"Database not up to date. Current: {current_revision}, Latest: {head_revision}")
                return False
            
            logger.info("Database schema is up to date")
            return True 