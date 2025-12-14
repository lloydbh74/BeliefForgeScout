"""
Deduplication manager for preventing duplicate replies.

Tracks reply history and enforces cooldown periods to ensure:
- No duplicate replies to same tweet
- Cooldown period between replies to same author
- Rate limiting (max replies per hour/day)
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy import func
from sqlalchemy.orm import Session

from src.db.models import RepliedTweet
from src.db.connection import get_db
from src.config.loader import get_config

logger = logging.getLogger(__name__)


class DeduplicationManager:
    """Manages deduplication logic and reply history tracking"""

    def __init__(self):
        """Initialize deduplication manager with configuration"""
        self.bot_config, _ = get_config()
        self.dedup_config = self.bot_config.deduplication

    def check_tweet_eligibility(
        self,
        tweet_id: str,
        author_username: str,
        session: Optional[Session] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if a tweet is eligible for reply (not already replied, author not on cooldown).

        Args:
            tweet_id: Tweet ID to check
            author_username: Tweet author username
            session: Database session (optional)

        Returns:
            Tuple of (is_eligible: bool, rejection_reason: Optional[str])
        """
        should_close = session is None
        if session is None:
            session = next(get_db())

        try:
            # Check if we've already replied to this tweet
            if self._has_replied_to_tweet(tweet_id, session):
                return False, f"Already replied to tweet {tweet_id}"

            # Check author cooldown
            if self._is_author_on_cooldown(author_username, session):
                return False, f"Author @{author_username} on cooldown"

            # Check rate limits (hour/day)
            hour_limit_ok, reason = self._check_rate_limits(session)
            if not hour_limit_ok:
                return False, reason

            return True, None

        finally:
            if should_close:
                session.close()

    def _has_replied_to_tweet(self, tweet_id: str, session: Session) -> bool:
        """Check if we've already replied to this tweet"""
        cutoff = datetime.utcnow() - timedelta(days=self.dedup_config.history_days)

        existing = session.query(RepliedTweet).filter(
            RepliedTweet.tweet_id == tweet_id,
            RepliedTweet.replied_at >= cutoff
        ).first()

        return existing is not None

    def _is_author_on_cooldown(self, author_username: str, session: Session) -> bool:
        """Check if author is on cooldown (recent reply)"""
        cooldown_hours = self.dedup_config.same_author_cooldown_hours
        cutoff = datetime.utcnow() - timedelta(hours=cooldown_hours)

        recent_reply = session.query(RepliedTweet).filter(
            RepliedTweet.author_username == author_username,
            RepliedTweet.replied_at >= cutoff
        ).first()

        return recent_reply is not None

    def _check_rate_limits(self, session: Session) -> Tuple[bool, Optional[str]]:
        """Check if we're within rate limits"""
        limits = self.dedup_config.engagement_limits

        # Check hourly limit
        hour_cutoff = datetime.utcnow() - timedelta(hours=1)
        hour_count = session.query(func.count(RepliedTweet.tweet_id)).filter(
            RepliedTweet.replied_at >= hour_cutoff
        ).scalar() or 0

        if hour_count >= limits['max_replies_per_hour']:
            return False, f"Hourly limit reached: {hour_count}/{limits['max_replies_per_hour']}"

        # Check daily limit
        day_cutoff = datetime.utcnow() - timedelta(days=1)
        day_count = session.query(func.count(RepliedTweet.tweet_id)).filter(
            RepliedTweet.replied_at >= day_cutoff
        ).scalar() or 0

        if day_count >= limits['max_replies_per_day']:
            return False, f"Daily limit reached: {day_count}/{limits['max_replies_per_day']}"

        return True, None

    def filter_tweets_batch(
        self,
        tweets: List[Dict[str, Any]],
        session: Optional[Session] = None
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Filter tweets for deduplication.

        Args:
            tweets: List of tweet dictionaries
            session: Database session (optional)

        Returns:
            Tuple of (eligible_tweets, rejected_tweets)
        """
        should_close = session is None
        if session is None:
            session = next(get_db())

        try:
            eligible = []
            rejected = []

            for tweet in tweets:
                tweet_id = tweet.get('id')
                author = tweet.get('author', {})
                author_username = author.get('username')

                if not tweet_id or not author_username:
                    tweet['rejection_reason'] = "Missing tweet ID or author"
                    rejected.append(tweet)
                    continue

                is_eligible, reason = self.check_tweet_eligibility(
                    tweet_id, author_username, session
                )

                if is_eligible:
                    eligible.append(tweet)
                else:
                    tweet['rejection_reason'] = reason
                    rejected.append(tweet)

            logger.info(f"Deduplication: {len(eligible)}/{len(tweets)} tweets eligible")

            return eligible, rejected

        finally:
            if should_close:
                session.close()

    def record_reply(
        self,
        tweet: Dict[str, Any],
        reply_text: str,
        score_data: Optional[Dict[str, Any]] = None,
        commercial_signals: Optional[Dict[str, Any]] = None,
        session: Optional[Session] = None
    ) -> RepliedTweet:
        """
        Record a replied tweet in the database.

        Args:
            tweet: Original tweet data
            reply_text: Text of the reply we posted
            score_data: Scoring breakdown (optional)
            commercial_signals: Commercial analysis (optional)
            session: Database session (optional)

        Returns:
            Created RepliedTweet record
        """
        should_close = session is None
        if session is None:
            session = next(get_db())

        try:
            author = tweet.get('author', {})

            replied_tweet = RepliedTweet(
                tweet_id=tweet['id'],
                author_username=author.get('username', 'unknown'),
                tweet_text=tweet.get('text'),
                replied_at=datetime.utcnow(),
                reply_text=reply_text,
                commercial_priority=commercial_signals.get('priority') if commercial_signals else None,
                score=score_data.get('total_score') if score_data else None,
                engagement_velocity=score_data.get('engagement_velocity_score') if score_data else None,
                user_authority=score_data.get('user_authority_score') if score_data else None,
                timing_score=score_data.get('timing_score') if score_data else None,
                discussion_score=score_data.get('discussion_score') if score_data else None
            )

            session.add(replied_tweet)
            session.commit()

            logger.info(f"Recorded reply to tweet {tweet['id']} by @{author.get('username')}")

            return replied_tweet

        finally:
            if should_close:
                session.close()

    def get_recent_replies(
        self,
        hours: int = 24,
        session: Optional[Session] = None
    ) -> List[RepliedTweet]:
        """
        Get recent replies within time window.

        Args:
            hours: Time window in hours
            session: Database session (optional)

        Returns:
            List of RepliedTweet records
        """
        should_close = session is None
        if session is None:
            session = next(get_db())

        try:
            cutoff = datetime.utcnow() - timedelta(hours=hours)

            replies = session.query(RepliedTweet).filter(
                RepliedTweet.replied_at >= cutoff
            ).order_by(
                RepliedTweet.replied_at.desc()
            ).all()

            return replies

        finally:
            if should_close:
                session.close()

    def get_reply_stats(self, session: Optional[Session] = None) -> Dict[str, Any]:
        """
        Get statistics about reply history.

        Args:
            session: Database session (optional)

        Returns:
            Dictionary with stats
        """
        should_close = session is None
        if session is None:
            session = next(get_db())

        try:
            now = datetime.utcnow()

            # Count replies in different time windows
            hour_count = session.query(func.count(RepliedTweet.tweet_id)).filter(
                RepliedTweet.replied_at >= now - timedelta(hours=1)
            ).scalar() or 0

            day_count = session.query(func.count(RepliedTweet.tweet_id)).filter(
                RepliedTweet.replied_at >= now - timedelta(days=1)
            ).scalar() or 0

            week_count = session.query(func.count(RepliedTweet.tweet_id)).filter(
                RepliedTweet.replied_at >= now - timedelta(days=7)
            ).scalar() or 0

            total_count = session.query(func.count(RepliedTweet.tweet_id)).scalar() or 0

            # Get unique authors replied to (7 days)
            unique_authors = session.query(func.count(func.distinct(RepliedTweet.author_username))).filter(
                RepliedTweet.replied_at >= now - timedelta(days=7)
            ).scalar() or 0

            limits = self.dedup_config.engagement_limits

            stats = {
                'hour_count': hour_count,
                'hour_limit': limits['max_replies_per_hour'],
                'hour_remaining': max(0, limits['max_replies_per_hour'] - hour_count),
                'day_count': day_count,
                'day_limit': limits['max_replies_per_day'],
                'day_remaining': max(0, limits['max_replies_per_day'] - day_count),
                'week_count': week_count,
                'total_count': total_count,
                'unique_authors_7d': unique_authors
            }

            return stats

        finally:
            if should_close:
                session.close()

    def cleanup_old_records(
        self,
        days: Optional[int] = None,
        session: Optional[Session] = None
    ) -> int:
        """
        Clean up old reply records beyond retention period.

        Args:
            days: Retention period in days (default: from config)
            session: Database session (optional)

        Returns:
            Number of records deleted
        """
        if days is None:
            days = self.dedup_config.history_days

        should_close = session is None
        if session is None:
            session = next(get_db())

        try:
            cutoff = datetime.utcnow() - timedelta(days=days)

            deleted = session.query(RepliedTweet).filter(
                RepliedTweet.replied_at < cutoff
            ).delete()

            session.commit()

            logger.info(f"Cleaned up {deleted} old reply records (older than {days} days)")

            return deleted

        finally:
            if should_close:
                session.close()


# Convenience functions
def check_eligibility(tweet_id: str, author_username: str) -> Tuple[bool, Optional[str]]:
    """Check if tweet is eligible for reply"""
    manager = DeduplicationManager()
    return manager.check_tweet_eligibility(tweet_id, author_username)


def filter_duplicates(tweets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Filter out tweets that have already been replied to"""
    manager = DeduplicationManager()
    eligible, _ = manager.filter_tweets_batch(tweets)
    return eligible


def record_reply(tweet: Dict[str, Any], reply_text: str) -> RepliedTweet:
    """Record a reply in the database"""
    manager = DeduplicationManager()
    return manager.record_reply(tweet, reply_text)


if __name__ == "__main__":
    # Test deduplication manager
    import sys

    logging.basicConfig(level=logging.INFO)

    try:
        manager = DeduplicationManager()

        # Get stats
        stats = manager.get_reply_stats()
        logger.info("\n✓ Deduplication manager test:")
        logger.info(f"  - Replies last hour: {stats['hour_count']}/{stats['hour_limit']}")
        logger.info(f"  - Replies last day: {stats['day_count']}/{stats['day_limit']}")
        logger.info(f"  - Replies last week: {stats['week_count']}")
        logger.info(f"  - Total replies: {stats['total_count']}")
        logger.info(f"  - Unique authors (7d): {stats['unique_authors_7d']}")

        # Test eligibility check
        test_tweet_id = "test_tweet_123"
        test_author = "test_author"

        is_eligible, reason = manager.check_tweet_eligibility(test_tweet_id, test_author)
        logger.info(f"\nTest eligibility check:")
        logger.info(f"  - Tweet {test_tweet_id} eligible: {is_eligible}")
        if reason:
            logger.info(f"  - Reason: {reason}")

    except Exception as e:
        logger.error(f"✗ Deduplication manager test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
