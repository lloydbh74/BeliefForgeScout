import logging
from typing import List, Optional
from datetime import datetime
from supabase import create_client, Client

from .models import ScoutPost, DraftReply
from ..config import config

logger = logging.getLogger(__name__)

class ScoutDB:
    def __init__(self):
        if not config.app.supabase_url or not config.app.supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in the environment or .env file.")
        
        # Initialize Supabase Client
        self.supabase: Client = create_client(
            config.app.supabase_url,
            config.app.supabase_key
        )
        logger.info("✅ Connected to Supabase!")

    def is_processed(self, post_id: str) -> bool:
        """Check if post was already scanned."""
        try:
            # .limit(1) to avoid fetching large rows unnecessarily
            response = self.supabase.table("scout_processed_posts").select("post_id").eq("post_id", post_id).limit(1).execute()
            return len(response.data) > 0
        except Exception as e:
            logger.error(f"Error checking is_processed in Supabase: {e}")
            return False

    def mark_processed(self, post_id: str, intent: str, is_relevant: bool, 
                       prompt_tokens: int = 0, completion_tokens: int = 0, total_cost: float = 0.0):
        """Mark post as processed including screening cost."""
        try:
            self.supabase.table("scout_processed_posts").upsert({
                "post_id": post_id,
                "processed_at": datetime.now().isoformat(),
                "intent": intent,
                "is_relevant": is_relevant,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_cost": total_cost
            }).execute()
        except Exception as e:
            logger.error(f"Error marking post as processed: {e}")

    def save_briefing(self, post: ScoutPost, draft: DraftReply, intent: str):
        """Save a generated draft as a briefing (automated workflow)."""
        try:
            self.supabase.table("scout_briefings").upsert({
                "post_id": post.id,
                "subreddit": post.subreddit,
                "title": post.title,
                "post_content": post.content,
                "post_url": post.url,
                "draft_content": draft.content,
                "intent": intent,
                "status": "pending",
                "created_at": datetime.now().isoformat(),
                "source": "auto",
                "score": int(getattr(post, 'score', 0)),
                "comment_count": int(getattr(post, 'comment_count', 0)),
                "post_created_at": datetime.fromtimestamp(post.created_utc).isoformat() if hasattr(post, 'created_utc') and post.created_utc else datetime.now().isoformat(),
                "prompt_tokens": int(draft.prompt_tokens),
                "completion_tokens": int(draft.completion_tokens),
                "total_cost": float(draft.total_cost)
            }).execute()
        except Exception as e:
            logger.error(f"Error saving briefing to Supabase: {e}")
    
    def save_manual_briefing(self, post_id: str, subreddit: str, title: str, 
                            post_content: str, post_url: str, draft_content: str,
                            intent: str = 'Manual',
                            parent_comment_id: Optional[str] = None, 
                            parent_author: Optional[str] = None,
                            score: int = 0,
                            comment_count: int = 0,
                            post_created_at: Optional[float] = None):
        """Save a manually generated draft from URL input."""
        logger.info(f"💾 Saving manual briefing for {post_id} (Score: {score}, Intent: {intent})")
        
        try:
            post_created_dt = datetime.fromtimestamp(post_created_at).isoformat() if post_created_at else None
            
            self.supabase.table("scout_briefings").upsert({
                "post_id": post_id,
                "subreddit": subreddit,
                "title": title,
                "post_content": post_content,
                "post_url": post_url,
                "draft_content": draft_content,
                "intent": intent,
                "status": "pending",
                "created_at": datetime.now().isoformat(),
                "source": "manual",
                "parent_comment_id": parent_comment_id,
                "parent_author": parent_author,
                "score": score,
                "comment_count": comment_count,
                "post_created_at": post_created_dt,
                "prompt_tokens": 0, # Manual doesn't track tokens via this direct method yet
                "completion_tokens": 0,
                "total_cost": 0.0
            }).execute()
            logger.info(f"✅ Manual briefing {post_id} saved successfully.")
        except Exception as e:
            logger.error(f"Error saving manual briefing: {e}")
    
    def check_duplicate_briefing(self, post_id: str) -> Optional[dict]:
        """Check if a briefing already exists for this post/comment."""
        try:
            response = self.supabase.table("scout_briefings").select("*").eq("post_id", post_id).limit(1).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error checking duplicate: {e}")
            return None
            
    def get_pending_briefings(self) -> List[dict]:
        """Get all briefings waiting for review."""
        try:
            response = self.supabase.table("scout_briefings").select("*").eq("status", "pending").order("created_at", desc=True).execute()
            results = response.data
            logger.info(f"🔍 get_pending_briefings found {len(results)} items.")
            return results
        except Exception as e:
            logger.error(f"Error getting pending briefings: {e}")
            return []

    def get_archived_briefings(self, limit: int = 50) -> List[dict]:
        """Get all past decisions (approved, discarded, posted)."""
        try:
            response = self.supabase.table("scout_briefings").select(
                "*, scout_engagements(score, reply_count, has_handshake)"
            ).in_("status", ["approved", "discarded", "posted", "archived"]).order(
                "created_at", desc=True
            ).limit(limit).execute()
            
            # Flatten or format response for UI
            formatted_results = []
            for item in response.data:
                # Add engagement info if it exists
                engagements = item.get("scout_engagements", [])
                engagement = engagements[0] if engagements else {}
                item["live_score"] = engagement.get("score")
                item["live_replies"] = engagement.get("reply_count")
                item["has_handshake"] = engagement.get("has_handshake")
                
                # Cleanup joined table key
                if "scout_engagements" in item:
                    del item["scout_engagements"]
                    
                formatted_results.append(item)
                
            return formatted_results
        except Exception as e:
            logger.error(f"Error fetching archived briefings: {e}")
            return []

    def reconcile_posted_briefings(self):
        """
        Check if 'approved' briefings now exist in the engagements table.
        If they do, it means the user actually posted them.
        """
        try:
            # First query to get approved briefings that are in engagements
            response = self.supabase.table("scout_briefings").select("post_id, scout_engagements!inner(post_id)").eq("status", "approved").execute()
            
            posted_ids = [item["post_id"] for item in response.data]
            
            if posted_ids:
                logger.info(f"🔄 Reconciling {len(posted_ids)} briefings as 'posted'.")
                # Step 2: Update their status
                # Currently Supabase doesn't support bulk update with an IN clause easily via Python client,
                # but we can iterate since the amount won't be massive in a single run
                for pid in posted_ids:
                    self.supabase.table("scout_briefings").update({"status": "posted"}).eq("post_id", pid).execute()
        except Exception as e:
            logger.error(f"Error reconciling posted briefings: {e}")

    def update_briefing_status(self, post_id: str, status: str, content: Optional[str] = None):
        """Update status (e.g., approved/discarded) and optionally the content (edited)."""
        try:
            update_data = {"status": status}
            if content:
                update_data["draft_content"] = content
                
            self.supabase.table("scout_briefings").update(update_data).eq("post_id", post_id).execute()
        except Exception as e:
            logger.error(f"Error updating status: {e}")

    def get_recent_engagements(self, limit: int = 50) -> List[dict]:
        """Fetch recent engagements for the dashboard."""
        try:
            response = self.supabase.table("scout_engagements").select("*").order("posted_at", desc=True).limit(limit).execute()
            return response.data
        except Exception as e:
            logger.error(f"Error fetching recent engagements: {e}")
            return []

    def get_pending_dms(self) -> List[dict]:
        """Fetch all engagements that have a drafted DM ready for review."""
        try:
            response = self.supabase.table("scout_engagements").select("*").eq("status", "draft").order("scheduled_at", desc=False).execute()
            return response.data
        except Exception as e:
            logger.error(f"Error fetching pending DMs: {e}")
            return []

    def get_stats(self) -> dict:
        """Get aggregate statistics for the dashboard via the RPC function."""
        try:
            response = self.supabase.rpc('get_dashboard_stats', {}).execute()
            if response.data:
                stats = response.data
                
                # Calculate total cost from tables
                try:
                    briefing_cost = self.supabase.table("scout_briefings").select("total_cost").execute()
                    processed_cost = self.supabase.table("scout_processed_posts").select("total_cost").execute()
                    engagement_cost = self.supabase.table("scout_engagements").select("total_cost").execute()
                    
                    total_campaign_cost = (
                        sum(float(item.get('total_cost') or 0.0) for item in briefing_cost.data) +
                        sum(float(item.get('total_cost') or 0.0) for item in processed_cost.data) +
                        sum(float(item.get('total_cost') or 0.0) for item in engagement_cost.data)
                    )
                except Exception:
                    total_campaign_cost = 0.0

                return {
                    "pending": stats.get("pending_briefings", 0),
                    "approved": stats.get("approved_briefings", 0),
                    "discarded": 0,
                    "total_scanned": stats.get("total_scanned_posts", 0),
                    "total_cost": total_campaign_cost
                }
            return {"pending": 0, "approved": 0, "discarded": 0, "total_scanned": 0}
        except Exception as e:
            logger.error(f"Error calling get_stats: {e}")
            return {"pending": 0, "approved": 0, "discarded": 0, "total_scanned": 0}

    def get_latest_engagement_timestamp(self) -> float:
        """
        Returns the UTC timestamp of the most recently recorded engagement.
        Used for incremental sync — only fetch Reddit comments newer than this.
        Returns None if no engagements exist (triggers full backfill).
        """
        try:
            response = (
                self.supabase.table("scout_engagements")
                .select("posted_at")
                .order("posted_at", desc=True)
                .limit(1)
                .execute()
            )
            if response.data and response.data[0].get("posted_at"):
                ts_str = response.data[0]["posted_at"]
                dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                # Convert to UTC timestamp (float)
                return dt.timestamp()
        except Exception as e:
            logger.error(f"Error fetching latest engagement timestamp: {e}")
        return None

    def upsert_engagement(self, data: dict):
        """Insert or Update engagement record, including new advanced fields."""
        try:
            payload = {
                "comment_id": data['id'],
                "post_id": data['post_id'],
                "subreddit": data['subreddit'],
                "body_snippet": data['body'],
                "score": data['score'],
                "reply_count": data['replies'],
                "posted_at": datetime.fromtimestamp(data['created_utc']).isoformat() if data.get('created_utc') else None,
                "last_updated": datetime.now().isoformat(),
                "has_handshake": data['handshake']
            }
            
            # Add advanced fields if provided
            if 'bot_score' in data:
                payload['bot_score'] = data['bot_score']
            if 'engagement_type' in data:
                payload['engagement_type'] = data['engagement_type']
            if 'status' in data:
                payload['status'] = data['status']
            if 'scheduled_at' in data:
                payload['scheduled_at'] = data['scheduled_at']
            if 'dm_content' in data:
                payload['dm_content'] = data['dm_content']
            
            # Cost Tracking
            if 'prompt_tokens' in data:
                payload['prompt_tokens'] = payload.get('prompt_tokens', 0) + data['prompt_tokens']
            if 'completion_tokens' in data:
                payload['completion_tokens'] = payload.get('completion_tokens', 0) + data['completion_tokens']
            if 'total_cost' in data:
                payload['total_cost'] = payload.get('total_cost', 0) + data['total_cost']

            self.supabase.table("scout_engagements").upsert(payload).execute()
        except Exception as e:
            logger.error(f"Error upserting engagement: {e}")

    def get_setting(self, key: str, default: any = None) -> any:
        """Fetch a setting from the scout_settings table."""
        try:
            response = self.supabase.table("scout_settings").select("value").eq("key", key).execute()
            if response.data:
                return response.data[0]['value']
            return default
        except Exception as e:
            logger.error(f"Error fetching setting {key}: {e}")
            return default

    def update_setting(self, key: str, value: any, description: Optional[str] = None):
        """Update or create a setting."""
        try:
            payload = {"key": key, "value": value}
            if description:
                payload["description"] = description
            payload["updated_at"] = datetime.now().isoformat()
            
            self.supabase.table("scout_settings").upsert(payload).execute()
        except Exception as e:
            logger.error(f"Error updating setting {key}: {e}")

    def get_engagement_stats(self) -> dict:
        """Get engagement metrics via RPC."""
        try:
            response = self.supabase.rpc('get_dashboard_stats', {}).execute()
            if response.data:
                stats = response.data
                
                return {
                    "active_conversations": stats.get("active_conversations", 0),
                    "net_karma": stats.get("net_karma_earned", 0),
                    "replies_received": 0,  # Not tracked in get_dashboard_stats easily, let's query it
                    "handshakes": stats.get("total_handshakes", 0)
                }
            return {"active_conversations": 0, "net_karma": 0, "replies_received": 0, "handshakes": 0}
            
        except Exception as e:
            logger.error(f"Error fetching engagement stats: {e}")
            return {"active_conversations": 0, "net_karma": 0, "replies_received": 0, "handshakes": 0}

    def clear_campaign_data(self):
        """Wipe discovered posts and briefings (reset campaign)."""
        try:
            # Note: To clear records in Supabase we can do deletes without conditions IF no RLS limits us
            # but usually it's better to explicitly match against something. 
            # We'll use eq or neq trick.
            self.supabase.table("scout_briefings").delete().neq("post_id", "nothing").execute()
            self.supabase.table("scout_engagements").delete().neq("comment_id", "nothing").execute()
            self.supabase.table("scout_processed_posts").delete().neq("post_id", "nothing").execute()
            logger.info("💥 Campaign data cleared (briefings, processed_posts, engagements).")
        except Exception as e:
            logger.error(f"Error clearing campaign data: {e}")
