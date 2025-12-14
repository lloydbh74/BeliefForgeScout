from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta

from ..db.connection import get_db_dependency
from ..db.models import ScrapedTweet

router = APIRouter(tags=["analytics"])

@router.get("/history")
async def get_processing_history(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    status: Optional[str] = None,
    search_term: Optional[str] = None,
    platform: Optional[str] = None,
    db: Session = Depends(get_db_dependency)
):
    """Get paginated history of scraped tweets"""
    query = db.query(ScrapedTweet)

    if status:
        query = query.filter(ScrapedTweet.status == status)
    
    if search_term:
        query = query.filter(ScrapedTweet.search_term.ilike(f"%{search_term}%"))

    if platform:
        if platform.lower() == 'reddit':
            query = query.filter(ScrapedTweet.search_term.like("r/%"))
        elif platform.lower() == 'twitter':
            query = query.filter(~ScrapedTweet.search_term.like("r/%"))

    # Order by most recent
    query = query.order_by(ScrapedTweet.scraped_at.desc())

    # Pagination
    total = query.count()
    tweets = query.offset((page - 1) * limit).limit(limit).all()

    return {
        "data": [t.to_dict() for t in tweets],
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit
        }
    }

@router.get("/funnel")
async def get_funnel_stats(
    days: int = Query(7, ge=1, le=30),
    platform: Optional[str] = None,
    db: Session = Depends(get_db_dependency)
):
    """Get funnel statistics for the last N days"""
    start_date = datetime.utcnow() - timedelta(days=days)
    
    base_query = db.query(ScrapedTweet).filter(ScrapedTweet.scraped_at >= start_date)

    if platform:
        if platform.lower() == 'reddit':
            base_query = base_query.filter(ScrapedTweet.search_term.like("r/%"))
        elif platform.lower() == 'twitter':
            base_query = base_query.filter(~ScrapedTweet.search_term.like("r/%"))
    
    stats = {
        "scraped": base_query.count(),
        "filtered": base_query.filter(ScrapedTweet.status == 'filtered').count(),
        "scored_low": base_query.filter(ScrapedTweet.status == 'scored_low').count(),
        "deduplicated": base_query.filter(ScrapedTweet.status == 'deduplicated').count(),
        "queued": base_query.filter(ScrapedTweet.status == 'queued').count()
    }
    
    return stats