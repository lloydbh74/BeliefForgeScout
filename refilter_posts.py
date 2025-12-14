
import asyncio
import logging
import os
import sys
from datetime import datetime
import aiohttp

# Add project root to path
sys.path.append(os.getcwd())

from sqlalchemy import or_
from src.db.connection import get_db
from src.db.models import ScrapedTweet
from src.core.orchestrator import BotOrchestrator
from src.core.models import SocialPost, Platform, Author, SocialMetrics

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("RefilterPosts")

async def fetch_reddit_post(session, post_id, scraper_instance):
    """Fetch a single Reddit post by ID logic with retries"""
    url = f"https://www.reddit.com/comments/{post_id}.json"
    retries = 3
    base_delay = 5
    
    for attempt in range(retries):
        try:
            async with session.get(url) as response:
                if response.status == 429:
                    wait_time = base_delay * (2 ** attempt)
                    logger.warning(f"Rate limited for post {post_id}. Waiting {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    continue
                    
                if response.status != 200:
                    logger.warning(f"Failed to fetch post {post_id}: HTTP {response.status}")
                    return None
                
                data = await response.json()
                if not isinstance(data, list) or not data:
                    return None
                
                # Reddit post JSON structure: List of listings. First listing contains the post.
                post_listing = data[0]
                children = post_listing.get('data', {}).get('children', [])
                if not children:
                    return None
                    
                post_data = children[0].get('data', {})
                return scraper_instance._parse_reddit_post(post_data, "unknown")
                
        except Exception as e:
            logger.error(f"Error fetching post {post_id}: {e}")
            return None
            
    return None

async def process_candidates():
    logger.info("Starting refilter process...")
    
    # 1. Initialize Orchestrator to get components
    orchestrator = BotOrchestrator()
    await orchestrator.initialize() # For scrapers/reply generator
    
    # We need a dedicated http session for our fetcher (or use the one in scraper)
    # Orchestrator initializes RedditScraper
    reddit_scraper = None
    for s in orchestrator.scrapers:
        if s.__class__.__name__ == 'RedditScraper':
            reddit_scraper = s
            break
            
    if not reddit_scraper:
        logger.error("Reddit scraper not found in orchestrator")
        return

    # 2. Get Candidates
    with get_db() as db:
        # Filter for Reddit posts that were rejected
        # We look for "filtered" status and search_term starting with "r/" 
        # (Assuming search_term was correctly populated)
        candidates = db.query(ScrapedTweet).filter(
            ScrapedTweet.status == 'filtered',
            ScrapedTweet.search_term.like('r/%')
        ).all()
        
        logger.info(f"Found {len(candidates)} filtered Reddit candidates")
        
        processed_count = 0
        queued_count = 0
        
        for candidate in candidates:
            # Check rejection reason if we want to be specific
            # if "Too few followers" not in (candidate.rejection_reason or ""):
            #     continue
            
            logger.info(f"Processing candidate {candidate.tweet_id} ({candidate.status}: {candidate.rejection_reason})")
            
            # 3. Re-scrape to get fresh metrics
            post = await fetch_reddit_post(reddit_scraper.session, candidate.tweet_id, reddit_scraper)
            
            if not post:
                logger.warning(f"Could not re-scrape post {candidate.tweet_id}. Skipping.")
                continue
                
            # 4. Re-run Base Filter
            passed, reason = orchestrator.base_filter.filter_tweet(post)
            if not passed:
                logger.info(f"Post {post.id} still rejected: {reason}")
                # Update reason if changed
                candidate.rejection_reason = reason
                db.commit()
                continue
                
            logger.info(f"Post {post.id} PASSED base filter")
            
            # 5. Commercial Filter
            # CommercialFilter expects list
            passed_comm, rejected_comm = orchestrator.commercial_filter.filter_posts_batch([post])
            if not passed_comm:
                logger.info(f"Post {post.id} rejected by commercial filter")
                candidate.status = 'filtered'
                candidate.rejection_reason = "Commercial filter rejection"
                db.commit()
                continue
                
            # 6. Scorer
            score_result = orchestrator.scorer.score_post(post)
            orchestrator.scorer.filter_and_rank([post], apply_threshold=True)
            
            if not post.score['meets_threshold']:
                logger.info(f"Post {post.id} scored low ({post.score['total_score']})")
                candidate.status = 'scored_low'
                candidate.score_details = post.score
                db.commit()
                continue
                
            logger.info(f"Post {post.id} passed scoring ({post.score['total_score']})")
            
            # 7. Generate Reply & Queue
            # Reuse _generate_replies logic or call generator directly
            # _generate_replies checks session limits, we might want to override or respect?
            # Let's call generator directly
            try:
                reply_data = await orchestrator.reply_generator.generate_reply(post)
                post.generated_reply = reply_data
                
                # Send for approval (creates ReplyQueue entry)
                # Orchestrator._send_for_approval expects list
                await orchestrator._send_for_approval([post])
                
                logger.info(f"Post {post.id} QUEUED for approval")
                
                # Update ScrapedTweet status (Orchestrator._send_for_approval updates it too via _log_post_processing)
                # But refilter script might have separate session.
                # DB changes in _send_for_approval are committed.
                
                queued_count += 1
                
            except Exception as e:
                logger.error(f"Failed to generate/queue reply: {e}")
            
            processed_count += 1
            # Rate limiting
            await asyncio.sleep(5)

    logger.info(f"Refilter complete. Processed {processed_count}, Queued {queued_count}")
    await orchestrator.shutdown()

if __name__ == "__main__":
    asyncio.run(process_candidates())
