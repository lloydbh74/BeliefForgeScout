import os
from dataclasses import dataclass
from typing import List, Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

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
