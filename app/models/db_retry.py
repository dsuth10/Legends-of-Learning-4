"""
Database connection retry handling with exponential backoff.

This module provides utilities for handling SQLite busy errors and connection retries
with exponential backoff to handle concurrent write operations gracefully.
"""

import time
import logging
from functools import wraps
from typing import Any, Callable, TypeVar
from sqlalchemy.exc import OperationalError

# Type variable for generic function return type
T = TypeVar('T')

# Configure logger
logger = logging.getLogger(__name__)

def with_retry(max_retries: int = 5, initial_delay: float = 0.1) -> Callable:
    """
    Decorator that implements retry logic with exponential backoff for database operations.
    
    Args:
        max_retries (int): Maximum number of retry attempts (default: 5)
        initial_delay (float): Initial delay in seconds before first retry (default: 0.1)
        
    Returns:
        Callable: Decorated function with retry logic
        
    Example:
        @with_retry(max_retries=3)
        def save_to_db():
            # Database operation that might fail due to concurrent access
            db.session.commit()
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            delay = initial_delay
            last_error = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                    
                except OperationalError as e:
                    last_error = e
                    
                    # Check if it's a database locked error
                    if "database is locked" not in str(e).lower():
                        raise  # Re-raise if it's not a locking issue
                    
                    if attempt == max_retries:
                        logger.error(f"Max retries ({max_retries}) exceeded: {str(e)}")
                        raise  # Re-raise the last error if we're out of retries
                    
                    # Calculate delay with exponential backoff (2^attempt * initial_delay)
                    delay = initial_delay * (2 ** attempt)
                    
                    logger.warning(
                        f"Database locked, attempt {attempt + 1}/{max_retries + 1}. "
                        f"Retrying in {delay:.2f} seconds..."
                    )
                    
                    time.sleep(delay)
            
            # This should never be reached due to the raise in the loop
            raise last_error if last_error else RuntimeError("Unexpected retry failure")
            
        return wrapper
    return decorator 