"""
Reddit scraper using unauthenticated JSON endpoints.
"""
import aiohttp
import logging
import asyncio
from datetime import datetime, timezone
from typing import List, Optional
import html

from src.core.models import SocialPost, Author, Platform, SocialMetrics
from src.scraping.base_scraper import SocialScraper

logger = logging.getLogger(__name__)

class RedditScraper(SocialScraper):
    """Scrapes Reddit using public JSON API"""
    
    def __init__(self, user_agent: str = "SocialReplyBot/1.0"):
        self.user_agent = user_agent
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def initialize(self) -> None:
        """Initialize HTTP session"""
        self.session = aiohttp.ClientSession(headers={
            'User-Agent': self.user_agent
        })
        
    async def close(self) -> None:
        """Close HTTP session"""
        if self.session:
            await self.session.close()
            
    async def scrape(self, query: str, limit: int = 10) -> List[SocialPost]:
        """
        Route scraping based on query type.
        If query starts with 'r/' it's a subreddit.
        Otherwise treats as a search term.
        """
        if query.startswith("r/"):
            subreddit = query.replace("r/", "")
            return await self.scrape_subreddit(subreddit, limit)
        else:
            # Fallback to searching all of reddit (implementation simplified for now)
            # For now, let's assume queries are mainly subreddits or we treat keywords as search
            return [] 

    async def scrape_subreddit(self, subreddit: str, limit: int = 25) -> List[SocialPost]:
        """
        Scrape new posts from a subreddit using .json endpoint.
        """
        if not self.session:
            await self.initialize()
            
        # Strip r/ or /r/ prefix if present to avoid double prefixing
        clean_subreddit = subreddit
        if clean_subreddit.startswith("r/"):
            clean_subreddit = clean_subreddit[2:]
        elif clean_subreddit.startswith("/r/"):
             clean_subreddit = clean_subreddit[3:]
             
        url = f"https://www.reddit.com/r/{clean_subreddit}/new.json?limit={limit}"
        logger.info(f"Scraping subreddit: r/{clean_subreddit}")
        
        try:
            async with self.session.get(url) as response:
                if response.status != 200:
                    logger.error(f"Failed to fetch Reddit data: {response.status}")
                    return []
                
                data = await response.json()
                posts = []
                
                children = data.get('data', {}).get('children', [])
                for child in children:
                    post_data = child.get('data', {})
                    if not post_data:
                        continue
                        
                    social_post = self._parse_reddit_post(post_data, subreddit)
                    if social_post:
                        posts.append(social_post)
                        
                logger.info(f"Found {len(posts)} posts in r/{subreddit}")
                
                # Respect rate limits (1 request per 2 seconds is safe for unauth)
                await asyncio.sleep(2)
                
                return posts
                
        except Exception as e:
            logger.error(f"Error scraping subreddit {subreddit}: {e}")
            return []

    def _parse_reddit_post(self, data: dict, subreddit: str) -> Optional[SocialPost]:
        """Convert raw Reddit JSON data to SocialPost"""
        try:
            # Skip pinned/stickied posts
            if data.get('stickied') or data.get('pinned'):
                return None
                
            # Basic validation
            if not data.get('title') or not data.get('author'):
                return None
                
            # Construct text from title + selftext
            title = data.get('title', '')
            selftext = data.get('selftext', '')
            full_text = f"{title}\n\n{selftext}".strip()
            
            # Timestamp
            created_utc = data.get('created_utc', 0)
            created_at = datetime.fromtimestamp(created_utc, tz=timezone.utc)
            
            # Author
            author = Author(
                username=data.get('author', 'unknown'),
                display_name=data.get('author', 'unknown'),
                platform=Platform.REDDIT,
                platform_id=data.get('author_fullname'),
                created_at=None, # Not readily available in post listing
                is_verified=False 
            )
            
            # Metrics
            metrics = SocialMetrics(
                likes=data.get('ups', 0),
                replies=data.get('num_comments', 0),
                shares=data.get('num_crossposts', 0),
                impressions=data.get('view_count', 0) or 0
            )
            
            # ID and URL
            post_id = data.get('id')
            permalink = data.get('permalink', '')
            url = f"https://www.reddit.com{permalink}"
            
            return SocialPost(
                id=post_id,
                platform=Platform.REDDIT,
                text=full_text,
                author=author,
                created_at=created_at,
                url=url,
                metrics=metrics,
                search_term=f"r/{subreddit}",
                raw_data=data
            )
            
        except Exception as e:
            logger.warning(f"Error parsing Reddit post: {e}")
            return None
