import pytest
import sqlite3
import os
from unittest.mock import patch, MagicMock
from scout.core.db import ScoutDB

def test_db_initialization(mock_db_path):
    """Verify that tables are created on initialization."""
    # Mock config.app.db_path to use our temp DB
    mock_config = MagicMock()
    mock_config.app.db_path = mock_db_path
    
    with patch("scout.core.db.config", mock_config):
        db = ScoutDB()
        
        # Check if tables exist
        with sqlite3.connect(mock_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='processed_posts'")
            assert cursor.fetchone() is not None
            
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='briefings'")
            assert cursor.fetchone() is not None

def test_is_processed_logic(mock_db_path):
    """Verify that is_processed correctly tracks post IDs."""
    mock_config = MagicMock()
    mock_config.app.db_path = mock_db_path
    
    with patch("scout.core.db.config", mock_config):
        db = ScoutDB()
        
        test_id = "test_post_123"
        
        # 1. Should not be processed initially
        assert db.is_processed(test_id) is False
        
        # 2. Mark as processed
        db.mark_processed(test_id, "test_intent", True)
        
        # 3. Should now be processed
        assert db.is_processed(test_id) is True
