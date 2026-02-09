"""
Reddit URL Parser
Extracts post_id, comment_id, and subreddit from Reddit URLs.
"""
import re
from typing import Optional, Dict
from urllib.parse import urlparse

class RedditURLParser:
    """Parse and validate Reddit URLs."""
    
    # Reddit URL patterns
    POST_PATTERN = r'/r/([^/]+)/comments/([a-z0-9]+)(?:/[^/]+/?)?$'
    COMMENT_PATTERN = r'/r/([^/]+)/comments/([a-z0-9]+)/[^/]+/([a-z0-9]+)/?'
    
    @staticmethod
    def validate_url(url: str) -> bool:
        """
        Quick validation to check if URL is from Reddit.
        
        Args:
            url: URL string to validate
            
        Returns:
            True if valid Reddit URL, False otherwise
        """
        if not url:
            return False
            
        try:
            parsed = urlparse(url)
            # Accept reddit.com, old.reddit.com, www.reddit.com, etc.
            return 'reddit.com' in parsed.netloc.lower()
        except Exception:
            return False
    
    @staticmethod
    def parse_reddit_url(url: str) -> Optional[Dict[str, str]]:
        """
        Parse Reddit URL and extract components.
        
        Args:
            url: Reddit URL (post or comment)
            
        Returns:
            Dictionary with:
                - type: "post" or "comment"
                - subreddit: subreddit name
                - post_id: post ID
                - comment_id: comment ID (only for comment URLs)
            Returns None if URL is invalid.
            
        Examples:
            Post: https://reddit.com/r/entrepreneur/comments/abc123/title/
            Comment: https://reddit.com/r/entrepreneur/comments/abc123/title/def456/
        """
        if not RedditURLParser.validate_url(url):
            return None
        
        try:
            parsed = urlparse(url)
            path = parsed.path
            
            # Try to match comment pattern first (more specific)
            comment_match = re.search(RedditURLParser.COMMENT_PATTERN, path)
            if comment_match:
                return {
                    'type': 'comment',
                    'subreddit': comment_match.group(1),
                    'post_id': comment_match.group(2),
                    'comment_id': comment_match.group(3)
                }
            
            # Try post pattern
            post_match = re.search(RedditURLParser.POST_PATTERN, path)
            if post_match:
                return {
                    'type': 'post',
                    'subreddit': post_match.group(1),
                    'post_id': post_match.group(2)
                }
            
            return None
            
        except Exception:
            return None
    
    @staticmethod
    def get_error_message(url: str) -> str:
        """
        Get user-friendly error message for invalid URLs.
        
        Args:
            url: URL that failed parsing
            
        Returns:
            Human-readable error message
        """
        if not url or not url.strip():
            return "Please enter a URL"
        
        if not RedditURLParser.validate_url(url):
            return "Please enter a valid Reddit URL (e.g., https://reddit.com/r/...)"
        
        return "Unable to parse Reddit URL. Please check the format."
