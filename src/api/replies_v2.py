"""
Refactored Replies API with optimized queries, caching, and service layer
Handles reply management with proper validation, error handling, and performance tracking
"""
from fastapi import APIRouter, HTTPException, Depends, Query, Body
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime

from ..db.connection import get_db_dependency
from ..services.ReplyService import ReplyService
from ..services.CacheService import cache_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["replies_v2"])

# Pydantic models for request validation
class ReplyEditRequest(BaseModel):
    reply_text: str = Field(..., min_length=1, max_length=280, description="Reply text (1-280 characters)")

class BulkActionRequest(BaseModel):
    reply_ids: List[int] = Field(..., min_items=1, description="List of reply IDs to process")
    reason: Optional[str] = Field(None, max_length=500, description="Optional reason for bulk action")

@router.get("/pending")
async def get_pending_replies_v2(
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of replies to return"),
    user_id: Optional[str] = Query(None, description="User ID for multi-tenant support"),
    db: Session = Depends(get_db_dependency)
):
    """
    Get pending replies for review with optimized queries and caching
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

@router.post("/{reply_id}/approve")
async def approve_reply_v2(
    reply_id: int,
    user_id: Optional[str] = Query(None, description="User ID for multi-tenant support"),
    db: Session = Depends(get_db_dependency)
):
    """
    Approve and post a reply with proper validation and tracking
    """
    try:
        # Initialize reply service
        reply_service = ReplyService(db)

        # Approve the reply
        result = await reply_service.approve_reply(reply_id, user_id)

        if not result["success"]:
            if "not found" in result["error"]:
                raise HTTPException(status_code=404, detail=result["error"])
            else:
                raise HTTPException(status_code=400, detail=result["error"])

        logger.info(f"Reply {reply_id} approved successfully by user {user_id}")

        return {
            "success": True,
            "message": "Reply approved and posted successfully",
            "data": result,
            "timestamp": datetime.utcnow().isoformat(),
            "api_version": "v2"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error approving reply {reply_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to approve reply: {str(e)}"
        )

@router.post("/{reply_id}/reject")
async def reject_reply_v2(
    reply_id: int,
    reason: Optional[str] = Query(None, max_length=500, description="Reason for rejection"),
    user_id: Optional[str] = Query(None, description="User ID for multi-tenant support"),
    db: Session = Depends(get_db_dependency)
):
    """
    Reject a reply with optional reason and tracking
    """
    try:
        # Initialize reply service
        reply_service = ReplyService(db)

        # Reject the reply
        result = await reply_service.reject_reply(reply_id, reason, user_id)

        if not result["success"]:
            if "not found" in result["error"]:
                raise HTTPException(status_code=404, detail=result["error"])
            else:
                raise HTTPException(status_code=400, detail=result["error"])

        logger.info(f"Reply {reply_id} rejected by user {user_id}. Reason: {reason}")

        return {
            "success": True,
            "message": "Reply rejected successfully",
            "data": result,
            "timestamp": datetime.utcnow().isoformat(),
            "api_version": "v2"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rejecting reply {reply_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to reject reply: {str(e)}"
        )

@router.post("/{reply_id}/edit")
async def edit_reply_v2(
    reply_id: int,
    request: ReplyEditRequest,
    user_id: Optional[str] = Query(None, description="User ID for multi-tenant support"),
    db: Session = Depends(get_db_dependency)
):
    """
    Edit a pending reply with validation and tracking
    """
    try:
        # Initialize reply service
        reply_service = ReplyService(db)

        # Edit the reply
        result = await reply_service.edit_reply(reply_id, request.reply_text, user_id)

        if not result["success"]:
            if "not found" in result["error"]:
                raise HTTPException(status_code=404, detail=result["error"])
            else:
                raise HTTPException(status_code=400, detail=result["error"])

        logger.info(f"Reply {reply_id} edited by user {user_id}")

        return {
            "success": True,
            "message": "Reply edited successfully",
            "data": result,
            "timestamp": datetime.utcnow().isoformat(),
            "api_version": "v2"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error editing reply {reply_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to edit reply: {str(e)}"
        )

@router.get("/history")
async def get_reply_history_v2(
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of replies to return"),
    user_id: Optional[str] = Query(None, description="User ID for multi-tenant support"),
    db: Session = Depends(get_db_dependency)
):
    """
    Get reply history with optimized queries
    """
    try:
        # Initialize reply service
        reply_service = ReplyService(db)

        # Get reply history from service layer
        result = await reply_service.get_reply_history(days, limit, user_id)

        if "error" in result:
            logger.warning(f"Reply history returned with error: {result['error']}")
            raise HTTPException(
                status_code=503,
                detail=f"Reply service unavailable: {result['error']}"
            )

        result["api_version"] = "v2"

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting reply history: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get reply history: {str(e)}"
        )

@router.post("/bulk/approve")
async def bulk_approve_replies_v2(
    request: BulkActionRequest,
    user_id: Optional[str] = Query(None, description="User ID for multi-tenant support"),
    db: Session = Depends(get_db_dependency)
):
    """
    Bulk approve multiple replies efficiently
    """
    try:
        # Validate request
        if len(request.reply_ids) > 100:
            raise HTTPException(
                status_code=400,
                detail="Cannot approve more than 100 replies at once"
            )

        # Initialize reply service
        reply_service = ReplyService(db)

        # Perform bulk approve
        result = await reply_service.bulk_approve(request.reply_ids, user_id)

        if not result["success"]:
            raise HTTPException(
                status_code=500,
                detail=result["error"]
            )

        logger.info(f"Bulk approved {result['approved_count']} replies by user {user_id}")

        return {
            "success": True,
            "message": f"Bulk approved {result['approved_count']} replies",
            "data": result,
            "timestamp": datetime.utcnow().isoformat(),
            "api_version": "v2"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in bulk approve: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Bulk approve failed: {str(e)}"
        )

@router.post("/bulk/reject")
async def bulk_reject_replies_v2(
    request: BulkActionRequest,
    user_id: Optional[str] = Query(None, description="User ID for multi-tenant support"),
    db: Session = Depends(get_db_dependency)
):
    """
    Bulk reject multiple replies efficiently
    """
    try:
        # Validate request
        if len(request.reply_ids) > 100:
            raise HTTPException(
                status_code=400,
                detail="Cannot reject more than 100 replies at once"
            )

        # Initialize reply service
        reply_service = ReplyService(db)

        # Perform bulk reject
        result = await reply_service.bulk_reject(request.reply_ids, request.reason, user_id)

        if not result["success"]:
            raise HTTPException(
                status_code=500,
                detail=result["error"]
            )

        logger.info(f"Bulk rejected {result['rejected_count']} replies by user {user_id}. Reason: {request.reason}")

        return {
            "success": True,
            "message": f"Bulk rejected {result['rejected_count']} replies",
            "data": result,
            "timestamp": datetime.utcnow().isoformat(),
            "api_version": "v2"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in bulk reject: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Bulk reject failed: {str(e)}"
        )

@router.get("/queue/stats")
async def get_queue_statistics_v2(
    db: Session = Depends(get_db_dependency),
    user_id: Optional[str] = Query(None, description="User ID for multi-tenant support")
):
    """
    Get reply queue statistics
    """
    try:
        # Initialize reply service
        reply_service = ReplyService(db)

        # Get queue statistics
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

@router.get("/{reply_id}")
async def get_reply_details_v2(
    reply_id: int,
    user_id: Optional[str] = Query(None, description="User ID for multi-tenant support"),
    db: Session = Depends(get_db_dependency)
):
    """
    Get detailed information about a specific reply
    """
    try:
        # Initialize reply service
        reply_service = ReplyService(db)

        # Get reply from pending replies first
        pending_result = await reply_service.get_pending_replies(1000, user_id)
        reply_data = next((r for r in pending_result.get("replies", []) if r["id"] == reply_id), None)

        if not reply_data:
            # Check history if not in pending
            history_result = await reply_service.get_reply_history(365, 1000, user_id)
            reply_data = next((r for r in history_result.get("history", []) if r["id"] == reply_id), None)

        if not reply_data:
            raise HTTPException(
                status_code=404,
                detail=f"Reply {reply_id} not found"
            )

        return {
            "success": True,
            "data": reply_data,
            "timestamp": datetime.utcnow().isoformat(),
            "api_version": "v2"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting reply details for {reply_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get reply details: {str(e)}"
        )