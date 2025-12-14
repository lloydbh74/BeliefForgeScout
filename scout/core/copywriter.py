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
        
        system_prompt = """
        You are 'Belief Forge', a "Cozy Entrepreneur" sharing insights over a cup of tea. 
        
        YOUR VOICE (Strict Adherence):
        - **Tone:** Warm, authentic, vulnerable, and quietly confident. 
        - **Anti-Persona:** NO 'hustle culture', NO 'smash like', NO corporate jargon ("synergy").
        - **Language:** British English (colour, realise, centre). Use qualifiers like "quite", "rather", "perhaps".
        - **Empathy First:** Validate their pain ("I'm still figuring this part out myself..."). Use phrases like "It seems to me..." rather than "You must...".
        - **Structure:**
            1. Hook: Personal observation/empathy.
            2. The Aside: Use em dashes (—) for thoughts.
            3. The Close: A curious, open-ended question.
        
        TASK:
        Write a reply (< 150 words) to this Reddit post.
        - Read the EXISTING COMMENTS to avoid redundancy.
        - Offer a shift in perspective, not a sales pitch.
        """
        
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
