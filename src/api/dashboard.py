from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict, Any
from datetime import datetime, timedelta
from ..db.connection import get_db_dependency
from ..db.models import ReplyQueue, ReplyPerformance, AnalyticsDaily, ScrapedTweet
from ..config.loader import get_config
import json

router = APIRouter(tags=["dashboard"])

@router.get("/")
async def get_dashboard_stats(db: Session = Depends(get_db_dependency)):
    """Get main dashboard statistics"""
    try:
        # Get today's stats
        today = datetime.now().date()

        # Tweets scraped (real count from ScrapedTweet table)
        scraped_query = db.query(ScrapedTweet).filter(
            ScrapedTweet.scraped_at >= today
        )
        total_scraped = scraped_query.count()

        # Split by platform (Reddit search terms start with "r/")
        reddit_scraped = scraped_query.filter(
            ScrapedTweet.search_term.like("r/%")
        ).count()
        twitter_scraped = total_scraped - reddit_scraped

        # Pending replies
        pending_replies = db.query(ReplyQueue).filter(
            ReplyQueue.status == "pending"
        ).count()

        # Success rate
        total_posted = db.query(ReplyQueue).filter(
            ReplyQueue.status == "posted"
        ).count()
        total_generated = db.query(ReplyQueue).count()

        success_rate = (total_posted / total_generated * 100) if total_generated > 0 else 0

        # Recent activity (last 24 hours)
        yesterday = datetime.now() - timedelta(days=1)
        recent_activity = db.query(ReplyQueue).filter(
            ReplyQueue.created_at >= yesterday
        ).order_by(ReplyQueue.created_at.desc()).limit(10).all()

        # Format activity feed
        activity_feed = []
        for activity in recent_activity:
            if activity.status == "posted":
                activity_feed.append({
                    "type": "reply_posted",
                    "text": f"Replied to @{activity.tweet_author}",
                    "time": format_time_ago(activity.created_at),
                    "color": "text-blue-600"
                })
            elif activity.status == "pending":
                activity_feed.append({
                    "type": "reply_generated",
                    "text": f"Generated reply for @{activity.tweet_author}",
                    "time": format_time_ago(activity.created_at),
                    "color": "text-purple-600"
                })

        # Get 7-day activity data for chart
        activity_data = get_7day_activity(db)

        # Get bot configuration for active hours
        try:
            bot_config, _ = get_config()
            # Handle potentially different config structures for active hours
            if hasattr(bot_config.schedule, 'active_hours') and isinstance(bot_config.schedule.active_hours, dict):
                start = bot_config.schedule.active_hours.get('start', '07:00')
                end = bot_config.schedule.active_hours.get('end', '23:59')
                active_hours = f"{start}-{end}"
            else:
                # Fallback or legacy attribute access
                active_hours = "07:00-24:00"
                
            platform_config = {
                "twitter": bot_config.platforms.twitter.enabled,
                "reddit": bot_config.platforms.reddit.enabled
            }
        except Exception as e:
            print(f"Error loading config in dashboard: {e}")
            active_hours = "07:00-24:00"
            platform_config = {"twitter": True, "reddit": True}

        return {
            "stats": {
                "tweets_scraped": total_scraped,
                "platform_breakdown": {
                    "twitter": twitter_scraped,
                    "reddit": reddit_scraped
                },
                "platform_config": platform_config,
                "pending_replies": pending_replies,
                "success_rate": round(success_rate, 1),
                "bot_status": "active",  # This should come from bot state
                "active_hours": active_hours
            },
            "activity_feed": activity_feed,
            "activity_chart": activity_data
        }

    except Exception as e:
        # Log the error and raise HTTP exception
        print(f"Error fetching dashboard stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get dashboard stats: {str(e)}")

@router.get("/pending-replies")
async def get_pending_replies(db: Session = Depends(get_db_dependency)):
    """Get all pending replies for review"""
    try:
        pending = db.query(ReplyQueue).filter(
            ReplyQueue.status == "pending"
        ).order_by(ReplyQueue.score.desc()).all()

        replies = []
        for reply in pending:
            replies.append({
                "id": reply.id,
                "tweet_text": reply.tweet_text,
                "tweet_author": reply.tweet_author,
                "tweet_author_followers": reply.tweet_author_followers,
                "generated_reply": reply.generated_reply,
                "score": reply.score,
                "commercial_category": reply.commercial_category,
                "timestamp": format_time_ago(reply.created_at),
                "tweet_url": reply.tweet_url
            })

        return {"replies": replies}

    except Exception as e:
        return {"replies": [], "error": str(e)}

def get_7day_activity(db: Session) -> Dict[str, List]:
    """Get scraping activity for the last 7 days"""
    try:
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=6)

        # Try to get data from analytics_daily table first
        daily_stats = db.query(AnalyticsDaily).filter(
            AnalyticsDaily.date >= start_date,
            AnalyticsDaily.date <= end_date
        ).order_by(AnalyticsDaily.date).all()

        if daily_stats:
            # Use real analytics data
            labels = []
            data = []
            for stat in daily_stats:
                labels.append(stat.date.strftime("%a"))  # Mon, Tue, etc.
                data.append(stat.tweets_scraped or 0)

            # Fill in missing days if needed
            current_date = start_date
            full_labels = []
            full_data = []

            for i in range(7):
                check_date = start_date + timedelta(days=i)
                day_label = check_date.strftime("%a")
                full_labels.append(day_label)

                # Find matching data or use 0
                day_data = next((d for d in data if labels[i % len(labels)] == day_label), 0)
                # If we don't have analytics data, estimate from reply_queue
                if day_data == 0:
                    replies_count = db.query(ReplyQueue).filter(
                        func.date(ReplyQueue.created_at) == check_date
                    ).count()
                    day_data = replies_count * 15  # Estimate 15 tweets scraped per reply

                full_data.append(day_data)

            return {"labels": full_labels, "data": full_data}
        else:
            # Fallback: estimate from reply_queue activity
            labels = []
            data = []

            for i in range(7):
                date = start_date + timedelta(days=i)
                labels.append(date.strftime("%a"))  # Mon, Tue, etc.

                # Count replies created on this day as a proxy for scraping activity
                replies_count = db.query(ReplyQueue).filter(
                    func.date(ReplyQueue.created_at) == date
                ).count()

                # Estimate scraped tweets (typically much higher than replies generated)
                estimated_scraped = replies_count * 15  # Rough estimate: 15 tweets scraped per reply
                data.append(estimated_scraped)

            return {"labels": labels, "data": data}

    except Exception as e:
        # Return fallback data if there's an error
        print(f"Error getting 7-day activity: {e}")
        return {
            "labels": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
            "data": [0, 0, 0, 0, 0, 0, 0]
        }

def format_time_ago(dt: datetime) -> str:
    """Format datetime as 'X minutes/hours ago'"""
    now = datetime.now()
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