"""
Post scoring system for ranking engagement opportunities across platforms.

Implements weighted scoring based on:
- Engagement velocity (40%): Like/view ratio, reply rate, post age
- User authority (30%): Follower count, verification, account maturity
- Timing (20%): Golden window (2-12 hours), UK active hours alignment
- Discussion opportunity (10%): Questions, keywords, substantive content
"""

import logging
import math
from typing import Dict, Any, List
from datetime import datetime
import datetime as dt_module

from src.config.loader import get_config
from src.core.models import SocialPost, Platform, SocialMetrics

logger = logging.getLogger(__name__)


class PostScorer:
    """Scores social posts based on engagement opportunity using weighted formula"""

    def __init__(self):
        """Initialize post scorer with configuration"""
        self.bot_config, _ = get_config()
        self.scoring = self.bot_config.scoring
        self.weights = self.scoring.weights
        self.thresholds = self.scoring.thresholds

        # UK timezone for timing calculations
        # UK timezone for timing calculations
        # Using simplified handling without pytz for now (UTC assumption works for basic logic)
        self.uk_tz_offset = 0 # Placeholder if needed, or stick to UTC

    def score_post(self, post: SocialPost) -> Dict[str, Any]:
        """
        Calculate comprehensive score for a post.

        Args:
            post: SocialPost object

        Returns:
            Dictionary with scoring breakdown
        """
        # Calculate component scores
        velocity_score = self._score_engagement_velocity(post)
        authority_score = self._score_user_authority(post)
        timing_score = self._score_timing(post)
        discussion_score = self._score_discussion_opportunity(post)

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
        if post.commercial_signals:
            commercial_multiplier = post.commercial_signals.get('multiplier', 1.0)
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

        # Attach score to post object for convenience
        post.score = scoring_result
        
        return scoring_result

    def _score_engagement_velocity(self, post: SocialPost) -> float:
        """Score engagement velocity (0-100)"""
        metrics = post.metrics
        likes = metrics.likes
        replies = metrics.replies
        impressions = metrics.impressions

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
        age_hours = self._calculate_post_age_hours(post)
        if 2 <= age_hours <= 6:
            score += 30
        elif 6 < age_hours <= 12:
            score += 20
        elif age_hours < 2:
            score += 10
        else:
            score += 5

        return min(score, 100)

    def _score_user_authority(self, post: SocialPost) -> float:
        """Score user authority (0-100)"""
        author = post.author
        followers = author.followers_count or 0
        verified = author.is_verified

        score = 0

        # Follower count (0-60 points) - Reduced for Reddit as followers matter less
        if post.platform == Platform.REDDIT:
            # On Reddit, we might use account age or karma (if available) as proxy
            # Since we don't scrape karma securely yet, we give a baseline
            score += 30 
        else:
            if followers > 0:
                follower_score = math.log10(followers + 1) * 10
                score += min(follower_score, 60)

        # Verification bonus
        if verified:
            score += 20
            
        # Account maturity would go here if we parsed it for everyone

        return min(score, 100)

    def _score_timing(self, post: SocialPost) -> float:
        """Score timing opportunity (0-100)"""
        score = 0
        age_hours = self._calculate_post_age_hours(post)

        # Reddit posts stay relevant longer
        if post.platform == Platform.REDDIT:
            if 0.5 <= age_hours <= 12:
                score += 60
            elif 12 < age_hours <= 24:
                score += 40
            else:
                score += 20
        else:
            if 2 <= age_hours <= 6:
                score += 60
            elif 6 < age_hours <= 12:
                score += 40
            else:
                score += 20

        # UK active hours alignment
        try:
            created_at = post.created_at
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=dt_module.timezone.utc)
            else:
                created_at = created_at.astimezone(dt_module.timezone.utc)
                
            # Simplified: just use UTC hour for now or handle offset manually
            # post_time_uk = created_at.astimezone(self.uk_tz)
            post_time_uk = created_at # simplified
            hour = post_time_uk.hour

            active_start = int(self.bot_config.schedule.active_hours['start'].split(':')[0])
            active_end = int(self.bot_config.schedule.active_hours['end'].split(':')[0])

            if active_start <= hour < active_end:
                 score += 30 # Simple alignment bonus
            else:
                 score += 5
        except:
            score += 15

        return min(score, 100)

    def _score_discussion_opportunity(self, post: SocialPost) -> float:
        """Score discussion opportunity (0-100)"""
        text = post.text
        replies = post.metrics.replies

        score = 0

        # Questions (0-30)
        if '?' in text:
            score += 30

        # Length (0-25)
        length = len(text)
        if post.platform == Platform.REDDIT:
            if length > 200: 
                score += 25
            elif length > 50:
                score += 15
        else:
            if 100 <= length <= 280:
                score += 25

        # Reply count sweet spot
        if 3 <= replies <= 20:
            score += 25
        elif replies < 3:
            score += 10
        else:
            score += 5

        return min(score, 100)

    def _calculate_post_age_hours(self, post: SocialPost) -> float:
        """Calculate post age in hours"""
        try:
            created_at = post.created_at
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=dt_module.timezone.utc)
            else:
                created_at = created_at.astimezone(dt_module.timezone.utc)
                
            now = datetime.now(dt_module.timezone.utc)
            age_seconds = (now - created_at).total_seconds()
            return max(0, age_seconds / 3600)
        except:
            return 0

    def _generate_reasoning(self, total, velocity, authority, timing, discussion, meets) -> str:
        """Generate human-readable reasoning"""
        status = "✓" if meets else "✗"
        return f"Score: {total:.1f}/100 {status}. V:{velocity} A:{authority} T:{timing} D:{discussion}"

    def filter_and_rank(self, posts: List[SocialPost], apply_threshold: bool = True) -> List[SocialPost]:
        """Score, filter, and rank posts"""
        scored_posts = []
        for post in posts:
            self.score_post(post)
            scored_posts.append(post)

        if apply_threshold:
            min_score = self.thresholds['minimum_score']
            scored_posts = [p for p in scored_posts if p.score['total_score'] >= min_score]
            logger.info(f"Scoring: {len(scored_posts)}/{len(posts)} posts meet threshold ({min_score})")

        # Sort by total score (descending)
        return sorted(
            scored_posts,
            key=lambda p: p.score['total_score'],
            reverse=True
        )
