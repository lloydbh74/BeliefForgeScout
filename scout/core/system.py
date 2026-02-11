import os
import logging
from typing import Dict
from scout.config import config

logger = logging.getLogger(__name__)

class SystemManager:
    """Manages system-level operations: settings, secrets, and automation."""
    
    def __init__(self, scheduler=None):
        self.scheduler = scheduler

    def save_settings(self, settings: Dict, api_keys: Dict) -> bool:
        """
        Persist dynamic settings to JSON and updates secrets in .env.
        api_keys: dict with keys like 'openrouter_api_key', 'reddit_client_id', etc.
        """
        try:
            # 1. Update JSON Settings
            config.save_settings(settings)
            
            # 2. Update memory config for secrets
            if 'openrouter_api_key' in api_keys:
                config.ai.api_key = api_keys['openrouter_api_key']
            if 'reddit_client_id' in api_keys:
                config.reddit.client_id = api_keys['reddit_client_id']
            if 'reddit_client_secret' in api_keys:
                config.reddit.client_secret = api_keys['reddit_client_secret']

            # 3. Update .env without wiping it
            env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
            env_vars = {}
            
            # Read existing
            if os.path.exists(env_path):
                with open(env_path, "r") as f:
                    for line in f:
                        if "=" in line and not line.strip().startswith("#"):
                            k, v = line.strip().split("=", 1)
                            env_vars[k] = v

            # Update with new values (Only if non-empty)
            if api_keys.get('openrouter_api_key'):
                env_vars["OPENROUTER_API_KEY"] = api_keys['openrouter_api_key']
            
            if api_keys.get('reddit_client_id'):
                env_vars["REDDIT_CLIENT_ID"] = api_keys['reddit_client_id']
                
            if api_keys.get('reddit_client_secret'):
                env_vars["REDDIT_CLIENT_SECRET"] = api_keys['reddit_client_secret']
                
            if settings.get('reddit_username'):
                env_vars["REDDIT_USERNAME"] = settings['reddit_username']
                
            if settings.get('telegram_token'):
                env_vars["TELEGRAM_BOT_TOKEN"] = settings['telegram_token']
                
            if settings.get('telegram_chat_id'):
                env_vars["TELEGRAM_CHAT_ID"] = settings['telegram_chat_id']
                
            env_vars["SCOUT_SCHEDULE_HOURS"] = "7,14,21"

            # Write back
            with open(env_path, "w") as f:
                f.write("# Generated and Managed by Scout (preserving custom keys)\n")
                for k, v in env_vars.items():
                    f.write(f"{k}={v}\n")
            
            logger.info("Settings and secrets persisted successfully.")
            return True
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
            return False

    def sync_scheduler(self, enabled: bool, job_id: str, job_func, trigger):
        """Sync the scheduler state with desired config."""
        if not self.scheduler:
            return

        if enabled:
            if not self.scheduler.get_job(job_id):
                self.scheduler.add_job(job_func, trigger, id=job_id)
                logger.info(f"Scheduler job {job_id} enabled.")
        else:
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
                logger.info(f"Scheduler job {job_id} disabled.")
