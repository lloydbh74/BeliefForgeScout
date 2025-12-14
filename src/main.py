"""
Main entry point for Social Reply Bot.

Runs scheduled bot sessions according to configured intervals,
respecting UK timezone active hours.
"""

import logging
import asyncio
import sys
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.loader import get_config
from src.core.orchestrator import BotOrchestrator
from src.timing.scheduler import TimingController
from src.telegram_bot.approval_bot import TelegramApprovalBot
from src.db.connection import get_db_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data/logs/bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


class BotApplication:
    """Main bot application with scheduling loop"""

    def __init__(self):
        """Initialize bot application"""
        self.bot_config, _ = get_config()
        self.timing_controller = TimingController()
        self.telegram_bot = TelegramApprovalBot()

        self.is_running = False
        self.session_count = 0

        logger.info("Bot application initialized")

    async def start(self):
        """Start the bot application"""
        logger.info("=" * 60)
        logger.info("Social Reply Bot for Belief Forge")
        logger.info("=" * 60)

        # Initialize database
        try:
            db_manager = get_db_manager()
            logger.info("✓ Database connection established")
        except Exception as e:
            logger.error(f"✗ Failed to connect to database: {e}")
            return

        # Initialize Telegram bot
        try:
            await self.telegram_bot.initialize()
            logger.info("✓ Telegram bot initialized")
        except Exception as e:
            logger.error(f"✗ Failed to initialize Telegram bot: {e}")
            # Continue without Telegram (optional)

        # Show current schedule info
        schedule_info = self.timing_controller.get_scheduling_info()
        logger.info(f"\nSchedule Information:")
        for key, value in schedule_info.items():
            logger.info(f"  {key}: {value}")

        # Start Telegram bot polling in background
        telegram_task = None
        try:
            telegram_task = asyncio.create_task(self._run_telegram_bot())
            logger.info("✓ Telegram bot polling started in background")
        except Exception as e:
            logger.error(f"✗ Failed to start Telegram polling: {e}")

        self.is_running = True

        # Send startup notification
        try:
            await self.telegram_bot.send_notification(
                "🤖 *Social Reply Bot Started*\n\n"
                f"Active hours: {self.bot_config.schedule.active_hours['start']}-"
                f"{self.bot_config.schedule.active_hours['end']} UK time\n"
                f"Check interval: {self.bot_config.schedule.check_intervals['scraping_minutes']} minutes\n\n"
                f"Use /status, /queue, /stats, or /help for commands"
            )
        except:
            pass

        # Start main loop
        try:
            await self.run_loop()
        finally:
            if telegram_task:
                telegram_task.cancel()
                try:
                    await telegram_task
                except asyncio.CancelledError:
                    pass

    async def _run_telegram_bot(self):
        """Run Telegram bot polling in background"""
        try:
            await self.telegram_bot.application.initialize()
            await self.telegram_bot.application.start()
            await self.telegram_bot.application.updater.start_polling()

            # Keep running until cancelled
            while True:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            logger.info("Telegram bot polling cancelled")
            raise
        except Exception as e:
            logger.error(f"Telegram bot polling error: {e}")

    async def run_loop(self):
        """Main scheduling loop"""
        scraping_interval = self.bot_config.schedule.check_intervals['scraping_minutes'] * 60

        logger.info(f"\n{'='*60}")
        logger.info(f"Starting main loop (check every {scraping_interval}s)")
        logger.info(f"{'='*60}\n")

        while self.is_running:
            try:
                # Check if within active hours
                if self.timing_controller.is_active_hours():
                    logger.info(f"\n--- Session {self.session_count + 1} ---")

                    # Run bot session
                    await self.run_session()

                    self.session_count += 1

                else:
                    logger.info("Outside active hours. Waiting...")
                    time_until = self.timing_controller.get_time_until_active()
                    if time_until:
                        logger.info(f"Time until next active window: {time_until}")

                # Wait for next check interval
                logger.info(f"Waiting {scraping_interval}s until next check...")
                await asyncio.sleep(scraping_interval)

            except KeyboardInterrupt:
                logger.info("\nShutdown signal received")
                break

            except Exception as e:
                logger.error(f"Error in main loop: {e}", exc_info=True)

                # Send error alert
                try:
                    await self.telegram_bot.send_error_alert(
                        str(e),
                        context="Main loop error"
                    )
                except:
                    pass

                # Wait before retrying
                await asyncio.sleep(60)

        await self.shutdown()

    async def run_session(self):
        """Run a single bot session"""
        orchestrator = BotOrchestrator()

        try:
            await orchestrator.initialize()

            start_time = datetime.utcnow()
            logger.info(f"Starting session at {start_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")

            stats = await orchestrator.run_session()

            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()

            logger.info(f"\nSession completed in {duration:.1f}s")
            logger.info(f"Status: {stats.get('status')}")
            logger.info(f"Stats:")
            logger.info(f"  - Tweets scraped: {stats.get('tweets_scraped', 0)}")
            logger.info(f"  - After base filter: {stats.get('tweets_after_base_filter', 0)}")
            logger.info(f"  - After commercial filter: {stats.get('tweets_after_commercial_filter', 0)}")
            logger.info(f"  - After scoring: {stats.get('tweets_after_scoring', 0)}")
            logger.info(f"  - After deduplication: {stats.get('tweets_after_deduplication', 0)}")
            logger.info(f"  - Replies generated: {stats.get('replies_generated', 0)}")
            logger.info(f"  - Sent for approval: {stats.get('replies_sent_for_approval', 0)}")

            # Check if we should take a break
            if orchestrator.replies_in_session > 0:
                if self.timing_controller.should_take_break(orchestrator.replies_in_session):
                    break_duration = self.timing_controller.get_break_duration()
                    logger.info(f"Taking break for {break_duration.total_seconds() / 60:.0f} minutes...")
                    await asyncio.sleep(break_duration.total_seconds())

        except Exception as e:
            logger.error(f"Session error: {e}", exc_info=True)
            raise

        finally:
            await orchestrator.shutdown()

    async def shutdown(self):
        """Shutdown bot application"""
        logger.info("\nShutting down bot application...")

        self.is_running = False

        # Stop Telegram bot
        try:
            await self.telegram_bot.send_notification(
                "🤖 *Social Reply Bot Stopped*\n\n"
                f"Total sessions: {self.session_count}"
            )
            await self.telegram_bot.stop()
        except:
            pass

        # Close database
        try:
            db_manager = get_db_manager()
            db_manager.close()
        except:
            pass

        logger.info("Shutdown complete")


async def main():
    """Main entry point"""
    app = BotApplication()

    try:
        await app.start()
    except KeyboardInterrupt:
        logger.info("\nInterrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    # Create data directories if they don't exist
    Path("data/logs").mkdir(parents=True, exist_ok=True)
    Path("data/db").mkdir(parents=True, exist_ok=True)

    # Run application
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\nGoodbye!")
        sys.exit(0)
