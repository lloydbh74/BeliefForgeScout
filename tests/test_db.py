from unittest.mock import patch, MagicMock
from scout.core.db import ScoutDB

def test_db_initialization():
    """Verify that DB initializes with correct Config."""
    mock_config = MagicMock()
    mock_config.app.supabase_url = "https://mock.supabase.co"
    mock_config.app.supabase_key = "mock-key"
    
    with patch("scout.core.db.config", mock_config):
        with patch("scout.core.db.create_client") as mock_create_client:
            ScoutDB()
            # Verify client was created
            mock_create_client.assert_called_once_with("https://mock.supabase.co", "mock-key")

def test_is_processed_logic():
    """Verify that is_processed correctly tracks post IDs through mocked Supabase client."""
    mock_config = MagicMock()
    mock_config.app.supabase_url = "https://mock.supabase.co"
    mock_config.app.supabase_key = "mock-key"
    
    with patch("scout.core.db.config", mock_config):
        with patch("scout.core.db.create_client") as mock_create_client:
            # Set up mock response
            mock_client = MagicMock()
            mock_create_client.return_value = mock_client
            
            db = ScoutDB()
            
            test_id = "test_post_123"
            
            # 1. Should not be processed initially
            mock_response = MagicMock()
            mock_response.data = []
            mock_client.table().select().eq().limit().execute.return_value = mock_response
            
            assert db.is_processed(test_id) is False
            
            # 2. Mark as processed
            db.mark_processed(test_id, "test_intent", True)
            mock_client.table().upsert.assert_called()
            
            # 3. Simulate it being processed
            mock_response.data = [{"post_id": test_id}]
            mock_client.table().select().eq().limit().execute.return_value = mock_response
            
            assert db.is_processed(test_id) is True
