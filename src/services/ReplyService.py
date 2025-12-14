"""
Reply service with optimized database operations and business logic
Handles reply queue management, approval workflow, and performance tracking
"""
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc, and_, or_, update, delete
from ..db.models import ReplyQueue, ReplyPerformance, AnalyticsDaily
from ..services.CacheService import cache_service

logger = logging.getLogger(__name__)

class ReplyService:
    """Service for reply management with optimized queries and business logic"""

    def __init__(self, db: Session):
        self.db = db

    async def get_pending_replies(self, limit: int = 100, user_id: str = None) -> Dict[str, Any]:
        """Get pending replies with optimized queries and caching"""
        cache_key, ttl = cache_service.cache_reply_queue(user_id)

        # Try cache first
        cached_replies = cache_service.get(cache_key)
        if cached_replies:
            logger.debug("Returning cached pending replies")
            return cached_replies

        try:
            # Optimized query with all needed data in single query
            pending_replies = self.db.query(
                ReplyQueue.id,
                ReplyQueue.tweet_text,
                ReplyQueue.tweet_author,
                ReplyQueue.tweet_author_followers,
                ReplyQueue.generated_reply,
                ReplyQueue.final_reply,
                ReplyQueue.score,
                ReplyQueue.commercial_category,
                ReplyQueue.created_at,
                ReplyQueue.tweet_url,
                ReplyQueue.voice_score,
                ReplyQueue.voice_violations
            ).filter(
                ReplyQueue.status == "pending"
            ).order_by(
                desc(ReplyQueue.score),
                ReplyQueue.created_at
            ).limit(limit).all()

            replies_data = []
            for reply in pending_replies:
                reply_dict = {
                    "id": reply.id,
                    "tweet_text": reply.tweet_text,
                    "tweet_author": reply.tweet_author,
                    "tweet_author_followers": reply.tweet_author_followers,
                    "generated_reply": reply.generated_reply,
                    "final_reply": reply.final_reply,
                    "score": reply.score,
                    "commercial_category": reply.commercial_category,
                    "voice_score": reply.voice_score,
                    "voice_violations": reply.voice_violations,
                    "timestamp": self._format_time_ago(reply.created_at),
                    "tweet_url": reply.tweet_url,
                    "created_at": reply.created_at.isoformat()
                }
                replies_data.append(reply_dict)

            result = {
                "replies": replies_data,
                "count": len(replies_data),
                "last_updated": datetime.utcnow().isoformat()
            }

            # Cache the result
            cache_service.set(cache_key, result, ttl)
            logger.debug(f"Cached {len(replies_data)} pending replies")

            return result

        except Exception as e:
            logger.error(f"Error getting pending replies: {e}")
            return {
                "replies": [],
                "count": 0,
                "last_updated": datetime.utcnow().isoformat(),
                "error": str(e)
            }

    async def approve_reply(self, reply_id: int, user_id: str = None) -> Dict[str, Any]:
        """Approve and post a reply with proper validation and tracking"""
        try:
            # Get reply with lock to prevent race conditions
            reply = self.db.query(ReplyQueue).filter(
                ReplyQueue.id == reply_id,
                ReplyQueue.status == "pending"
            ).with_for_update().first()

            if not reply:
                return {"success": False, "error": "Reply not found or already processed"}

            # Update reply status
            reply.status = "posted"
            reply.posted_at = datetime.utcnow()
            reply.final_reply = reply.generated_reply  # Use generated reply as final reply

            # Create performance record
            performance = ReplyPerformance(
                reply_id=reply.id,
                posted_at=reply.posted_at,
                marked_as_good_example=False,  # Will be updated based on performance
                voice_compliance_score=reply.voice_score or 0,
                voice_violations_count=reply.voice_violations or 0
            )
            self.db.add(performance)

            # Update daily analytics (optimize with upsert)
            today = datetime.utcnow().date()
            self._update_daily_analytics(today, replies_posted=1)

            # Commit transaction
            self.db.commit()

            # Invalidate cache
            cache_service.invalidate_reply_cache()

            logger.info(f"Reply {reply_id} approved and posted successfully")

            return {
                "success": True,
                "reply_id": reply_id,
                "status": "posted",
                "posted_at": reply.posted_at.isoformat()
            }

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error approving reply {reply_id}: {e}")
            return {
                "success": False,
                "error": f"Failed to approve reply: {str(e)}"
            }

    async def reject_reply(self, reply_id: int, reason: str = None, user_id: str = None) -> Dict[str, Any]:
        """Reject a reply with optional reason and tracking"""
        try:
            # Get reply with lock
            reply = self.db.query(ReplyQueue).filter(
                ReplyQueue.id == reply_id,
                ReplyQueue.status == "pending"
            ).with_for_update().first()

            if not reply:
                return {"success": False, "error": "Reply not found or already processed"}

            # Update reply status
            reply.status = "rejected"
            reply.rejected_at = datetime.utcnow()
            reply.rejection_reason = reason

            # Create performance record for tracking
            performance = ReplyPerformance(
                reply_id=reply.id,
                rejected_at=reply.rejected_at,
                rejection_reason=reason,
                voice_compliance_score=reply.voice_score or 0,
                voice_violations_count=reply.voice_violations or 0
            )
            self.db.add(performance)

            # Commit transaction
            self.db.commit()

            # Invalidate cache
            cache_service.invalidate_reply_cache()

            logger.info(f"Reply {reply_id} rejected. Reason: {reason}")

            return {
                "success": True,
                "reply_id": reply_id,
                "status": "rejected",
                "rejected_at": reply.rejected_at.isoformat()
            }

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error rejecting reply {reply_id}: {e}")
            return {
                "success": False,
                "error": f"Failed to reject reply: {str(e)}"
            }

    async def edit_reply(self, reply_id: int, reply_text: str, user_id: str = None) -> Dict[str, Any]:
        """Edit a pending reply with validation"""
        try:
            # Validate input
            if not reply_text or not reply_text.strip():
                return {"success": False, "error": "Reply text cannot be empty"}

            if len(reply_text) > 280:
                return {"success": False, "error": "Reply exceeds 280 character limit"}

            # Get reply with lock
            reply = self.db.query(ReplyQueue).filter(
                ReplyQueue.id == reply_id,
                ReplyQueue.status == "pending"
            ).with_for_update().first()

            if not reply:
                return {"success": False, "error": "Reply not found or already processed"}

            # Update reply text
            reply.generated_reply = reply_text.strip()
            reply.edited_at = datetime.utcnow()
            reply.edited_count = (reply.edited_count or 0) + 1

            # Re-validate voice compliance (this would integrate with voice validator)
            # For now, just update the score
            reply.voice_score = min(100, reply.voice_score or 80)  # Simple score adjustment

            # Commit transaction
            self.db.commit()

            # Invalidate cache
            cache_service.invalidate_reply_cache()

            logger.info(f"Reply {reply_id} edited successfully")

            return {
                "success": True,
                "reply_id": reply_id,
                "new_reply_text": reply_text,
                "edited_at": reply.edited_at.isoformat(),
                "voice_score": reply.voice_score
            }

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error editing reply {reply_id}: {e}")
            return {
                "success": False,
                "error": f"Failed to edit reply: {str(e)}"
            }

    async def get_reply_history(self, days: int = 30, limit: int = 100, user_id: str = None) -> Dict[str, Any]:
        """Get reply history with optimized queries"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)

            # Optimized query with joined performance data
            history_query = self.db.query(
                ReplyQueue.id,
                ReplyQueue.tweet_text,
                ReplyQueue.tweet_author,
                ReplyQueue.generated_reply,
                ReplyQueue.final_reply,
                ReplyQueue.status,
                ReplyQueue.created_at,
                ReplyQueue.posted_at,
                ReplyQueue.score,
                ReplyQueue.commercial_category,
                ReplyQueue.engagement_rate,
                ReplyQueue.engagement_likes,
                ReplyQueue.engagement_retweets,
                ReplyPerformance.marked_as_good_example,
                ReplyPerformance.engagement_metrics_snapshot
            ).outerjoin(
                ReplyPerformance,
                ReplyQueue.id == ReplyPerformance.reply_id
            ).filter(
                ReplyQueue.created_at >= cutoff_date
            ).order_by(
                desc(ReplyQueue.created_at)
            ).limit(limit).all()

            history_data = []
            for item in history_query:
                history_item = {
                    "id": item.id,
                    "tweet_text": item.tweet_text,
                    "tweet_author": item.tweet_author,
                    "generated_reply": item.generated_reply,
                    "final_reply": item.final_reply,
                    "status": item.status,
                    "score": item.score,
                    "commercial_category": item.commercial_category,
                    "created_at": item.created_at.isoformat(),
                    "posted_at": item.posted_at.isoformat() if item.posted_at else None,
                    "timestamp": self._format_time_ago(item.created_at),
                    "engagement_metrics": {
                        "rate": item.engagement_rate,
                        "likes": item.engagement_likes,
                        "retweets": item.engagement_retweets
                    } if item.engagement_rate else None,
                    "marked_as_good_example": item.marked_as_good_example or False
                }

                # Parse engagement metrics snapshot if available
                if item.engagement_metrics_snapshot:
                    try:
                        import json
                        snapshot = json.loads(item.engagement_metrics_snapshot)
                        if isinstance(snapshot, dict):
                            history_item["engagement_metrics_snapshot"] = snapshot
                    except Exception:
                        pass

                history_data.append(history_item)

            return {
                "history": history_data,
                "count": len(history_data),
                "period_days": days,
                "last_updated": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Error getting reply history: {e}")
            return {
                "history": [],
                "count": 0,
                "period_days": days,
                "last_updated": datetime.utcnow().isoformat(),
                "error": str(e)
            }

    async def bulk_approve(self, reply_ids: List[int], user_id: str = None) -> Dict[str, Any]:
        """Bulk approve multiple replies efficiently"""
        try:
            if not reply_ids:
                return {"success": False, "error": "No reply IDs provided"}

            approved_count = 0
            failed_replies = []

            for reply_id in reply_ids:
                result = await self.approve_reply(reply_id, user_id)
                if result["success"]:
                    approved_count += 1
                else:
                    failed_replies.append({"reply_id": reply_id, "error": result["error"]})

            logger.info(f"Bulk approved {approved_count} replies, {len(failed_replies)} failed")

            return {
                "success": True,
                "approved_count": approved_count,
                "failed_count": len(failed_replies),
                "failed_replies": failed_replies
            }

        except Exception as e:
            logger.error(f"Error in bulk approve: {e}")
            return {
                "success": False,
                "error": f"Bulk approve failed: {str(e)}"
            }

    async def bulk_reject(self, reply_ids: List[int], reason: str = None, user_id: str = None) -> Dict[str, Any]:
        """Bulk reject multiple replies efficiently"""
        try:
            if not reply_ids:
                return {"success": False, "error": "No reply IDs provided"}

            rejected_count = 0
            failed_replies = []

            for reply_id in reply_ids:
                result = await self.reject_reply(reply_id, reason, user_id)
                if result["success"]:
                    rejected_count += 1
                else:
                    failed_replies.append({"reply_id": reply_id, "error": result["error"]})

            logger.info(f"Bulk rejected {rejected_count} replies, {len(failed_replies)} failed")

            return {
                "success": True,
                "rejected_count": rejected_count,
                "failed_count": len(failed_replies),
                "failed_replies": failed_replies
            }

        except Exception as e:
            logger.error(f"Error in bulk reject: {e}")
            return {
                "success": False,
                "error": f"Bulk reject failed: {str(e)}"
            }

    def _update_daily_analytics(self, date: datetime.date, **updates):
        """Update daily analytics efficiently"""
        try:
            # Use raw SQL for efficient upsert
            updates_clause = ", ".join([f"{k} = {k} + {v}" for k, v in updates.items()])

            sql = f"""
                INSERT INTO analytics_daily (date, {", ".join(updates.keys())})
                VALUES (:date, {", ".join([f":{k}" for k in updates.keys()])})
                ON CONFLICT (date) DO UPDATE SET {updates_clause}
            """

            params = {"date": date, **updates}
            self.db.execute(text(sql), params)

        except Exception as e:
            logger.error(f"Error updating daily analytics: {e}")

    def _format_time_ago(self, dt: datetime) -> str:
        """Format datetime as 'X minutes/hours ago'"""
        if not dt:
            return "unknown"

        now = datetime.utcnow()
        diff = now - dt

        if diff < timedelta(minutes=1):
            return "just now"
        elif diff < timedelta(hours=1):
            minutes = diff.seconds // 60
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        elif diff < timedelta(days=1):
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        else:
            days = diff.days
            return f"{days} day{'s' if days != 1 else ''} ago"

    # Performance and maintenance methods
    def cleanup_old_pending_replies(self, days: int = 7) -> int:
        """Clean up old pending replies"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)

            deleted_count = self.db.query(ReplyQueue).filter(
                ReplyQueue.status == "pending",
                ReplyQueue.created_at < cutoff_date
            ).delete()

            self.db.commit()

            # Invalidate cache
            cache_service.invalidate_reply_cache()

            logger.info(f"Cleaned up {deleted_count} old pending replies")
            return deleted_count

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error cleaning up old pending replies: {e}")
            return 0

    def get_queue_statistics(self) -> Dict[str, Any]:
        """Get reply queue statistics"""
        try:
            stats = self.db.query(
                ReplyQueue.status,
                func.count(ReplyQueue.id).label('count'),
                func.avg(ReplyQueue.score).label('avg_score')
            ).group_by(ReplyQueue.status).all()

            statistics = {}
            total_count = 0

            for stat in stats:
                statistics[stat.status] = {
                    "count": stat.count,
                    "avg_score": round(float(stat.avg_score or 0), 1)
                }
                total_count += stat.count

            statistics["total"] = total_count
            return statistics

        except Exception as e:
            logger.error(f"Error getting queue statistics: {e}")
            return {"total": 0, "error": str(e)}