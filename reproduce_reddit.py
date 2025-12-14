
import asyncio
import logging
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from src.scraping.reddit_scraper import RedditScraper

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Reddittest")

async def test_scraper_class():
    scraper = RedditScraper()
    await scraper.initialize()
    
    # Test WITH prefixes to verify fix
    subreddits = ["r/Entrepreneur", "r/startups", "buildinpublic"]
    
    for sub in subreddits:
        print(f"\nTesting '{sub}'...")
        try:
            posts = await scraper.scrape_subreddit(sub, limit=5)
            print(f"Result: Found {len(posts)} posts")
            if posts:
                print(f"Sample: {posts[0].title[:50]}...")
            else:
                print("No posts found.")
        except Exception as e:
            print(f"Error scraping {sub}: {e}")
            
    await scraper.close()

if __name__ == "__main__":
    asyncio.run(test_scraper_class())
