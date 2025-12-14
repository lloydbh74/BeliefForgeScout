"""
Telegram bot for human-in-the-loop reply approval.

Provides interactive interface for:
- Approving/rejecting generated replies
- Bot status and control commands
- Queue management
- Real-time notifications
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes, MessageHandler, filters
)
from sqlalchemy.orm import Session

from src.db.models import ReplyQueue
from src.db.connection import get_db
from src.config.loader import get_config
from src.filtering.deduplication import DeduplicationManager

logger = logging.getLogger(__name__)


class TelegramApprovalBot:
    """Telegram bot for reply approval and bot control"""

    def __init__(self):
        """Initialize Telegram bot"""
        self.bot_config, self.env_config = get_config()
        self.token = self.env_config.telegram_bot_token
        self.chat_id = self.env_config.telegram_chat_id

        self.application: Optional[Application] = None
        self.dedup_manager = DeduplicationManager()

    async def initialize(self):
        """Initialize bot application"""
        self.application = Application.builder().token(self.token).build()

        # Register command handlers
        self.application.add_handler(CommandHandler("start", self.cmd_start))
        self.application.add_handler(CommandHandler("status", self.cmd_status))
        self.application.add_handler(CommandHandler("queue", self.cmd_queue))
        self.application.add_handler(CommandHandler("stats", self.cmd_stats))
        self.application.add_handler(CommandHandler("help", self.cmd_help))

        # Register callback handlers for inline buttons
        self.application.add_handler(CallbackQueryHandler(self.handle_approval_callback))

        logger.info("Telegram bot initialized")

    async def start(self):
        """Start the bot"""
        if not self.application:
            await self.initialize()

        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()

        logger.info("Telegram bot started")

    async def stop(self):
        """Stop the bot"""
        if self.application:
            # Only stop application components that were started
            # We don't start the updater, so we don't need to stop it
            try:
                if self.application.updater.running:
                    await self.application.updater.stop()
            except:
                pass  # Updater not running

            try:
                await self.application.stop()
            except:
                pass

            try:
                await self.application.shutdown()
            except:
                pass

        logger.info("Telegram bot stopped")

    # Command handlers
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        welcome_message = """
🤖 *Social Reply Bot for Belief Forge*

I help you review and approve AI-generated replies to tweets.

*Commands:*
/status - Bot status
/queue - View pending replies
/stats - Reply statistics
/help - Show this help

When a new reply is ready, I'll send it to you for approval with ✅ Approve and ❌ Reject buttons.
"""
        await update.message.reply_text(welcome_message, parse_mode='Markdown')

    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        with get_db() as session:
            # Count pending replies
            pending_count = session.query(ReplyQueue).filter(
                ReplyQueue.status == 'pending'
            ).count()

            # Get recent stats
            dedup_stats = self.dedup_manager.get_reply_stats(session)

            status_message = f"""
📊 *Bot Status*

*Pending Approvals:* {pending_count}

*Rate Limits:*
• Hour: {dedup_stats['hour_count']}/{dedup_stats['hour_limit']} ({dedup_stats['hour_remaining']} remaining)
• Day: {dedup_stats['day_count']}/{dedup_stats['day_limit']} ({dedup_stats['day_remaining']} remaining)

*History (7 days):*
• Replies: {dedup_stats['week_count']}
• Unique authors: {dedup_stats['unique_authors_7d']}
"""

        await update.message.reply_text(status_message, parse_mode='Markdown')

    async def cmd_queue(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /queue command"""
        with get_db() as session:
            pending_replies = session.query(ReplyQueue).filter(
                ReplyQueue.status == 'pending'
            ).order_by(
                ReplyQueue.created_at.desc()
            ).limit(5).all()

            if not pending_replies:
                await update.message.reply_text("✅ No pending replies in queue")
                return

            message = f"📋 *Pending Replies ({len(pending_replies)})*\n\n"

            for reply in pending_replies:
                message += f"*Tweet by @{reply.tweet_author}*\n"
                message += f"Priority: {reply.commercial_priority}\n"
                message += f"Score: {reply.reply_score:.1f}\n"
                message += f"Created: {reply.created_at.strftime('%H:%M')}\n\n"

        await update.message.reply_text(message, parse_mode='Markdown')

    async def cmd_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command"""
        with get_db() as session:
            dedup_stats = self.dedup_manager.get_reply_stats(session)

            # Count by status
            pending = session.query(ReplyQueue).filter(ReplyQueue.status == 'pending').count()
            approved = session.query(ReplyQueue).filter(ReplyQueue.status == 'approved').count()
            rejected = session.query(ReplyQueue).filter(ReplyQueue.status == 'rejected').count()
            posted = session.query(ReplyQueue).filter(ReplyQueue.status == 'posted').count()

            stats_message = f"""
📈 *Reply Statistics*

*Queue Status:*
• Pending: {pending}
• Approved: {approved}
• Rejected: {rejected}
• Posted: {posted}

*Recent Activity:*
• Last hour: {dedup_stats['hour_count']} replies
• Last day: {dedup_stats['day_count']} replies
• Last week: {dedup_stats['week_count']} replies

*All Time:*
• Total: {dedup_stats['total_count']} replies
• Unique authors (7d): {dedup_stats['unique_authors_7d']}
"""

        await update.message.reply_text(stats_message, parse_mode='Markdown')

    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_message = """
🤖 *Social Reply Bot Help*

*Commands:*
/start - Start bot and show welcome
/status - Current bot status
/queue - View pending replies
/stats - Reply statistics
/help - Show this help

*Approval Process:*
1. Bot scrapes tweets and generates replies
2. You receive notification with reply preview
3. Click ✅ to approve or ❌ to reject
4. Approved replies are queued for posting

*Priority Levels:*
🔴 Critical - Imposter syndrome, self-doubt
🟠 High - Brand clarity, positioning
🟡 Medium-High - Growth frustration
🟢 Medium - General challenges

*Tips:*
• Review voice guidelines before approving
• Check for British English (colour, realise)
• Ensure NO exclamation marks
• Keep replies under 100 characters
"""

        await update.message.reply_text(help_message, parse_mode='Markdown')

    async def handle_approval_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle approval button clicks"""
        query = update.callback_query
        await query.answer()

        # Parse callback data: "approve_{id}" or "reject_{id}"
        action, reply_id = query.data.split('_', 1)
        reply_id = int(reply_id)

        with get_db() as session:
            reply = session.query(ReplyQueue).filter(ReplyQueue.id == reply_id).first()

            if not reply:
                await query.edit_message_text("❌ Reply not found (may have been deleted)")
                return

            if action == "approve":
                reply.status = 'approved'
                reply.approved_by = query.from_user.username
                reply.approved_at = datetime.utcnow()
                session.commit()

                await query.edit_message_text(
                    f"✅ *Approved*\n\n"
                    f"Tweet: {reply.tweet_text[:100]}...\n\n"
                    f"Reply: {reply.reply_text}\n\n"
                    f"Approved by @{reply.approved_by}",
                    parse_mode='Markdown'
                )

                logger.info(f"Reply {reply_id} approved by @{query.from_user.username}")

            elif action == "reject":
                reply.status = 'rejected'
                reply.approved_by = query.from_user.username
                reply.approved_at = datetime.utcnow()
                reply.rejection_reason = "Rejected by human reviewer"
                session.commit()

                await query.edit_message_text(
                    f"❌ *Rejected*\n\n"
                    f"Tweet: {reply.tweet_text[:100]}...\n\n"
                    f"Reply: {reply.reply_text}\n\n"
                    f"Rejected by @{reply.approved_by}",
                    parse_mode='Markdown'
                )

                logger.info(f"Reply {reply_id} rejected by @{query.from_user.username}")

    # Notification methods
    async def send_approval_request(self, reply_queue_item: ReplyQueue):
        """
        Send approval request for a generated reply.

        Args:
            reply_queue_item: ReplyQueue database record
        """
        if not self.application:
            await self.initialize()

        # Priority emoji
        priority_emoji = {
            'critical': '🔴',
            'high': '🟠',
            'medium_high': '🟡',
            'medium': '🟢',
            'baseline': '⚪'
        }.get(reply_queue_item.commercial_priority, '⚪')

        # Build message
        message = f"""
{priority_emoji} *New Reply Ready for Approval*

*Original Tweet:*
@{reply_queue_item.tweet_author}: "{reply_queue_item.tweet_text[:150]}..."

*Proposed Reply:*
"{reply_queue_item.reply_text}"

*Metrics:*
• Score: {reply_queue_item.reply_score:.1f}
• Priority: {reply_queue_item.commercial_priority}
• Voice score: {reply_queue_item.voice_validation_score:.1f}
• Characters: {len(reply_queue_item.reply_text)}

*Tweet Link:*
https://twitter.com/{reply_queue_item.tweet_author}/status/{reply_queue_item.tweet_id}
"""

        # Create inline keyboard
        keyboard = [
            [
                InlineKeyboardButton("✅ Approve", callback_data=f"approve_{reply_queue_item.id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"reject_{reply_queue_item.id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Send message
        await self.application.bot.send_message(
            chat_id=self.chat_id,
            text=message,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

        logger.info(f"Sent approval request for reply {reply_queue_item.id} to Telegram")

    async def send_notification(self, message: str, parse_mode: str = 'Markdown'):
        """
        Send a general notification.

        Args:
            message: Notification message
            parse_mode: Parse mode (Markdown or HTML)
        """
        if not self.application:
            await self.initialize()

        await self.application.bot.send_message(
            chat_id=self.chat_id,
            text=message,
            parse_mode=parse_mode
        )

    async def send_error_alert(self, error_message: str, context: Optional[str] = None):
        """
        Send error alert.

        Args:
            error_message: Error message
            context: Optional context information
        """
        message = f"🚨 *Error Alert*\n\n{error_message}"

        if context:
            message += f"\n\n*Context:*\n{context}"

        await self.send_notification(message)
        logger.error(f"Sent error alert to Telegram: {error_message}")

    async def send_daily_summary(self, stats: Dict[str, Any]):
        """
        Send daily summary.

        Args:
            stats: Statistics dictionary
        """
        message = f"""
📊 *Daily Summary*

*Replies Today:*
• Generated: {stats.get('generated', 0)}
• Approved: {stats.get('approved', 0)}
• Rejected: {stats.get('rejected', 0)}
• Posted: {stats.get('posted', 0)}

*Quality Metrics:*
• Avg voice score: {stats.get('avg_voice_score', 0):.1f}
• Avg character count: {stats.get('avg_chars', 0):.0f}

*Engagement:*
• Critical priority: {stats.get('critical_count', 0)}
• High priority: {stats.get('high_count', 0)}

*Costs:*
• API cost: ${stats.get('api_cost', 0):.2f}
"""

        await self.send_notification(message)
        logger.info("Sent daily summary to Telegram")


# Global bot instance
_bot_instance: Optional[TelegramApprovalBot] = None


def get_telegram_bot() -> TelegramApprovalBot:
    """Get global Telegram bot instance (singleton)"""
    global _bot_instance

    if _bot_instance is None:
        _bot_instance = TelegramApprovalBot()

    return _bot_instance


if __name__ == "__main__":
    # Test Telegram bot
    import sys
    import asyncio

    logging.basicConfig(level=logging.INFO)

    async def test_bot():
        """Test bot functionality"""
        bot = get_telegram_bot()

        try:
            logger.info("Testing Telegram bot...")

            await bot.initialize()
            logger.info("✓ Bot initialized")

            # Send test message
            await bot.send_notification("🤖 Test message from Social Reply Bot")
            logger.info("✓ Test message sent")

            logger.info("\n✓ Telegram bot test successful!")
            logger.info(f"Bot token configured: {bot.token[:10]}...")
            logger.info(f"Chat ID: {bot.chat_id}")

        except Exception as e:
            logger.error(f"✗ Telegram bot test failed: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
        finally:
            await bot.stop()

    # Run test
    asyncio.run(test_bot())
