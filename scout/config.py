import os
import json
from dataclasses import dataclass
from typing import List, Optional
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path=env_path)

@dataclass
class RedditConfig:
    client_id: str
    client_secret: str
    user_agent: str
    username: Optional[str] = None
    password: Optional[str] = None

@dataclass
class AIConfig:
    api_key: str
    base_url: str = "https://openrouter.ai/api/v1"
    tier1_model: str = "google/gemini-2.0-flash-exp:free" # Evaluating newer free options
    tier2_model: str = "anthropic/claude-3-haiku"

@dataclass
class AppConfig:
    db_path: str = "scout.db"
    schedule_hours: List[int] = None
    
    def __post_init__(self):
        if self.schedule_hours is None:
            self.schedule_hours = [6, 18]

class ScoutConfig:
    def __init__(self):
        self.reddit = RedditConfig(
            client_id=os.getenv("REDDIT_CLIENT_ID", ""),
            client_secret=os.getenv("REDDIT_CLIENT_SECRET", ""),
            user_agent=os.getenv("REDDIT_USER_AGENT", "ScoutApp/1.0"),
            username=os.getenv("REDDIT_USERNAME"),
            password=os.getenv("REDDIT_PASSWORD")
        )
        
        self.ai = AIConfig(
            api_key=os.getenv("OPENROUTER_API_KEY", ""),
            base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        )
        
        schedule_str = os.getenv("SCOUT_SCHEDULE_HOURS", "6,18")
        try:
            hours = [int(h.strip()) for h in schedule_str.split(",") if h.strip().isdigit()]
        except ValueError:
            hours = [6, 18]

        self.app = AppConfig(
            db_path=os.getenv("SCOUT_DB_PATH", "scout.db"),
            schedule_hours=hours
        )
        
        # Load Dynamic Settings
        self.settings_path = os.path.join(os.path.dirname(__file__), "settings.json")
        self.settings = self._load_settings()

    def _load_settings(self) -> dict:
        """Load dynamic settings from JSON, with defaults."""
        defaults = {
            "system_prompt": "You are a helpful assistant.",
            "target_subreddits": ["entrepreneur", "python"],
            "pathfinder_keywords": ["burnout", "feeling like a fraud", "want to quit", "business failure"],
            "scheduler_enabled": False,
            "telegram_token": "",
            "telegram_chat_id": "",
            "reddit_username": ""
        }
        if os.path.exists(self.settings_path):
            try:
                with open(self.settings_path, 'r') as f:
                    loaded = json.load(f)
                    defaults.update(loaded)
            except Exception as e:
                print(f"Error loading settings.json: {e}")
        
        # Fallback: If Telegram keys are empty in JSON/Defaults, check ENV
        if not defaults.get("telegram_token"):
            defaults["telegram_token"] = os.getenv("TELEGRAM_BOT_TOKEN", "")
        if not defaults.get("telegram_chat_id"):
            defaults["telegram_chat_id"] = os.getenv("TELEGRAM_CHAT_ID", "")
        # Fallback: Reddit Username
        if not defaults.get("reddit_username"):
            defaults["reddit_username"] = os.getenv("REDDIT_USERNAME", "")

        return defaults

    def save_settings(self, new_settings: dict):
        """Save settings to JSON file."""
        self.settings.update(new_settings)
        try:
            with open(self.settings_path, 'w') as f:
                json.dump(self.settings, f, indent=4)
        except Exception as e:
            print(f"Error saving settings.json: {e}")

    def validate(self) -> List[str]:
        """Returns a list of missing configuration errors."""
        errors = []
        if not self.reddit.client_id:
            errors.append("Missing REDDIT_CLIENT_ID")
        if not self.reddit.client_secret:
            errors.append("Missing REDDIT_CLIENT_SECRET")
        if not self.ai.api_key:
            errors.append("Missing OPENROUTER_API_KEY")
        return errors

# Global instance
config = ScoutConfig()
