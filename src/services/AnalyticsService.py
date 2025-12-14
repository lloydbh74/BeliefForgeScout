"""
Analytics service with optimized database queries and caching
Provides business logic for analytics data processing and aggregation
"""
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta, date
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, or_, text
from ..db.models import ReplyQueue, ReplyPerformance, AnalyticsDaily, RepliedTweets
from ..services.CacheService import cache_service

logger = logging.getLogger(__name__)

class AnalyticsService:
    """Service for analytics data processing with query optimization and caching"""

    def __init__(self, db: Session):
        self.db = db

    async def get_dashboard_stats(self, user_id: str = None) -> Dict[str, Any]:
        """Get dashboard statistics with optimized queries and caching"""
        cache_key, ttl = cache_service.cache_dashboard_stats(user_id)

        # Try cache first
        cached_stats = cache_service.get(cache_key)
        if cached_stats:
            logger.debug("Returning cached dashboard stats")
            return cached_stats

        try:
            today = date.today()

            # Optimized single query for all stats
            stats_query = self.db.query(
                func.count(ReplyQueue.id).label('total_replies'),
                func.sum(func.case([(ReplyQueue.status == 'posted', 1)], else_=0)).label('posted_replies'),
                func.sum(func.case([(ReplyQueue.status == 'pending', 1)], else_=0)).label('pending_replies'),
                func.avg(ReplyQueue.score).label('avg_score'),
                func.avg(func.case([(ReplyQueue.engagement_rate > 0, ReplyQueue.engagement_rate)], else_=0)).label('avg_engagement')
            ).filter(
                func.date(ReplyQueue.created_at) == today
            )

            stats_result = stats_query.first()
            total_replies = stats_result.total_replies or 0
            posted_replies = stats_result.posted_replies or 0
            pending_replies = stats_result.pending_replies or 0
            avg_score = float(stats_result.avg_score or 0)
            avg_engagement = float(stats_result.avg_engagement or 0)

            success_rate = (posted_replies / total_replies * 100) if total_replies > 0 else 0

            # Get activity data for last 7 days in single query
            activity_data = await self._get_7day_activity_optimized()

            # Get recent activity with optimized query
            recent_activity = await self._get_recent_activity_optimized()

            dashboard_stats = {
                "stats": {
                    "tweets_scraped": self._estimate_tweets_scraped(total_replies),
                    "pending_replies": pending_replies,
                    "success_rate": round(success_rate, 1),
                    "avg_score": round(avg_score, 1),
                    "avg_engagement": round(avg_engagement, 2),
                    "bot_status": await self._get_bot_status(),
                    "active_hours": await self._get_active_hours()
                },
                "activity_feed": recent_activity,
                "activity_chart": activity_data,
                "last_updated": datetime.utcnow().isoformat()
            }

            # Cache the result
            cache_service.set(cache_key, dashboard_stats, ttl)
            logger.debug("Dashboard stats cached successfully")

            return dashboard_stats

        except Exception as e:
            logger.error(f"Error getting dashboard stats: {e}")
            # Return empty stats rather than mock data
            return {
                "stats": {
                    "tweets_scraped": 0,
                    "pending_replies": 0,
                    "success_rate": 0,
                    "avg_score": 0,
                    "avg_engagement": 0,
                    "bot_status": "inactive",
                    "active_hours": "07:00-24:00"
                },
                "activity_feed": [],
                "activity_chart": {"labels": [], "data": []},
                "last_updated": datetime.utcnow().isoformat(),
                "error": str(e)
            }

    async def get_performance_metrics(self, days: int = 30, user_id: str = None) -> Dict[str, Any]:
        """Get performance metrics with optimized queries and caching"""
        cache_key, ttl = cache_service.cache_performance_metrics(days, user_id)

        # Try cache first
        cached_metrics = cache_service.get(cache_key)
        if cached_metrics:
            logger.debug("Returning cached performance metrics")
            return cached_metrics

        try:
            end_date = date.today()
            start_date = end_date - timedelta(days=days-1)

            # Optimized query for daily stats
            daily_stats = self.db.query(
                AnalyticsDaily.date,
                AnalyticsDaily.tweets_scraped,
                AnalyticsDaily.replies_generated,
                AnalyticsDaily.replies_posted,
                AnalyticsDaily.api_cost_usd,
                AnalyticsDaily.avg_engagement_rate
            ).filter(
                AnalyticsDaily.date >= start_date,
                AnalyticsDaily.date <= end_date
            ).order_by(AnalyticsDaily.date).all()

            # Calculate aggregates efficiently
            totals = {
                "total_tweets_scraped": sum(day.tweets_scraped or 0 for day in daily_stats),
                "total_replies_generated": sum(day.replies_generated or 0 for day in daily_stats),
                "total_replies_posted": sum(day.replies_posted or 0 for day in daily_stats),
                "total_cost_usd": round(sum(day.api_cost_usd or 0 for day in daily_stats), 2)
            }

            # Calculate success rate and average engagement
            success_rate = (totals["total_replies_posted"] / totals["total_replies_generated"] * 100) if totals["total_replies_generated"] > 0 else 0
            avg_engagement = sum(day.avg_engagement_rate or 0 for day in daily_stats if day.avg_engagement_rate) / len([d for d in daily_stats if d.avg_engagement_rate]) if daily_stats else 0

            # Prepare chart data
            chart_data = {
                "labels": [day.date.strftime("%Y-%m-%d") for day in daily_stats],
                "datasets": {
                    "tweets_scraped": [day.tweets_scraped or 0 for day in daily_stats],
                    "replies_generated": [day.replies_generated or 0 for day in daily_stats],
                    "replies_posted": [day.replies_posted or 0 for day in daily_stats],
                    "success_rate": [((day.replies_posted / day.replies_generated * 100) if day.replies_generated > 0 else 0) for day in daily_stats],
                    "engagement_rate": [day.avg_engagement_rate or 0 for day in daily_stats]
                }
            }

            performance_metrics = {
                "summary": {
                    **totals,
                    "success_rate": round(success_rate, 2),
                    "avg_engagement_rate": round(avg_engagement, 2),
                    "cost_per_reply": round(totals["total_cost_usd"] / totals["total_replies_posted"], 2) if totals["total_replies_posted"] > 0 else 0
                },
                "chart_data": chart_data,
                "period_days": days,
                "last_updated": datetime.utcnow().isoformat()
            }

            # Cache the result
            cache_service.set(cache_key, performance_metrics, ttl)
            logger.debug("Performance metrics cached successfully")

            return performance_metrics

        except Exception as e:
            logger.error(f"Error getting performance metrics: {e}")
            return {
                "summary": {
                    "total_tweets_scraped": 0,
                    "total_replies_generated": 0,
                    "total_replies_posted": 0,
                    "success_rate": 0,
                    "avg_engagement_rate": 0,
                    "total_cost_usd": 0,
                    "cost_per_reply": 0
                },
                "chart_data": {"labels": [], "datasets": {}},
                "period_days": days,
                "last_updated": datetime.utcnow().isoformat(),
                "error": str(e)
            }

    async def get_commercial_category_performance(self, days: int = 30, user_id: str = None) -> Dict[str, Any]:
        """Get commercial category performance with optimized queries"""
        cache_key, ttl = cache_service.cache_commercial_categories(days, user_id)

        # Try cache first
        cached_data = cache_service.get(cache_key)
        if cached_data:
            logger.debug("Returning cached commercial category data")
            return cached_data

        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)

            # Optimized single query for category stats
            category_stats = self.db.query(
                ReplyQueue.commercial_category,
                func.count(ReplyQueue.id).label('total_replies'),
                func.sum(func.case([(ReplyQueue.status == 'posted', 1)], else_=0)).label('posted_replies'),
                func.avg(ReplyQueue.score).label('avg_score'),
                func.avg(func.case([(ReplyQueue.engagement_rate > 0, ReplyQueue.engagement_rate)], else_=0)).label('avg_engagement'),
                func.sum(ReplyQueue.engagement_likes).label('total_likes'),
                func.sum(ReplyQueue.engagement_retweets).label('total_retweets')
            ).filter(
                ReplyQueue.created_at >= cutoff_date
            ).group_by(ReplyQueue.commercial_category).all()

            categories = []
            for stat in category_stats:
                total_replies = stat.total_replies or 0
                posted_replies = stat.posted_replies or 0
                success_rate = (posted_replies / total_replies * 100) if total_replies > 0 else 0

                category = {
                    "category": stat.commercial_category or "unknown",
                    "total_replies": total_replies,
                    "posted_replies": posted_replies,
                    "success_rate": round(success_rate, 2),
                    "avg_score": round(float(stat.avg_score or 0), 1),
                    "avg_engagement_rate": round(float(stat.avg_engagement or 0), 2),
                    "total_likes": stat.total_likes or 0,
                    "total_retweets": stat.total_retweets or 0
                }
                categories.append(category)

            # Sort by success rate
            categories.sort(key=lambda x: x['success_rate'], reverse=True)

            result = {
                "categories": categories,
                "summary": {
                    "total_categories": len(categories),
                    "total_replies": sum(c['total_replies'] for c in categories),
                    "avg_success_rate": round(sum(c['success_rate'] for c in categories) / len(categories), 2) if categories else 0,
                    "top_category": categories[0]['category'] if categories else None
                },
                "period_days": days,
                "last_updated": datetime.utcnow().isoformat()
            }

            # Cache the result
            cache_service.set(cache_key, result, ttl)
            logger.debug("Commercial category data cached successfully")

            return result

        except Exception as e:
            logger.error(f"Error getting commercial category performance: {e}")
            return {
                "categories": [],
                "summary": {
                    "total_categories": 0,
                    "total_replies": 0,
                    "avg_success_rate": 0,
                    "top_category": None
                },
                "period_days": days,
                "last_updated": datetime.utcnow().isoformat(),
                "error": str(e)
            }

    async def _get_7day_activity_optimized(self) -> Dict[str, List]:
        """Get 7-day activity data with optimized query"""
        try:
            end_date = date.today()
            start_date = end_date - timedelta(days=6)

            # Try analytics_daily first (faster)
            daily_stats = self.db.query(
                AnalyticsDaily.date,
                AnalyticsDaily.tweets_scraped
            ).filter(
                AnalyticsDaily.date >= start_date,
                AnalyticsDaily.date <= end_date
            ).order_by(AnalyticsDaily.date).all()

            if daily_stats and len(daily_stats) >= 7:
                # We have complete analytics data
                labels = []
                data = []
                current_date = start_date

                for i in range(7):
                    check_date = start_date + timedelta(days=i)
                    day_stat = next((s for s in daily_stats if s.date == check_date), None)
                    labels.append(check_date.strftime("%a"))
                    data.append(day_stat.tweets_scraped if day_stat else 0)

                return {"labels": labels, "data": data}

            # Fallback to ReplyQueue estimation
            reply_activity = self.db.query(
                func.date(ReplyQueue.created_at).label('date'),
                func.count(ReplyQueue.id).label('reply_count')
            ).filter(
                func.date(ReplyQueue.created_at) >= start_date,
                func.date(ReplyQueue.created_at) <= end_date
            ).group_by(func.date(ReplyQueue.created_at)).all()

            # Create complete 7-day data
            labels = []
            data = []
            current_date = start_date

            for i in range(7):
                check_date = start_date + timedelta(days=i)
                day_activity = next((a for a in reply_activity if a.date == check_date), None)
                labels.append(check_date.strftime("%a"))

                # Estimate scraped tweets (15x replies as rough estimate)
                estimated_scraped = (day_activity.reply_count or 0) * 15
                data.append(estimated_scraped)

            return {"labels": labels, "data": data}

        except Exception as e:
            logger.error(f"Error getting 7-day activity: {e}")
            # Return empty data structure
            days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
            return {"labels": days, "data": [0] * 7}

    async def _get_recent_activity_optimized(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent activity with optimized query"""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=24)

            # Optimized query for recent activity
            recent_replies = self.db.query(
                ReplyQueue.id,
                ReplyQueue.status,
                ReplyQueue.created_at,
                ReplyQueue.tweet_author,
                ReplyQueue.commercial_category,
                ReplyQueue.score,
                ReplyQueue.engagement_rate
            ).filter(
                ReplyQueue.created_at >= cutoff_time
            ).order_by(desc(ReplyQueue.created_at)).limit(limit).all()

            activity_feed = []
            for reply in recent_replies:
                activity_type = "reply_posted" if reply.status == "posted" else "reply_generated"

                activity = {
                    "type": activity_type,
                    "description": self._generate_activity_description(reply),
                    "timestamp": reply.created_at.isoformat(),
                    "tweet_author": reply.tweet_author,
                    "commercial_category": reply.commercial_category,
                    "score": reply.score,
                    "engagement_rate": reply.engagement_rate
                }
            activity_feed.append(activity)

            return activity_feed

        except Exception as e:
            logger.error(f"Error getting recent activity: {e}")
            from fastapi import HTTPException
            raise HTTPException(status_code=500, detail=f"Failed to get scraping activity: {str(e)}")

    def summarize_daily_activity(self, target_date: date = None) -> bool:
        """
        Aggregate daily activity into AnalyticsDaily table.
        Should be run before cleanup_old_data to preserve history.
        """
        try:
            if target_date is None:
                target_date = date.today() - timedelta(days=1)

            # Check if already exists
            existing = self.db.query(AnalyticsDaily).filter(
                AnalyticsDaily.date == target_date
            ).first()

            if existing:
                logger.info(f"Analytics already summarized for {target_date}")
                return True

            # Calculate metrics for the day
            # 1. Scraped Tweets (count from ScrapedTweet table)
            from ..db.models import ScrapedTweet
            
            # Start/End of the target day
            start_dt = datetime.combine(target_date, datetime.min.time())
            end_dt = datetime.combine(target_date, datetime.max.time())

            scraped_count = self.db.query(func.count(ScrapedTweet.tweet_id)).filter(
                ScrapedTweet.scraped_at >= start_dt,
                ScrapedTweet.scraped_at <= end_dt
            ).scalar() or 0

            # 2. Filtered/Queued counts
            filtered_count = self.db.query(func.count(ScrapedTweet.tweet_id)).filter(
                ScrapedTweet.scraped_at >= start_dt,
                ScrapedTweet.scraped_at <= end_dt,
                ScrapedTweet.status == 'filtered'
            ).scalar() or 0
            
            # 3. Reply stats (using ReplyQueue)
            replies_generated = self.db.query(func.count(ReplyQueue.id)).filter(
                ReplyQueue.created_at >= start_dt,
                ReplyQueue.created_at <= end_dt
            ).scalar() or 0

            replies_posted = self.db.query(func.count(ReplyQueue.id)).filter(
                ReplyQueue.created_at >= start_dt,
                ReplyQueue.created_at <= end_dt,
                ReplyQueue.status == 'posted'
            ).scalar() or 0

            # 4. Averages
            avg_engagement = self.db.query(func.avg(ReplyQueue.engagement_rate)).filter(
                ReplyQueue.created_at >= start_dt,
                ReplyQueue.created_at <= end_dt,
                ReplyQueue.engagement_rate > 0
            ).scalar() or 0.0

            # Create record
            daily_stat = AnalyticsDaily(
                date=target_date,
                tweets_scraped=scraped_count,
                tweets_filtered=filtered_count,
                replies_generated=replies_generated,
                replies_posted=replies_posted,
                avg_engagement_rate=avg_engagement
            )

            self.db.add(daily_stat)
            self.db.commit()
            
            logger.info(f"Summarized analytics for {target_date}: {scraped_count} scraped, {replies_generated} generated")
            return True

        except Exception as e:
            logger.error(f"Failed to summarize daily activity: {e}")
            self.db.rollback()
            return False

    def cleanup_old_data(self) -> Dict[str, int]:
        """
        Clean up old data based on retention policy.
        Preserves 'valued' data (replies/queued) longer than 'noise' (filtered).
        """
        from ..config.loader import get_config, RetentionConfig
        from ..db.models import ScrapedTweet
        
        bot_config, _ = get_config()
        retention = bot_config.monitoring.retention
        
        stats = {"deleted_noise": 0, "deleted_history": 0}
        
        try:
            # 1. Summarize yesterday's data first to ensure we don't lose stats
            yesterday = date.today() - timedelta(days=1)
            self.summarize_daily_activity(yesterday)

            # 2. Delete OLD noise (filtered, low score)
            # tweets that were NOT turned into replies
            noise_cutoff = datetime.utcnow() - timedelta(days=retention.scraped_data_days)
            
            noise_query = self.db.query(ScrapedTweet).filter(
                ScrapedTweet.scraped_at < noise_cutoff,
                ScrapedTweet.status.in_(['scraped', 'filtered', 'scored_low', 'deduplicated'])
            )
            stats["deleted_noise"] = noise_query.delete(synchronize_session=False)

            # 3. Delete VERY OLD history (queued, etc) if configured
            # This is separate because we might want to keep "successes" longer
            history_cutoff = datetime.utcnow() - timedelta(days=retention.scraped_data_keep_queued_days)
            
            history_query = self.db.query(ScrapedTweet).filter(
                ScrapedTweet.scraped_at < history_cutoff
            )
            # Note: We delete everything older than the MAX retention limit
            stats["deleted_history"] = history_query.delete(synchronize_session=False)

            self.db.commit()
            
            if stats["deleted_noise"] > 0 or stats["deleted_history"] > 0:
                logger.info(f"Data cleanup complete: {stats}")
                
            return stats

        except Exception as e:
            logger.error(f"Data cleanup failed: {e}")
            self.db.rollback()
            return stats

    def _generate_activity_description(self, reply) -> str:
        """Generate human-readable activity description"""
        if reply.status == "posted":
            return f"Posted reply to @{reply.tweet_author or 'unknown'}"
        elif reply.status == "pending":
            return f"Generated reply for @{reply.tweet_author or 'unknown'}"
        elif reply.status == "rejected":
            return f"Rejected reply for @{reply.tweet_author or 'unknown'}"
        else:
            return f"Processed reply for @{reply.tweet_author or 'unknown'}"

    def _estimate_tweets_scraped(self, reply_count: int) -> int:
        """Estimate tweets scraped from reply count"""
        # Rough estimation: typically 15-20 tweets scraped per reply generated
        return reply_count * 15

    async def _get_bot_status(self) -> str:
        """Get current bot status"""
        # This should integrate with actual bot status management
        # For now, return basic status
        try:
            # Check for recent activity
            recent_activity = self.db.query(ReplyQueue).filter(
                ReplyQueue.created_at >= datetime.utcnow() - timedelta(minutes=10)
            ).first()

            return "active" if recent_activity else "inactive"
        except Exception:
            return "unknown"

    async def _get_active_hours(self) -> str:
        """Get bot active hours from config"""
        try:
            from ..config.loader import get_config
            bot_config, _ = get_config()
            return f"{bot_config.schedule.active_hours_start}:00-{bot_config.schedule.active_hours_end}:00"
        except Exception:
            return "07:00-24:00"  # Default fallback

    # Cache invalidation methods
    def invalidate_analytics_cache(self):
        """Invalidate analytics cache entries"""
        return cache_service.invalidate_analytics_cache()

    def invalidate_reply_cache(self):
        """Invalidate reply-related cache entries"""
        return cache_service.invalidate_reply_cache()