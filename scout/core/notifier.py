import asyncio
import logging
from telegram import Bot
from ..config import config

logger = logging.getLogger(__name__)

class Notifier:
    def __init__(self):
        self.token = config.settings.get("telegram_token", "")
        self.chat_id = config.settings.get("telegram_chat_id", "")
        self.bot = None

    async def send_message(self, text: str):
        """Send a message via Telegram."""
        if not self.token or not self.chat_id:
            logger.warning("Notification skipped: Telegram Token/Chat ID missing.")
            return

        try:
            if not self.bot:
                self.bot = Bot(token=self.token)
            
            await self.bot.send_message(chat_id=self.chat_id, text=text, parse_mode='Markdown')
            logger.info("Notification sent successfully.")
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")

    def notify_mission_report(self, new_briefings: int):
        """Sync wrapper to send mission report."""
        if new_briefings == 0:
            return

        msg = f"🦅 *Scout Mission Report*\n\nFound *{new_briefings}* new opportunities.\nCheck the dashboard to review."
        
        # Asyncio handling for sync context
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        loop.run_until_complete(self.send_message(msg))
