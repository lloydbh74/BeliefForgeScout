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
                    created_at TIMESTAMP
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
        """Save a generated draft as a briefing."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO briefings 
                (post_id, subreddit, title, post_content, post_url, draft_content, intent, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                post.id, post.subreddit, post.title, post.content, post.url, 
                draft.content, intent, 'pending', datetime.now()
            ))
            conn.commit()
            
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
                cursor.execute("UPDATE briefings SET status = ?, draft_content = ? WHERE post_id = ?", (status, content, post_id))
            else:
                cursor.execute("UPDATE briefings SET status = ? WHERE post_id = ?", (status, post_id))
            conn.commit()
