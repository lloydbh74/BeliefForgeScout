"""
Tweet scoring system for ranking engagement opportunities.

Implements weighted scoring based on:
- Engagement velocity (40%): Like/view ratio, reply rate, tweet age
- User authority (30%): Follower count, verification, account maturity
- Timing (20%): Golden window (2-12 hours), UK active hours alignment
- Discussion opportunity (10%): Questions, hashtags, substantive content
"""

import logging
import math
from typing import Dict, Any, List, Tuple
from datetime import datetime, timedelta
import pytz

from src.config.loader import get_config

logger = logging.getLogger(__name__)


class TweetScorer:
    """Scores tweets based on engagement opportunity using weighted formula"""

    def __init__(self):
        """Initialize tweet scorer with configuration"""
        self.bot_config, _ = get_config()
        self.scoring = self.bot_config.scoring
        self.weights = self.scoring.weights
        self.thresholds = self.scoring.thresholds

        # UK timezone for timing calculations
        self.uk_tz = pytz.timezone(self.bot_config.schedule.timezone)

    def score_tweet(self, tweet: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate comprehensive score for a tweet.

        Args:
            tweet: Tweet data dictionary

        Returns:
            Dictionary with scoring breakdown:
            {
                'total_score': float,
                'engagement_velocity_score': float,
                'user_authority_score': float,
                'timing_score': float,
                'discussion_score': float,
                'meets_threshold': bool,
                'reasoning': str
            }
        """
        # Calculate component scores
        velocity_score = self._score_engagement_velocity(tweet)
        authority_score = self._score_user_authority(tweet)
        timing_score = self._score_timing(tweet)
        discussion_score = self._score_discussion_opportunity(tweet)

        # Apply weights
        weighted_velocity = velocity_score * self.weights['engagement_velocity']
        weighted_authority = authority_score * self.weights['user_authority']
        weighted_timing = timing_score * self.weights['timing_score']
        weighted_discussion = discussion_score * self.weights['discussion_opportunity']

        # Total score (0-100)
        total_score = (
            weighted_velocity +
            weighted_authority +
            weighted_timing +
            weighted_discussion
        )

        # Apply commercial multiplier if available
        if 'commercial_signals' in tweet:
            commercial_multiplier = tweet['commercial_signals'].get('multiplier', 1.0)
            total_score = total_score * commercial_multiplier

        # Cap at 100
        total_score = min(total_score, 100)

        meets_threshold = total_score >= self.thresholds['minimum_score']

        scoring_result = {
            'total_score': round(total_score, 2),
            'engagement_velocity_score': round(velocity_score, 2),
            'user_authority_score': round(authority_score, 2),
            'timing_score': round(timing_score, 2),
            'discussion_score': round(discussion_score, 2),
            'meets_threshold': meets_threshold,
            'reasoning': self._generate_reasoning(
                total_score, velocity_score, authority_score, timing_score, discussion_score, meets_threshold
            )
        }

        return scoring_result

    def _score_engagement_velocity(self, tweet: Dict[str, Any]) -> float:
        """
        Score engagement velocity (0-100).

        Factors:
        - Like/impression ratio (if available)
        - Reply rate relative to likes
        - Tweet age (fresher = higher velocity)
        """
        metrics = tweet.get('public_metrics', {})
        likes = metrics.get('like_count', 0)
        replies = metrics.get('reply_count', 0)
        retweets = metrics.get('retweet_count', 0)
        impressions = metrics.get('impression_count', 0)

        score = 0

        # Like/impression ratio (0-40 points)
        if impressions > 0:
            engagement_rate = likes / impressions
            score += min(engagement_rate * 1000, 40)  # Cap at 40
        else:
            # Fallback: absolute like count (logarithmic scale)
            if likes > 0:
                score += min(math.log10(likes + 1) * 15, 40)

        # Reply rate (0-30 points)
        if likes > 0:
            reply_rate = replies / likes
            score += min(reply_rate * 100, 30)

        # Freshness bonus (0-30 points)
        # Peak velocity at 2-6 hours, declining after
        age_hours = self._calculate_tweet_age_hours(tweet)
        if 2 <= age_hours <= 6:
            score += 30
        elif 6 < age_hours <= 12:
            score += 20
        elif age_hours < 2:
            score += 10  # Too fresh, not enough signal
        else:
            score += 5  # Too old, declining velocity

        return min(score, 100)

    def _score_user_authority(self, tweet: Dict[str, Any]) -> float:
        """
        Score user authority (0-100).

        Factors:
        - Follower count (logarithmic scale)
        - Verification status
        - Account age/maturity
        """
        author = tweet.get('author', {})
        followers = author.get('followers_count', 0)
        verified = author.get('verified', False)

        score = 0

        # Follower count (0-60 points, logarithmic)
        if followers > 0:
            # Log scale: 500 followers = 27, 5000 = 37, 50000 = 47
            follower_score = math.log10(followers + 1) * 10
            score += min(follower_score, 60)

        # Verification bonus (20 points)
        if verified:
            score += 20

        # Account maturity bonus (0-20 points)
        # If created_at available, give points for older accounts
        created_at = author.get('created_at')
        if created_at:
            try:
                created_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                account_age_days = (datetime.now(pytz.utc) - created_date).days

                if account_age_days > 730:  # 2+ years
                    score += 20
                elif account_age_days > 365:  # 1-2 years
                    score += 15
                elif account_age_days > 180:  # 6-12 months
                    score += 10
                elif account_age_days > 90:  # 3-6 months
                    score += 5
            except:
                pass

        return min(score, 100)

    def _score_timing(self, tweet: Dict[str, Any]) -> float:
        """
        Score timing opportunity (0-100).

        Factors:
        - Golden window (2-12 hours old)
        - UK active hours alignment
        - Day of week (weekdays slightly better)
        """
        score = 0

        # Tweet age score (0-60 points)
        age_hours = self._calculate_tweet_age_hours(tweet)

        if 2 <= age_hours <= 4:
            score += 60  # Perfect timing
        elif 4 < age_hours <= 8:
            score += 50  # Good timing
        elif 8 < age_hours <= 12:
            score += 40  # Acceptable timing
        elif age_hours < 2:
            score += 20  # Too early
        else:
            score += 10  # Too late

        # UK active hours alignment (0-30 points)
        created_at = tweet.get('created_at')
        if created_at:
            try:
                tweet_time = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                tweet_time_uk = tweet_time.astimezone(self.uk_tz)
                hour = tweet_time_uk.hour

                # Active hours: 07:00-24:00
                active_start = int(self.bot_config.schedule.active_hours['start'].split(':')[0])
                active_end = int(self.bot_config.schedule.active_hours['end'].split(':')[0])

                if active_start <= hour < active_end:
                    # Peak hours (9-17): 30 points
                    if 9 <= hour < 17:
                        score += 30
                    # Good hours (7-9, 17-21): 25 points
                    elif (7 <= hour < 9) or (17 <= hour < 21):
                        score += 25
                    # Off-peak but active (21-24): 20 points
                    else:
                        score += 20
                else:
                    score += 5  # Outside active hours
            except:
                score += 15  # Default if parsing fails

        # Weekday bonus (0-10 points)
        if created_at:
            try:
                tweet_time = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                weekday = tweet_time.weekday()

                if 0 <= weekday <= 4:  # Monday-Friday
                    score += 10
                else:  # Weekend
                    score += 5
            except:
                pass

        return min(score, 100)

    def _score_discussion_opportunity(self, tweet: Dict[str, Any]) -> float:
        """
        Score discussion opportunity (0-100).

        Factors:
        - Contains questions
        - Target hashtags present
        - Substantive length
        - Reply count sweet spot (3-20)
        """
        text = tweet.get('text', '')
        metrics = tweet.get('public_metrics', {})
        replies = metrics.get('reply_count', 0)

        score = 0

        # Question marks (0-30 points)
        question_count = text.count('?')
        if question_count > 0:
            score += min(question_count * 15, 30)

        # Target hashtags (0-20 points)
        text_lower = text.lower()
        target_hashtags = self.bot_config.targets.hashtags
        hashtag_matches = sum(1 for tag in target_hashtags if tag.lower() in text_lower)
        score += min(hashtag_matches * 10, 20)

        # Substantive length (0-25 points)
        text_length = len(text)
        if 100 <= text_length <= 280:
            score += 25
        elif 50 <= text_length < 100:
            score += 15
        else:
            score += 5

        # Reply count sweet spot (0-25 points)
        if 3 <= replies <= 10:
            score += 25  # Perfect: conversation started but not overwhelming
        elif 10 < replies <= 20:
            score += 20  # Good: active discussion
        elif replies < 3:
            score += 10  # Quiet: might be ignored
        else:
            score += 5  # Too busy: hard to get noticed

        return min(score, 100)

    def _calculate_tweet_age_hours(self, tweet: Dict[str, Any]) -> float:
        """Calculate tweet age in hours"""
        created_at_str = tweet.get('created_at')
        if not created_at_str:
            return 0

        try:
            created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
            now = datetime.now(pytz.utc)
            age_seconds = (now - created_at).total_seconds()
            return age_seconds / 3600
        except:
            return 0

    def _generate_reasoning(
        self,
        total: float,
        velocity: float,
        authority: float,
        timing: float,
        discussion: float,
        meets_threshold: bool
    ) -> str:
        """Generate human-readable reasoning for score"""
        threshold = self.thresholds['minimum_score']

        reasons = []

        # Overall verdict
        if meets_threshold:
            reasons.append(f"Score: {total:.1f}/{threshold} ✓")
        else:
            reasons.append(f"Score: {total:.1f}/{threshold} ✗")

        # Component analysis
        if velocity >= 70:
            reasons.append("high engagement velocity")
        elif velocity >= 50:
            reasons.append("moderate engagement velocity")
        else:
            reasons.append("low engagement velocity")

        if authority >= 70:
            reasons.append("authoritative user")
        elif authority >= 50:
            reasons.append("established user")
        else:
            reasons.append("emerging user")

        if timing >= 70:
            reasons.append("optimal timing window")
        elif timing >= 50:
            reasons.append("acceptable timing")
        else:
            reasons.append("suboptimal timing")

        if discussion >= 70:
            reasons.append("strong discussion opportunity")
        elif discussion >= 50:
            reasons.append("moderate discussion potential")

        return ". ".join(reasons) + "."

    def score_tweets_batch(self, tweets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Score a batch of tweets and add scoring data.

        Args:
            tweets: List of tweet dictionaries

        Returns:
            List of tweets with 'score' key added
        """
        scored_tweets = []

        for tweet in tweets:
            score_data = self.score_tweet(tweet)
            tweet['score'] = score_data
            scored_tweets.append(tweet)

        return scored_tweets

    def filter_and_rank(
        self,
        tweets: List[Dict[str, Any]],
        apply_threshold: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Score, filter, and rank tweets.

        Args:
            tweets: List of tweet dictionaries
            apply_threshold: Whether to filter by minimum score threshold

        Returns:
            Sorted list of tweets (highest score first)
        """
        # Score all tweets
        scored_tweets = self.score_tweets_batch(tweets)

        # Filter by threshold if enabled
        if apply_threshold:
            min_score = self.thresholds['minimum_score']
            scored_tweets = [t for t in scored_tweets if t['score']['meets_threshold']]
            logger.info(f"Scoring: {len(scored_tweets)}/{len(tweets)} tweets meet threshold ({min_score})")

        # Sort by total score (descending)
        sorted_tweets = sorted(
            scored_tweets,
            key=lambda t: t['score']['total_score'],
            reverse=True
        )

        return sorted_tweets


# Convenience functions
def score_tweet(tweet: Dict[str, Any]) -> Dict[str, Any]:
    """Score a single tweet"""
    scorer = TweetScorer()
    return scorer.score_tweet(tweet)


def rank_tweets(tweets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Score and rank tweets"""
    scorer = TweetScorer()
    return scorer.filter_and_rank(tweets, apply_threshold=True)


if __name__ == "__main__":
    # Test tweet scorer
    import sys

    logging.basicConfig(level=logging.INFO)

    # Test tweets
    test_tweets = [
        {
            'id': '1',
            'author': {
                'username': 'high_value_founder',
                'followers_count': 8000,
                'verified': False,
                'created_at': '2020-01-01T00:00:00Z'
            },
            'text': 'Does anyone else struggle with imposter syndrome when talking to investors? How do you overcome it?',
            'created_at': (datetime.utcnow() - timedelta(hours=4)).isoformat() + 'Z',
            'public_metrics': {'like_count': 45, 'reply_count': 8, 'retweet_count': 5, 'impression_count': 2000},
            'commercial_signals': {'priority': 'critical', 'multiplier': 3.0}
        },
        {
            'id': '2',
            'author': {
                'username': 'medium_founder',
                'followers_count': 2000,
                'verified': False,
                'created_at': '2022-06-01T00:00:00Z'
            },
            'text': 'Working on brand positioning today. It\'s harder than I thought.',
            'created_at': (datetime.utcnow() - timedelta(hours=8)).isoformat() + 'Z',
            'public_metrics': {'like_count': 15, 'reply_count': 3, 'retweet_count': 1, 'impression_count': 800},
            'commercial_signals': {'priority': 'high', 'multiplier': 2.0}
        },
        {
            'id': '3',
            'author': {
                'username': 'low_engagement',
                'followers_count': 600,
                'verified': False,
                'created_at': '2023-11-01T00:00:00Z'
            },
            'text': 'Just launched my product',
            'created_at': (datetime.utcnow() - timedelta(hours=15)).isoformat() + 'Z',
            'public_metrics': {'like_count': 3, 'reply_count': 0, 'retweet_count': 0, 'impression_count': 100},
            'commercial_signals': {'priority': 'baseline', 'multiplier': 1.0}
        }
    ]

    try:
        scorer = TweetScorer()

        logger.info("\n✓ Tweet scorer test results:\n")

        for tweet in test_tweets:
            score_data = scorer.score_tweet(tweet)
            logger.info(f"Tweet {tweet['id']}: {tweet['text'][:60]}...")
            logger.info(f"  Total Score: {score_data['total_score']}")
            logger.info(f"  - Engagement Velocity: {score_data['engagement_velocity_score']}")
            logger.info(f"  - User Authority: {score_data['user_authority_score']}")
            logger.info(f"  - Timing: {score_data['timing_score']}")
            logger.info(f"  - Discussion: {score_data['discussion_score']}")
            logger.info(f"  Meets Threshold: {score_data['meets_threshold']}")
            logger.info(f"  Reasoning: {score_data['reasoning']}\n")

        # Test ranking
        ranked = scorer.filter_and_rank(test_tweets)
        logger.info(f"Ranked tweets (highest to lowest):")
        for i, tweet in enumerate(ranked, 1):
            score = tweet['score']['total_score']
            logger.info(f"  {i}. Tweet {tweet['id']} (score: {score})")

    except Exception as e:
        logger.error(f"✗ Tweet scorer test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
