from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from ..db.connection import get_db_dependency
from ..db.models import ReplyQueue, ReplyPerformance, AnalyticsDaily

router = APIRouter(tags=["analytics"])

@router.get("/")
async def get_analytics_summary(db: Session = Depends(get_db_dependency)):
    """Get analytics summary with recent activity"""
    try:
        # Generate some mock recent activity data for now
        # In a real implementation, this would come from a logs table or activity tracking
        current_time = datetime.now()

        recent_activity = [
            {
                "type": "scrape",
                "description": "Completed Twitter scraping session",
                "timestamp": (current_time - timedelta(minutes=30)).isoformat()
            },
            {
                "type": "generate",
                "description": "Generated 3 reply candidates",
                "timestamp": (current_time - timedelta(minutes=45)).isoformat()
            },
            {
                "type": "post",
                "description": "Successfully posted reply to entrepreneur tweet",
                "timestamp": (current_time - timedelta(hours=2)).isoformat()
            }
        ]

        # Get basic stats
        today = current_time.date()
        today_analytics = db.query(AnalyticsDaily).filter(
            AnalyticsDaily.date == today
        ).first()

        performance_data = {
            "scraping": today_analytics.tweets_scraped if today_analytics else 0,
            "replies": today_analytics.replies_generated if today_analytics else 0,
            "posted": today_analytics.replies_posted if today_analytics else 0
        }

        return {
            "recent_activity": recent_activity,
            "performance_data": performance_data,
            "engagement_stats": {
                "average_likes": 2.5,
                "average_retweets": 0.8,
                "reply_rate": 15.2
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get analytics: {str(e)}")

@router.get("/performance")
async def get_performance_metrics(
    days: int = 30,
    db: Session = Depends(get_db_dependency)
):
    """Get performance metrics for the specified time period"""
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        # Get daily analytics
        daily_stats = db.query(AnalyticsDaily).filter(
            AnalyticsDaily.date >= start_date.date(),
            AnalyticsDaily.date <= end_date.date()
        ).order_by(AnalyticsDaily.date).all()

        # Calculate totals and averages
        total_tweets_scraped = sum(day.tweets_scraped for day in daily_stats)
        total_replies_generated = sum(day.replies_generated for day in daily_stats)
        total_replies_posted = sum(day.replies_posted for day in daily_stats)
        total_cost = sum(day.api_cost_usd for day in daily_stats)

        # Calculate total engagement from averages
        total_engagement = sum((day.avg_engagement_rate or 0) * (day.replies_posted or 0) for day in daily_stats)

        success_rate = (total_replies_posted / total_replies_generated * 100) if total_replies_generated > 0 else 0
        avg_engagement_rate = (total_engagement / total_replies_posted) if total_replies_posted > 0 else 0

        # Format chart data
        chart_labels = [day.date.strftime("%Y-%m-%d") for day in daily_stats]
        chart_data = {
            "tweets_scraped": [day.tweets_scraped for day in daily_stats],
            "replies_generated": [day.replies_generated for day in daily_stats],
            "replies_posted": [day.replies_posted for day in daily_stats],
            "success_rate": [(day.replies_posted / day.replies_generated * 100) if day.replies_generated > 0 else 0 for day in daily_stats],
            "engagement_rate": [day.avg_engagement_rate or 0 for day in daily_stats]
        }

        return {
            "summary": {
                "total_tweets_scraped": total_tweets_scraped,
                "total_replies_generated": total_replies_generated,
                "total_replies_posted": total_replies_posted,
                "success_rate": round(success_rate, 2),
                "avg_engagement_rate": round(avg_engagement_rate, 2),
                "total_cost_usd": round(total_cost, 2),
                "cost_per_reply": round(total_cost / total_replies_posted, 2) if total_replies_posted > 0 else 0
            },
            "chart_data": {
                "labels": chart_labels,
                "datasets": chart_data
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get performance metrics: {str(e)}")

@router.get("/commercial-categories")
async def get_commercial_category_performance(db: Session = Depends(get_db_dependency)):
    """Get performance breakdown by commercial category"""
    try:
        # Get performance by commercial category
        category_stats = db.query(
            ReplyQueue.commercial_category,
            func.count(ReplyQueue.id).label('total'),
            func.sum(func.case([(ReplyQueue.status == 'posted', 1)], else_=0)).label('posted'),
            func.avg(ReplyQueue.score).label('avg_score'),
            func.avg(ReplyQueue.engagement_rate).label('avg_engagement')
        ).filter(
            ReplyQueue.created_at >= datetime.now() - timedelta(days=30)
        ).group_by(ReplyQueue.commercial_category).all()

        category_data = []
        for stat in category_stats:
            success_rate = (stat.posted / stat.total * 100) if stat.total > 0 else 0
            category_data.append({
                "category": stat.commercial_category or "unknown",
                "total_replies": stat.total,
                "posted_replies": int(stat.posted or 0),
                "success_rate": round(success_rate, 2),
                "avg_score": round(float(stat.avg_score or 0), 1),
                "avg_engagement_rate": round(float(stat.avg_engagement or 0), 2)
            })

        # Sort by success rate
        category_data.sort(key=lambda x: x['success_rate'], reverse=True)

        # Prepare chart data
        categories = [item['category'] for item in category_data]
        success_rates = [item['success_rate'] for item in category_data]
        reply_counts = [item['total_replies'] for item in category_data]

        return {
            "categories": category_data,
            "chart_data": {
                "categories": categories,
                "success_rates": success_rates,
                "reply_counts": reply_counts
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get category performance: {str(e)}")

@router.get("/hashtags")
async def get_hashtag_performance(db: Session = Depends(get_db_dependency)):
    """Get performance by hashtag"""
    try:
        # Get hashtag targeting data from config (mock for now)
        # In a real implementation, this would track which hashtag each tweet came from
        mock_hashtag_data = [
            {
                "hashtag": "#StartupLife",
                "tweets_found": 45,
                "conversion_rate": 12.5,
                "avg_score": 78,
                "status": "active",
                "last_scrape": datetime.now() - timedelta(hours=2)
            },
            {
                "hashtag": "#SoloFounder",
                "tweets_found": 32,
                "conversion_rate": 15.2,
                "avg_score": 82,
                "status": "active",
                "last_scrape": datetime.now() - timedelta(hours=1)
            },
            {
                "hashtag": "#EntrepreneurLife",
                "tweets_found": 38,
                "conversion_rate": 10.8,
                "avg_score": 75,
                "status": "active",
                "last_scrape": datetime.now() - timedelta(hours=3)
            },
            {
                "hashtag": "#BuildInPublic",
                "tweets_found": 0,
                "conversion_rate": 0,
                "avg_score": 0,
                "status": "timeout",
                "last_scrape": datetime.now() - timedelta(hours=1)
            },
            {
                "hashtag": "#Bootstrapped",
                "tweets_found": 0,
                "conversion_rate": 0,
                "avg_score": 0,
                "status": "timeout",
                "last_scrape": datetime.now() - timedelta(hours=1)
            }
        ]

        # Sort by conversion rate
        mock_hashtag_data.sort(key=lambda x: x['conversion_rate'], reverse=True)

        return {
            "hashtags": mock_hashtag_data,
            "summary": {
                "total_hashtags": len(mock_hashtag_data),
                "active_hashtags": len([h for h in mock_hashtag_data if h['status'] == 'active']),
                "total_tweets_found": sum(h['tweets_found'] for h in mock_hashtag_data),
                "avg_conversion_rate": sum(h['conversion_rate'] for h in mock_hashtag_data if h['conversion_rate'] > 0) / len([h for h in mock_hashtag_data if h['conversion_rate'] > 0]) if mock_hashtag_data else 0
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get hashtag performance: {str(e)}")

@router.get("/voice-compliance")
async def get_voice_compliance_metrics(db: Session = Depends(get_db_dependency)):
    """Get voice compliance metrics"""
    try:
        # Get voice compliance data
        voice_stats = db.query(
            func.count(ReplyQueue.id).label('total'),
            func.avg(ReplyQueue.voice_score).label('avg_score'),
            func.sum(func.case([(ReplyQueue.voice_violations > 0, 1)], else_=0)).label('violations')
        ).filter(
            ReplyQueue.created_at >= datetime.now() - timedelta(days=30)
        ).first()

        total_replies = voice_stats.total or 0
        avg_voice_score = float(voice_stats.avg_score or 0)
        total_violations = int(voice_stats.violations or 0)

        compliance_rate = ((total_replies - total_violations) / total_replies * 100) if total_replies > 0 else 100

        # Get common violations
        violation_types = db.query(
            ReplyQueue.voice_violations
        ).filter(
            ReplyQueue.voice_violations > 0,
            ReplyQueue.created_at >= datetime.now() - timedelta(days=30)
        ).limit(10).all()

        return {
            "compliance_rate": round(compliance_rate, 2),
            "avg_voice_score": round(avg_voice_score, 1),
            "total_replies": total_replies,
            "total_violations": total_violations,
            "violation_types": [v.voice_violations for v in violation_types if v.voice_violations]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get voice compliance metrics: {str(e)}")

@router.get("/engagement-heatmap")
async def get_engagement_heatmap(db: Session = Depends(get_db_dependency)):
    """Get engagement data by day of week and hour"""
    try:
        # Get posted replies with engagement data
        posted_replies = db.query(ReplyQueue).filter(
            ReplyQueue.status == 'posted',
            ReplyQueue.posted_at >= datetime.now() - timedelta(days=30)
        ).all()

        # Initialize heatmap data
        heatmap_data = {}
        for day in range(7):  # 0=Monday, 6=Sunday
            for hour in range(24):
                heatmap_data[f"{day}-{hour}"] = {
                    "day": day,
                    "hour": hour,
                    "count": 0,
                    "total_engagement": 0,
                    "avg_engagement": 0
                }

        # Populate with actual data
        for reply in posted_replies:
            if reply.posted_at:
                day = reply.posted_at.weekday()
                hour = reply.posted_at.hour
                key = f"{day}-{hour}"

                if key in heatmap_data:
                    heatmap_data[key]["count"] += 1
                    heatmap_data[key]["total_engagement"] += reply.engagement_rate or 0

        # Calculate averages
        for key, data in heatmap_data.items():
            if data["count"] > 0:
                data["avg_engagement"] = data["total_engagement"] / data["count"]

        # Convert to list format
        heatmap_list = list(heatmap_data.values())

        # Get day names
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

        return {
            "heatmap_data": heatmap_list,
            "day_names": day_names,
            "best_time": max(heatmap_list, key=lambda x: x["avg_engagement"]) if heatmap_list else None,
            "worst_time": min(heatmap_list, key=lambda x: x["avg_engagement"]) if heatmap_list else None
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get engagement heatmap: {str(e)}")

@router.get("/top-performers")
async def get_top_performing_replies(db: Session = Depends(get_db_dependency)):
    """Get top performing replies by engagement"""
    try:
        # Get top 10 replies by engagement rate
        top_replies = db.query(ReplyQueue).filter(
            ReplyQueue.status == 'posted',
            ReplyQueue.engagement_rate > 0
        ).order_by(desc(ReplyQueue.engagement_rate)).limit(10).all()

        top_reply_data = []
        for reply in top_replies:
            top_reply_data.append({
                "id": reply.id,
                "tweet_text": reply.tweet_text[:100] + "..." if len(reply.tweet_text) > 100 else reply.tweet_text,
                "tweet_author": reply.tweet_author,
                "final_reply": reply.final_reply,
                "engagement_rate": reply.engagement_rate,
                "engagement_likes": reply.engagement_likes,
                "engagement_retweets": reply.engagement_retweets,
                "commercial_category": reply.commercial_category,
                "posted_at": reply.posted_at.isoformat() if reply.posted_at else None,
                "marked_as_good_example": reply.marked_as_good_example
            })

        return {
            "top_replies": top_reply_data,
            "summary": {
                "total_shown": len(top_reply_data),
                "avg_engagement": sum(r['engagement_rate'] for r in top_reply_data) / len(top_reply_data) if top_reply_data else 0,
                "highest_engagement": max(r['engagement_rate'] for r in top_reply_data) if top_reply_data else 0
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get top performers: {str(e)}")

@router.get("/learning-corpus")
async def get_learning_corpus(db: Session = Depends(get_db_dependency)):
    """Get replies marked as good examples for LLM learning"""
    try:
        good_examples = db.query(ReplyQueue).filter(
            ReplyQueue.status == 'posted',
            ReplyQueue.marked_as_good_example == True,
            ReplyQueue.engagement_rate > 0
        ).order_by(desc(ReplyQueue.engagement_rate)).limit(20).all()

        corpus_data = []
        for example in good_examples:
            corpus_data.append({
                "id": example.id,
                "tweet_text": example.tweet_text,
                "tweet_author": example.tweet_author,
                "final_reply": example.final_reply,
                "engagement_rate": example.engagement_rate,
                "commercial_category": example.commercial_category,
                "posted_at": example.posted_at.isoformat() if example.posted_at else None
            })

        return {
            "examples": corpus_data,
            "total_count": len(corpus_data),
            "avg_engagement": sum(r['engagement_rate'] for r in corpus_data) / len(corpus_data) if corpus_data else 0
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get learning corpus: {str(e)}")

@router.get("/scraping-activity")
async def get_scraping_activity(days: int = 7, db: Session = Depends(get_db_dependency)):
    """Get scraping activity for the last N days"""
    try:
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days-1)

        # Get daily analytics for the date range
        daily_stats = db.query(AnalyticsDaily).filter(
            AnalyticsDaily.date >= start_date,
            AnalyticsDaily.date <= end_date
        ).order_by(AnalyticsDaily.date).all()

        # If no analytics data exists, estimate from reply_queue activity
        if not daily_stats:
            # Fallback: estimate scraping activity from reply creation patterns
            scraping_data = []
            for i in range(days):
                date = end_date - timedelta(days=days-1-i)
                # Count replies created on this day as a proxy for scraping activity
                replies_count = db.query(ReplyQueue).filter(
                    func.date(ReplyQueue.created_at) == date
                ).count()

                # Estimate scraped tweets (typically much higher than replies generated)
                estimated_scraped = replies_count * 20  # Rough estimate: 20 tweets scraped per reply

                scraping_data.append({
                    "date": date.strftime("%Y-%m-%d"),
                    "tweets_scraped": estimated_scraped,
                    "replies_generated": replies_count
                })
        else:
            scraping_data = []
            for stat in daily_stats:
                scraping_data.append({
                    "date": stat.date.strftime("%Y-%m-%d"),
                    "tweets_scraped": stat.tweets_scraped,
                    "replies_generated": stat.replies_generated
                })

        # Get today's scraping activity from logs if available
        today_scraped = 0
        today_replies = db.query(ReplyQueue).filter(
            func.date(ReplyQueue.created_at) == end_date
        ).count()

        # If we have bot logs, we could parse them for more accurate scraping counts
        # For now, use a reasonable estimate based on recent activity
        if today_replies > 0:
            today_scraped = today_replies * 15  # Estimate 15 tweets scraped per reply today

        return {
            "daily_data": scraping_data,
            "summary": {
                "total_days": len(scraping_data),
                "total_tweets_scraped": sum(d["tweets_scraped"] for d in scraping_data),
                "total_replies_generated": sum(d["replies_generated"] for d in scraping_data),
                "today_scraped": today_scraped,
                "today_replies": today_replies,
                "avg_scraped_per_day": sum(d["tweets_scraped"] for d in scraping_data) // len(scraping_data) if scraping_data else 0
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get scraping activity: {str(e)}")