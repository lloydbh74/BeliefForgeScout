"""
Commercial filtering for Belief Forge targeting.

Detects commercial priority keywords and profile indicators to maximize ROI.
Applies priority multipliers based on keyword categories.
"""

import logging
from typing import Dict, Any, List, Tuple, Optional

from src.config.loader import get_config
from src.core.models import SocialPost

logger = logging.getLogger(__name__)


class CommercialFilter:
    """Applies commercial filters and calculates priority scores"""

    # Priority multipliers
    PRIORITY_MULTIPLIERS = {
        'critical': 3.0,      # Imposter syndrome, self-doubt
        'high': 2.0,          # Brand clarity, positioning
        'medium_high': 1.5,   # Growth frustration
        'medium': 1.2,        # General challenges
        'baseline': 1.0       # No specific signals
    }

    def __init__(self):
        """Initialize commercial filter with configuration"""
        self.bot_config, _ = get_config()
        self.commercial = self.bot_config.commercial

    def analyze_post(self, post: SocialPost) -> Dict[str, Any]:
        """
        Analyze post for commercial signals.

        Args:
            post: SocialPost object

        Returns:
            Dictionary with commercial analysis
        """
        text = post.text.lower()
        
        # Check priority keywords
        priority, matched_keywords = self._check_priority_keywords(text)

        # Check profile indicators (if author data exists)
        profile_indicators = self._check_profile_indicators(post)

        # Calculate commercial score
        multiplier = self.PRIORITY_MULTIPLIERS[priority]
        commercial_score = self._calculate_commercial_score(
            multiplier,
            len(matched_keywords),
            len(profile_indicators)
        )

        analysis = {
            'priority': priority,
            'multiplier': multiplier,
            'matched_keywords': matched_keywords,
            'matched_profile_indicators': profile_indicators,
            'commercial_score': commercial_score
        }
        
        # Attach to post object
        post.commercial_signals = analysis

        return analysis

    def _check_priority_keywords(self, text: str) -> Tuple[str, List[str]]:
        """Check text for priority keywords."""
        # Check critical
        matched = [k for k in self.commercial.priority_keywords.critical if k.lower() in text]
        if matched: return 'critical', matched

        # Check high
        matched = [k for k in self.commercial.priority_keywords.high if k.lower() in text]
        if matched: return 'high', matched

        # Check medium-high
        matched = [k for k in self.commercial.priority_keywords.medium_high if k.lower() in text]
        if matched: return 'medium_high', matched

        # Check medium
        matched = [k for k in self.commercial.priority_keywords.medium if k.lower() in text]
        if matched: return 'medium', matched

        return 'baseline', []

    def _check_profile_indicators(self, post: SocialPost) -> List[str]:
        """Check author profile and post text for target indicators."""
        matched = []
        author = post.author
        
        # Combine author fields
        search_text = f"{author.display_name} {author.username} {author.bio or ''} {post.text}".lower()

        # Check entrepreneur keywords
        for keyword in self.commercial.profile_indicators.entrepreneur_keywords:
            if keyword.lower() in search_text:
                matched.append(f"entrepreneur:{keyword}")

        # Check target stage indicators
        text_lower = post.text.lower()
        for stage in self.commercial.profile_indicators.target_stage:
            if stage.lower() in text_lower:
                matched.append(f"stage:{stage}")

        return matched

    def _calculate_commercial_score(
        self,
        multiplier: float,
        keyword_count: int,
        indicator_count: int
    ) -> float:
        """Calculate commercial score based on signals."""
        base_score = multiplier * 20
        keyword_bonus = min(keyword_count * 5, 20)
        indicator_bonus = min(indicator_count * 3, 15)
        return round(min(base_score + keyword_bonus + indicator_bonus, 100), 2)

    def filter_posts_batch(
        self,
        posts: List[SocialPost],
        min_priority: str = 'medium'
    ) -> Tuple[List[SocialPost], List[SocialPost]]:
        """Filter posts by commercial priority."""
        priority_order = ['critical', 'high', 'medium_high', 'medium', 'baseline']
        min_priority_index = priority_order.index(min_priority)

        passed = []
        rejected = []

        for post in posts:
            analysis = self.analyze_post(post)
            priority = analysis['priority']
            priority_index = priority_order.index(priority)

            if priority_index <= min_priority_index:
                passed.append(post)
            else:
                # We can store rejection reason in a temporary attribute if needed or log it
                rejected.append(post)

        logger.info(f"Commercial filter: {len(passed)}/{len(posts)} posts passed (min priority: {min_priority})")
        return passed, rejected

    def rank_posts_by_priority(self, posts: List[SocialPost]) -> List[SocialPost]:
        """Rank posts by commercial priority."""
        priority_order = {'critical': 0, 'high': 1, 'medium_high': 2, 'medium': 3, 'baseline': 4}

        # Ensure all analyzed
        for post in posts:
            if not post.commercial_signals:
                self.analyze_post(post)

        return sorted(
            posts,
            key=lambda p: (
                priority_order[p.commercial_signals['priority']],
                -p.commercial_signals['commercial_score']
            )
        )
