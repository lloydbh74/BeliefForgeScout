"""
Shared pytest fixtures and configuration.

This file provides reusable fixtures for testing the Social Reply Bot.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, AsyncMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.db.models import Base


# Database Fixtures

@pytest.fixture(scope='function')
def test_db():
    """Create in-memory SQLite database for testing"""
    engine = create_engine('sqlite:///:memory:', echo=False)
    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    session = Session()

    yield session

    session.close()
    Base.metadata.drop_all(engine)


# Tweet Fixtures

@pytest.fixture
def sample_tweet_imposter_syndrome():
    """Tweet about imposter syndrome (critical priority)"""
    return {
        'id': '1234567890',
        'text': 'Struggling with major imposter syndrome today. Does anyone else feel like a fraud sometimes?',
        'author': {
            'username': 'sarah_founder',
            'display_name': 'Sarah | Building in Public',
            'followers': 1200,
            'verified': False
        },
        'created_at': datetime.utcnow() - timedelta(hours=3),
        'public_metrics': {
            'like_count': 15,
            'reply_count': 8,
            'retweet_count': 3,
            'quote_count': 1
        },
        'commercial_signals': {
            'priority': 'critical',
            'multiplier': 3.0,
            'matched_keywords': ['imposter syndrome']
        }
    }


@pytest.fixture
def sample_tweet_brand_clarity():
    """Tweet about brand clarity (high priority)"""
    return {
        'id': '9876543210',
        'text': 'Been working on my brand positioning for weeks. Still not sure who I am serving. Help?',
        'author': {
            'username': 'mike_startup',
            'display_name': 'Mike | Founder',
            'followers': 800,
            'verified': False
        },
        'created_at': datetime.utcnow() - timedelta(hours=5),
        'public_metrics': {
            'like_count': 12,
            'reply_count': 5,
            'retweet_count': 2,
            'quote_count': 0
        },
        'commercial_signals': {
            'priority': 'high',
            'multiplier': 2.0,
            'matched_keywords': ['brand positioning']
        }
    }


@pytest.fixture
def sample_tweet_growth_frustration():
    """Tweet about growth frustration (medium-high priority)"""
    return {
        'id': '5555555555',
        'text': 'Feeling stuck at a plateau. No matter what I try, I cannot seem to get traction.',
        'author': {
            'username': 'john_entrepreneur',
            'display_name': 'John | Bootstrapped',
            'followers': 600,
            'verified': False
        },
        'created_at': datetime.utcnow() - timedelta(hours=4),
        'public_metrics': {
            'like_count': 10,
            'reply_count': 4,
            'retweet_count': 1,
            'quote_count': 0
        },
        'commercial_signals': {
            'priority': 'medium_high',
            'multiplier': 1.5,
            'matched_keywords': ['stuck', 'plateau', 'no traction']
        }
    }


@pytest.fixture
def sample_tweet_low_quality():
    """Low quality tweet (should be filtered out)"""
    return {
        'id': '1111111111',
        'text': 'Check out my NFT drop! Limited time offer! Buy now!',
        'author': {
            'username': 'crypto_spam',
            'display_name': 'Crypto Guru',
            'followers': 50000,
            'verified': False
        },
        'created_at': datetime.utcnow() - timedelta(minutes=30),
        'public_metrics': {
            'like_count': 5,
            'reply_count': 2,
            'retweet_count': 1,
            'quote_count': 0
        }
    }


# Reply Text Fixtures

@pytest.fixture
def valid_british_reply():
    """Valid reply with British English"""
    return "I understand that feeling. Perhaps focus on what you've already achieved?"


@pytest.fixture
def valid_british_reply_with_qualifier():
    """Valid reply with gentle qualifier"""
    return "I realise this is quite challenging. What aspect troubles you most?"


@pytest.fixture
def invalid_reply_exclamation():
    """Invalid reply with exclamation marks"""
    return "You can do this! Don't give up! You're amazing!"


@pytest.fixture
def invalid_reply_american_spelling():
    """Invalid reply with American spellings"""
    return "I realize this is challenging while you're trying to organize your thoughts."


@pytest.fixture
def invalid_reply_jargon():
    """Invalid reply with corporate jargon"""
    return "You need to leverage your strengths and disrupt the market to create synergy!"


@pytest.fixture
def invalid_reply_salesy():
    """Invalid reply with salesy language"""
    return "Buy now! Limited time offer! DM me for discount code!"


@pytest.fixture
def invalid_reply_too_long():
    """Invalid reply exceeding character limit"""
    return "I completely understand what you're going through because I've been there myself many times before, and I want to share with you that it's completely normal to feel this way when you're building something new and putting yourself out there for everyone to see and judge, which can be quite overwhelming and scary at times."


@pytest.fixture
def reply_with_warnings():
    """Reply that passes but has warnings"""
    return "I understand that feeling quite well, actually - what specific challenge are you facing right now? #BuildInPublic"


# OpenRouter API Response Fixtures

@pytest.fixture
def openrouter_success_response():
    """Successful OpenRouter API response"""
    return {
        "choices": [{
            "message": {
                "content": "I understand that feeling. What aspect troubles you most?"
            }
        }],
        "usage": {
            "prompt_tokens": 200,
            "completion_tokens": 15,
            "total_tokens": 215
        }
    }


@pytest.fixture
def openrouter_success_response_british():
    """Successful OpenRouter response with British English"""
    return {
        "choices": [{
            "message": {
                "content": "I realise this is quite challenging. Perhaps consider what truly matters to you?"
            }
        }],
        "usage": {
            "prompt_tokens": 180,
            "completion_tokens": 18,
            "total_tokens": 198
        }
    }


@pytest.fixture
def openrouter_rate_limit_response():
    """Rate limit error response"""
    return {
        "error": {
            "message": "Rate limit exceeded. Please try again later.",
            "type": "rate_limit_error",
            "code": "rate_limit_exceeded"
        }
    }


@pytest.fixture
def openrouter_auth_error_response():
    """Authentication error response"""
    return {
        "error": {
            "message": "Invalid API key provided",
            "type": "invalid_request_error",
            "code": "invalid_api_key"
        }
    }


@pytest.fixture
def openrouter_timeout_response():
    """Timeout error response"""
    return {
        "error": {
            "message": "Request timeout",
            "type": "timeout_error",
            "code": "request_timeout"
        }
    }


# Configuration Mock Fixtures

@pytest.fixture
def mock_bot_config():
    """Mock bot configuration"""
    config = MagicMock()

    # Voice configuration
    config.voice.tone = "warm, authentic friend - never salesy"
    config.voice.language = "British English"
    config.voice.character_limits = {
        'preferred_max': 100,
        'absolute_max': 280
    }
    config.voice.required_patterns = [
        "British spellings (realise, colour, whilst, amongst)",
        "Gentle qualifiers (quite, rather, perhaps)"
    ]
    config.voice.strict_avoidance = [
        "Exclamation marks (!)",
        "Corporate jargon (synergy, leverage, disrupt)",
        "American spellings (-ize, -or endings)"
    ]
    config.voice.validation = {
        'enabled': True,
        'strict_mode': True,
        'max_violations': 0
    }

    # LLM configuration
    config.llm.provider = "openrouter"
    config.llm.model = "anthropic/claude-3.5-sonnet"
    config.llm.parameters = {
        'temperature': 0.7,
        'max_tokens': 150,
        'top_p': 0.9
    }
    config.llm.rate_limits = {
        'requests_per_minute': 20,
        'daily_budget_usd': 50
    }
    config.llm.learning = {
        'enabled': True,
        'corpus_size': 5,
        'min_engagement_rate': 0.05,
        'rotation': True
    }

    # Deduplication configuration
    config.deduplication.history_days = 7
    config.deduplication.same_author_cooldown_hours = 48
    config.deduplication.engagement_limits = {
        'max_replies_per_hour': 5,
        'max_replies_per_day': 20,
        'max_replies_per_session': 10
    }

    return config


@pytest.fixture
def mock_env_config():
    """Mock environment configuration"""
    config = MagicMock()
    config.openrouter_api_key = "sk-or-v1-test-key"
    config.telegram_bot_token = "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"
    config.telegram_chat_id = "987654321"
    return config


# Telegram Bot Mock Fixtures

@pytest.fixture
def mock_telegram_bot():
    """Mock Telegram bot"""
    bot = AsyncMock()
    bot.send_message = AsyncMock()
    bot.edit_message_text = AsyncMock()
    return bot


@pytest.fixture
def mock_telegram_update():
    """Mock Telegram update object"""
    update = MagicMock()
    update.message.reply_text = AsyncMock()
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()
    update.callback_query.from_user.username = "test_user"
    return update


# Learning Corpus Fixtures

@pytest.fixture
def sample_learning_corpus(test_db):
    """Create sample learning corpus in database"""
    from src.db.models import ReplyPerformance

    examples = [
        ReplyPerformance(
            tweet_id='learning_1',
            reply_id='reply_1',
            reply_text="I understand that feeling. What aspect troubles you most?",
            posted_at=datetime.utcnow() - timedelta(days=1),
            like_count=5,
            reply_count=2,
            engagement_rate=0.08,
            validation_score=100,
            had_violations=False,
            marked_as_good_example=True,
            original_tweet_text="Struggling with imposter syndrome today.",
            commercial_priority='critical'
        ),
        ReplyPerformance(
            tweet_id='learning_2',
            reply_id='reply_2',
            reply_text="I realise this is quite challenging. Perhaps focus on one clear step?",
            posted_at=datetime.utcnow() - timedelta(days=2),
            like_count=8,
            reply_count=3,
            engagement_rate=0.12,
            validation_score=100,
            had_violations=False,
            marked_as_good_example=True,
            original_tweet_text="Feeling stuck with my brand positioning.",
            commercial_priority='high'
        ),
        ReplyPerformance(
            tweet_id='learning_3',
            reply_id='reply_3',
            reply_text="For my fellow founders: clarity comes through doing, not just thinking.",
            posted_at=datetime.utcnow() - timedelta(days=3),
            like_count=12,
            reply_count=5,
            engagement_rate=0.15,
            validation_score=100,
            had_violations=False,
            marked_as_good_example=True,
            original_tweet_text="How do I figure out my niche?",
            commercial_priority='high'
        )
    ]

    for example in examples:
        test_db.add(example)

    test_db.commit()

    return examples


# Pytest Markers

def pytest_configure(config):
    """Register custom pytest markers"""
    config.addinivalue_line(
        "markers", "critical: mark test as critical for brand safety"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "requires_api: mark test as requiring real API access"
    )
