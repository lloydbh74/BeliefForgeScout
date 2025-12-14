"""
Twitter/X scraper using Playwright for browser automation.

Scrapes tweets from hashtags, lists, and user profiles while maintaining
authenticated session via cookies.
"""

import json
import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
import re

from src.config.loader import get_config
from src.core.models import SocialPost, Author, Platform, SocialMetrics
from src.scraping.base_scraper import SocialScraper

logger = logging.getLogger(__name__)


class TwitterScraper(SocialScraper):
    """Scrapes tweets from Twitter/X using Playwright browser automation"""

    def __init__(self, cookies_path: Optional[str] = None, headless: bool = True):
        """
        Initialize Twitter scraper.

        Args:
            cookies_path: Path to cookies.json file (default: data/cookies.json)
            headless: Run browser in headless mode (default: True)
        """
        self.bot_config, self.env_config = get_config()

        if cookies_path is None:
            project_root = Path(__file__).parent.parent.parent
            cookies_path = project_root / "data" / "cookies.json"

        self.cookies_path = Path(cookies_path)
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

    async def __aenter__(self):
        """Async context manager entry"""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()

    async def initialize(self) -> None:
        """Initialize browser and load Twitter cookies"""
        try:
            playwright = await async_playwright().start()

            # Launch browser
            self.browser = await playwright.chromium.launch(
                headless=self.headless,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox'
                ]
            )

            # Create context with cookies
            self.context = await self.browser.new_context(
                viewport={'width': 1280, 'height': 720},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )

            # Load cookies if available
            if self.cookies_path.exists():
                with open(self.cookies_path, 'r') as f:
                    cookies = json.load(f)
                await self.context.add_cookies(cookies)
                logger.info(f"Loaded {len(cookies)} cookies from {self.cookies_path}")
            else:
                logger.warning(f"No cookies found at {self.cookies_path}. Authentication may be required.")

            # Create page
            self.page = await self.context.new_page()

            # Add random delays to appear more human
            await self.page.set_extra_http_headers({
                'Accept-Language': 'en-GB,en;q=0.9'
            })

            logger.info("Browser initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize browser: {e}")
            raise

    async def close(self) -> None:
        """Close browser and cleanup"""
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        logger.info("Browser closed")

    async def scrape(self, query: str, limit: int = 10) -> List[SocialPost]:
        """
        Generic scrape routing.
        Allows scraping by #hashtag, string (keyword), or list_url.
        """
        if query.startswith("http") and "twitter.com/i/lists" in query:
             return await self.scrape_list(query, limit)
        elif query.startswith("#"):
             return await self.scrape_hashtag(query, limit)
        else:
             return await self.scrape_keyword(query, limit)

    async def scrape_hashtag(self, hashtag: str, max_tweets: int = 20) -> List[SocialPost]:
        """
        Scrape tweets from a hashtag.
        """
        if not self.page:
            raise RuntimeError("Browser not initialized. Call initialize() first.")

        # Normalize hashtag
        hashtag = hashtag.lstrip('#')
        search_url = f"https://twitter.com/search?q=%23{hashtag}&src=typed_query&f=live"

        logger.info(f"Scraping hashtag: #{hashtag}")

        try:
            # Navigate to search page (don't wait for networkidle - Twitter has constant activity)
            await self.page.goto(search_url, timeout=30000)

            # Wait for page to load and tweets to appear (give it more time)
            await asyncio.sleep(3)  # Initial wait for page render
            await self.page.wait_for_selector('[data-testid="tweet"]', timeout=30000)

            # Random delay (human-like behavior)
            await self._random_delay(1000, 2000)

            # Scroll to load more tweets
            tweets = []
            scroll_attempts = 0
            max_scrolls = 5

            while len(tweets) < max_tweets and scroll_attempts < max_scrolls:
                # Extract tweets from current view
                tweet_elements = await self.page.query_selector_all('[data-testid="tweet"]')

                for element in tweet_elements:
                    if len(tweets) >= max_tweets:
                        break

                    try:
                        tweet_data = await self._extract_tweet_data(element)
                        if tweet_data:
                            # Add search term context
                            tweet_data.search_term = f"#{hashtag}"
                            
                            if not self._is_duplicate(tweet_data, tweets):
                                tweets.append(tweet_data)
                    except Exception as e:
                        logger.warning(f"Failed to extract tweet: {e}")
                        continue

                # Scroll down to load more
                await self.page.evaluate('window.scrollBy(0, window.innerHeight)')
                await self._random_delay(2000, 3000)
                scroll_attempts += 1

            logger.info(f"Scraped {len(tweets)} tweets from #{hashtag}")
            return tweets

        except Exception as e:
            logger.error(f"Failed to scrape hashtag #{hashtag}: {e}")
            return []

    async def scrape_keyword(self, keyword: str, max_tweets: int = 20) -> List[SocialPost]:
        """
        Scrape tweets containing a specific keyword or phrase.
        """
        if not self.page:
            raise RuntimeError("Browser not initialized. Call initialize() first.")

        # URL encode the keyword for Twitter search
        import urllib.parse
        encoded_keyword = urllib.parse.quote(keyword)
        search_url = f"https://twitter.com/search?q={encoded_keyword}&src=typed_query&f=live"

        logger.info(f"Scraping keyword: {keyword}")

        try:
            # Navigate to search page
            await self.page.goto(search_url, timeout=30000)

            # Wait for page to load and tweets to appear
            await asyncio.sleep(3)
            await self.page.wait_for_selector('[data-testid="tweet"]', timeout=30000)

            # Random delay (human-like behavior)
            await self._random_delay(1000, 2000)

            # Scroll to load more tweets
            tweets = []
            scroll_attempts = 0
            max_scrolls = 5

            while len(tweets) < max_tweets and scroll_attempts < max_scrolls:
                # Extract tweets from current view
                tweet_elements = await self.page.query_selector_all('[data-testid="tweet"]')

                for element in tweet_elements:
                    if len(tweets) >= max_tweets:
                        break

                    try:
                        tweet_data = await self._extract_tweet_data(element)
                        if tweet_data:
                            # Add search term context
                            tweet_data.search_term = keyword
                            
                            if not self._is_duplicate(tweet_data, tweets):
                                tweets.append(tweet_data)
                    except Exception as e:
                        logger.warning(f"Failed to extract tweet: {e}")
                        continue

                # Scroll down to load more
                await self.page.evaluate('window.scrollBy(0, window.innerHeight)')
                await self._random_delay(2000, 3000)
                scroll_attempts += 1

            logger.info(f"Scraped {len(tweets)} tweets for keyword: {keyword}")
            return tweets

        except Exception as e:
            logger.error(f"Failed to scrape keyword '{keyword}': {e}")
            return []

    async def scrape_list(self, list_url: str, max_tweets: int = 20) -> List[SocialPost]:
        """
        Scrape tweets from a Twitter list.
        """
        if not self.page:
            raise RuntimeError("Browser not initialized. Call initialize() first.")

        logger.info(f"Scraping list: {list_url}")

        try:
            # Navigate to list (don't wait for networkidle - Twitter has constant activity)
            await self.page.goto(list_url, timeout=30000)

            # Wait for page to load and tweets to appear
            await asyncio.sleep(3)  # Initial wait for page render
            await self.page.wait_for_selector('[data-testid="tweet"]', timeout=30000)

            # Extract tweets (similar to hashtag scraping)
            tweets = []
            tweet_elements = await self.page.query_selector_all('[data-testid="tweet"]')

            for element in tweet_elements[:max_tweets]:
                try:
                    tweet_data = await self._extract_tweet_data(element)
                    if tweet_data:
                        tweet_data.search_term = list_url
                        tweets.append(tweet_data)
                except Exception as e:
                    logger.warning(f"Failed to extract tweet from list: {e}")
                    continue

            logger.info(f"Scraped {len(tweets)} tweets from list")
            return tweets

        except Exception as e:
            logger.error(f"Failed to scrape list {list_url}: {e}")
            return []

    async def _extract_tweet_data(self, tweet_element) -> Optional[SocialPost]:
        """
        Extract tweet data from a tweet element and convert to SocialPost.
        """
        try:
            # Extract tweet text
            text_element = await tweet_element.query_selector('[data-testid="tweetText"]')
            text = await text_element.inner_text() if text_element else ""

            # Extract author username
            author_element = await tweet_element.query_selector('[data-testid="User-Name"]')
            author_text = await author_element.inner_text() if author_element else ""
            username = self._extract_username(author_text)

            # Extract tweet ID from link
            tweet_link = await tweet_element.query_selector('a[href*="/status/"]')
            tweet_url = await tweet_link.get_attribute('href') if tweet_link else ""
            tweet_id = self._extract_tweet_id(tweet_url)

            if not tweet_id or not text:
                return None

            # Extract metrics (likes, replies, retweets)
            metrics_dict = await self._extract_metrics(tweet_element)

            # Extract timestamp
            time_element = await tweet_element.query_selector('time')
            timestamp_str = await time_element.get_attribute('datetime') if time_element else datetime.utcnow().isoformat()
            
            # Convert timestamp
            created_at = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))

            # Build Author object
            full_url = f"https://twitter.com{tweet_url}" if not tweet_url.startswith('http') else tweet_url
            
            author = Author(
                username=username,
                display_name=author_text.split('@')[0].strip() if '@' in author_text else username,
                platform=Platform.TWITTER,
                platform_id=username, # Twitter doesn't expose ID easily in DOM
                followers_count=metrics_dict.get('followers', 0),
                is_verified=False # TODO: Check for verified badge
            )
            
            metrics = SocialMetrics(
                likes=metrics_dict.get('likes', 0),
                replies=metrics_dict.get('replies', 0),
                shares=metrics_dict.get('retweets', 0),
                impressions=0
            )

            # Build SocialPost
            post = SocialPost(
                id=tweet_id,
                platform=Platform.TWITTER,
                text=text,
                author=author,
                created_at=created_at,
                url=full_url,
                metrics=metrics,
                scraped_at=datetime.utcnow(),
                language='en',
                raw_data={
                    'public_metrics': metrics_dict  # Keep for backward compat if needed temporarily
                }
            )

            return post

        except Exception as e:
            logger.warning(f"Failed to extract tweet data: {e}")
            return None

    async def _extract_metrics(self, tweet_element) -> Dict[str, int]:
        """Extract engagement metrics from tweet element"""
        metrics = {'likes': 0, 'replies': 0, 'retweets': 0}

        try:
            # Extract metrics from aria-labels or text content
            metrics_elements = await tweet_element.query_selector_all('[role="group"] button')

            for element in metrics_elements:
                aria_label = await element.get_attribute('aria-label')
                if aria_label:
                    # Parse aria-label (e.g., "45 Likes", "12 Replies")
                    if 'like' in aria_label.lower():
                        metrics['likes'] = self._parse_count(aria_label)
                    elif 'repl' in aria_label.lower():
                        metrics['replies'] = self._parse_count(aria_label)
                    elif 'retweet' in aria_label.lower():
                        metrics['retweets'] = self._parse_count(aria_label)

        except Exception as e:
            logger.warning(f"Failed to extract metrics: {e}")

        return metrics

    @staticmethod
    def _extract_username(author_text: str) -> str:
        """Extract username from author text"""
        match = re.search(r'@(\w+)', author_text)
        return match.group(1) if match else 'unknown'

    @staticmethod
    def _extract_tweet_id(tweet_url: str) -> Optional[str]:
        """Extract tweet ID from URL"""
        match = re.search(r'/status/(\d+)', tweet_url)
        return match.group(1) if match else None

    @staticmethod
    def _parse_count(text: str) -> int:
        """Parse count from text (e.g., '45 Likes' -> 45)"""
        match = re.search(r'(\d+(?:,\d+)*)', text)
        if match:
            return int(match.group(1).replace(',', ''))
        return 0

    @staticmethod
    def _is_duplicate(post: SocialPost, posts: List[SocialPost]) -> bool:
        """Check if post is duplicate"""
        return any(p.id == post.id for p in posts)


    async def _random_delay(self, min_ms: int, max_ms: int) -> None:
        """Add random delay for human-like behavior"""
        import random
        delay = random.randint(min_ms, max_ms) / 1000.0
        await asyncio.sleep(delay)


if __name__ == "__main__":
    # Test scraper
    import sys

    logging.basicConfig(level=logging.INFO)

    async def test():
        bot_config, _ = get_config()
        hashtags = bot_config.targets.hashtags[:2]  # Test with first 2 hashtags

        logger.info(f"Testing scraper with hashtags: {hashtags}")

        tweets = await scrape_tweets(hashtags=hashtags, max_tweets_per_source=5)

        logger.info(f"✓ Scraped {len(tweets)} tweets")
        for tweet in tweets[:3]:
            logger.info(f"  - @{tweet['author']['username']}: {tweet['text'][:50]}...")

    try:
        asyncio.run(test())
    except Exception as e:
        logger.error(f"✗ Scraper test failed: {e}")
        sys.exit(1)
