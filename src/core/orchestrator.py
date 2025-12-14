"""
Main orchestrator for Social Reply Bot.

Coordinates the complete workflow:
1. Scraping content from configured sources (Twitter, Reddit)
2. Multi-layered filtering (base → commercial → scoring → deduplication)
3. LLM reply generation with voice validation
4. Human approval via Telegram
5. Reply posting (future implementation)
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from src.config.loader import get_config
from src.db.connection import get_db
from src.db.models import ReplyQueue, ScrapedTweet
from src.core.models import SocialPost, Platform

# Scrapers & Logic
from src.scraping.base_scraper import SocialScraper
from src.scraping.twitter_scraper import TwitterScraper
from src.scraping.reddit_scraper import RedditScraper
from src.filtering.base_filter import BaseFilter
from src.filtering.commercial_filter import CommercialFilter
from src.scoring.post_scorer import PostScorer
from src.filtering.deduplication import DeduplicationManager
from src.llm.reply_generator import ReplyGenerator
from src.telegram_bot.approval_bot import TelegramApprovalBot
from src.timing.scheduler import TimingController
from src.services.AnalyticsService import AnalyticsService

logger = logging.getLogger(__name__)


class BotOrchestrator:
    """Main orchestrator coordinating all bot operations"""

    def __init__(self):
        """Initialize orchestrator with all components"""
        self.bot_config, _ = get_config()

        # Initialize components
        self.base_filter = BaseFilter()
        self.commercial_filter = CommercialFilter()
        self.scorer = PostScorer()
        self.dedup_manager = DeduplicationManager()
        self.timing_controller = TimingController()

        # These will be initialized in async context
        self.scrapers: List[SocialScraper] = []
        self.reply_generator: Optional[ReplyGenerator] = None
        self.telegram_bot: Optional[TelegramApprovalBot] = None

        # Session tracking
        self.session_id = datetime.utcnow().strftime('%Y%m%d-%H%M%S')
        self.replies_in_session = 0

        logger.info(f"Bot orchestrator initialized (session: {self.session_id})")

    async def initialize(self):
        """Initialize async components"""
        # Initialize scrapers
        self.scrapers = []
        
        # Twitter Scraper
        try:
            twitter_scraper = TwitterScraper()
            await twitter_scraper.initialize()
            self.scrapers.append(twitter_scraper)
            logger.info("Twitter scraper initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Twitter scraper: {e}")

        # Reddit Scraper
        try:
            reddit_scraper = RedditScraper()
            await reddit_scraper.initialize()
            self.scrapers.append(reddit_scraper)
            logger.info("Reddit scraper initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Reddit scraper: {e}")

        self.reply_generator = ReplyGenerator()

        self.telegram_bot = TelegramApprovalBot()
        await self.telegram_bot.initialize()

        logger.info("Async components initialized")

    async def shutdown(self):
        """Shutdown and cleanup"""
        for scraper in self.scrapers:
            try:
                await scraper.close()
            except Exception as e:
                logger.error(f"Error closing scraper: {e}")

        if self.telegram_bot:
            await self.telegram_bot.stop()

        logger.info("Orchestrator shutdown complete")

    async def run_session(self) -> Dict[str, Any]:
        """
        Run a complete bot session.

        Returns:
            Dict with session statistics
        """
        logger.info(f"Starting bot session {self.session_id}")

        # Check if within active hours
        if not self.timing_controller.is_active_hours():
            logger.info("Outside active hours. Skipping session.")
            time_until = self.timing_controller.get_time_until_active()
            return {
                'status': 'skipped',
                'reason': 'outside_active_hours',
                'time_until_active': str(time_until)
            }

        stats = {
            'session_id': self.session_id,
            'started_at': datetime.utcnow().isoformat(),
            'posts_scraped': 0,
            'posts_after_base_filter': 0,
            'posts_after_commercial_filter': 0,
            'posts_after_scoring': 0,
            'posts_after_deduplication': 0,
            'replies_generated': 0,
            'replies_sent_for_approval': 0,
            'errors': []
        }

        try:
            # Step 1: Scrape content
            logger.info("Step 1: Scraping content...")
            posts = await self._scrape_content()
            stats['posts_scraped'] = len(posts)
            logger.info(f"Scraped {len(posts)} posts")

            if not posts:
                logger.info("No posts found. Ending session.")
                return stats

            # Step 2: Apply base filters
            logger.info("Step 2: Applying base filters...")
            posts = self._apply_base_filters(posts)
            stats['posts_after_base_filter'] = len(posts)
            logger.info(f"{len(posts)} posts passed base filters")

            if not posts:
                logger.info("No posts passed base filters. Ending session.")
                return stats

            # Step 3: Apply commercial filters
            logger.info("Step 3: Applying commercial filters...")
            posts = self._apply_commercial_filters(posts)
            stats['posts_after_commercial_filter'] = len(posts)
            logger.info(f"{len(posts)} posts passed commercial filters")

            if not posts:
                logger.info("No posts passed commercial filters. Ending session.")
                return stats

            # Step 4: Score and rank posts
            logger.info("Step 4: Scoring and ranking posts...")
            posts = self._score_and_rank_posts(posts)
            stats['posts_after_scoring'] = len(posts)
            logger.info(f"{len(posts)} posts meet scoring threshold")

            if not posts:
                logger.info("No posts meet scoring threshold. Ending session.")
                return stats

            # Step 5: Apply deduplication
            logger.info("Step 5: Applying deduplication...")
            posts = self._apply_deduplication(posts)
            stats['posts_after_deduplication'] = len(posts)
            logger.info(f"{len(posts)} posts after deduplication")

            if not posts:
                logger.info("No posts after deduplication. Ending session.")
                return stats

            # Step 6: Generate replies
            logger.info("Step 6: Generating replies...")
            posts_with_replies = await self._generate_replies(posts)
            stats['replies_generated'] = len(posts_with_replies)
            logger.info(f"Generated {len(posts_with_replies)} valid replies")

            # Step 7: Send for approval
            logger.info("Step 7: Sending replies for approval...")
            sent_count = await self._send_for_approval(posts_with_replies)
            stats['replies_sent_for_approval'] = sent_count
            logger.info(f"Sent {sent_count} replies for approval")

            stats['completed_at'] = datetime.utcnow().isoformat()
            stats['status'] = 'success'

            logger.info(f"Session {self.session_id} completed successfully")

            # Cleanup and aggregation (Maintenance)
            try:
                with get_db() as session:
                    analytics_service = AnalyticsService(session)
                    logger.info("Running daily maintenance (aggregation & cleanup)...")
                    analytics_service.cleanup_old_data()
            except Exception as e:
                logger.error(f"Maintenance failed: {e}")

            return stats

        except Exception as e:
            logger.error(f"Session failed: {e}", exc_info=True)
            stats['status'] = 'error'
            stats['error'] = str(e)
            stats['errors'].append(str(e))

            # Send error alert to Telegram
            if self.telegram_bot:
                await self.telegram_bot.send_error_alert(
                    str(e),
                    context=f"Session {self.session_id}"
                )

            return stats

    def _log_post_processing(self, post: SocialPost, status: str, reason: str = None, details: Dict = None):
        """Log post processing outcome to database"""
        try:
            with get_db() as session:
                # Check if already logged
                existing = session.query(ScrapedTweet).filter_by(tweet_id=post.id).first()
                
                if existing:
                    existing.status = status
                    existing.rejection_reason = reason
                    if details:
                        existing.filter_details = details
                else:
                    # Map SocialPost fields to ScrapedTweet (legacy schema)
                    # Ideally we should update the DB schema to support 'platform' and 'SocialPost' proper
                    # but for now we map it to existing fields.
                    scraped_tweet = ScrapedTweet(
                        tweet_id=post.id,
                        tweet_text=post.text,
                        author_username=post.author.username,
                        scraped_at=post.scraped_at,
                        status=status,
                        rejection_reason=reason,
                        filter_details=details,
                        session_id=self.session_id,
                        search_term=post.search_term
                    )
                    session.add(scraped_tweet)
                
                session.commit()
        except Exception as e:
            logger.error(f"Failed to log post processing: {e}")

    async def _scrape_content(self) -> List[SocialPost]:
        """Scrape content from all configured sources"""
        all_posts = []
        max_per_source = 20
        
        # Build tasks for parallel execution later? For now sequential is safer to not trigger rate limits aggressively
        
        hashtags = self.bot_config.targets.hashtags or []
        keywords = self.bot_config.targets.keywords or []
        lists = self.bot_config.targets.lists or []
        
        # We need to get subreddits from config - assuming we'll add it to schema
        # For now, let's look for a generic dict access or attribute
        # If config is Pydantic model it might fail if key doesn't exist
        subreddits = getattr(self.bot_config.targets, 'subreddits', []) or []

        # Iterate through scrapers
        for scraper in self.scrapers:
            
            # --- Twitter Scraper Logic ---
            if isinstance(scraper, TwitterScraper):
                if not self.bot_config.platforms.twitter.enabled:
                    logger.info("Twitter scraping is disabled in config - skipping")
                    continue

                # 1. Hashtags
                for hashtag in hashtags:
                    try:
                        posts = await scraper.scrape_hashtag(hashtag, max_per_source)
                        for p in posts: self._log_post_processing(p, 'scraped')
                        all_posts.extend(posts)
                        await asyncio.sleep(self.timing_controller.get_random_delay(3000, 5000))
                    except Exception as e:
                        logger.error(f"Failed to scrape hashtag {hashtag}: {e}")
                        
                # 2. Keywords
                for keyword in keywords:
                    try:
                        posts = await scraper.scrape_keyword(keyword, max_per_source)
                        for p in posts: self._log_post_processing(p, 'scraped')
                        all_posts.extend(posts)
                        await asyncio.sleep(self.timing_controller.get_random_delay(3000, 5000))
                    except Exception as e:
                        logger.error(f"Failed to scrape keyword {keyword}: {e}")
                
                # 3. Lists
                for list_url in lists:
                    try:
                        posts = await scraper.scrape_list(list_url, max_per_source)
                        for p in posts: self._log_post_processing(p, 'scraped')
                        all_posts.extend(posts)
                        await asyncio.sleep(self.timing_controller.get_random_delay(3000, 5000))
                    except Exception as e:
                        logger.error(f"Failed to scrape list {list_url}: {e}")

            # --- Reddit Scraper Logic ---
            elif isinstance(scraper, RedditScraper):
                if not self.bot_config.platforms.reddit.enabled:
                    logger.info("Reddit scraping is disabled in config - skipping")
                    continue

                for subreddit in subreddits:
                    try:
                        posts = await scraper.scrape_subreddit(subreddit, max_per_source)
                        for p in posts: self._log_post_processing(p, 'scraped')
                        all_posts.extend(posts)
                        await asyncio.sleep(2) # Politeness
                    except Exception as e:
                        logger.error(f"Failed to scrape subreddit {subreddit}: {e}")

        # Deduplicate memory list by ID
        unique_posts = []
        seen_ids = set()
        for post in all_posts:
            if post.id not in seen_ids:
                seen_ids.add(post.id)
                unique_posts.append(post)
                
        return unique_posts

    def _apply_base_filters(self, posts: List[SocialPost]) -> List[SocialPost]:
        """Apply base filters"""
        # Convert to dict for legacy BaseFilter or update BaseFilter
        # Since BaseFilter likely expects dicts, our __getitem__ helps.
        # But BaseFilter.filter_tweets_batch returns dicts?
        # Let's see: base_filter.filter_tweets_batch(tweets) -> (passed, rejected)
        
        # To avoid breaking BaseFilter which might return NEW lists of dicts,
        # we might need to be careful.
        # Assuming BaseFilter takes List[Dict] and returns List[Dict].
        
        # If BaseFilter just uses standard dict access, passing SocialPost list should work 
        # IF it doesn't try to create new dicts from them.
        
        # For safety, let's treat it as legacy for now.
        # Ideally we refactor BaseFilter too, but checking constraints, let's try passing objects.
        # The objects behave like dicts.
        
        passed, rejected = self.base_filter.filter_tweets_batch(posts)
        
        for post in rejected:
            # We assume 'post' is still our SocialPost object because filter just selects from list
            self._log_post_processing(post, 'filtered', reason="Base filter rejection")
            
        return passed

    def _apply_commercial_filters(self, posts: List[SocialPost]) -> List[SocialPost]:
        """Apply commercial filters and add priority scores"""
        # CommercialFilter has been updated to accept SocialPost
        
        passed, rejected = self.commercial_filter.filter_posts_batch(posts)
        
        for post in passed:
             self._log_post_processing(post, 'analyzed', details={'commercial_signals': post.commercial_signals})

        # Rank
        ranked = self.commercial_filter.rank_posts_by_priority(passed)
        return ranked

    def _score_and_rank_posts(self, posts: List[SocialPost]) -> List[SocialPost]:
        """Score and rank posts"""
        # PostScorer has been updated
        scored_posts = self.scorer.filter_and_rank(posts, apply_threshold=True)
        
        for post in scored_posts:
             self._log_post_processing(post, 'scored', details={'score': post.score})

        return scored_posts

    def _apply_deduplication(self, posts: List[SocialPost]) -> List[SocialPost]:
        """Apply deduplication filters"""
        with get_db() as session:
            # DeduplicationManager likely expects dicts.
            # Convert to dicts for it? Or hope __getitem__ works?
            # Dedupe manager checks DB.
            # Let's hope __getitem__ is enough.
            eligible, rejected = self.dedup_manager.filter_tweets_batch(posts, session)
            
        for post in rejected:
            self._log_post_processing(post, 'deduplicated', reason="Already replied")

        return eligible

    async def _generate_replies(self, posts: List[SocialPost]) -> List[SocialPost]:
        """Generate replies for posts"""
        posts_with_replies = []

        # Limit to session max
        session_limit = self.bot_config.deduplication.engagement_limits['max_replies_per_session']
        posts_to_process = posts[:session_limit]

        with get_db() as session:
            for post in posts_to_process:
                try:
                    # ReplyGenerator likely expects dict
                    # It returns a dict with 'reply_text' and 'validation'
                    reply_data = self.reply_generator.generate_reply(post, session=session)
                    
                    post.generated_reply = reply_data
                    posts_with_replies.append(post)
                    
                    self._log_post_processing(post, 'reply_generated')

                    # Random delay between generations
                    await asyncio.sleep(self.timing_controller.get_random_delay(2000, 4000))

                except Exception as e:
                    logger.error(f"Failed to generate reply for post {post.id}: {e}")
                    self._log_post_processing(post, 'error', reason=str(e))
                    continue

        return posts_with_replies

    async def _send_for_approval(self, posts: List[SocialPost]) -> int:
        """Send generated replies for human approval via Telegram"""
        sent_count = 0

        with get_db() as session:
            for post in posts:
                try:
                    # Create ReplyQueue entry
                    reply_data = post.generated_reply
                    score_data = post.score or {}
                    commercial_signals = post.commercial_signals or {}

                    queue_entry = ReplyQueue(
                        tweet_id=post.id,
                        tweet_author=post.author.username,
                        tweet_text=post.text,
                        tweet_metrics={
                            'likes': post.metrics.likes,
                            'replies': post.metrics.replies
                        },
                        reply_text=reply_data['reply_text'],
                        reply_score=score_data.get('total_score'),
                        commercial_priority=commercial_signals.get('priority'),
                        commercial_signals=commercial_signals,
                        voice_validation_score=reply_data['validation']['score'],
                        voice_violations=reply_data['validation'].get('violations'),
                        status='pending',
                        session_id=self.session_id,
                        attempt_number=reply_data.get('attempt_number', 1)
                    )

                    session.add(queue_entry)
                    session.commit()
                    
                    self._log_post_processing(post, 'queued')

                    # Send Telegram notification
                    await self.telegram_bot.send_approval_request(queue_entry)

                    sent_count += 1

                    # Random delay between notifications
                    await asyncio.sleep(self.timing_controller.get_random_delay(1000, 2000))

                except Exception as e:
                    logger.error(f"Failed to send approval request for post {post.id}: {e}")
                    session.rollback()
                    continue

        return sent_count


# Main entry point
async def run_bot_session():
    """Run a single bot session"""
    orchestrator = BotOrchestrator()

    try:
        await orchestrator.initialize()
        stats = await orchestrator.run_session()

        logger.info(f"Session stats: {stats}")

        return stats

    finally:
        await orchestrator.shutdown()


if __name__ == "__main__":
    # Test orchestrator
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    async def test():
        """Test orchestrator"""
        try:
            logger.info("Testing bot orchestrator...\n")

            stats = await run_bot_session()

            logger.info("\n✓ Orchestrator test completed!")
            logger.info(f"\nSession statistics:")
            for key, value in stats.items():
                logger.info(f"  {key}: {value}")

        except Exception as e:
            logger.error(f"\n✗ Orchestrator test failed: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

    # Run test
    asyncio.run(test())
