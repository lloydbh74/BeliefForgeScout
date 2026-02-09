import logging
from typing import List, Optional
from openai import OpenAI

from .models import ScoutPost, DraftReply
from ..config import config

logger = logging.getLogger(__name__)

class Copywriter:
    def __init__(self):
        self._client = None
        self.model = config.ai.tier2_model

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
            
            return DraftReply(
                post_id=post.id,
                content=content,
                strategy_used=f"Tier 2 ({intent})",
                status="pending"
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
            
            return DraftReply(
                post_id=comment_data['post_id'],
                content=content,
                strategy_used=f"Reply to @{comment_data['author']}",
                status="pending"
            )
        
        except Exception as e:
            logger.error(f"Reply generation failed for {comment_data['id']}: {e}")
            return DraftReply(
                post_id=comment_data['post_id'],
                content="Error generating reply.",
                strategy_used="error",
                status="error"
            )
