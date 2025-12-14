"""
OpenRouter API client for LLM-powered reply generation.

Provides a simple interface to OpenRouter's API with retry logic,
rate limiting, and cost tracking.
"""

import logging
import time
import httpx
from typing import Dict, Any, List, Optional
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from src.config.loader import get_config

logger = logging.getLogger(__name__)


class OpenRouterClient:
    """Client for OpenRouter API (Claude models)"""

    BASE_URL = "https://openrouter.ai/api/v1"

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize OpenRouter client.

        Args:
            api_key: OpenRouter API key (default: from config)
        """
        self.bot_config, self.env_config = get_config()

        if api_key is None:
            api_key = self.env_config.openrouter_api_key

        self.api_key = api_key
        self.llm_config = self.bot_config.llm
        self.model = self.llm_config.model
        self.parameters = self.llm_config.parameters

        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 60 / self.llm_config.rate_limits['requests_per_minute']

        # Cost tracking
        self.total_cost_usd = 0.0
        self.total_tokens = 0

        # HTTP client
        self.client = httpx.Client(
            base_url=self.BASE_URL,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "HTTP-Referer": "https://beliefforge.com",
                "X-Title": "Social Reply Bot"
            },
            timeout=60.0
        )

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()

    def close(self):
        """Close HTTP client"""
        self.client.close()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        reraise=True
    )
    def generate_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate completion from OpenRouter.

        Args:
            messages: List of message dicts [{"role": "system"|"user"|"assistant", "content": str}]
            temperature: Sampling temperature (default: from config)
            max_tokens: Maximum tokens to generate (default: from config)
            model: Model to use (default: from config)

        Returns:
            Dict with completion response:
            {
                "content": str,
                "model": str,
                "tokens": {"prompt": int, "completion": int, "total": int},
                "cost_usd": float
            }

        Raises:
            httpx.HTTPStatusError: On API error
            ValueError: On budget exceeded
        """
        # Check budget before making request
        daily_budget = self.llm_config.rate_limits['daily_budget_usd']
        if self.total_cost_usd >= daily_budget:
            raise ValueError(f"Daily budget exceeded: ${self.total_cost_usd:.4f} / ${daily_budget}")

        # Apply rate limiting
        self._rate_limit()

        # Use config defaults if not specified
        if temperature is None:
            temperature = self.parameters['temperature']
        if max_tokens is None:
            max_tokens = self.parameters['max_tokens']
        if model is None:
            model = self.model

        # Prepare request
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": self.parameters.get('top_p', 0.9)
        }

        logger.debug(f"Requesting completion from {model} (temp={temperature}, max_tokens={max_tokens})")

        # Make request
        try:
            response = self.client.post("/chat/completions", json=payload)
            response.raise_for_status()
            data = response.json()

            # Extract completion
            content = data['choices'][0]['message']['content']

            # Extract token usage
            usage = data.get('usage', {})
            prompt_tokens = usage.get('prompt_tokens', 0)
            completion_tokens = usage.get('completion_tokens', 0)
            total_tokens = usage.get('total_tokens', 0)

            # Estimate cost (OpenRouter provides cost in response)
            # Claude Sonnet 3.5 pricing: ~$3/1M input tokens, ~$15/1M output tokens
            estimated_cost = (prompt_tokens / 1_000_000 * 3) + (completion_tokens / 1_000_000 * 15)

            # Update tracking
            self.total_tokens += total_tokens
            self.total_cost_usd += estimated_cost

            logger.info(f"Generated completion: {len(content)} chars, {total_tokens} tokens, ${estimated_cost:.4f}")

            return {
                "content": content,
                "model": model,
                "tokens": {
                    "prompt": prompt_tokens,
                    "completion": completion_tokens,
                    "total": total_tokens
                },
                "cost_usd": estimated_cost
            }

        except httpx.HTTPStatusError as e:
            logger.error(f"OpenRouter API error: {e.response.status_code} - {e.response.text}")
            raise

        except Exception as e:
            logger.error(f"Unexpected error calling OpenRouter: {e}")
            raise

    def generate_reply(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None
    ) -> str:
        """
        Generate a reply using system and user prompts.

        Args:
            system_prompt: System prompt (voice guidelines, constraints)
            user_prompt: User prompt (tweet context, instructions)
            temperature: Sampling temperature (optional)

        Returns:
            Generated reply text
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        response = self.generate_completion(messages, temperature=temperature)
        return response['content'].strip()

    def _rate_limit(self):
        """Enforce rate limiting between requests"""
        now = time.time()
        time_since_last_request = now - self.last_request_time

        if time_since_last_request < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last_request
            logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s")
            time.sleep(sleep_time)

        self.last_request_time = time.time()

    def get_usage_stats(self) -> Dict[str, Any]:
        """
        Get usage statistics.

        Returns:
            Dict with usage stats
        """
        daily_budget = self.llm_config.rate_limits['daily_budget_usd']

        return {
            'total_tokens': self.total_tokens,
            'total_cost_usd': round(self.total_cost_usd, 4),
            'daily_budget_usd': daily_budget,
            'budget_remaining_usd': round(daily_budget - self.total_cost_usd, 4),
            'budget_used_percent': round((self.total_cost_usd / daily_budget) * 100, 2)
        }

    def reset_usage_stats(self):
        """Reset usage statistics (call at start of new day)"""
        self.total_cost_usd = 0.0
        self.total_tokens = 0
        logger.info("Usage statistics reset")


# Convenience functions
def generate_reply(system_prompt: str, user_prompt: str) -> str:
    """
    Generate a reply using OpenRouter.

    Args:
        system_prompt: System prompt
        user_prompt: User prompt

    Returns:
        Generated reply text
    """
    with OpenRouterClient() as client:
        return client.generate_reply(system_prompt, user_prompt)


if __name__ == "__main__":
    # Test OpenRouter client
    import sys

    logging.basicConfig(level=logging.INFO)

    try:
        logger.info("Testing OpenRouter client...")

        with OpenRouterClient() as client:
            # Test simple completion
            system_prompt = """You are a helpful assistant that writes very short replies.
Keep your response to under 50 characters."""

            user_prompt = "Say hello to test the API."

            logger.info(f"\nSending test request to {client.model}...")

            reply = client.generate_reply(system_prompt, user_prompt)

            logger.info(f"\n✓ OpenRouter client test successful!")
            logger.info(f"  Reply: {reply}")

            # Show usage stats
            stats = client.get_usage_stats()
            logger.info(f"\nUsage stats:")
            logger.info(f"  - Tokens: {stats['total_tokens']}")
            logger.info(f"  - Cost: ${stats['total_cost_usd']}")
            logger.info(f"  - Budget: ${stats['budget_remaining_usd']} / ${stats['daily_budget_usd']} remaining")

    except Exception as e:
        logger.error(f"\n✗ OpenRouter client test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
