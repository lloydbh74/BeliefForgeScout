"""
Unified data models for social media content.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from enum import Enum

class Platform(Enum):
    TWITTER = "twitter"
    REDDIT = "reddit"

@dataclass
class Author:
    """Unified author model"""
    username: str
    display_name: str
    platform: Platform
    platform_id: Optional[str] = None
    followers_count: Optional[int] = 0
    is_verified: bool = False
    created_at: Optional[datetime] = None
    bio: Optional[str] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)

    def __setitem__(self, key, value):
        """Allow dict-like assignment for legacy code"""
        if hasattr(self, key):
            setattr(self, key, value)
        else:
            self.raw_data[key] = value

    def __getitem__(self, key):
        """Allow dict-like access for legacy code"""
        if hasattr(self, key):
            return getattr(self, key)
        return self.raw_data.get(key)
    
    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

@dataclass
class SocialMetrics:
    """Unified interaction metrics"""
    likes: int = 0          # Likes / Upvotes
    replies: int = 0        # Replies / Comments
    shares: int = 0         # Retweets / Crossposts
    impressions: int = 0    # Views (if available)

@dataclass
class SocialPost:
    """Unified content model for any platform"""
    id: str
    platform: Platform
    text: str
    author: Author
    created_at: datetime
    url: str
    metrics: SocialMetrics
    
    # Metadata
    scraped_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    search_term: str = ""
    language: str = "en"
    
    # Platform-specific data (kept for reference)
    raw_data: Dict[str, Any] = field(default_factory=dict)
    
    # Analysis & Processing (added later in pipeline)
    commercial_signals: Optional[Dict[str, Any]] = None
    score: Optional[Dict[str, Any]] = None
    generated_reply: Optional[Dict[str, Any]] = None

    def __getitem__(self, key):
        """Allow dict-like access for backward compatibility"""
        # Handle computed metrics for legacy code
        if key == 'public_metrics' and hasattr(self, 'metrics'):
            return {
                'like_count': self.metrics.likes,
                'reply_count': self.metrics.replies,
                'retweet_count': self.metrics.shares,
                'impression_count': self.metrics.impressions
            }

        if hasattr(self, key):
            val = getattr(self, key)
            # Handle nested author access for legacy code: tweet['author']['username']
            if key == 'author' and isinstance(val, Author):
                 return val
            return val
            
        if key in self.raw_data:
            return self.raw_data[key]
        raise KeyError(key)

    def get(self, key, default=None):
        """Dict-like get method"""
        try:
            return self[key]
        except KeyError:
            return default

    def __setitem__(self, key, value):
        """Allow dict-like assignment for legacy code"""
        if hasattr(self, key):
            setattr(self, key, value)
        else:
            self.raw_data[key] = value

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'id': self.id,
            'platform': self.platform.value,
            'text': self.text,
            'author': {
                'username': self.author.username,
                'display_name': self.author.display_name,
                'followers_count': self.author.followers_count
            },
            'created_at': self.created_at.isoformat(),
            'url': self.url,
            'metrics': {
                'likes': self.metrics.likes,
                'replies': self.metrics.replies,
                'shares': self.metrics.shares
            },
            'score': self.score,
            'commercial_signals': self.commercial_signals,
            'generated_reply': self.generated_reply
        }
