import logging
from typing import List
from openai import OpenAI

from .models import ScoutPost, DraftReply
from .text_utils import normalize_whitespace
from ..config import config

logger = logging.getLogger(__name__)

class Copywriter:
    def __init__(self):
        self._client = None
        self.model = config.ai.tier2_model
        # Rates per 1M tokens (USD)
        self.rates = {
            "gpt-4o": {"prompt": 5.0, "completion": 15.0},
            "anthropic/claude-3.5-sonnet": {"prompt": 3.0, "completion": 15.0},
            "openai/gpt-3.5-turbo": {"prompt": 0.5, "completion": 1.5},
            "meta-llama/llama-3-8b": {"prompt": 0.05, "completion": 0.05},
            "meta-llama/llama-3-70b": {"prompt": 0.59, "completion": 0.79}
        }

    def _calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        rate = self.rates.get(self.model, {"prompt": 1.0, "completion": 3.0}) # Fallback to rough avg
        cost = (prompt_tokens * rate["prompt"] / 1_000_000) + (completion_tokens * rate["completion"] / 1_000_000)
        return round(cost, 6)

    @property
    def client(self):
        if not self._client:
            self._client = OpenAI(
                base_url=config.ai.base_url,
                api_key=config.ai.api_key
            )
        return self._client

    def generate_draft(self, post: ScoutPost, intent: str) -> DraftReply:
        """
        Generate a 'Tribe Voice' draft using Tier 2 model.
        """
        logger.info(f"Generating draft for {post.id} (Intent: {intent})...")
        
        # Context Awareness: Include top comments to avoid redundancy
        context_str = "\n".join([f"- {c}" for c in post.top_comments])
        
        # Get Dynamic Prompt (or fallback)
        dynamic_prompt = config.settings.get("system_prompt", "")
        if not dynamic_prompt:
             # Fallback if empty
             dynamic_prompt = """
             You are 'Belief Forge'. Helpful, authentic, british english.
             """

        system_prompt = dynamic_prompt
        
        user_prompt = f"""
        POST TITLE: {post.title}
        POST BODY: {post.content}
        INTENT DETECTED: {intent}
        
        EXISTING COMMENTS (Do not repeat these):
        {context_str}
        
        Draft the reply:
        """

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            
            content = response.choices[0].message.content.strip()
            content = normalize_whitespace(content)
            
            # Usage
            usage = response.usage
            cost = self._calculate_cost(usage.prompt_tokens, usage.completion_tokens)
            
            return DraftReply(
                post_id=post.id,
                content=content,
                strategy_used=f"Tier 2 ({intent})",
                status="pending",
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
                total_cost=cost
            )

        except Exception as e:
            logger.error(f"Copywriter failed for {post.id}: {e}")
            return DraftReply(
                post_id=post.id, 
                content="Error generating draft.", 
                strategy_used="error", 
                status="error"
            )
    
    def generate_reply_draft(self, comment_data: dict, context: List[dict] = None) -> DraftReply:
        """
        Generate a reply to an existing comment with thread context.
        
        Args:
            comment_data: Dictionary with comment info (from fetch_comment_by_id)
            context: Optional list of ancestor comments for thread context
            
        Returns:
            DraftReply object
        """
        logger.info(f"Generating reply to comment {comment_data['id']}...")
        
        # Build context string
        context_str = ""
        if context:
            context_str = "\n\nTHREAD CONTEXT (earlier comments):\n"
            for i, ctx in enumerate(context, 1):
                context_str += f"{i}. @{ctx['author']}: {ctx['body']}\n"
        
        # Get dynamic prompt
        dynamic_prompt = config.settings.get("system_prompt", "")
        if not dynamic_prompt:
            dynamic_prompt = """
            You are 'Belief Forge'. Helpful, authentic, british english.
            """
        
        system_prompt = dynamic_prompt
        
        user_prompt = f"""
        ORIGINAL POST: {comment_data['post_title']}
        POST CONTENT: {comment_data['post_content']}
        {context_str}
        
        YOU ARE REPLYING TO:
        @{comment_data['author']} said: {comment_data['body']}
        
        Draft a thoughtful reply that:
        1. Directly addresses @{comment_data['author']}'s comment
        2. Stays relevant to the original post context
        3. Adds value to the conversation
        
        Your reply:
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            
            content = response.choices[0].message.content.strip()
            content = normalize_whitespace(content)
            
            # Usage
            usage = response.usage
            cost = self._calculate_cost(usage.prompt_tokens, usage.completion_tokens)
            
            return DraftReply(
                post_id=comment_data['post_id'],
                content=content,
                strategy_used=f"Reply to @{comment_data['author']}",
                status="pending",
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
                total_cost=cost
            )
        
        except Exception as e:
            logger.error(f"Reply generation failed for {comment_data['id']}: {e}")
            return DraftReply(
                post_id=comment_data['post_id'],
                content="Error generating reply.",
                strategy_used="error",
                status="error"
            )
    def detect_bot_score(self, text: str) -> dict:
        """
        Analyze a comment and return a bot probability score AND usage data.
        """
        logger.info("Analyzing bot score for comment...")
        
        system_prompt = """
        You are an expert at identifying AI-generated spam and bot behavior on Reddit.
        Analyze the provided text and return ONLY a single float between 0.0 (definitely human) and 1.0 (definitely AI).
        
        Indicators of a bot:
        - Excessive generic praise.
        - Perfect grammar but lack of nuance.
        - Repetitive sentence structures.
        - Non-sequiturs that sound vaguely relevant.
        """
        
        user_prompt = f"Text to analyze: \"{text}\"\n\nBot Score (0.0 - 1.0):"
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=10
            )
            score_str = response.choices[0].message.content.strip()
            
            # Usage
            usage = response.usage
            cost = self._calculate_cost(usage.prompt_tokens, usage.completion_tokens)
            
            # Extract float
            import re
            match = re.search(r"(\d+\.\d+|\d+)", score_str)
            score = float(match.group(1)) if match else 0.5
            
            return {
                "score": score,
                "prompt_tokens": usage.prompt_tokens,
                "completion_tokens": usage.completion_tokens,
                "total_cost": cost
            }
        except Exception as e:
            logger.error(f"Bot detection failed: {e}")
            return {"score": 0.0, "prompt_tokens": 0, "completion_tokens": 0, "total_cost": 0.0}

    def generate_personalized_dm(self, template: str, user_data: dict, topic: str, context_body: str) -> str:
        """
        Draft a deeply personalized DM using the provided template and context.
        """
        logger.info(f"Generating personalized DM for @{user_data.get('author')}...")
        
        system_prompt = """
        You are 'Belief Forge'. Your goal is to personalize a recruitment message for a potential beta tester.
        """
        
        user_prompt = f"""
        TEMPLATE:
        {template}
        
        USER DATA:
        Name/Handle: @{user_data.get('author')}
        Topic: {topic}
        Their Comment: {context_body}
        
        TASK:
        Replace the placeholders in the template with contextually relevant information.
        Pay special attention to '{{deep_insight}}' or personalized hooks. 
        Ensure the '{{deep_insight}}' mentions a specific detail from their comment to prove authenticity.
        
        Return the FINAL message only.
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            content = response.choices[0].message.content.strip()
            
            # Usage
            usage = response.usage
            cost = self._calculate_cost(usage.prompt_tokens, usage.completion_tokens)
            
            return {
                "content": content,
                "prompt_tokens": usage.prompt_tokens,
                "completion_tokens": usage.completion_tokens,
                "total_cost": cost
            }
        except Exception as e:
            logger.error(f"DM generation failed: {e}")
            return {"content": template, "prompt_tokens": 0, "completion_tokens": 0, "total_cost": 0.0}
