"""
Base filtering for tweet eligibility.

Applies engagement thresholds, recency checks, language detection,
and banned keyword/pattern filtering.
"""

import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta, timezone

from src.core.models import Platform
from src.config.loader import get_config

logger = logging.getLogger(__name__)


class BaseFilter:
    """Applies base filters to determine tweet eligibility"""

    def __init__(self):
        """Initialize base filter with configuration"""
        self.bot_config, _ = get_config()
        self.filters = self.bot_config.filters

    def filter_tweet(self, tweet: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Apply all base filters to a tweet.

        Args:
            tweet: Tweet data dictionary

        Returns:
            Tuple of (passes_filter: bool, rejection_reason: Optional[str])
        """
        # Engagement filters
        passes, reason = self._check_engagement(tweet)
        if not passes:
            return False, reason

        # Recency filter
        passes, reason = self._check_recency(tweet)
        if not passes:
            return False, reason

        # Language filter
        passes, reason = self._check_language(tweet)
        if not passes:
            return False, reason

        # Content quality filters
        passes, reason = self._check_content_quality(tweet)
        if not passes:
            return False, reason

        # All filters passed
        return True, None

    def _check_engagement(self, tweet: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Check engagement metrics"""
        metrics = tweet.get('metrics', {})
        author = tweet.get('author', {})
        
        # Check platform - Reddit posts often don't have follower counts available in scraped data
        # so we skip this check for Reddit to avoid false negatives.
        is_reddit = tweet.get('platform') == Platform.REDDIT
        
        if not is_reddit:
            followers = author.get('followers_count', 0)
            if followers < self.filters.engagement.min_followers:
                return False, f"Too few followers: {followers} < {self.filters.engagement.min_followers}"
            if followers > self.filters.engagement.max_followers:
                return False, f"Too many followers: {followers} > {self.filters.engagement.max_followers}"

        # Check likes/upvotes
        likes = metrics.get('likes', 0)
        if likes < self.filters.engagement.min_likes:
            return False, f"Too few likes: {likes} < {self.filters.engagement.min_likes}"

        # Check replies/comments
        replies = metrics.get('replies', 0)
        if replies < self.filters.engagement.min_replies:
             return False, f"Too few replies: {replies} < {self.filters.engagement.min_replies}"
        if replies > self.filters.engagement.max_replies:
             return False, f"Too many replies: {replies} > {self.filters.engagement.max_replies}"

        return True, None

    def _check_recency(self, tweet: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Check tweet age against recency window"""
        created_at_val = tweet.get('created_at')
        if not created_at_val:
            return False, "Missing created_at timestamp"

        try:
            # Handle datetime objects (from SocialPost) or strings (from dicts)
            if isinstance(created_at_val, datetime):
                created_at = created_at_val
            else:
                # Parse timestamp (ISO format)
                created_at = datetime.fromisoformat(created_at_val.replace('Z', '+00:00'))
            
            # Ensure timezone awareness (assume UTC if missing)
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
                
            now = datetime.now(timezone.utc)
            
            # Allow for slight clock skew or future posts (up to 5 mins)
            age_seconds = (now - created_at).total_seconds()
            
            if age_seconds < -300: # 5 mins in future
                 return False, f"Future timestamp: {created_at}"
            
            age_hours = max(0, age_seconds / 3600)

            # Check minimum age
            if age_hours < self.filters.recency.min_age_hours:
                return False, f"Too recent: {age_hours:.1f}h < {self.filters.recency.min_age_hours}h"

            # Check maximum age
            if age_hours > self.filters.recency.max_age_hours:
                return False, f"Too old: {age_hours:.1f}h > {self.filters.recency.max_age_hours}h"

            return True, None

        except Exception as e:
            logger.warning(f"Failed to parse timestamp: {e}")
            return False, f"Invalid timestamp: {created_at_str}"

    def _check_language(self, tweet: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Check tweet language"""
        language = tweet.get('language', 'unknown')
        required_language = self.filters.language.get('required', 'en')

        if language != required_language:
            return False, f"Wrong language: {language} != {required_language}"

        return True, None

    def _check_content_quality(self, tweet: Dict[str, Any]) -> Tuple[bool, Optional[str]]:

        """Check content quality (length, banned words)"""
        text = tweet.get('text', '')
        
        # Determine max length based on platform
        max_len = self.filters.content_quality.max_length
        if tweet.get('platform') == Platform.REDDIT:
            max_len = self.filters.content_quality.reddit_max_length

        # Length checks
        text_length = len(text)
        if text_length < self.filters.content_quality.min_length:
            return False, f"Too short: {text_length} < {self.filters.content_quality.min_length}"
        if text_length > max_len:
            return False, f"Too long: {text_length} > {max_len}"

        # Banned keywords
        text_lower = text.lower()
        for keyword in self.filters.content_quality.banned_keywords:
            if keyword.lower() in text_lower:
                return False, f"Banned keyword: '{keyword}'"

        # Banned patterns (regex)
        for pattern in self.filters.content_quality.banned_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return False, f"Banned pattern: '{pattern}'"

        return True, None

    def filter_tweets_batch(self, tweets: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Filter a batch of tweets.

        Args:
            tweets: List of tweet dictionaries

        Returns:
            Tuple of (passed_tweets, rejected_tweets_with_reasons)
        """
        passed = []
        rejected = []

        for tweet in tweets:
            passes, reason = self.filter_tweet(tweet)
            if passes:
                passed.append(tweet)
            else:
                tweet['rejection_reason'] = reason
                rejected.append(tweet)

        logger.info(f"Base filter: {len(passed)}/{len(tweets)} tweets passed")

        return passed, rejected

    def get_filter_stats(self, tweets: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Get statistics about filter results.

        Args:
            tweets: List of tweet dictionaries

        Returns:
            Dictionary of rejection reasons with counts
        """
        stats = {}

        for tweet in tweets:
            passes, reason = self.filter_tweet(tweet)
            if not passes:
                stats[reason] = stats.get(reason, 0) + 1

        return stats


# Convenience function
def filter_tweets(tweets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Apply base filters to a list of tweets.

    Args:
        tweets: List of tweet dictionaries

    Returns:
        List of tweets that passed all base filters
    """
    base_filter = BaseFilter()
    passed, _ = base_filter.filter_tweets_batch(tweets)
    return passed


if __name__ == "__main__":
    # Test base filter
    import sys

    logging.basicConfig(level=logging.INFO)

    # Test tweet data
    test_tweets = [
        {
            'id': '1',
            'author': {'username': 'test_user', 'followers_count': 1000},
            'text': 'Building in public is challenging but rewarding. Anyone else struggling with self-doubt?',
            'created_at': (datetime.utcnow() - timedelta(hours=6)).isoformat() + 'Z',
            'public_metrics': {'like_count': 15, 'reply_count': 5, 'retweet_count': 2},
            'language': 'en'
        },
        {
            'id': '2',
            'author': {'username': 'test_user2', 'followers_count': 200},  # Too few followers
            'text': 'Test tweet',
            'created_at': datetime.utcnow().isoformat() + 'Z',
            'public_metrics': {'like_count': 1, 'reply_count': 0, 'retweet_count': 0},
            'language': 'en'
        },
        {
            'id': '3',
            'author': {'username': 'crypto_spammer', 'followers_count': 5000},
            'text': 'Check out this amazing NFT giveaway! Limited time offer!',  # Banned keywords
            'created_at': (datetime.utcnow() - timedelta(hours=5)).isoformat() + 'Z',
            'public_metrics': {'like_count': 20, 'reply_count': 8, 'retweet_count': 5},
            'language': 'en'
        }
    ]

    try:
        base_filter = BaseFilter()
        passed, rejected = base_filter.filter_tweets_batch(test_tweets)

        logger.info(f"\n✓ Base filter test results:")
        logger.info(f"  - Passed: {len(passed)}/{len(test_tweets)} tweets")
        logger.info(f"  - Rejected: {len(rejected)}/{len(test_tweets)} tweets")

        logger.info(f"\nRejection reasons:")
        stats = base_filter.get_filter_stats(test_tweets)
        for reason, count in stats.items():
            logger.info(f"  - {reason}: {count}")

    except Exception as e:
        logger.error(f"✗ Base filter test failed: {e}")
        sys.exit(1)
