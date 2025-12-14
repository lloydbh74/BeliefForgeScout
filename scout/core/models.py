from datetime import datetime
from typing import Optional, List, Dict
from dataclasses import dataclass, field

@dataclass
class ScoutPost:
    """Represents a standardized Reddit post for the Scout."""
    id: str
    title: str
    content: str
    url: str
    subreddit: str
    author: str
    created_utc: float
    score: int = 0
    comment_count: int = 0
    is_self: bool = True
    
    # Context (for Tier 2)
    top_comments: List[str] = field(default_factory=list)
    
    @property
    def created_at(self) -> datetime:
        return datetime.fromtimestamp(self.created_utc)
        
    @property
    def full_text(self) -> str:
        return f"{self.title}\n\n{self.content}"

@dataclass
class AnalysisResult:
    """Result from the Tier 1 Screener."""
    post_id: str
    is_relevant: bool
    intent: str  # 'distress', 'strategy', 'venting', 'ignore'
    confidence: float
    reasoning: str
    
@dataclass
class DraftReply:
    """Result from the Tier 2 Copywriter."""
    post_id: str
    content: str
    strategy_used: str
    status: str = "pending" # pending, approved, posted, discarded
