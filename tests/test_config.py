import pytest
from unittest.mock import patch, MagicMock
import os
from scout.core.system import SystemManager

def test_save_settings_preserves_auth_hash(temp_env_dir):
    """Verify that saving settings doesn't wipe AUTH_PASSWORD_HASH."""
    env_path = temp_env_dir / ".env"
    
    # 1. Setup mock .env with an auth hash
    initial_content = (
        "AUTH_PASSWORD_HASH=secret_hash\n"
        "OPENROUTER_API_KEY=old_key\n"
    )
    env_path.write_text(initial_content)
    
    # 2. Mock the config object to prevent it from trying to save its own state
    mock_config = MagicMock()
    
    # 3. Initialize SystemManager and patch the env path logic
    # We patch the path calculation inside SystemManager.save_settings
    with patch("scout.core.system.os.path.join", return_value=str(env_path)):
        with patch("scout.core.system.config", mock_config):
            manager = SystemManager()
            
            new_settings = {"reddit_username": "new_user"}
            new_api_keys = {"openrouter_api_key": "new_key"}
            
            success = manager.save_settings(new_settings, new_api_keys)
            
            assert success is True
            
    # 4. Verify results
    result_content = env_path.read_text()
    
    # Auth hash MUST be preserved
    assert "AUTH_PASSWORD_HASH=secret_hash" in result_content
    # New key MUST be updated
    assert "OPENROUTER_API_KEY=new_key" in result_content
    # New username MUST be added
    assert "REDDIT_USERNAME=new_user" in result_content
