"""
Unit tests for OpenRouter API client.

CRITICAL: These tests ensure budget safety and cost tracking accuracy.
"""

import pytest
import httpx
from unittest.mock import Mock, patch, MagicMock
import time

from src.llm.openrouter_client import OpenRouterClient, generate_reply


@pytest.fixture
def mock_config():
    """Mock configuration for testing"""
    bot_config = Mock()
    bot_config.llm = Mock()
    bot_config.llm.model = "anthropic/claude-3.5-sonnet"
    bot_config.llm.parameters = {
        "temperature": 0.7,
        "max_tokens": 150,
        "top_p": 0.9
    }
    bot_config.llm.rate_limits = {
        "requests_per_minute": 20,
        "daily_budget_usd": 50.0
    }

    env_config = Mock()
    env_config.openrouter_api_key = "test-api-key-12345"

    return bot_config, env_config


@pytest.fixture
def mock_response_success():
    """Mock successful OpenRouter API response"""
    return {
        "choices": [{
            "message": {
                "content": "I understand your challenge. Perhaps consider focusing on what truly matters to you?"
            }
        }],
        "usage": {
            "prompt_tokens": 50,
            "completion_tokens": 20,
            "total_tokens": 70
        }
    }


class TestOpenRouterClientInitialization:
    """Test OpenRouter client initialization"""

    @patch('src.llm.openrouter_client.get_config')
    def test_init_with_default_api_key(self, mock_get_config, mock_config):
        """Test initialization with API key from config"""
        mock_get_config.return_value = mock_config

        client = OpenRouterClient()

        assert client.api_key == "test-api-key-12345"
        assert client.model == "anthropic/claude-3.5-sonnet"
        assert client.parameters["temperature"] == 0.7
        assert client.total_cost_usd == 0.0
        assert client.total_tokens == 0

    @patch('src.llm.openrouter_client.get_config')
    def test_init_with_custom_api_key(self, mock_get_config, mock_config):
        """Test initialization with custom API key"""
        mock_get_config.return_value = mock_config

        client = OpenRouterClient(api_key="custom-key")

        assert client.api_key == "custom-key"

    @patch('src.llm.openrouter_client.get_config')
    def test_rate_limit_calculation(self, mock_get_config, mock_config):
        """Test rate limit interval calculation"""
        mock_get_config.return_value = mock_config

        client = OpenRouterClient()

        # 20 req/min = 3 seconds between requests
        assert client.min_request_interval == 3.0

    @patch('src.llm.openrouter_client.get_config')
    def test_http_client_headers(self, mock_get_config, mock_config):
        """Test HTTP client has correct headers"""
        mock_get_config.return_value = mock_config

        client = OpenRouterClient()

        assert "Authorization" in client.client.headers
        assert client.client.headers["Authorization"] == "Bearer test-api-key-12345"
        assert client.client.headers["X-Title"] == "Social Reply Bot"


class TestOpenRouterClientBudgetSafety:
    """Test budget safety features (CRITICAL)"""

    @patch('src.llm.openrouter_client.get_config')
    def test_budget_check_prevents_request_when_exceeded(self, mock_get_config, mock_config):
        """CRITICAL: Test that budget check prevents requests when exceeded"""
        mock_get_config.return_value = mock_config

        client = OpenRouterClient()
        client.total_cost_usd = 50.01  # Exceed budget

        with pytest.raises(ValueError, match="Daily budget exceeded"):
            client.generate_completion([
                {"role": "user", "content": "Test"}
            ])

    @patch('src.llm.openrouter_client.get_config')
    def test_budget_check_allows_request_when_under(self, mock_get_config, mock_config, mock_response_success):
        """Test that budget check allows requests when under budget"""
        mock_get_config.return_value = mock_config

        with patch.object(httpx.Client, 'post') as mock_post:
            mock_post.return_value = Mock(
                status_code=200,
                json=lambda: mock_response_success
            )

            client = OpenRouterClient()
            client.total_cost_usd = 10.0  # Under budget

            # Should not raise
            result = client.generate_completion([
                {"role": "user", "content": "Test"}
            ])

            assert result is not None

    @patch('src.llm.openrouter_client.get_config')
    def test_cost_tracking_accumulates(self, mock_get_config, mock_config, mock_response_success):
        """CRITICAL: Test that costs accumulate across requests"""
        mock_get_config.return_value = mock_config

        with patch.object(httpx.Client, 'post') as mock_post:
            mock_post.return_value = Mock(
                status_code=200,
                json=lambda: mock_response_success
            )

            client = OpenRouterClient()

            # Make first request
            client.generate_completion([{"role": "user", "content": "Test 1"}])
            first_cost = client.total_cost_usd

            # Make second request
            client.generate_completion([{"role": "user", "content": "Test 2"}])
            second_cost = client.total_cost_usd

            # Cost should accumulate
            assert second_cost > first_cost
            assert second_cost == pytest.approx(first_cost * 2, rel=0.1)

    @patch('src.llm.openrouter_client.get_config')
    def test_cost_calculation_accuracy(self, mock_get_config, mock_config, mock_response_success):
        """CRITICAL: Test cost calculation is accurate"""
        mock_get_config.return_value = mock_config

        with patch.object(httpx.Client, 'post') as mock_post:
            mock_post.return_value = Mock(
                status_code=200,
                json=lambda: mock_response_success
            )

            client = OpenRouterClient()
            result = client.generate_completion([{"role": "user", "content": "Test"}])

            # Expected cost: (50 * 3/1M) + (20 * 15/1M) = 0.00015 + 0.0003 = 0.00045
            expected_cost = (50 / 1_000_000 * 3) + (20 / 1_000_000 * 15)

            assert result["cost_usd"] == pytest.approx(expected_cost, rel=0.001)
            assert client.total_cost_usd == pytest.approx(expected_cost, rel=0.001)


class TestOpenRouterClientRateLimiting:
    """Test rate limiting functionality"""

    @patch('src.llm.openrouter_client.get_config')
    def test_rate_limiting_delays_requests(self, mock_get_config, mock_config, mock_response_success):
        """Test that rate limiting adds delays between requests"""
        mock_get_config.return_value = mock_config

        with patch.object(httpx.Client, 'post') as mock_post:
            mock_post.return_value = Mock(
                status_code=200,
                json=lambda: mock_response_success
            )

            with patch('time.sleep') as mock_sleep:
                client = OpenRouterClient()

                # Make first request
                start = time.time()
                client.generate_completion([{"role": "user", "content": "Test 1"}])

                # Make second request immediately
                client.generate_completion([{"role": "user", "content": "Test 2"}])

                # Should have called sleep to enforce rate limit
                assert mock_sleep.called

                # Sleep duration should be close to min_request_interval
                sleep_duration = mock_sleep.call_args[0][0]
                assert sleep_duration > 0
                assert sleep_duration <= client.min_request_interval

    @patch('src.llm.openrouter_client.get_config')
    def test_rate_limiting_not_applied_if_enough_time_passed(self, mock_get_config, mock_config, mock_response_success):
        """Test that rate limiting is not applied if enough time has passed"""
        mock_get_config.return_value = mock_config

        with patch.object(httpx.Client, 'post') as mock_post:
            mock_post.return_value = Mock(
                status_code=200,
                json=lambda: mock_response_success
            )

            with patch('time.sleep') as mock_sleep:
                client = OpenRouterClient()

                # Make first request
                client.generate_completion([{"role": "user", "content": "Test 1"}])

                # Simulate time passing (more than min_request_interval)
                client.last_request_time = time.time() - 10

                # Make second request
                client.generate_completion([{"role": "user", "content": "Test 2"}])

                # Should not have called sleep for second request
                assert mock_sleep.call_count <= 1


class TestOpenRouterClientCompletion:
    """Test completion generation"""

    @patch('src.llm.openrouter_client.get_config')
    def test_generate_completion_success(self, mock_get_config, mock_config, mock_response_success):
        """Test successful completion generation"""
        mock_get_config.return_value = mock_config

        with patch.object(httpx.Client, 'post') as mock_post:
            mock_post.return_value = Mock(
                status_code=200,
                json=lambda: mock_response_success
            )

            client = OpenRouterClient()
            result = client.generate_completion([
                {"role": "system", "content": "You are helpful"},
                {"role": "user", "content": "Hello"}
            ])

            assert result["content"] == "I understand your challenge. Perhaps consider focusing on what truly matters to you?"
            assert result["model"] == "anthropic/claude-3.5-sonnet"
            assert result["tokens"]["total"] == 70
            assert result["cost_usd"] > 0

    @patch('src.llm.openrouter_client.get_config')
    def test_generate_completion_with_custom_params(self, mock_get_config, mock_config, mock_response_success):
        """Test completion with custom parameters"""
        mock_get_config.return_value = mock_config

        with patch.object(httpx.Client, 'post') as mock_post:
            mock_post.return_value = Mock(
                status_code=200,
                json=lambda: mock_response_success
            )

            client = OpenRouterClient()
            result = client.generate_completion(
                [{"role": "user", "content": "Test"}],
                temperature=0.5,
                max_tokens=100,
                model="different-model"
            )

            # Verify custom params were used in request
            call_args = mock_post.call_args
            payload = call_args[1]["json"]

            assert payload["temperature"] == 0.5
            assert payload["max_tokens"] == 100
            assert payload["model"] == "different-model"

    @patch('src.llm.openrouter_client.get_config')
    def test_generate_completion_http_error(self, mock_get_config, mock_config):
        """Test handling of HTTP errors"""
        mock_get_config.return_value = mock_config

        with patch.object(httpx.Client, 'post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 429
            mock_response.text = "Rate limit exceeded"
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "429", request=Mock(), response=mock_response
            )
            mock_post.return_value = mock_response

            client = OpenRouterClient()

            with pytest.raises(httpx.HTTPStatusError):
                client.generate_completion([{"role": "user", "content": "Test"}])

    @patch('src.llm.openrouter_client.get_config')
    def test_generate_reply_convenience_method(self, mock_get_config, mock_config, mock_response_success):
        """Test generate_reply convenience method"""
        mock_get_config.return_value = mock_config

        with patch.object(httpx.Client, 'post') as mock_post:
            mock_post.return_value = Mock(
                status_code=200,
                json=lambda: mock_response_success
            )

            client = OpenRouterClient()
            reply = client.generate_reply(
                system_prompt="Be helpful",
                user_prompt="Hello"
            )

            assert isinstance(reply, str)
            assert len(reply) > 0
            # Should strip whitespace
            assert reply == reply.strip()


class TestOpenRouterClientUsageStats:
    """Test usage statistics tracking"""

    @patch('src.llm.openrouter_client.get_config')
    def test_get_usage_stats(self, mock_get_config, mock_config):
        """Test getting usage statistics"""
        mock_get_config.return_value = mock_config

        client = OpenRouterClient()
        client.total_cost_usd = 10.5
        client.total_tokens = 1000

        stats = client.get_usage_stats()

        assert stats["total_tokens"] == 1000
        assert stats["total_cost_usd"] == 10.5
        assert stats["daily_budget_usd"] == 50.0
        assert stats["budget_remaining_usd"] == 39.5
        assert stats["budget_used_percent"] == 21.0

    @patch('src.llm.openrouter_client.get_config')
    def test_reset_usage_stats(self, mock_get_config, mock_config):
        """Test resetting usage statistics"""
        mock_get_config.return_value = mock_config

        client = OpenRouterClient()
        client.total_cost_usd = 10.5
        client.total_tokens = 1000

        client.reset_usage_stats()

        assert client.total_cost_usd == 0.0
        assert client.total_tokens == 0


class TestOpenRouterClientContextManager:
    """Test context manager functionality"""

    @patch('src.llm.openrouter_client.get_config')
    def test_context_manager_closes_client(self, mock_get_config, mock_config):
        """Test that context manager closes HTTP client"""
        mock_get_config.return_value = mock_config

        with patch.object(httpx.Client, 'close') as mock_close:
            with OpenRouterClient() as client:
                assert client is not None

            # Should have closed client
            assert mock_close.called


class TestConvenienceFunctions:
    """Test module-level convenience functions"""

    @patch('src.llm.openrouter_client.get_config')
    def test_generate_reply_function(self, mock_get_config, mock_config, mock_response_success):
        """Test generate_reply convenience function"""
        mock_get_config.return_value = mock_config

        with patch.object(httpx.Client, 'post') as mock_post:
            mock_post.return_value = Mock(
                status_code=200,
                json=lambda: mock_response_success
            )

            reply = generate_reply(
                system_prompt="Be helpful",
                user_prompt="Hello"
            )

            assert isinstance(reply, str)
            assert len(reply) > 0


class TestOpenRouterClientRetry:
    """Test retry logic for network errors"""

    @patch('src.llm.openrouter_client.get_config')
    def test_retry_on_timeout(self, mock_get_config, mock_config, mock_response_success):
        """Test that client retries on timeout"""
        mock_get_config.return_value = mock_config

        with patch.object(httpx.Client, 'post') as mock_post:
            # First call times out, second succeeds
            mock_post.side_effect = [
                httpx.TimeoutException("Request timeout"),
                Mock(status_code=200, json=lambda: mock_response_success)
            ]

            client = OpenRouterClient()
            result = client.generate_completion([{"role": "user", "content": "Test"}])

            # Should have succeeded after retry
            assert result is not None
            assert mock_post.call_count == 2

    @patch('src.llm.openrouter_client.get_config')
    def test_retry_exhaustion(self, mock_get_config, mock_config):
        """Test that retry eventually gives up"""
        mock_get_config.return_value = mock_config

        with patch.object(httpx.Client, 'post') as mock_post:
            # Always timeout
            mock_post.side_effect = httpx.TimeoutException("Request timeout")

            client = OpenRouterClient()

            with pytest.raises(httpx.TimeoutException):
                client.generate_completion([{"role": "user", "content": "Test"}])

            # Should have tried 3 times (initial + 2 retries)
            assert mock_post.call_count == 3


@pytest.mark.critical
class TestBudgetSafetyIntegration:
    """CRITICAL: Integration tests for budget safety"""

    @patch('src.llm.openrouter_client.get_config')
    def test_cannot_exceed_budget_even_with_retries(self, mock_get_config, mock_config):
        """CRITICAL: Ensure budget check happens before retries"""
        mock_get_config.return_value = mock_config

        client = OpenRouterClient()
        client.total_cost_usd = 50.01  # Already over budget

        with patch.object(httpx.Client, 'post') as mock_post:
            with pytest.raises(ValueError, match="Daily budget exceeded"):
                client.generate_completion([{"role": "user", "content": "Test"}])

            # Should NOT have made any HTTP request
            assert not mock_post.called

    @patch('src.llm.openrouter_client.get_config')
    def test_budget_check_on_every_request(self, mock_get_config, mock_config, mock_response_success):
        """CRITICAL: Ensure budget is checked on every request"""
        mock_get_config.return_value = mock_config

        with patch.object(httpx.Client, 'post') as mock_post:
            # Make cost per request push us over budget on 3rd request
            # Budget is $50, so use tokens that cost ~$30 each
            response_with_high_cost = mock_response_success.copy()
            response_with_high_cost["usage"] = {
                "prompt_tokens": 5_000_000,  # Very high token count
                "completion_tokens": 1_000_000,
                "total_tokens": 6_000_000
            }
            # Cost: (5M * 3/1M) + (1M * 15/1M) = 15 + 15 = $30

            mock_post.return_value = Mock(
                status_code=200,
                json=lambda: response_with_high_cost
            )

            client = OpenRouterClient()

            # First request should succeed ($0 -> $30 < $50)
            client.generate_completion([{"role": "user", "content": "Test 1"}])
            assert client.total_cost_usd == pytest.approx(30.0, rel=0.01)

            # Second request should succeed ($30 < $50, then becomes $60)
            client.generate_completion([{"role": "user", "content": "Test 2"}])
            assert client.total_cost_usd == pytest.approx(60.0, rel=0.01)

            # Third request should fail due to budget ($60 >= $50)
            with pytest.raises(ValueError, match="Daily budget exceeded"):
                client.generate_completion([{"role": "user", "content": "Test 3"}])
