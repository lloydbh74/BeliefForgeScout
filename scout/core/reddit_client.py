import praw
import logging
import time
from typing import List, Set
from datetime import datetime, timedelta

from .models import ScoutPost
from ..config import config

logger = logging.getLogger(__name__)

class RedditScout:
    def __init__(self):
        self.processed_ids: Set[str] = set() # Mock persistence for now
        self._reddit = None

    @property
    def reddit(self):
        """Lazy load Reddit instance to allow config updates."""
        if self._reddit is None:
             self._init_client()
        return self._reddit
    
    def _init_client(self):
        """Initialize PRAW client. Falls back to read-only if no username/pass."""
        if not config.reddit.client_id or not config.reddit.client_secret:
            logger.warning("Reddit Client ID/Secret missing. Usage might fail.")
            
        self._reddit = praw.Reddit(
            client_id=config.reddit.client_id,
            client_secret=config.reddit.client_secret,
            user_agent=config.reddit.user_agent,
            username=config.reddit.username or None,
            password=config.reddit.password or None
        )
        if self._reddit.read_only:
             logger.info("Reddit Client running in READ-ONLY mode.")

        
    def _to_scout_post(self, submission) -> ScoutPost:
        """Convert PRAW submission to ScoutPost."""
        # Grab top comments for context (Tier 2 requirement)
        top_comments = []
        if hasattr(submission, 'comments'):
            submission.comments.replace_more(limit=0)
            for comment in submission.comments[:3]:
                top_comments.append(comment.body[:200] + "...")

        return ScoutPost(
            id=submission.id,
            title=submission.title,
            content=submission.selftext,
            url=submission.url,
            subreddit=submission.subreddit.display_name,
            author=str(submission.author) if submission.author else "[deleted]",
            created_utc=submission.created_utc,
            score=submission.score,
            comment_count=submission.num_comments,
            is_self=submission.is_self,
            top_comments=top_comments
        )

    def scan_watchtower(self, subreddits: List[str], limit: int = 10) -> List[ScoutPost]:
        """Track A: Scan known territories (New + Rising)."""
        logger.info(f"Watchtower scanning {len(subreddits)} subreddits...")
        posts = []
        
        # Combine into a multireddit string for efficiency
        sub_string = "+".join(subreddits)
        
        try:
            # check read_only mode if no creds
            if self.reddit.read_only:
                 logger.warning("Running in Read-Only mode (no auth credentials found)")

            # Scan New
            for submission in self.reddit.subreddit(sub_string).new(limit=limit):
                if submission.id not in self.processed_ids:
                    posts.append(self._to_scout_post(submission))
                    self.processed_ids.add(submission.id)
            
            # Scan Rising (Good for catching potential viral help threads)
            for submission in self.reddit.subreddit(sub_string).rising(limit=5):
                if submission.id not in self.processed_ids:
                    posts.append(self._to_scout_post(submission))
                    self.processed_ids.add(submission.id)
                    
        except Exception as e:
            logger.error(f"Watchtower scan failed: {e}")
            
        logger.info(f"Watchtower found {len(posts)} unique posts.")
        return posts

    def scan_pathfinder(self, keywords: List[str], limit: int = 10) -> List[ScoutPost]:
        """Track B: Search the wilds for keywords."""
        logger.info(f"Pathfinder searching for: {keywords}")
        posts = []
        
        # Join keywords with OR for broader search
        query = " OR ".join(f'"{k}"' for k in keywords) 
        
        try:
            # Search all subreddits, sorted by new
            for submission in self.reddit.subreddit("all").search(query, sort="new", limit=limit):
                if submission.id not in self.processed_ids:
                    posts.append(self._to_scout_post(submission))
                    self.processed_ids.add(submission.id)
                    
        except Exception as e:
            logger.error(f"Pathfinder search failed: {e}")

        logger.info(f"Pathfinder found {len(posts)} unique posts.")
        return posts
        
    def check_author_cooldown(self, author: str) -> bool:
        """
        Enhancement: Check if we engaged with this author recently.
        TODO: Implement persistence logic.
        """
        return False # Not on cooldown
        
    def scan_my_history(self, limit: int = 20) -> List[dict]:
        """
        Profile Watcher: Fetch recent comments.
        Supports both Authenticated (user.me) and Read-Only (redditor name) modes.
        """
        engagements = []
        try:
            # 1. Try Authenticated User
            user = self.reddit.user.me()
            
            # 2. If Read-Only, try Configured Username
            if not user:
                target_user = config.settings.get("reddit_username")
                if target_user:
                    user = self.reddit.redditor(target_user)
            
            if not user:
                logger.warning("Cannot scan: No authenticated user AND no 'reddit_username' in settings.")
                return []
                
            # Fetch comments (works for both me and redditor objects)
            logger.info(f"Scanning profile: {user}")
            
            # Limit to last 14 days roughly (fetching more to be safe then filtering)
            cutoff_date = datetime.now() - timedelta(days=14)
            comments_stream = user.comments.new(limit=limit)

            for comment in comments_stream:
                # 1. Date Check (Optimization: Stop processing if way too old? 
                # PRAW new() is ordered, so once we hit old posts we could break, 
                # but 'limit' is small so simple filter is safer)
                created_dt = datetime.fromtimestamp(comment.created_utc)
                if created_dt < cutoff_date:
                    continue

                # Refresh to get latest replies/score
                try:
                    comment.refresh()
                except Exception as e:
                    # Sometimes refresh fails on deleted content
                    continue
                
                # Check for "Handshake" (Reply from OP)
                has_handshake = False
                try:
                    submission_author = comment.submission.author
                    if submission_author:
                        comment.replies.replace_more(limit=0)
                        for reply in comment.replies:
                            if reply.author == submission_author:
                                has_handshake = True
                                break
                except:
                    pass # Deleted/removed context
                            
                engagements.append({
                    "id": comment.id,
                    "post_id": comment.submission.id,
                    "subreddit": comment.subreddit.display_name,
                    "body": comment.body[:100],
                    "score": comment.score,
                    "replies": len(comment.replies),
                    "created_utc": comment.created_utc,
                    "handshake": has_handshake
                })
                
        except Exception as e:
            logger.error(f"Profile scan failed: {e}")
            
        return engagements
