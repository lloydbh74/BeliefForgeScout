"""
Refactored Dashboard API with optimized queries, caching, and service layer
Eliminates N+1 query problems and mock data dependencies
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
import logging
from datetime import datetime

from ..db.connection import get_db_dependency
from ..services.AnalyticsService import AnalyticsService
from ..services.CacheService import cache_service
from ..services.ReplyService import ReplyService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["dashboard_v2"])

@router.get("/")
async def get_dashboard_stats(
    db: Session = Depends(get_db_dependency),
    user_id: Optional[str] = Query(None, description="User ID for multi-tenant support")
):
    """
    Get main dashboard statistics with optimized queries and caching
    Replaces the original endpoint with performance improvements and real data only
    """
    try:
        # Initialize analytics service
        analytics_service = AnalyticsService(db)

        # Get dashboard stats from service layer
        dashboard_data = await analytics_service.get_dashboard_stats(user_id)

        if "error" in dashboard_data:
            logger.warning(f"Dashboard stats returned with error: {dashboard_data['error']}")
            # Return error structure rather than mock data
            raise HTTPException(
                status_code=503,
                detail=f"Dashboard service unavailable: {dashboard_data['error']}"
            )

        # Add cache headers
        return {
            **dashboard_data,
            "cache_status": "hit" if cache_service.get(f"dashboard_stats:{user_id or 'default'}") else "miss",
            "api_version": "v2"
        }

    except Exception as e:
        logger.error(f"Error in dashboard stats endpoint: {e}")
        # Return proper error instead of mock data
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load dashboard statistics: {str(e)}"
        )

@router.get("/health")
async def dashboard_health(
    db: Session = Depends(get_db_dependency)
):
    """Health check for dashboard service"""
    try:
        # Check database connectivity
        db.execute("SELECT 1")
        db_status = "healthy"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = "unhealthy"

    # Check cache service
    cache_health = cache_service.health_check()

    # Overall status
    overall_status = "healthy" if db_status == "healthy" and cache_health.get("status") != "unhealthy" else "degraded"

    return {
        "status": overall_status,
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "database": {"status": db_status},
            "cache": cache_health
        },
        "api_version": "v2"
    }

@router.get("/cache/stats")
async def get_cache_stats():
    """Get cache statistics for monitoring"""
    try:
        return cache_service.get_stats()
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get cache statistics: {str(e)}"
        )

@router.post("/cache/invalidate")
async def invalidate_cache(
    cache_type: str = Query(..., description="Type of cache to invalidate: 'analytics', 'replies', 'all"),
    user_id: Optional[str] = Query(None, description="User ID for targeted invalidation")
):
    """Invalidate cache entries"""
    try:
        if cache_type == "analytics":
            deleted = cache_service.invalidate_analytics_cache()
        elif cache_type == "replies":
            deleted = cache_service.invalidate_reply_cache()
        elif cache_type == "all":
            cache_service.clear_all()
            deleted = "all"
        elif cache_type == "user" and user_id:
            deleted = cache_service.invalidate_user_cache(user_id)
        else:
            raise HTTPException(
                status_code=400,
                detail="Invalid cache_type. Use 'analytics', 'replies', 'all', or 'user' with user_id"
            )

        return {
            "success": True,
            "cache_type": cache_type,
            "deleted_count": deleted,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error invalidating cache: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to invalidate cache: {str(e)}"
        )

@router.get("/pending-replies")
async def get_pending_replies_v2(
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of replies to return"),
    user_id: Optional[str] = Query(None, description="User ID for multi-tenant support"),
    db: Session = Depends(get_db_dependency)
):
    """
    Get pending replies with optimized queries and caching
    Replaces the original endpoint with performance improvements
    """
    try:
        # Initialize reply service
        reply_service = ReplyService(db)

        # Get pending replies from service layer
        result = await reply_service.get_pending_replies(limit, user_id)

        if "error" in result:
            logger.warning(f"Pending replies returned with error: {result['error']}")
            raise HTTPException(
                status_code=503,
                detail=f"Reply service unavailable: {result['error']}"
            )

        # Add cache status
        cache_key = f"reply_queue:{user_id or 'default'}"
        result["cache_status"] = "hit" if cache_service.get(cache_key) else "miss"
        result["api_version"] = "v2"

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in pending replies endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load pending replies: {str(e)}"
        )

@router.get("/queue-stats")
async def get_queue_statistics(
    db: Session = Depends(get_db_dependency),
    user_id: Optional[str] = Query(None, description="User ID for multi-tenant support")
):
    """Get reply queue statistics"""
    try:
        reply_service = ReplyService(db)
        stats = reply_service.get_queue_statistics()

        return {
            "statistics": stats,
            "last_updated": datetime.utcnow().isoformat(),
            "api_version": "v2"
        }

    except Exception as e:
        logger.error(f"Error getting queue statistics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get queue statistics: {str(e)}"
        )

@router.post("/cleanup")
async def cleanup_old_data(
    days: int = Query(7, ge=1, le=90, description="Number of days to keep pending replies"),
    db: Session = Depends(get_db_dependency),
    user_id: Optional[str] = Query(None, description="User ID for multi-tenant support")
):
    """Clean up old pending replies and expired cache entries"""
    try:
        # Initialize reply service
        reply_service = ReplyService(db)

        # Clean up old pending replies
        cleaned_count = reply_service.cleanup_old_pending_replies(days)

        # Invalidate related cache
        cache_service.invalidate_reply_cache()

        logger.info(f"Cleanup completed: {cleaned_count} old pending replies removed")

        return {
            "success": True,
            "cleaned_replies": cleaned_count,
            "cutoff_days": days,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Cleanup failed: {str(e)}"
        )