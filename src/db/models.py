"""
Database models for Social Reply Bot using SQLAlchemy.

These models match the schema defined in init-db.sql and provide
ORM access to all database tables.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import (
    Column, Integer, String, Text, Float, Boolean, DateTime,
    ForeignKey, JSON, Date, Index, UniqueConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()


class ReplyQueue(Base):
    """
    Reply approval queue - stores generated replies awaiting human approval.
    """
    __tablename__ = 'reply_queue'

    id = Column(Integer, primary_key=True)
    tweet_id = Column(Text, nullable=False)
    tweet_author = Column(Text)
    tweet_text = Column(Text)
    tweet_metrics = Column(JSON)  # {likes, replies, retweets, followers}
    created_at = Column(DateTime, default=datetime.utcnow)

    # Generated reply
    reply_text = Column(Text, nullable=False)
    reply_score = Column(Float)
    commercial_priority = Column(Text)  # critical, high, medium_high, medium, low
    commercial_signals = Column(JSON)  # Matched keywords and profile indicators
    voice_validation_score = Column(Float)
    voice_violations = Column(JSON)  # List of voice guideline violations

    # Approval status
    status = Column(Text, default='pending')  # pending, approved, rejected, posted
    approved_by = Column(Text)
    approved_at = Column(DateTime)
    rejection_reason = Column(Text)

    # Metadata
    session_id = Column(Text)
    attempt_number = Column(Integer, default=1)

    __table_args__ = (
        UniqueConstraint('tweet_id', 'session_id', name='unique_tweet_per_session'),
        Index('idx_reply_queue_status', 'status', 'created_at'),
        Index('idx_reply_queue_session', 'session_id')
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'tweet_id': self.tweet_id,
            'tweet_author': self.tweet_author,
            'tweet_text': self.tweet_text,
            'tweet_metrics': self.tweet_metrics,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'reply_text': self.reply_text,
            'reply_score': self.reply_score,
            'commercial_priority': self.commercial_priority,
            'commercial_signals': self.commercial_signals,
            'voice_validation_score': self.voice_validation_score,
            'voice_violations': self.voice_violations,
            'status': self.status,
            'approved_by': self.approved_by,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'rejection_reason': self.rejection_reason,
            'session_id': self.session_id,
            'attempt_number': self.attempt_number
        }


class ReplyPerformance(Base):
    """
    Reply performance tracking - stores posted replies with engagement metrics.
    Used as learning corpus for future reply generation.
    """
    __tablename__ = 'reply_performance'

    id = Column(Integer, primary_key=True)
    tweet_id = Column(Text, nullable=False)
    reply_id = Column(Text)  # Twitter reply ID
    reply_text = Column(Text, nullable=False)
    posted_at = Column(DateTime, nullable=False)

    # Performance metrics (updated periodically)
    like_count = Column(Integer, default=0)
    reply_count = Column(Integer, default=0)
    engagement_rate = Column(Float, default=0.0)

    # Quality indicators
    validation_score = Column(Float)
    had_violations = Column(Boolean, default=False)

    # Learning flags
    marked_as_good_example = Column(Boolean, default=False)
    marked_as_bad_example = Column(Boolean, default=False)

    # Context
    original_tweet_text = Column(Text)
    commercial_priority = Column(Text)

    __table_args__ = (
        Index('idx_good_examples', 'marked_as_good_example', 'posted_at'),
        Index('idx_recent_replies', 'posted_at')
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'tweet_id': self.tweet_id,
            'reply_id': self.reply_id,
            'reply_text': self.reply_text,
            'posted_at': self.posted_at.isoformat() if self.posted_at else None,
            'like_count': self.like_count,
            'reply_count': self.reply_count,
            'engagement_rate': self.engagement_rate,
            'validation_score': self.validation_score,
            'had_violations': self.had_violations,
            'marked_as_good_example': self.marked_as_good_example,
            'marked_as_bad_example': self.marked_as_bad_example,
            'original_tweet_text': self.original_tweet_text,
            'commercial_priority': self.commercial_priority
        }


class BotSettings(Base):
    """
    User-editable bot settings - allows configuration changes without code restart.
    """
    __tablename__ = 'bot_settings'

    id = Column(Integer, primary_key=True)
    category = Column(Text, nullable=False)  # search, filtering, engagement, scheduling
    key = Column(Text, nullable=False)
    value = Column(JSON, nullable=False)  # Store as JSON for flexibility
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = Column(Text)

    __table_args__ = (
        UniqueConstraint('category', 'key', name='unique_category_key'),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'category': self.category,
            'key': self.key,
            'value': self.value,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'updated_by': self.updated_by
        }


class AnalyticsDaily(Base):
    """
    Daily analytics aggregation - provides insights into bot performance.
    """
    __tablename__ = 'analytics_daily'

    id = Column(Integer, primary_key=True)
    date = Column(Date, nullable=False, unique=True)

    # Volume metrics
    tweets_scraped = Column(Integer, default=0)
    tweets_filtered = Column(Integer, default=0)
    replies_generated = Column(Integer, default=0)
    replies_approved = Column(Integer, default=0)
    replies_rejected = Column(Integer, default=0)
    replies_auto_posted = Column(Integer, default=0)
    replies_posted = Column(Integer, default=0)

    # Quality metrics
    avg_voice_validation_score = Column(Float)
    voice_violation_rate = Column(Float)
    avg_character_count = Column(Float)

    # Commercial metrics
    critical_priority_count = Column(Integer, default=0)
    high_priority_count = Column(Integer, default=0)
    medium_priority_count = Column(Integer, default=0)
    low_priority_count = Column(Integer, default=0)

    # Engagement metrics
    avg_likes_received = Column(Float)
    avg_replies_received = Column(Float)
    avg_engagement_rate = Column(Float)

    # Cost metrics
    api_cost_usd = Column(Float, default=0.0)
    token_usage = Column(Integer, default=0)

    __table_args__ = (
        Index('idx_analytics_date', 'date'),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'date': self.date.isoformat() if self.date else None,
            'tweets_scraped': self.tweets_scraped,
            'tweets_filtered': self.tweets_filtered,
            'replies_generated': self.replies_generated,
            'replies_approved': self.replies_approved,
            'replies_rejected': self.replies_rejected,
            'replies_auto_posted': self.replies_auto_posted,
            'replies_posted': self.replies_posted,
            'avg_voice_validation_score': self.avg_voice_validation_score,
            'voice_violation_rate': self.voice_violation_rate,
            'avg_character_count': self.avg_character_count,
            'critical_priority_count': self.critical_priority_count,
            'high_priority_count': self.high_priority_count,
            'medium_priority_count': self.medium_priority_count,
            'low_priority_count': self.low_priority_count,
            'avg_likes_received': self.avg_likes_received,
            'avg_replies_received': self.avg_replies_received,
            'avg_engagement_rate': self.avg_engagement_rate,
            'api_cost_usd': self.api_cost_usd,
            'token_usage': self.token_usage
        }


class ErrorLog(Base):
    """
    Error logging table - tracks errors for monitoring and troubleshooting.
    """
    __tablename__ = 'error_log'

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    severity = Column(Text)  # critical, error, warning
    error_type = Column(Text)
    error_message = Column(Text)
    stack_trace = Column(Text)
    tweet_id = Column(Text)
    session_id = Column(Text)
    resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime)

    __table_args__ = (
        Index('idx_error_log_timestamp', 'timestamp'),
        Index('idx_error_log_severity', 'severity')
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'severity': self.severity,
            'error_type': self.error_type,
            'error_message': self.error_message,
            'stack_trace': self.stack_trace,
            'tweet_id': self.tweet_id,
            'session_id': self.session_id,
            'resolved': self.resolved,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None
        }


class User(Base):
    """
    User authentication table - stores admin users for dashboard access.
    """
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    email = Column(Text, unique=True, nullable=False)
    hashed_password = Column(Text, nullable=False)
    role = Column(Text, default='admin')
    telegram_chat_id = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)

    # Relationships
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    notification_settings = relationship("NotificationSettings", back_populates="user", uselist=False)

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary for JSON serialization (excludes password)"""
        return {
            'id': self.id,
            'email': self.email,
            'role': self.role,
            'telegram_chat_id': self.telegram_chat_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }


class Session(Base):
    """
    User sessions table - JWT token management for dashboard authentication.
    """
    __tablename__ = 'sessions'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    token = Column(Text, unique=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="sessions")

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'token': self.token,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class NotificationSettings(Base):
    """
    Notification preferences - controls how users receive notifications.
    """
    __tablename__ = 'notification_settings'

    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    telegram_enabled = Column(Boolean, default=True)
    email_enabled = Column(Boolean, default=False)
    telegram_events = Column(JSON, default=["reply_ready", "error_critical"])
    email_events = Column(JSON, default=["daily_summary"])

    # Relationships
    user = relationship("User", back_populates="notification_settings")

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary for JSON serialization"""
        return {
            'user_id': self.user_id,
            'telegram_enabled': self.telegram_enabled,
            'email_enabled': self.email_enabled,
            'telegram_events': self.telegram_events,
            'email_events': self.email_events
        }


class RepliedTweet(Base):
    """
    Deduplication tracking - stores tweets we've already replied to.
    Prevents duplicate replies and tracks engagement history.
    """
    __tablename__ = 'replied_tweets'

    tweet_id = Column(Text, primary_key=True)
    author_username = Column(Text, nullable=False)
    tweet_text = Column(Text)
    replied_at = Column(DateTime, nullable=False)
    reply_text = Column(Text)
    commercial_priority = Column(Text)
    score = Column(Float)

    # Scoring components (for analysis)
    engagement_velocity = Column(Float)
    user_authority = Column(Float)
    timing_score = Column(Float)
    discussion_score = Column(Float)

    __table_args__ = (
        Index('idx_replied_tweets_timestamp', 'replied_at'),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary for JSON serialization"""
        return {
            'tweet_id': self.tweet_id,
            'author_username': self.author_username,
            'tweet_text': self.tweet_text,
            'replied_at': self.replied_at.isoformat() if self.replied_at else None,
            'reply_text': self.reply_text,
            'commercial_priority': self.commercial_priority,
            'score': self.score,
            'engagement_velocity': self.engagement_velocity,
            'user_authority': self.user_authority,
            'timing_score': self.timing_score,
            'discussion_score': self.discussion_score
        }


class ScrapedTweet(Base):
    """
    Scraping history - tracks every tweet found by the bot and its processing outcome.
    Used for analytics, debugging, and funnel visualization.
    """
    __tablename__ = 'scraped_tweets'

    tweet_id = Column(Text, primary_key=True)
    tweet_text = Column(Text)
    author_username = Column(Text)
    scraped_at = Column(DateTime, default=datetime.utcnow)
    
    # Processing status
    status = Column(Text)  # scraped, filtered, scored_low, deduplicated, queued
    rejection_reason = Column(Text)
    
    # Detailed breakdown
    filter_details = Column(JSON)  # e.g., {"followers": "150 < 200"}
    score_details = Column(JSON)   # e.g., {"total": 0.4, "breakdown": {...}}
    
    # Metadata
    session_id = Column(Text)
    search_term = Column(Text)  # Hashtag or keyword used to find this tweet

    __table_args__ = (
        Index('idx_scraped_tweets_status', 'status'),
        Index('idx_scraped_tweets_timestamp', 'scraped_at'),
        Index('idx_scraped_tweets_session', 'session_id')
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary for JSON serialization"""
        return {
            'tweet_id': self.tweet_id,
            'tweet_text': self.tweet_text,
            'author_username': self.author_username,
            'scraped_at': self.scraped_at.isoformat() if self.scraped_at else None,
            'status': self.status,
            'rejection_reason': self.rejection_reason,
            'filter_details': self.filter_details,
            'score_details': self.score_details,
            'session_id': self.session_id,
            'search_term': self.search_term,
            'url': self._get_url()
        }

    def _get_url(self) -> str:
        """Generate URL based on platform logic"""
        # Reddit detection (if search term starts with r/ or it's a reddit ID format)
        is_reddit = False
        if self.search_term and self.search_term.startswith('r/'):
            is_reddit = True
        
        # Twitter usually has numeric IDs, Reddit has alphanumeric base36
        # But safest is relying on how we scraped it.
        
        if is_reddit:
            # Reddit URL: https://www.reddit.com/comments/{id}
            # Note: tweet_id might be t3_xyz, usually we just want the ID part for comments/
            # If it's a full ID like t3_12345, we might need to strip or just use it.
            # Reddit web handles /comments/t3_xyz correctly usually.
            return f"https://www.reddit.com/comments/{self.tweet_id}"
        else:
            # Twitter URL: https://twitter.com/{user}/status/{id}
            username = self.author_username or 'i'
            return f"https://twitter.com/{username}/status/{self.tweet_id}"
