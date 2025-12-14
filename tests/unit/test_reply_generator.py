"""
Unit tests for Reply Generator.

Tests the integration between LLM client, voice validator, and learning corpus.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from src.llm.reply_generator import ReplyGenerator


@pytest.fixture
def mock_config():
    """Mock configuration"""
    bot_config = Mock()
    bot_config.llm = Mock()
    bot_config.llm.model = "anthropic/claude-3.5-sonnet"
    bot_config.llm.parameters = {"temperature": 0.7, "max_tokens": 150}
    bot_config.voice = Mock()
    bot_config.voice.character_limits = {"preferred_max": 100, "absolute_max": 280}

    env_config = Mock()
    return bot_config, env_config


@pytest.fixture
def sample_tweet():
    """Sample tweet for testing"""
    return {
        "tweet_id": "123456789",
        "author_username": "entrepreneur_joe",
        "text": "Feeling like a fraud today. Everyone else seems to have it figured out.",
        "engagement": {"likes": 50, "retweets": 10, "replies": 5},
        "commercial_signals": ["imposter syndrome", "self-doubt"]
    }


@pytest.fixture
def valid_reply_response():
    """Mock valid reply from LLM"""
    return {
        "content": "I understand that feeling. Remember, everyone struggles sometimes.",
        "model": "anthropic/claude-3.5-sonnet",
        "tokens": {"prompt": 100, "completion": 20, "total": 120},
        "cost_usd": 0.0005
    }


@pytest.fixture
def invalid_reply_response():
    """Mock invalid reply from LLM (has exclamation mark)"""
    return {
        "content": "You're amazing! Don't worry, you've got this!",
        "model": "anthropic/claude-3.5-sonnet",
        "tokens": {"prompt": 100, "completion": 20, "total": 120},
        "cost_usd": 0.0005
    }


class TestReplyGeneratorInitialization:
    """Test Reply Generator initialization"""

    @patch('src.llm.reply_generator.get_config')
    @patch('src.llm.reply_generator.OpenRouterClient')
    @patch('src.llm.reply_generator.VoiceValidator')
    def test_init(self, mock_validator, mock_client, mock_get_config, mock_config):
        """Test initialization"""
        mock_get_config.return_value = mock_config

        generator = ReplyGenerator()

        assert generator.llm_client is not None
        assert generator.voice_validator is not None


class TestReplyGenerationSuccess:
    """Test successful reply generation"""

    @patch('src.llm.reply_generator.get_config')
    @patch('src.llm.reply_generator.get_db')
    def test_generate_valid_reply_first_attempt(
        self, mock_get_db, mock_get_config, mock_config,
        sample_tweet, valid_reply_response
    ):
        """Test generating valid reply on first attempt"""
        mock_get_config.return_value = mock_config
        mock_session = Mock()
        mock_session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
        mock_get_db.return_value = iter([mock_session])

        with patch.object(ReplyGenerator, '_build_system_prompt', return_value="System prompt"):
            with patch.object(ReplyGenerator, '_build_user_prompt', return_value="User prompt"):
                with patch('src.llm.openrouter_client.OpenRouterClient.generate_completion') as mock_generate:
                    mock_generate.return_value = valid_reply_response

                    generator = ReplyGenerator()
                    result = generator.generate_reply(sample_tweet, max_attempts=3)

                    assert result['reply_text'] == valid_reply_response['content']
                    assert result['attempt_number'] == 1
                    assert result['llm_cost_usd'] == 0.0005
                    assert result['validation']['is_valid'] is True

    @patch('src.llm.reply_generator.get_config')
    @patch('src.llm.reply_generator.get_db')
    def test_generate_valid_reply_after_retry(
        self, mock_get_db, mock_get_config, mock_config,
        sample_tweet, invalid_reply_response, valid_reply_response
    ):
        """Test generating valid reply after one invalid attempt"""
        mock_get_config.return_value = mock_config
        mock_session = Mock()
        mock_session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
        mock_get_db.return_value = iter([mock_session])

        with patch.object(ReplyGenerator, '_build_system_prompt', return_value="System prompt"):
            with patch.object(ReplyGenerator, '_build_user_prompt', return_value="User prompt"):
                with patch('src.llm.openrouter_client.OpenRouterClient.generate_completion') as mock_generate:
                    # First attempt: invalid (has exclamation)
                    # Second attempt: valid
                    mock_generate.side_effect = [invalid_reply_response, valid_reply_response]

                    generator = ReplyGenerator()
                    result = generator.generate_reply(sample_tweet, max_attempts=3)

                    assert result['reply_text'] == valid_reply_response['content']
                    assert result['attempt_number'] == 2
                    assert result['llm_cost_usd'] == 0.001  # Two attempts
                    assert result['validation']['is_valid'] is True


class TestReplyGenerationFailure:
    """Test reply generation failure scenarios"""

    @patch('src.llm.reply_generator.get_config')
    @patch('src.llm.reply_generator.get_db')
    def test_max_attempts_exceeded(
        self, mock_get_db, mock_get_config, mock_config,
        sample_tweet, invalid_reply_response
    ):
        """Test failure when max attempts exceeded"""
        mock_get_config.return_value = mock_config
        mock_session = Mock()
        mock_session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
        mock_get_db.return_value = iter([mock_session])

        with patch.object(ReplyGenerator, '_build_system_prompt', return_value="System prompt"):
            with patch.object(ReplyGenerator, '_build_user_prompt', return_value="User prompt"):
                with patch('src.llm.openrouter_client.OpenRouterClient.generate_completion') as mock_generate:
                    # All attempts return invalid replies
                    mock_generate.return_value = invalid_reply_response

                    generator = ReplyGenerator()

                    with pytest.raises(ValueError, match="Failed to generate valid reply"):
                        generator.generate_reply(sample_tweet, max_attempts=3)

                    # Should have attempted 3 times
                    assert mock_generate.call_count == 3


class TestPromptBuilding:
    """Test prompt building functionality"""

    @patch('src.llm.reply_generator.get_config')
    def test_build_system_prompt(self, mock_get_config, mock_config):
        """Test system prompt includes voice guidelines"""
        mock_get_config.return_value = mock_config

        generator = ReplyGenerator()
        system_prompt = generator._build_system_prompt()

        assert isinstance(system_prompt, str)
        assert len(system_prompt) > 0
        # Should mention British English
        assert "british" in system_prompt.lower() or "uk" in system_prompt.lower()
        # Should mention character limits
        assert "280" in system_prompt or "character" in system_prompt.lower()

    @patch('src.llm.reply_generator.get_config')
    @patch('src.llm.reply_generator.get_db')
    def test_build_user_prompt(self, mock_get_db, mock_get_config, mock_config, sample_tweet):
        """Test user prompt includes tweet context"""
        mock_get_config.return_value = mock_config
        mock_session = Mock()
        mock_session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
        mock_get_db.return_value = iter([mock_session])

        generator = ReplyGenerator()
        user_prompt = generator._build_user_prompt(sample_tweet, mock_session)

        assert isinstance(user_prompt, str)
        assert len(user_prompt) > 0
        # Should include tweet text
        assert sample_tweet["text"] in user_prompt
        # Should include author
        assert sample_tweet["author_username"] in user_prompt


class TestContextManager:
    """Test context manager functionality"""

    @patch('src.llm.reply_generator.get_config')
    def test_context_manager(self, mock_get_config, mock_config):
        """Test context manager closes LLM client"""
        mock_get_config.return_value = mock_config

        with patch('src.llm.openrouter_client.OpenRouterClient.close') as mock_close:
            with ReplyGenerator() as generator:
                assert generator is not None

            # Should have closed client
            assert mock_close.called


class TestCostTracking:
    """Test cost accumulation across attempts"""

    @patch('src.llm.reply_generator.get_config')
    @patch('src.llm.reply_generator.get_db')
    def test_cost_accumulates_across_attempts(
        self, mock_get_db, mock_get_config, mock_config,
        sample_tweet
    ):
        """Test that costs accumulate across multiple attempts"""
        mock_get_config.return_value = mock_config
        mock_session = Mock()
        mock_session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
        mock_get_db.return_value = iter([mock_session])

        # Each attempt costs $0.001
        responses = [
            {
                "content": "Invalid reply!",  # Has exclamation
                "model": "test",
                "tokens": {"total": 100},
                "cost_usd": 0.001
            },
            {
                "content": "Another invalid reply!",  # Has exclamation
                "model": "test",
                "tokens": {"total": 100},
                "cost_usd": 0.001
            },
            {
                "content": "Valid reply without issues",  # Valid
                "model": "test",
                "tokens": {"total": 100},
                "cost_usd": 0.001
            }
        ]

        with patch.object(ReplyGenerator, '_build_system_prompt', return_value="System"):
            with patch.object(ReplyGenerator, '_build_user_prompt', return_value="User"):
                with patch('src.llm.openrouter_client.OpenRouterClient.generate_completion') as mock_generate:
                    mock_generate.side_effect = responses

                    generator = ReplyGenerator()
                    result = generator.generate_reply(sample_tweet, max_attempts=3)

                    # Should have cost $0.003 total (3 attempts)
                    assert result['llm_cost_usd'] == pytest.approx(0.003, rel=0.001)


@pytest.mark.integration
class TestReplyGeneratorIntegration:
    """Integration tests (require mocked DB)"""

    @patch('src.llm.reply_generator.get_config')
    @patch('src.llm.reply_generator.get_db')
    def test_full_generation_flow(
        self, mock_get_db, mock_get_config, mock_config,
        sample_tweet, valid_reply_response
    ):
        """Test complete generation flow"""
        mock_get_config.return_value = mock_config
        mock_session = Mock()
        mock_session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
        mock_get_db.return_value = iter([mock_session])

        with patch.object(ReplyGenerator, '_build_system_prompt', return_value="System prompt"):
            with patch.object(ReplyGenerator, '_build_user_prompt', return_value="User prompt"):
                with patch('src.llm.openrouter_client.OpenRouterClient.generate_completion') as mock_generate:
                    mock_generate.return_value = valid_reply_response

                    with ReplyGenerator() as generator:
                        result = generator.generate_reply(sample_tweet)

                        # Verify result structure
                        assert 'reply_text' in result
                        assert 'validation' in result
                        assert 'attempt_number' in result
                        assert 'llm_cost_usd' in result
                        assert 'generated_at' in result

                        # Verify validation was performed
                        assert result['validation']['is_valid'] is True
                        assert result['validation']['score'] >= 0
