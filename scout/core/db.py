import sqlite3
import json
import logging
from typing import List, Set, Optional
from datetime import datetime

from .models import ScoutPost, AnalysisResult, DraftReply
from ..config import config

logger = logging.getLogger(__name__)

class ScoutDB:
    def __init__(self):
        self.db_path = config.app.db_path
        self._init_db()

    def _init_db(self):
        """Create tables if they don't exist."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Table to track processed posts (prevent duplicates)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS processed_posts (
                    post_id TEXT PRIMARY KEY,
                    processed_at TIMESTAMP,
                    intent TEXT,
                    is_relevant BOOLEAN
                )
            ''')
            
            # Table for Briefings (Drafts waiting for approval)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS briefings (
                    post_id TEXT PRIMARY KEY,
                    subreddit TEXT,
                    title TEXT,
                    post_content TEXT,
                    post_url TEXT,
                    draft_content TEXT,
                    intent TEXT,
                    status TEXT, -- pending, approved, posted, discarded
                    created_at TIMESTAMP,
                    source TEXT DEFAULT 'auto', -- 'auto' or 'manual'
                    parent_comment_id TEXT,
                    parent_author TEXT,
                    score INTEGER DEFAULT 0,
                    comment_count INTEGER DEFAULT 0
                )
            ''')

            # Migration: Add score and comment_count to briefings if they don't exist
            try:
                cursor.execute("ALTER TABLE briefings ADD COLUMN score INTEGER DEFAULT 0")
                cursor.execute("ALTER TABLE briefings ADD COLUMN comment_count INTEGER DEFAULT 0")
            except sqlite3.OperationalError:
                # Columns already exist
                pass
            
            # Table for Engagements (Profile Watcher)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS engagements (
                    comment_id TEXT PRIMARY KEY,
                    post_id TEXT,
                    subreddit TEXT,
                    body_snippet TEXT,
                    score INTEGER,
                    reply_count INTEGER,
                    posted_at TIMESTAMP,
                    last_updated TIMESTAMP,
                    has_handshake BOOLEAN DEFAULT 0
                )
            ''')
            conn.commit()

    def is_processed(self, post_id: str) -> bool:
        """Check if post was already scanned."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM processed_posts WHERE post_id = ?", (post_id,))
            return cursor.fetchone() is not None

    def mark_processed(self, post_id: str, intent: str, is_relevant: bool):
        """Mark post as processed."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO processed_posts (post_id, processed_at, intent, is_relevant) VALUES (?, ?, ?, ?)",
                (post_id, datetime.now(), intent, is_relevant)
            )
            conn.commit()

    def save_briefing(self, post: ScoutPost, draft: DraftReply, intent: str):
        """Save a generated draft as a briefing (automated workflow)."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO briefings 
                (post_id, subreddit, title, post_content, post_url, draft_content, intent, status, created_at, source, score, comment_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                post.id, post.subreddit, post.title, post.content, post.url, 
                draft.content, intent, 'pending', datetime.now(), 'auto',
                getattr(post, 'score', 0), getattr(post, 'comment_count', 0)
            ))
            conn.commit()
    
    def save_manual_briefing(self, post_id: str, subreddit: str, title: str, 
                            post_content: str, post_url: str, draft_content: str,
                            parent_comment_id: Optional[str] = None, 
                            parent_author: Optional[str] = None):
        """Save a manually generated draft from URL input."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO briefings 
                (post_id, subreddit, title, post_content, post_url, draft_content, 
                 intent, status, created_at, source, parent_comment_id, parent_author)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                post_id, subreddit, title, post_content, post_url, draft_content,
                'Manual', 'pending', datetime.now(), 'manual', parent_comment_id, parent_author
            ))
            conn.commit()
    
    def check_duplicate_briefing(self, post_id: str) -> Optional[dict]:
        """Check if a briefing already exists for this post/comment."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM briefings WHERE post_id = ?", (post_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
            
    def get_pending_briefings(self) -> List[dict]:
        """Get all briefings waiting for review."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM briefings WHERE status = 'pending' ORDER BY created_at DESC")
            return [dict(row) for row in cursor.fetchall()]

    def update_briefing_status(self, post_id: str, status: str, content: Optional[str] = None):
        """Update status (e.g., approved/discarded) and optionally the content (edited)."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            if content:
                cursor.execute(
                    "UPDATE briefings SET status = ?, draft_content = ? WHERE post_id = ?", 
                    (status, content, post_id)
                )
            else:
                cursor.execute(
                    "UPDATE briefings SET status = ? WHERE post_id = ?", 
                    (status, post_id)
                )
            conn.commit()

    def get_recent_engagements(self, limit: int = 50) -> List[dict]:
        """Fetch recent engagements for the dashboard."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM engagements ORDER BY posted_at DESC LIMIT ?", 
                (limit,)
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_stats(self) -> dict:
        """Get aggregate statistics for the dashboard."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            stats = {
                "pending": 0,
                "approved": 0,
                "discarded": 0,
                "total_scanned": 0
            }
            
            # Briefing stats
            cursor.execute("SELECT status, COUNT(*) FROM briefings GROUP BY status")
            for row in cursor.fetchall():
                status, count = row
                if status in stats:
                    stats[status] = count
                # Map 'posted' to 'approved' for simplicity if used internally
                if status == 'posted':
                     stats['approved'] += count # Accumulate if separate
            
            # Total processed
            cursor.execute("SELECT COUNT(*) FROM processed_posts")
            stats["total_scanned"] = cursor.fetchone()[0]
            
            return stats

    def upsert_engagement(self, data: dict):
        """Insert or Update engagement record."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO engagements 
                (comment_id, post_id, subreddit, body_snippet, score, reply_count, posted_at, last_updated, has_handshake)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data['id'], data['post_id'], data['subreddit'], data['body'], 
                data['score'], data['replies'], data['created_utc'], 
                datetime.now(), data['handshake']
            ))
            conn.commit()

    def get_engagement_stats(self) -> dict:
        """Get engagement metrics."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Aggregate stats
            cursor.execute('''
                SELECT 
                    COUNT(*) as total,
                    SUM(score) as total_score,
                    SUM(reply_count) as total_replies,
                    SUM(has_handshake) as total_handshakes
                FROM engagements
            ''')
            row = cursor.fetchone()
            
            return {
                "active_conversations": row[0] or 0,
                "net_karma": row[1] or 0,
                "replies_received": row[2] or 0,
                "handshakes": row[3] or 0
            }
