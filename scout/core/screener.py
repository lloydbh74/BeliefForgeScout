import json
import logging
from typing import List, Dict, Optional
from openai import OpenAI
import time

from .models import ScoutPost, AnalysisResult
from ..config import config

logger = logging.getLogger(__name__)

class Screener:
    def __init__(self):
        self._client = None
        self.model = config.ai.tier1_model

    @property
    def client(self):
        if not self._client:
            self._client = OpenAI(
                base_url=config.ai.base_url,
                api_key=config.ai.api_key
            )
        return self._client

    def analyze_batch(self, posts: List[ScoutPost]) -> List[AnalysisResult]:
        """
        Analyze a batch of posts for relevance and intent.
        Grouping posts is cheaper/faster for Tier 1 models.
        """
        results = []
        if not posts:
            return results

        logger.info(f"Screening batch of {len(posts)} posts using {self.model}...")

        # Prepare the prompt payload
        posts_text = ""
        for i, post in enumerate(posts):
            posts_text += f"""
            --- POST {i} (ID: {post.id}) ---
            SUBREDDIT: r/{post.subreddit}
            TITLE: {post.title}
            BODY: {post.content[:500]}... (truncated)
            """

        system_prompt = """
        You are the 'Belief Forge Scout'. Your mission is to find high-value conversations for a supportive entrepreneurship brand.
        
        CLASSIFICATION RULES:
        1. RELEVANT: A founder/creator actively struggling, asking for strategy, or needing mindset help.
        2. IGNORE: Self-promotion, success stories, news, generic low-effort questions, crypto/spam.
        
        INTENT CATEGORIES:
        - 'distress': Burnout, depression, want to quit. (High Priority)
        - 'strategy': 'How do I X?', marketing questions, technical help. (Medium Priority)
        - 'venting': Complaining about customers/platform. (Low Priority)
        - 'ignore': Irrelevant.
        
        Output a valid JSON object with keys: "results": [ { "post_id": "...", "is_relevant": true/false, "intent": "...", "confidence": 0.0-1.0, "reasoning": "short reason" } ]
        """

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Analyze these {len(posts)} posts:\n{posts_text}"}
                ],
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            parsed = json.loads(content)
            
            # Map back to AnalysisResult objects
            results_map = {item['post_id']: item for item in parsed.get('results', [])}
            
            for post in posts:
                if post.id in results_map:
                    res = results_map[post.id]
                    results.append(AnalysisResult(
                        post_id=res.get('post_id'),
                        is_relevant=res.get('is_relevant', False),
                        intent=res.get('intent', 'ignore'),
                        confidence=res.get('confidence', 0.0),
                        reasoning=res.get('reasoning', '')
                    ))
                else:
                    # Fallback if LLM missed one
                    logger.warning(f"Screener missed ID {post.id} in batch response.")

        except Exception as e:
            logger.error(f"Screener batch analysis failed: {e}")
            
        logger.info(f"Screening complete. Found {len([r for r in results if r.is_relevant])} relevant posts.")
        return results
