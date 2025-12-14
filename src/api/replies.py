from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from ..db.connection import get_db_dependency
from ..db.models import ReplyQueue, ReplyPerformance
from .auth import get_current_user

router = APIRouter(tags=["replies"])

class ReplyAction(BaseModel):
    action: str  # approve, reject, edit, skip
    reply_id: int
    edited_text: Optional[str] = None

class BulkAction(BaseModel):
    action: str
    reply_ids: List[int]

@router.get("/pending")
async def get_pending_replies(
    limit: int = 50,
    offset: int = 0,
    priority_filter: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_dependency)
):
    """Get pending replies with optional filtering"""
    try:
        query = db.query(ReplyQueue).filter(ReplyQueue.status == "pending")

        # Apply priority filter if specified (using default priority for now)
        if priority_filter and priority_filter != "all":
            # Since commercial_category doesn't exist in the model yet,
            # we'll return all pending replies for now
            pass

        # Order by reply_score (highest first) and then by creation date
        query = query.order_by(ReplyQueue.reply_score.desc(), ReplyQueue.created_at.desc())

        # Apply pagination
        total = query.count()
        replies = query.offset(offset).limit(limit).all()

        reply_data = []
        for reply in replies:
            # Extract author info from tweet_metrics if available
            tweet_metrics = reply.tweet_metrics or {}

            reply_data.append({
                "id": reply.id,
                "tweet_id": reply.tweet_id,
                "tweet_text": reply.tweet_text,
                "tweet_author": reply.tweet_author,
                "author": reply.tweet_author,  # For frontend compatibility
                "author_followers": tweet_metrics.get("followers", 0),
                "tweet_author_followers": tweet_metrics.get("followers", 0),  # Frontend compatibility
                "generated_reply": reply.reply_text,
                "score": reply.reply_score,
                "commercial_category": reply.commercial_priority,
                "priority_keywords": reply.commercial_signals,
                "voice_score": reply.voice_validation_score,
                "created_at": reply.created_at.isoformat(),
                "status": reply.status
            })

        return {
            "replies": reply_data,
            "total": total,
            "limit": limit,
            "offset": offset
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get pending replies: {str(e)}")

@router.post("/{reply_id}/approve")
async def approve_reply(
    reply_id: int,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_dependency)
):
    """Approve and post a reply"""
    try:
        reply = db.query(ReplyQueue).filter(ReplyQueue.id == reply_id).first()
        if not reply:
            raise HTTPException(status_code=404, detail="Reply not found")

        reply.status = "approved"
        reply.approved_at = datetime.utcnow()
        # Note: In a real implementation, this would trigger posting to Twitter
        # background_tasks.add_task(post_reply_to_twitter, reply.id)

        db.commit()

        return {
            "message": "Reply approved successfully",
            "reply_id": reply.id,
            "status": reply.status
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to approve reply: {str(e)}")

@router.post("/{reply_id}/reject")
async def reject_reply(
    reply_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_dependency)
):
    """Reject a reply"""
    try:
        reply = db.query(ReplyQueue).filter(ReplyQueue.id == reply_id).first()
        if not reply:
            raise HTTPException(status_code=404, detail="Reply not found")

        reply.status = "rejected"
        reply.rejected_at = datetime.utcnow()

        db.commit()

        return {
            "message": "Reply rejected successfully",
            "reply_id": reply.id,
            "status": reply.status
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to reject reply: {str(e)}")

@router.post("/{reply_id}/edit")
async def edit_reply(
    reply_id: int,
    edit_data: dict,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_dependency)
):
    """Edit a reply text"""
    try:
        reply = db.query(ReplyQueue).filter(ReplyQueue.id == reply_id).first()
        if not reply:
            raise HTTPException(status_code=404, detail="Reply not found")

        if not edit_data.get("reply_text"):
            raise HTTPException(status_code=400, detail="Reply text is required")

        reply.generated_reply = edit_data["reply_text"]
        # Status remains pending after edit

        db.commit()

        return {
            "message": "Reply edited successfully",
            "reply_id": reply.id,
            "status": reply.status
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to edit reply: {str(e)}")

@router.post("/action")
async def handle_reply_action(
    action_data: ReplyAction,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_dependency)
):
    """Handle individual reply actions (approve, reject, edit, skip)"""
    try:
        reply = db.query(ReplyQueue).filter(ReplyQueue.id == action_data.reply_id).first()
        if not reply:
            raise HTTPException(status_code=404, detail="Reply not found")

        if reply.status != "pending":
            raise HTTPException(
                status_code=400,
                detail=f"Reply is already {reply.status}, cannot {action_data.action}"
            )

        action = action_data.action.lower()

        if action == "approve":
            reply.status = "approved"
            reply.approved_at = datetime.now()
            # Schedule for posting
            background_tasks.add_task(schedule_reply_posting, reply.id)
            message = "Reply approved and scheduled for posting"

        elif action == "reject":
            reply.status = "rejected"
            reply.rejected_at = datetime.now()
            message = "Reply rejected"

        elif action == "skip":
            reply.status = "skipped"
            reply.skipped_at = datetime.now()
            message = "Reply skipped"

        elif action == "edit":
            if not action_data.edited_text:
                raise HTTPException(status_code=400, detail="Edited text is required for edit action")

            # Save original text
            reply.original_reply = reply.generated_reply
            reply.generated_reply = action_data.edited_text
            reply.edited_at = datetime.now()

            # Re-calculate voice score for edited reply
            new_voice_score = calculate_voice_score(action_data.edited_text)
            reply.voice_score = new_voice_score

            message = "Reply edited successfully"

        else:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid action: {action}. Must be: approve, reject, edit, skip"
            )

        db.commit()
        return {"message": message, "reply_id": reply.id, "new_status": reply.status}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to handle reply action: {str(e)}")

@router.post("/bulk-action")
async def handle_bulk_action(
    bulk_data: BulkAction,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_dependency)
):
    """Handle bulk actions on multiple replies"""
    try:
        if not bulk_data.reply_ids:
            raise HTTPException(status_code=400, detail="No reply IDs provided")

        action = bulk_data.action.lower()
        if action not in ["approve", "reject", "skip"]:
            raise HTTPException(
                status_code=400,
                detail="Invalid bulk action. Must be: approve, reject, skip"
            )

        processed_count = 0
        errors = []

        for reply_id in bulk_data.reply_ids:
            try:
                reply = db.query(ReplyQueue).filter(ReplyQueue.id == reply_id).first()
                if not reply:
                    errors.append(f"Reply {reply_id} not found")
                    continue

                if reply.status != "pending":
                    errors.append(f"Reply {reply_id} is already {reply.status}")
                    continue

                if action == "approve":
                    reply.status = "approved"
                    reply.approved_at = datetime.now()
                    background_tasks.add_task(schedule_reply_posting, reply.id)

                elif action == "reject":
                    reply.status = "rejected"
                    reply.rejected_at = datetime.now()

                elif action == "skip":
                    reply.status = "skipped"
                    reply.skipped_at = datetime.now()

                processed_count += 1

            except Exception as e:
                errors.append(f"Error processing reply {reply_id}: {str(e)}")

        db.commit()

        return {
            "message": f"Bulk {action} completed",
            "processed_count": processed_count,
            "total_requested": len(bulk_data.reply_ids),
            "errors": errors
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to handle bulk action: {str(e)}")

@router.get("/history")
async def get_reply_history(
    limit: int = 50,
    offset: int = 0,
    status_filter: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_dependency)
):
    """Get reply history with optional status filtering"""
    try:
        query = db.query(ReplyQueue)

        # Apply status filter if specified
        if status_filter and status_filter != "all":
            query = query.filter(ReplyQueue.status == status_filter)

        # Order by creation date (most recent first)
        query = query.order_by(ReplyQueue.created_at.desc())

        # Apply pagination
        total = query.count()
        replies = query.offset(offset).limit(limit).all()

        reply_data = []
        for reply in replies:
            reply_data.append({
                "id": reply.id,
                "tweet_text": reply.tweet_text,
                "tweet_author": reply.tweet_author,
                "tweet_author_followers": reply.tweet_author_followers,
                "generated_reply": reply.generated_reply,
                "final_reply": reply.final_reply,
                "score": reply.score,
                "commercial_category": reply.commercial_category,
                "status": reply.status,
                "created_at": reply.created_at.isoformat(),
                "approved_at": reply.approved_at.isoformat() if reply.approved_at else None,
                "posted_at": reply.posted_at.isoformat() if reply.posted_at else None,
                "engagement_likes": reply.engagement_likes,
                "engagement_retweets": reply.engagement_retweets,
                "engagement_replies": reply.engagement_replies,
                "engagement_rate": reply.engagement_rate
            })

        return {
            "replies": reply_data,
            "total": total,
            "limit": limit,
            "offset": offset
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get reply history: {str(e)}")

@router.get("/{reply_id}")
async def get_reply_details(reply_id: int, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db_dependency)):
    """Get detailed information about a specific reply"""
    try:
        reply = db.query(ReplyQueue).filter(ReplyQueue.id == reply_id).first()
        if not reply:
            raise HTTPException(status_code=404, detail="Reply not found")

        return {
            "id": reply.id,
            "tweet_id": reply.tweet_id,
            "tweet_text": reply.tweet_text,
            "tweet_author": reply.tweet_author,
            "tweet_author_followers": reply.tweet_author_followers,
            "tweet_author_verified": reply.tweet_author_verified,
            "tweet_author_bio": reply.tweet_author_bio,
            "tweet_author_following": reply.tweet_author_following,
            "tweet_url": reply.tweet_url,
            "original_reply": reply.original_reply,
            "generated_reply": reply.generated_reply,
            "final_reply": reply.final_reply,
            "score": reply.score,
            "score_breakdown": reply.score_breakdown,
            "commercial_category": reply.commercial_category,
            "priority_keywords": reply.priority_keywords,
            "voice_score": reply.voice_score,
            "voice_violations": reply.voice_violations,
            "status": reply.status,
            "created_at": reply.created_at.isoformat(),
            "approved_at": reply.approved_at.isoformat() if reply.approved_at else None,
            "posted_at": reply.posted_at.isoformat() if reply.posted_at else None,
            "engagement_likes": reply.engagement_likes,
            "engagement_retweets": reply.engagement_retweets,
            "engagement_replies": reply.engagement_replies,
            "engagement_rate": reply.engagement_rate,
            "marked_as_good_example": reply.marked_as_good_example
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get reply details: {str(e)}")

@router.post("/{reply_id}/mark-example")
async def mark_as_good_example(reply_id: int, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db_dependency)):
    """Mark a reply as a good example for LLM learning"""
    try:
        reply = db.query(ReplyQueue).filter(ReplyQueue.id == reply_id).first()
        if not reply:
            raise HTTPException(status_code=404, detail="Reply not found")

        if reply.status != "posted":
            raise HTTPException(
                status_code=400,
                detail="Only posted replies can be marked as good examples"
            )

        # Toggle the good example flag
        reply.marked_as_good_example = not reply.marked_as_good_example
        db.commit()

        status = "marked" if reply.marked_as_good_example else "unmarked"
        return {
            "message": f"Reply {status} as good example",
            "reply_id": reply_id,
            "is_good_example": reply.marked_as_good_example
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to mark reply as example: {str(e)}")

# Helper functions
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

def calculate_voice_score(text: str) -> float:
    """Calculate voice compliance score for British English"""
    # This would implement the actual voice validation logic
    # For now, return a mock score
    return 85.0  # 85% compliance

async def schedule_reply_posting(reply_id: int):
    """Background task to schedule reply for posting"""
    try:
        # This would integrate with your bot's posting system
        print(f"Reply {reply_id} scheduled for posting")
    except Exception as e:
        print(f"Failed to schedule reply {reply_id} for posting: {str(e)}")

# Import required modules
from datetime import timedelta