import pytest
import os
import shutil
import tempfile
from pathlib import Path
import sqlite3

@pytest.fixture
def temp_env_dir():
    """Create a temporary directory for .env and settings.json files."""
    tmpdir = tempfile.mkdtemp()
    yield Path(tmpdir)
    # Use ignore_errors because Windows often locks files (sqlite) briefly
    shutil.rmtree(tmpdir, ignore_errors=True)

@pytest.fixture
def mock_scout_env(temp_env_dir):
    """Create a mock .env file in the temporary directory."""
    env_content = """OPENROUTER_API_KEY=test_key
REDDIT_CLIENT_ID=test_id
REDDIT_CLIENT_SECRET=test_secret
AUTH_PASSWORD_HASH=$2b$12$test_hash
"""
    env_path = temp_env_dir / ".env"
    env_path.write_text(env_content)
    return env_path

@pytest.fixture
def mock_db_path(temp_env_dir):
    """Provide a path for a temporary sqlite database."""
    return str(temp_env_dir / "test_scout.db")
