"""
Reply generator using OpenRouter LLM with learning corpus.

Constructs prompts with voice guidelines, commercial context, and examples
from successful past replies to maintain consistency.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from src.llm.openrouter_client import OpenRouterClient
from src.voice.validator import VoiceValidator
from src.db.models import ReplyPerformance
from src.db.connection import get_db
from src.config.loader import get_config

logger = logging.getLogger(__name__)


class ReplyGenerator:
    """Generates tweet replies using LLM with learning from past successes"""

    def __init__(self):
        """Initialize reply generator"""
        self.bot_config, _ = get_config()
        self.llm_config = self.bot_config.llm
        self.voice_config = self.bot_config.voice

        self.llm_client = OpenRouterClient()
        self.voice_validator = VoiceValidator()

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.llm_client.close()

    def generate_reply(
        self,
        tweet: Dict[str, Any],
        max_attempts: int = 3,
        session: Optional[Session] = None
    ) -> Dict[str, Any]:
        """
        Generate a reply for a tweet with voice validation.

        Args:
            tweet: Tweet data dictionary
            max_attempts: Maximum generation attempts
            session: Database session (optional)

        Returns:
            Dict with reply data:
            {
                'reply_text': str,
                'validation': Dict,
                'attempt_number': int,
                'llm_cost_usd': float,
                'generated_at': str
            }

        Raises:
            ValueError: If unable to generate valid reply after max_attempts
        """
        should_close = session is None
        if session is None:
            session = next(get_db())

        try:
            # Build prompts
            system_prompt = self._build_system_prompt(tweet.get('platform'))
            user_prompt = self._build_user_prompt(tweet, session)

            total_cost = 0.0

            for attempt in range(1, max_attempts + 1):
                logger.info(f"Generating reply (attempt {attempt}/{max_attempts})...")

                # Generate reply
                response = self.llm_client.generate_completion(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ]
                )

                reply_text = response['content'].strip()
                total_cost += response['cost_usd']

                # Validate voice
                validation = self.voice_validator.validate(reply_text, platform=tweet.get('platform'))

                logger.info(f"Generated reply (attempt {attempt}): {len(reply_text)} chars, validation score: {validation['score']}")

                # Check if valid
                if validation['is_valid']:
                    logger.info(f"✓ Valid reply generated on attempt {attempt}")

                    return {
                        'reply_text': reply_text,
                        'validation': validation,
                        'attempt_number': attempt,
                        'llm_cost_usd': total_cost,
                        'generated_at': datetime.utcnow().isoformat()
                    }
                else:
                    logger.warning(f"Reply validation failed: {validation['violations']}")

                    # If not last attempt, adjust user prompt with feedback
                    if attempt < max_attempts:
                        user_prompt = self._build_user_prompt_with_feedback(
                            tweet, validation, reply_text, session
                        )

            # Failed to generate valid reply
            raise ValueError(f"Failed to generate valid reply after {max_attempts} attempts")

        finally:
            if should_close:
                session.close()

    def _build_system_prompt(self, platform: Optional[str] = None) -> str:
        """Build system prompt with voice guidelines and constraints"""
        
        # Platform-specific limits
        is_reddit = platform == 'reddit' or (hasattr(platform, 'value') and platform.value == 'reddit')
        
        pref_max = 1000 if is_reddit else self.voice_config.character_limits['preferred_max']
        abs_max = 5000 if is_reddit else self.voice_config.character_limits['absolute_max']
        
        prompt = f"""You are a thoughtful assistant helping Belief Forge engage with entrepreneurs.
"""
        prompt += f"""
# Brand Context
Belief Forge helps entrepreneurs overcome belief-based barriers (imposter syndrome, self-doubt, brand clarity struggles) to build authentic, purpose-driven businesses.

# Voice Guidelines (CRITICAL - MUST FOLLOW)

## Tone
{self.voice_config.tone}

## Language
{self.voice_config.language}

## Character Limits
- Preferred maximum: {pref_max} characters
- Absolute maximum: {abs_max} characters
"""

        if is_reddit:
             prompt += "- AIM FOR DEPTH: Write 3-5 sentences or short paragraphs. Be thorough and helpful.\n"
        else:
             prompt += f"- KEEP IT SHORT: Aim for {pref_max} characters or less. Twitter style.\n"

        prompt += """
## Required Patterns
"""
        for pattern in self.voice_config.required_patterns:
            prompt += f"- {pattern}\n"

        prompt += """
## STRICT AVOIDANCE (NEVER USE)
"""
        for avoidance in self.voice_config.strict_avoidance:
            prompt += f"- {avoidance}\n"

        prompt += """
# Reply Guidelines
1. Be genuinely helpful, not promotional
2. Share relatable insights from experience
3. Ask thoughtful questions to deepen conversation
4. Use gentle qualifiers (quite, rather, perhaps, might)
5. Write as if texting a friend you respect
6. Focus on ONE clear point or question
7. Make it conversational and authentic
"""

        if is_reddit:
            prompt += """
# Reddit Specifics
- You are replying to a forum post, not a tweet.
- Use formatting (bullet points, bold) if it helps clarity.
- Don't use hashtags.
"""

        prompt += f"""
# Examples of Good Replies
- "I've found that naming the imposter syndrome actually helps. What specific doubt shows up most for you?"
- "For my fellow founders: the clarity comes through doing, not just thinking. Which first step feels right?"
- "I used to think I needed perfect positioning. Turns out, serving one person well taught me everything."

Remember:
- NO exclamation marks
- British English only
- Warm and authentic, never corporate"""
        
        if not is_reddit:
            prompt += f"\n- Under {pref_max} characters"

        return prompt

    def _build_user_prompt(
        self,
        tweet: Dict[str, Any],
        session: Session
    ) -> str:
        """Build user prompt with tweet context and learning examples"""
        author = tweet.get('author', {})
        text = tweet.get('text', '')

        # Get commercial signals
        commercial = tweet.get('commercial_signals', {})
        priority = commercial.get('priority', 'baseline')
        matched_keywords = commercial.get('matched_keywords', [])

        prompt = f"""# Tweet to Reply To

Author: @{author.get('username')}
Tweet: "{text}"

# Context
"""

        # Add commercial context
        if priority != 'baseline':
            prompt += f"Priority: {priority.upper()}\n"
            if matched_keywords:
                prompt += f"Keywords detected: {', '.join(matched_keywords)}\n"

        prompt += """
# Your Task
Write a thoughtful, authentic reply that:
1. Acknowledges their specific challenge
2. Offers a relatable insight or gentle question
3. Invites continued conversation
4. Stays under 100 characters if possible

"""

        # Add learning corpus examples
        if self.llm_config.learning['enabled']:
            examples = self._get_learning_examples(session)
            if examples:
                prompt += "# Examples of Successful Past Replies\n\n"
                for i, example in enumerate(examples, 1):
                    prompt += f"Example {i}:\n"
                    prompt += f"Original tweet: \"{example.original_tweet_text[:100]}...\"\n"
                    prompt += f"Our reply: \"{example.reply_text}\"\n"
                    prompt += f"(Engagement rate: {example.engagement_rate:.1%})\n\n"

        prompt += "Now write your reply (NO explanations, just the tweet text):"

        return prompt

    def _build_user_prompt_with_feedback(
        self,
        tweet: Dict[str, Any],
        validation: Dict[str, Any],
        previous_attempt: str,
        session: Session
    ) -> str:
        """Build user prompt with feedback from previous failed attempt"""
        base_prompt = self._build_user_prompt(tweet, session)

        feedback = f"""
# Previous Attempt Failed Validation

Previous reply: "{previous_attempt}"

Violations:
"""
        for violation in validation['violations']:
            feedback += f"- {violation}\n"

        feedback += """
Please generate a new reply that fixes these violations. Remember:
- NO exclamation marks
- British English spellings (realise, colour, whilst, amongst)
- Under 100 characters if possible
- No corporate jargon or salesy language

New reply:"""

        return base_prompt + feedback

    def _get_learning_examples(self, session: Session) -> List[ReplyPerformance]:
        """
        Retrieve successful reply examples for learning corpus.

        Args:
            session: Database session

        Returns:
            List of ReplyPerformance records
        """
        corpus_size = self.llm_config.learning['corpus_size']
        min_engagement = self.llm_config.learning['min_engagement_rate']

        # Query for good examples
        examples = session.query(ReplyPerformance).filter(
            ReplyPerformance.marked_as_good_example == True,
            ReplyPerformance.engagement_rate >= min_engagement
        ).order_by(
            ReplyPerformance.posted_at.desc()
        ).limit(corpus_size).all()

        # If rotation enabled and we have examples, randomly sample
        if self.llm_config.learning['rotation'] and len(examples) > corpus_size:
            import random
            examples = random.sample(examples, corpus_size)

        return examples

    def batch_generate_replies(
        self,
        tweets: List[Dict[str, Any]],
        session: Optional[Session] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate replies for a batch of tweets.

        Args:
            tweets: List of tweet dictionaries
            session: Database session (optional)

        Returns:
            List of tweets with 'generated_reply' key added
        """
        should_close = session is None
        if session is None:
            session = next(get_db())

        try:
            results = []

            for i, tweet in enumerate(tweets, 1):
                logger.info(f"Generating reply {i}/{len(tweets)} for tweet {tweet.get('id')}...")

                try:
                    reply_data = self.generate_reply(tweet, session=session)
                    tweet['generated_reply'] = reply_data
                    results.append(tweet)

                except Exception as e:
                    logger.error(f"Failed to generate reply for tweet {tweet.get('id')}: {e}")
                    tweet['generation_error'] = str(e)
                    results.append(tweet)

            logger.info(f"Successfully generated {sum(1 for t in results if 'generated_reply' in t)}/{len(tweets)} replies")

            return results

        finally:
            if should_close:
                session.close()

    def get_generation_stats(self) -> Dict[str, Any]:
        """Get LLM usage statistics"""
        return self.llm_client.get_usage_stats()


# Convenience function
def generate_reply_for_tweet(tweet: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate a reply for a single tweet.

    Args:
        tweet: Tweet data dictionary

    Returns:
        Reply data dictionary
    """
    with ReplyGenerator() as generator:
        return generator.generate_reply(tweet)


if __name__ == "__main__":
    # Test reply generator
    import sys

    logging.basicConfig(level=logging.INFO)

    # Test tweet
    test_tweet = {
        'id': 'test_123',
        'author': {
            'username': 'test_founder',
            'display_name': 'Sarah the Founder'
        },
        'text': 'Struggling with major imposter syndrome today as I prepare for investor meetings. Does anyone else feel like a fraud sometimes?',
        'commercial_signals': {
            'priority': 'critical',
            'multiplier': 3.0,
            'matched_keywords': ['imposter syndrome']
        }
    }

    try:
        logger.info("Testing reply generator...\n")

        with ReplyGenerator() as generator:
            reply_data = generator.generate_reply(test_tweet, max_attempts=3)

            logger.info("\n✓ Reply generator test successful!")
            logger.info(f"\nGenerated reply:")
            logger.info(f"  Text: {reply_data['reply_text']}")
            logger.info(f"  Characters: {reply_data['validation']['character_count']}")
            logger.info(f"  Validation score: {reply_data['validation']['score']}")
            logger.info(f"  Attempts: {reply_data['attempt_number']}")
            logger.info(f"  Cost: ${reply_data['llm_cost_usd']:.4f}")

            if reply_data['validation']['warnings']:
                logger.info(f"\nWarnings:")
                for warning in reply_data['validation']['warnings']:
                    logger.info(f"  - {warning}")

            # Show usage stats
            stats = generator.get_generation_stats()
            logger.info(f"\nLLM Usage:")
            logger.info(f"  - Total cost: ${stats['total_cost_usd']}")
            logger.info(f"  - Budget remaining: ${stats['budget_remaining_usd']} / ${stats['daily_budget_usd']}")

    except Exception as e:
        logger.error(f"\n✗ Reply generator test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
