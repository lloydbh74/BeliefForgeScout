"""
Unit tests for RedditURLParser
"""
import pytest
from scout.core.url_parser import RedditURLParser


class TestRedditURLParser:
    """Test suite for URL parsing functionality."""
    
    def test_validate_url_valid_reddit(self):
        """Test validation of valid Reddit URLs."""
        assert RedditURLParser.validate_url("https://reddit.com/r/test/comments/abc123/title/")
        assert RedditURLParser.validate_url("https://www.reddit.com/r/test/comments/abc123/")
        assert RedditURLParser.validate_url("https://old.reddit.com/r/test/comments/abc123/")
    
    def test_validate_url_invalid(self):
        """Test validation rejects non-Reddit URLs."""
        assert not RedditURLParser.validate_url("https://google.com")
        assert not RedditURLParser.validate_url("")
        assert not RedditURLParser.validate_url(None)
    
    def test_parse_post_url(self):
        """Test parsing of post URLs."""
        url = "https://reddit.com/r/entrepreneur/comments/abc123/my_title/"
        result = RedditURLParser.parse_reddit_url(url)
        
        assert result is not None
        assert result['type'] == 'post'
        assert result['subreddit'] == 'entrepreneur'
        assert result['post_id'] == 'abc123'
        assert 'comment_id' not in result
    
    def test_parse_comment_url(self):
        """Test parsing of comment URLs."""
        url = "https://reddit.com/r/entrepreneur/comments/abc123/my_title/def456/"
        result = RedditURLParser.parse_reddit_url(url)
        
        assert result is not None
        assert result['type'] == 'comment'
        assert result['subreddit'] == 'entrepreneur'
        assert result['post_id'] == 'abc123'
        assert result['comment_id'] == 'def456'
    
    def test_parse_url_without_trailing_slash(self):
        """Test parsing works without trailing slash."""
        url = "https://reddit.com/r/test/comments/abc123"
        result = RedditURLParser.parse_reddit_url(url)
        
        assert result is not None
        assert result['type'] == 'post'
        assert result['post_id'] == 'abc123'
    
    def test_parse_invalid_url(self):
        """Test parsing returns None for invalid URLs."""
        assert RedditURLParser.parse_reddit_url("https://google.com") is None
        assert RedditURLParser.parse_reddit_url("https://reddit.com/r/test") is None
    
    def test_get_error_message(self):
        """Test error messages are user-friendly."""
        msg = RedditURLParser.get_error_message("")
        assert "Please enter a URL" in msg
        
        msg = RedditURLParser.get_error_message("https://google.com")
        assert "valid Reddit URL" in msg
