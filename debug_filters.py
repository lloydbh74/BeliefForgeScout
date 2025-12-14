
import sys
import os
import logging
from datetime import datetime

# Add project root to path
sys.path.append(os.getcwd())

from src.filtering.base_filter import BaseFilter
from src.core.models import Platform

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("FilterDebug")

def test_reddit_post_filtering():
    print("Initializing BaseFilter...")
    base_filter = BaseFilter()
    
    # Mock a Reddit post as it appears after scraping -> to_dict() or similar
    # BaseFilter expects a dictionary similar to what the scraper produces
    # But wait, Scraper produces SocialPost objects.
    # BaseFilter.filter_tweets_batch takes List[Dict[str, Any]].
    # Yet Orchestrator passes SocialPost objects?
    # Let's check Orchestrator again.
    # Orchestrator Line 354: passed, rejected = self.base_filter.filter_tweets_batch(posts)
    # If posts are SocialPost objects, then BaseFilter must handle objects OR dictionaries.
    # Let's check BaseFilter code again.
    # BaseFilter._check_engagement: author = tweet.get('author', {})
    # It attempts dictionary access `.get()`.
    # SocialPost objects don't have .get(). They are Pydantic or Dataclasses?
    # Let's check src/core/models.py to see if SocialPost has __getitem__ or if it's a dict.
    
    # Assuming for a moment Orchestrator passes objects and BaseFilter breaks, 
    # OR SocialPost implements __getitem__.
    
    # Let's create a partial mock that behaves like the Scraper output dict (legacy)
    # or the object if that's what's used.
    
    # RedditScraper produces SocialPost.
    # Orchestrator passes list of SocialPost.
    # BaseFilter calls tweet.get().
    
    print("\n--- Testing Mock Reddit Post ---")
    mock_reddit_post = {
        'id': 't3_1pl0k3y',
        'text': 'What are you building right now? Share your startup!',
        'author': {
            'username': 'some_founder',
            'followers_count': 0, # Reddit scraper doesn't set this, so it's 0 or None
        },
        'created_at': datetime.utcnow().isoformat() + 'Z',
        'public_metrics': {
            'like_count': 5,
            'reply_count': 2,
            'retweet_count': 0
        },
        'language': 'en',
        'platform': 'reddit'
    }
    
    passes, reason = base_filter.filter_tweet(mock_reddit_post)
    print(f"Result: {'PASSED' if passes else 'REJECTED'}")
    if not passes:
        print(f"Reason: {reason}")

if __name__ == "__main__":
    test_reddit_post_filtering()
