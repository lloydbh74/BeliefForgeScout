import asyncio
import logging
from src.scraping.reddit_scraper import RedditScraper

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_reddit_scraper():
    print("Initializing RedditScraper...")
    scraper = RedditScraper()
    await scraper.initialize()
    
    try:
        subreddit = "python"
        print(f"Scraping subreddit: r/{subreddit}...")
        posts = await scraper.scrape_subreddit(subreddit, limit=5)
        
        print(f"Found {len(posts)} posts.")
        
        for i, post in enumerate(posts):
            print(f"\n--- Post {i+1} ---")
            print(f"ID: {post.id}")
            print(f"Author: {post.author.username}")
            print(f"Title: {post.text[:50]}...")
            print(f"Metrics: Likes={post.metrics.likes}, Replies={post.metrics.replies}")
            print(f"URL: {post.url}")
            
            # Verify dict access
            print(f"Dict Access Test (post['text']): {post['text'][:20]}...")
            
    except Exception as e:
        logger.error(f"Scraping failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await scraper.close()
        print("\nScraper closed.")

if __name__ == "__main__":
    asyncio.run(test_reddit_scraper())
