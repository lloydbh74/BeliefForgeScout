"""
Base interface for social media scrapers.
"""
from abc import ABC, abstractmethod
from typing import List, Optional
from src.core.models import SocialPost

class SocialScraper(ABC):
    """Abstract base class for all platform scrapers"""
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize resources (browsers, sessions)"""
        pass
        
    @abstractmethod
    async def close(self) -> None:
        """Cleanup resources"""
        pass
        
    @abstractmethod
    async def scrape(self, query: str, limit: int = 10) -> List[SocialPost]:
        """
        Generic scrape method.
        Implementation should detect if 'query' is a hashtag, user, or topic
        and route accordingly.
        """
        pass
