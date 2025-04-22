"""
Tests for database retry logic.
"""

import pytest
import time
from unittest.mock import Mock, patch
from sqlalchemy.exc import OperationalError

from app.models.db_retry import with_retry

def test_successful_operation():
    """Test that normal operations work without retries."""
    mock_func = Mock(return_value="success")
    decorated = with_retry()(mock_func)
    
    result = decorated()
    assert result == "success"
    assert mock_func.call_count == 1

def test_retry_on_locked_database():
    """Test that operations retry on database locked errors."""
    mock_func = Mock(side_effect=[
        OperationalError("database is locked", None, None),
        OperationalError("database is locked", None, None),
        "success"
    ])
    
    decorated = with_retry(max_retries=3, initial_delay=0.01)(mock_func)
    
    result = decorated()
    assert result == "success"
    assert mock_func.call_count == 3

def test_max_retries_exceeded():
    """Test that operations fail after max retries."""
    error = OperationalError("database is locked", None, None)
    mock_func = Mock(side_effect=error)
    
    decorated = with_retry(max_retries=2, initial_delay=0.01)(mock_func)
    
    with pytest.raises(OperationalError) as exc_info:
        decorated()
    
    assert "database is locked" in str(exc_info.value)
    assert mock_func.call_count == 3  # Initial try + 2 retries

def test_non_locking_error_not_retried():
    """Test that non-locking errors are raised immediately."""
    error = OperationalError("different error", None, None)
    mock_func = Mock(side_effect=error)
    
    decorated = with_retry()(mock_func)
    
    with pytest.raises(OperationalError) as exc_info:
        decorated()
    
    assert "different error" in str(exc_info.value)
    assert mock_func.call_count == 1  # No retries

def test_exponential_backoff():
    """Test that retry delays follow exponential backoff."""
    mock_func = Mock(side_effect=[
        OperationalError("database is locked", None, None),
        OperationalError("database is locked", None, None),
        "success"
    ])
    
    initial_delay = 0.01
    start_time = time.time()
    
    decorated = with_retry(max_retries=2, initial_delay=initial_delay)(mock_func)
    result = decorated()
    
    elapsed_time = time.time() - start_time
    
    # Expected delays: 0.01s and 0.02s
    min_expected_time = initial_delay + (initial_delay * 2)
    
    assert result == "success"
    assert elapsed_time >= min_expected_time 