# Test Strategy: Reply Generation and Posting Functionality

## Executive Summary

This document outlines a comprehensive testing strategy for the Twitter/X engagement bot's reply generation and posting pipeline. Testing focuses on ensuring brand safety through voice validation, API integration reliability, and end-to-end workflow integrity.

**Critical Priority**: Voice validation testing is paramount for brand safety - any reply that violates British English guidelines could damage the Belief Forge brand.

---

## Table of Contents

1. [Overview](#overview)
2. [Components to Test](#components-to-test)
3. [Test Framework Recommendation](#test-framework-recommendation)
4. [Test Categories](#test-categories)
5. [Mock Strategies](#mock-strategies)
6. [Test Data Fixtures](#test-data-fixtures)
7. [Test Implementation Plan](#test-implementation-plan)
8. [Priority Matrix](#priority-matrix)

---

## Overview

### Pipeline Workflow

The reply pipeline follows this flow:

```
Tweet Input → LLM Generation → Voice Validation → Telegram Approval → Posting
     ↓              ↓                  ↓                  ↓              ↓
Database      OpenRouter API    Validation Rules   Telegram API   Twitter API
```

### Testing Objectives

1. **Brand Safety**: Ensure all replies meet British English voice guidelines
2. **API Reliability**: Handle external API failures gracefully
3. **Data Integrity**: Verify database operations are atomic and correct
4. **Workflow Integrity**: Validate end-to-end pipeline behaves correctly
5. **Cost Control**: Ensure budget limits and rate limiting work correctly

---

## Components to Test

### 1. Voice Validator (`src/voice/validator.py`)

**CRITICAL - HIGHEST PRIORITY**

**Functionality**:
- Character limit validation (100 preferred, 280 absolute max)
- British English spelling detection
- Exclamation mark detection (forbidden)
- Corporate jargon detection
- Salesy language detection
- Emoji counting
- Hashtag counting
- Scoring algorithm

**Risk**: Voice violations could damage brand reputation and authenticity.

### 2. LLM Reply Generator (`src/llm/reply_generator.py`)

**HIGH PRIORITY**

**Functionality**:
- Reply generation with retry logic
- System prompt construction
- User prompt construction with learning examples
- Learning corpus retrieval
- Feedback-based regeneration
- Batch processing
- Cost tracking integration

**Risk**: Poor generation quality wastes API costs and human review time.

### 3. OpenRouter Client (`src/llm/openrouter_client.py`)

**HIGH PRIORITY**

**Functionality**:
- API request handling
- Rate limiting (20 req/min)
- Budget enforcement ($50/day)
- Cost calculation
- Retry logic with exponential backoff
- Error handling (timeouts, network errors, API errors)
- Usage statistics tracking

**Risk**: Budget overruns or API failures could halt bot operations.

### 4. Telegram Approval Bot (`src/telegram_bot/approval_bot.py`)

**MEDIUM-HIGH PRIORITY**

**Functionality**:
- Command handlers (/status, /queue, /stats, /help)
- Approval callback handling (approve/reject buttons)
- Message formatting and sending
- Error alert notifications
- Daily summary reports
- Bot lifecycle (start/stop/initialize)

**Risk**: Approval failures could block the reply pipeline.

### 5. Orchestrator Integration (`src/core/orchestrator.py`)

**MEDIUM PRIORITY**

**Functionality**:
- End-to-end pipeline coordination
- Error handling and recovery
- Session management
- Database transaction integrity
- Async workflow coordination

**Risk**: Pipeline failures could leave database in inconsistent state.

### 6. Reply Posting (NOT YET IMPLEMENTED)

**FUTURE PRIORITY**

**Note**: No posting module exists yet. Tests should be written when this is implemented.

**Expected Functionality**:
- Twitter API authentication
- Reply posting with rate limiting
- Error handling for posting failures
- Engagement tracking
- Reply ID capture for performance tracking

---

## Test Framework Recommendation

### Primary Framework: pytest

**Rationale**:
- Industry standard for Python testing
- Excellent async support (pytest-asyncio)
- Powerful fixture system
- Parametrized testing
- Good mocking support with pytest-mock
- Clear assertion syntax
- Extensive plugin ecosystem

### Required Packages

```txt
# Testing framework
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-mock==3.12.0
pytest-cov==4.1.0

# Mocking and fixtures
responses==0.24.1
httpx-mock==0.15.0
faker==20.1.0

# Database testing
pytest-postgresql==5.0.0
sqlalchemy-utils==0.41.1

# Async testing support
aioresponses==0.7.6
```

### Project Structure

```
tests/
├── __init__.py
├── conftest.py                    # Shared fixtures
├── unit/
│   ├── __init__.py
│   ├── test_voice_validator.py    # Voice validation tests
│   ├── test_reply_generator.py    # Reply generation tests
│   ├── test_openrouter_client.py  # OpenRouter API tests
│   └── test_telegram_bot.py       # Telegram bot tests
├── integration/
│   ├── __init__.py
│   ├── test_reply_pipeline.py     # End-to-end pipeline tests
│   └── test_database_ops.py       # Database integration tests
├── fixtures/
│   ├── __init__.py
│   ├── tweets.py                  # Tweet test data
│   ├── replies.py                 # Reply test data
│   └── api_responses.py           # Mock API responses
└── data/
    ├── sample_tweets.json
    ├── sample_replies.json
    └── voice_test_cases.json
```

---

## Test Categories

### 1. Unit Tests

Test individual components in isolation with mocked dependencies.

**Coverage Goals**: 80%+ for critical modules, 70%+ overall

#### A. Voice Validator Unit Tests

**File**: `tests/unit/test_voice_validator.py`

**Test Cases**:

1. **Character Limit Tests**
   - `test_reply_under_preferred_max` - 100 chars
   - `test_reply_between_preferred_and_absolute` - 100-280 chars
   - `test_reply_exceeds_absolute_max` - >280 chars (violation)

2. **Exclamation Mark Tests** (CRITICAL)
   - `test_no_exclamation_marks` - Valid case
   - `test_single_exclamation_mark` - Should fail
   - `test_multiple_exclamation_marks` - Should fail
   - `test_exclamation_in_quoted_text` - Edge case

3. **British Spelling Tests** (CRITICAL)
   - `test_british_spellings_valid` - realise, colour, whilst, amongst
   - `test_american_spelling_ize` - realize (violation)
   - `test_american_spelling_or` - color, favor (violation)
   - `test_american_spelling_while` - while instead of whilst (violation)
   - `test_american_spelling_among` - among instead of amongst (violation)
   - `test_mixed_spellings` - Some British, some American

4. **Corporate Jargon Tests**
   - `test_no_jargon` - Valid case
   - `test_synergy_jargon` - synergy, synergies (violation)
   - `test_leverage_jargon` - leverage, leveraging (violation)
   - `test_disrupt_jargon` - disrupt, disruptive (violation)
   - `test_game_changer_jargon` - game-changer (violation)
   - `test_crushing_it_jargon` - crushing it (violation)
   - `test_hustle_grind_jargon` - hustle, grind (violation)

5. **Salesy Language Tests**
   - `test_no_salesy_language` - Valid case
   - `test_buy_now` - "buy now" pattern (violation)
   - `test_limited_time` - "limited time" pattern (violation)
   - `test_dm_me` - "DM me" pattern (violation)
   - `test_link_in_bio` - "link in bio" pattern (violation)

6. **Emoji and Hashtag Tests**
   - `test_no_emoji` - Valid case
   - `test_single_emoji` - Warning (acceptable)
   - `test_multiple_emoji` - Warning/violation
   - `test_no_hashtags` - Valid case
   - `test_single_hashtag` - Warning
   - `test_multiple_hashtags` - Violation

7. **Scoring Tests**
   - `test_perfect_score` - 100 score
   - `test_score_with_warnings` - Deductions for warnings
   - `test_score_with_violations` - Major deductions
   - `test_strict_mode_validation` - Zero tolerance

8. **Improvement Suggestions**
   - `test_suggestions_for_char_limit`
   - `test_suggestions_for_american_spellings`
   - `test_suggestions_for_jargon`

**Parametrized Tests**:

```python
@pytest.mark.parametrize("text,expected_valid", [
    ("I realise this is quite challenging.", True),
    ("This is amazing!", False),  # Exclamation
    ("I realize this works.", False),  # American spelling
    ("We need to leverage synergy.", False),  # Jargon
])
def test_voice_validation_parametrized(text, expected_valid):
    validator = VoiceValidator()
    result = validator.validate(text)
    assert result['is_valid'] == expected_valid
```

#### B. Reply Generator Unit Tests

**File**: `tests/unit/test_reply_generator.py`

**Test Cases**:

1. **System Prompt Construction**
   - `test_system_prompt_contains_voice_guidelines`
   - `test_system_prompt_includes_brand_context`
   - `test_system_prompt_includes_character_limits`
   - `test_system_prompt_includes_avoidance_rules`

2. **User Prompt Construction**
   - `test_user_prompt_includes_tweet_text`
   - `test_user_prompt_includes_author_info`
   - `test_user_prompt_includes_commercial_signals`
   - `test_user_prompt_with_learning_examples`
   - `test_user_prompt_without_learning_examples`

3. **Reply Generation**
   - `test_generate_reply_success_first_attempt`
   - `test_generate_reply_success_after_retry`
   - `test_generate_reply_fails_after_max_attempts`
   - `test_generate_reply_tracks_cost`
   - `test_generate_reply_tracks_attempts`

4. **Learning Corpus**
   - `test_get_learning_examples_with_rotation`
   - `test_get_learning_examples_filters_by_engagement`
   - `test_get_learning_examples_limits_corpus_size`
   - `test_get_learning_examples_returns_empty_when_none`

5. **Feedback Integration**
   - `test_feedback_prompt_includes_violations`
   - `test_feedback_prompt_includes_previous_attempt`
   - `test_retry_with_feedback_improves_result`

6. **Batch Processing**
   - `test_batch_generate_replies_all_succeed`
   - `test_batch_generate_replies_partial_success`
   - `test_batch_generate_replies_handles_errors_gracefully`

7. **Context Manager**
   - `test_context_manager_closes_client`
   - `test_context_manager_handles_exceptions`

**Mock Strategy**: Mock `OpenRouterClient` and `VoiceValidator` to isolate generator logic.

#### C. OpenRouter Client Unit Tests

**File**: `tests/unit/test_openrouter_client.py`

**Test Cases**:

1. **API Request Tests**
   - `test_generate_completion_success`
   - `test_generate_completion_uses_config_defaults`
   - `test_generate_completion_overrides_parameters`
   - `test_generate_completion_includes_auth_headers`

2. **Rate Limiting Tests**
   - `test_rate_limiting_enforces_min_interval`
   - `test_rate_limiting_calculates_from_config`
   - `test_rate_limiting_allows_immediate_first_request`

3. **Budget Enforcement Tests** (CRITICAL)
   - `test_budget_allows_requests_under_limit`
   - `test_budget_blocks_requests_over_limit`
   - `test_budget_tracks_cost_across_requests`
   - `test_budget_reset_clears_tracking`

4. **Cost Calculation Tests**
   - `test_cost_calculation_for_claude_sonnet`
   - `test_cost_tracks_prompt_and_completion_tokens`
   - `test_total_cost_accumulates`

5. **Error Handling Tests**
   - `test_retry_on_timeout_exception`
   - `test_retry_on_network_error`
   - `test_no_retry_on_auth_error`
   - `test_no_retry_on_invalid_request`
   - `test_max_retries_exhausted`

6. **Usage Statistics Tests**
   - `test_get_usage_stats_returns_correct_data`
   - `test_usage_stats_calculates_remaining_budget`
   - `test_usage_stats_calculates_percentage_used`

7. **Context Manager Tests**
   - `test_context_manager_closes_http_client`
   - `test_context_manager_handles_exceptions`

**Mock Strategy**: Use `httpx-mock` to mock HTTP requests to OpenRouter API.

```python
def test_generate_completion_success(httpx_mock):
    httpx_mock.add_response(
        method="POST",
        url="https://openrouter.ai/api/v1/chat/completions",
        json={
            "choices": [{"message": {"content": "Test reply"}}],
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150
            }
        }
    )

    client = OpenRouterClient()
    response = client.generate_completion([
        {"role": "system", "content": "System prompt"},
        {"role": "user", "content": "User prompt"}
    ])

    assert response["content"] == "Test reply"
    assert response["tokens"]["total"] == 150
```

#### D. Telegram Bot Unit Tests

**File**: `tests/unit/test_telegram_bot.py`

**Test Cases**:

1. **Command Handler Tests**
   - `test_cmd_start_sends_welcome_message`
   - `test_cmd_status_shows_pending_count`
   - `test_cmd_queue_lists_pending_replies`
   - `test_cmd_stats_shows_statistics`
   - `test_cmd_help_shows_help_text`

2. **Approval Callback Tests**
   - `test_approve_callback_updates_status`
   - `test_approve_callback_records_approver`
   - `test_reject_callback_updates_status`
   - `test_reject_callback_records_rejector`
   - `test_callback_handles_missing_reply`

3. **Notification Tests**
   - `test_send_approval_request_formats_correctly`
   - `test_send_approval_request_includes_inline_buttons`
   - `test_send_notification_basic`
   - `test_send_error_alert_includes_context`
   - `test_send_daily_summary_formats_stats`

4. **Bot Lifecycle Tests**
   - `test_initialize_registers_handlers`
   - `test_start_initializes_application`
   - `test_stop_cleans_up_safely`

**Mock Strategy**: Mock `telegram.Bot` and `telegram.ext.Application` to avoid actual Telegram API calls.

### 2. Integration Tests

Test component interactions with real dependencies where possible.

**Coverage Goals**: Critical paths covered

#### A. Reply Pipeline Integration Tests

**File**: `tests/integration/test_reply_pipeline.py`

**Test Cases**:

1. **End-to-End Pipeline**
   - `test_full_pipeline_from_tweet_to_approval_queue`
   - `test_pipeline_handles_invalid_voice_gracefully`
   - `test_pipeline_retries_generation_on_failure`
   - `test_pipeline_tracks_session_id`

2. **Database Integration**
   - `test_reply_queue_entry_created_correctly`
   - `test_reply_queue_status_transitions`
   - `test_replied_tweets_deduplication`
   - `test_learning_corpus_retrieval`
   - `test_analytics_tracking`

3. **Multi-Component Workflows**
   - `test_generation_plus_validation_workflow`
   - `test_telegram_approval_plus_database_update`
   - `test_cost_tracking_across_pipeline`

4. **Error Recovery**
   - `test_database_rollback_on_telegram_failure`
   - `test_session_isolation_on_error`
   - `test_error_logging_integration`

#### B. Database Operations Tests

**File**: `tests/integration/test_database_ops.py`

**Test Cases**:

1. **CRUD Operations**
   - `test_create_reply_queue_entry`
   - `test_read_reply_queue_by_status`
   - `test_update_reply_queue_status`
   - `test_delete_old_replied_tweets`

2. **Transaction Safety**
   - `test_commit_on_success`
   - `test_rollback_on_exception`
   - `test_unique_constraint_enforcement`
   - `test_concurrent_access_handling`

3. **Query Performance**
   - `test_learning_corpus_query_efficient`
   - `test_deduplication_query_efficient`
   - `test_analytics_aggregation_query`

**Mock Strategy**: Use pytest-postgresql for isolated database testing.

### 3. Functional Tests

Test business logic and workflow correctness.

#### Functional Test Cases

1. **Voice Validation Correctness**
   - Test with real-world examples from the project
   - Test edge cases discovered in production
   - Test combinations of violations

2. **Reply Quality**
   - Test reply appropriateness for different commercial priorities
   - Test learning corpus influence on generation
   - Test feedback loop improves replies

3. **Rate Limiting**
   - Test hourly limits enforced (5 replies/hour)
   - Test daily limits enforced (20 replies/day)
   - Test session limits enforced (10 replies/session)

4. **Deduplication**
   - Test 7-day tweet history window
   - Test 48-hour same-author cooldown
   - Test unique tweet constraint

---

## Mock Strategies

### 1. OpenRouter API Mocking

**Approach**: Use `httpx-mock` for HTTP request mocking

**Example**:

```python
import pytest
from httpx_mock import HTTPXMock

@pytest.fixture
def mock_openrouter_success(httpx_mock: HTTPXMock):
    """Mock successful OpenRouter response"""
    httpx_mock.add_response(
        method="POST",
        url="https://openrouter.ai/api/v1/chat/completions",
        json={
            "choices": [{
                "message": {
                    "content": "I understand that feeling. What specific aspect challenges you most?"
                }
            }],
            "usage": {
                "prompt_tokens": 150,
                "completion_tokens": 20,
                "total_tokens": 170
            }
        },
        status_code=200
    )
    return httpx_mock

@pytest.fixture
def mock_openrouter_rate_limit(httpx_mock: HTTPXMock):
    """Mock rate limit error"""
    httpx_mock.add_response(
        method="POST",
        url="https://openrouter.ai/api/v1/chat/completions",
        json={"error": {"message": "Rate limit exceeded"}},
        status_code=429
    )
    return httpx_mock

@pytest.fixture
def mock_openrouter_timeout(httpx_mock: HTTPXMock):
    """Mock timeout"""
    from httpx import TimeoutException
    httpx_mock.add_exception(TimeoutException("Request timeout"))
    return httpx_mock
```

### 2. Telegram API Mocking

**Approach**: Mock `telegram.Bot` and `telegram.ext.Application`

**Example**:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

@pytest.fixture
def mock_telegram_bot():
    """Mock Telegram bot"""
    with patch('src.telegram_bot.approval_bot.Application') as mock_app:
        mock_bot = AsyncMock()
        mock_app.builder.return_value.token.return_value.build.return_value = mock_app
        mock_app.bot = mock_bot

        yield mock_bot

@pytest.mark.asyncio
async def test_send_approval_request(mock_telegram_bot):
    """Test sending approval request"""
    bot = TelegramApprovalBot()
    await bot.initialize()

    reply_queue_item = create_test_reply_queue_item()
    await bot.send_approval_request(reply_queue_item)

    mock_telegram_bot.send_message.assert_called_once()
    call_args = mock_telegram_bot.send_message.call_args
    assert 'New Reply Ready for Approval' in call_args.kwargs['text']
```

### 3. Database Mocking

**Approach**: Use pytest-postgresql for real isolated database or SQLite for lightweight tests

**Example**:

```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.db.models import Base

@pytest.fixture(scope='function')
def test_db():
    """Create test database for each test"""
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    session = Session()

    yield session

    session.close()
    Base.metadata.drop_all(engine)

def test_reply_queue_creation(test_db):
    """Test creating reply queue entry"""
    queue_entry = ReplyQueue(
        tweet_id='123',
        tweet_author='testuser',
        tweet_text='Test tweet',
        reply_text='Test reply',
        status='pending'
    )

    test_db.add(queue_entry)
    test_db.commit()

    retrieved = test_db.query(ReplyQueue).filter_by(tweet_id='123').first()
    assert retrieved is not None
    assert retrieved.status == 'pending'
```

### 4. Config Mocking

**Approach**: Use `pytest-mock` to override config values

**Example**:

```python
import pytest

@pytest.fixture
def mock_config_strict_mode(mocker):
    """Mock config with strict voice validation"""
    mock_config = MagicMock()
    mock_config.voice.validation = {'strict_mode': True, 'max_violations': 0}
    mock_config.voice.character_limits = {'preferred_max': 100, 'absolute_max': 280}

    mocker.patch('src.voice.validator.get_config', return_value=(mock_config, None))
    return mock_config

def test_strict_mode_validation(mock_config_strict_mode):
    """Test voice validator in strict mode"""
    validator = VoiceValidator()
    result = validator.validate("This is great!")  # Exclamation = violation

    assert not result['is_valid']
    assert len(result['violations']) > 0
```

---

## Test Data Fixtures

### 1. Tweet Fixtures

**File**: `tests/fixtures/tweets.py`

```python
import pytest
from datetime import datetime, timedelta

@pytest.fixture
def sample_tweet_imposter_syndrome():
    """Tweet about imposter syndrome (critical priority)"""
    return {
        'id': '1234567890',
        'text': 'Struggling with major imposter syndrome today. Does anyone else feel like a fraud sometimes?',
        'author': {
            'username': 'sarah_founder',
            'display_name': 'Sarah | Building in Public',
            'followers': 1200
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
            'followers': 800
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
def sample_tweet_low_quality():
    """Low quality tweet (should be filtered)"""
    return {
        'id': '1111111111',
        'text': 'Check out my NFT drop! Limited time offer! Buy now!',
        'author': {
            'username': 'crypto_spam',
            'display_name': 'Crypto Guru',
            'followers': 50000
        },
        'created_at': datetime.utcnow() - timedelta(minutes=30),
        'public_metrics': {
            'like_count': 5,
            'reply_count': 2,
            'retweet_count': 1,
            'quote_count': 0
        }
    }
```

### 2. Reply Fixtures

**File**: `tests/fixtures/replies.py`

```python
import pytest

@pytest.fixture
def valid_british_reply():
    """Valid reply with British English"""
    return "I understand that feeling. Perhaps focus on what you've already achieved?"

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
def invalid_reply_too_long():
    """Invalid reply exceeding character limit"""
    return "I completely understand what you're going through because I've been there myself many times before, and I want to share with you that it's completely normal to feel this way when you're building something new and putting yourself out there for everyone to see and judge."

@pytest.fixture
def reply_with_warnings():
    """Reply that passes but has warnings"""
    return "I understand that feeling quite well, actually - what specific challenge are you facing right now in your journey? #BuildInPublic"  # Has hashtag (warning)
```

### 3. API Response Fixtures

**File**: `tests/fixtures/api_responses.py`

```python
import pytest

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
def telegram_message_sent_response():
    """Successful Telegram message sent response"""
    return {
        "ok": True,
        "result": {
            "message_id": 123,
            "chat": {"id": 987654321},
            "date": 1234567890,
            "text": "Test message"
        }
    }
```

### 4. Voice Test Cases JSON

**File**: `tests/data/voice_test_cases.json`

```json
[
  {
    "text": "I realise this is quite challenging, whilst many struggle with it.",
    "expected_valid": true,
    "description": "Perfect British English with qualifiers"
  },
  {
    "text": "This is amazing! You should totally do this!",
    "expected_valid": false,
    "violations": ["Contains exclamation mark(s)"],
    "description": "Exclamation marks"
  },
  {
    "text": "I realize this is challenging while many struggle with it.",
    "expected_valid": false,
    "violations": ["American spelling: 'realize'", "American spelling: 'while'"],
    "description": "American spellings"
  },
  {
    "text": "We need to leverage synergy to disrupt the market.",
    "expected_valid": false,
    "violations": ["Corporate jargon: 'leverage'", "Corporate jargon: 'synergy'", "Corporate jargon: 'disrupt'"],
    "description": "Corporate jargon"
  },
  {
    "text": "Perhaps consider what truly matters to you?",
    "expected_valid": true,
    "description": "Gentle qualifier with question"
  }
]
```

---

## Test Implementation Plan

### Phase 1: Critical Path Testing (Week 1)

**Priority: CRITICAL - DO THIS FIRST**

1. **Voice Validator Tests** (Days 1-2)
   - Implement all voice validator unit tests
   - Add parametrized tests for comprehensive coverage
   - Create voice_test_cases.json fixture
   - Target: 95%+ coverage of validator.py

2. **OpenRouter Client Tests** (Days 3-4)
   - Implement API mocking with httpx-mock
   - Test budget enforcement thoroughly
   - Test rate limiting
   - Test retry logic
   - Target: 85%+ coverage of openrouter_client.py

3. **Reply Generator Tests** (Days 5-7)
   - Mock OpenRouter client and voice validator
   - Test prompt construction
   - Test retry with feedback
   - Test learning corpus integration
   - Target: 80%+ coverage of reply_generator.py

**Deliverables**:
- `tests/unit/test_voice_validator.py` (complete)
- `tests/unit/test_openrouter_client.py` (complete)
- `tests/unit/test_reply_generator.py` (complete)
- `tests/conftest.py` (shared fixtures)
- `pytest.ini` configuration file

### Phase 2: Integration Testing (Week 2)

**Priority: HIGH**

1. **Database Integration** (Days 1-2)
   - Set up pytest-postgresql
   - Test reply queue CRUD operations
   - Test learning corpus queries
   - Test deduplication logic

2. **Pipeline Integration** (Days 3-5)
   - Test end-to-end reply generation workflow
   - Test error handling and rollback
   - Test session management
   - Test cost tracking across pipeline

**Deliverables**:
- `tests/integration/test_database_ops.py`
- `tests/integration/test_reply_pipeline.py`

### Phase 3: Telegram Bot Testing (Week 3)

**Priority: MEDIUM**

1. **Telegram Command Tests** (Days 1-2)
   - Mock Telegram API
   - Test all command handlers
   - Test callback handlers

2. **Notification Tests** (Days 3-4)
   - Test message formatting
   - Test error alerts
   - Test daily summaries

**Deliverables**:
- `tests/unit/test_telegram_bot.py`

### Phase 4: Additional Coverage (Week 4)

**Priority: MEDIUM-LOW**

1. **Functional Tests**
   - Real-world scenario testing
   - Edge case discovery
   - Performance testing

2. **Test Documentation**
   - Document test execution
   - Document CI/CD integration
   - Create test maintenance guide

**Deliverables**:
- `tests/functional/test_scenarios.py`
- `TESTING.md` documentation

---

## Priority Matrix

### Priority 1: CRITICAL (Must have before production)

| Component | Test Type | Risk | Effort | Status |
|-----------|-----------|------|--------|--------|
| Voice Validator | Unit | Brand damage | Medium | TODO |
| OpenRouter Budget | Unit | Cost overrun | Low | TODO |
| Reply Generation | Unit | Quality issues | High | TODO |

### Priority 2: HIGH (Strongly recommended)

| Component | Test Type | Risk | Effort | Status |
|-----------|-----------|------|--------|--------|
| OpenRouter API | Unit | Service failure | Medium | TODO |
| Database Ops | Integration | Data corruption | Medium | TODO |
| Pipeline Integration | Integration | Workflow failure | High | TODO |

### Priority 3: MEDIUM (Nice to have)

| Component | Test Type | Risk | Effort | Status |
|-----------|-----------|------|--------|--------|
| Telegram Commands | Unit | UX issues | Low | TODO |
| Telegram Notifications | Unit | Communication gaps | Low | TODO |
| Error Handling | Integration | Incomplete recovery | Medium | TODO |

### Priority 4: LOW (Future enhancement)

| Component | Test Type | Risk | Effort | Status |
|-----------|-----------|------|--------|--------|
| Functional Scenarios | Functional | Edge cases | High | TODO |
| Performance Tests | Performance | Scalability | High | TODO |
| Load Tests | Performance | Rate limits | Medium | TODO |

---

## Running Tests

### Setup

```bash
# Install test dependencies
pip install -r requirements-test.txt

# Set up test environment
cp .env.example .env.test
# Edit .env.test with test API keys (or use mocks)
```

### Execution

```bash
# Run all tests
pytest

# Run specific test category
pytest tests/unit/
pytest tests/integration/

# Run specific test file
pytest tests/unit/test_voice_validator.py

# Run with coverage
pytest --cov=src --cov-report=html --cov-report=term

# Run with verbose output
pytest -v

# Run only critical tests
pytest -m critical

# Run tests matching pattern
pytest -k "voice"
```

### Continuous Integration

**Recommended CI Workflow** (GitHub Actions):

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-test.txt

      - name: Run tests
        run: pytest --cov=src --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml
```

---

## Test Maintenance Guidelines

### 1. Keep Tests Fast

- Use mocks for external APIs
- Use in-memory databases (SQLite) for simple tests
- Reserve real database tests for integration suite
- Parallelize test execution with `pytest-xdist`

### 2. Keep Tests Isolated

- Each test should be independent
- Use fixtures for setup/teardown
- Don't rely on test execution order
- Clean up database state between tests

### 3. Keep Tests Readable

- Use descriptive test names (test_what_when_then)
- One assertion per test when possible
- Use parametrized tests for similar cases
- Add docstrings explaining complex test logic

### 4. Keep Tests Updated

- Update tests when code changes
- Add tests for bug fixes
- Review test coverage regularly
- Remove obsolete tests

### 5. Test Error Paths

- Test expected failures, not just success
- Test edge cases and boundary conditions
- Test error recovery and rollback
- Test timeout and retry logic

---

## Recommendations

### Immediate Actions

1. **Start with Phase 1 immediately** - Voice validator testing is critical for brand safety
2. **Set up test infrastructure** - Create test directory structure and conftest.py
3. **Install pytest and dependencies** - Get testing environment ready
4. **Create CI pipeline** - Automate test execution on commits

### Before Production Deployment

1. **Complete Priority 1 tests** - Voice validator, budget enforcement, reply generation
2. **Achieve 80%+ coverage** - For critical modules
3. **Run full integration test suite** - Verify end-to-end workflow
4. **Test with real API calls** - At least once before production

### Ongoing Testing

1. **Add tests for new features** - Make testing part of development workflow
2. **Monitor test coverage** - Use tools like codecov.io
3. **Review failing tests** - Fix immediately, don't ignore
4. **Update fixtures** - Keep test data realistic and representative

---

## Conclusion

This test strategy provides a comprehensive roadmap for testing the reply generation and posting functionality. The highest priority is **voice validation testing**, as this protects the Belief Forge brand from reputational damage.

**Recommended Next Steps**:

1. Review this strategy with the team
2. Decide: Implement tests now OR document for later?
3. If implementing now: Start with Phase 1 (Week 1)
4. If documenting for later: Keep this as reference for future development

**Estimated Effort**:
- Phase 1 (Critical): 1 week (40 hours)
- Phase 2 (Integration): 1 week (40 hours)
- Phase 3 (Telegram): 1 week (40 hours)
- Phase 4 (Additional): 1 week (40 hours)

**Total**: 4 weeks for comprehensive test coverage

**Minimum Viable Testing** (Priority 1 only): 1 week (40 hours)

---

**Document Version**: 1.0
**Last Updated**: 2025-11-10
**Author**: Testing Strategy Analysis
**Status**: Ready for Review
