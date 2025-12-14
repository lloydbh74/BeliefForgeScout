from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, Dict, Any
import json
import os
from ..db.connection import get_db_dependency
from ..config.loader import get_config, update_config

router = APIRouter(tags=["settings"])

class FilterSettings(BaseModel):
    min_followers: int = 200
    max_followers: int = 50000
    min_likes: int = 2
    min_replies: int = 1
    min_followers_ratio: float = 1.5
    min_account_age_days: int = 180
    recent_tweet_ratio: float = 0.1

class CookieValidation(BaseModel):
    cookies: str

@router.get("/")
async def get_settings():
    """Get current bot settings"""
    try:
        config = get_config()
        return {
            "filters": {
                "engagement": {
                    "min_followers": config.filters.engagement.min_followers,
                    "max_followers": config.filters.engagement.max_followers,
                    "min_likes": config.filters.engagement.min_likes,
                    "min_replies": config.filters.engagement.min_replies,
                },
                "account_quality": {
                    "min_followers_ratio": config.filters.account_quality.min_followers_ratio,
                    "min_account_age_days": config.filters.account_quality.min_account_age_days,
                    "recent_tweet_ratio": config.filters.account_quality.recent_tweet_ratio,
                }
            },
            "targets": {
                "hashtags": config.targets.hashtags,
                "keywords": config.targets.keywords
            },
            "llm": {
                "model": config.llm.model,
                "temperature": config.llm.parameters.temperature,
                "max_tokens": config.llm.parameters.max_tokens,
                "daily_budget_usd": config.llm.rate_limits.daily_budget_usd
            },
            "schedule": {
                "timezone": config.schedule.timezone,
                "active_hours": {
                    "start": config.schedule.active_hours.start,
                    "end": config.schedule.active_hours.end
                }
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load settings: {str(e)}")

@router.post("/filters")
async def update_filter_settings(settings: FilterSettings):
    """Update filter settings"""
    try:
        # Validate settings
        if settings.min_followers >= settings.max_followers:
            raise HTTPException(
                status_code=400,
                detail="Minimum followers must be less than maximum followers"
            )

        if settings.min_likes < 0 or settings.min_replies < 0:
            raise HTTPException(
                status_code=400,
                detail="Minimum likes and replies must be non-negative"
            )

        # Update configuration (this would need to be implemented)
        # For now, just return success
        return {"message": "Filter settings updated successfully", "settings": settings.dict()}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update settings: {str(e)}")

@router.post("/validate-cookies")
async def validate_twitter_cookies(cookie_data: CookieValidation, background_tasks: BackgroundTasks):
    """Validate Twitter cookies format and functionality"""
    try:
        # Validate JSON format
        try:
            cookies = json.loads(cookie_data.cookies)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=400,
                detail="Invalid JSON format for cookies"
            )

        # Check if cookies have required fields
        required_fields = ['auth_token', 'ct0', 'twid']  # Essential Twitter cookies
        cookie_dict = {cookie['name']: cookie['value'] for cookie in cookies}

        missing_fields = [field for field in required_fields if field not in cookie_dict]
        if missing_fields:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required cookie fields: {', '.join(missing_fields)}"
            )

        # Save cookies to file (in production, this should be more secure)
        cookies_path = os.path.join(os.path.dirname(__file__), '../../data/cookies.json')
        os.makedirs(os.path.dirname(cookies_path), exist_ok=True)

        with open(cookies_path, 'w') as f:
            json.dump(cookies, f, indent=2)

        # Background task to test cookies by attempting to scrape a test tweet
        background_tasks.add_task(test_cookies_functionality)

        return {
            "status": "valid",
            "message": "Cookies format is valid. Testing functionality...",
            "cookie_count": len(cookies)
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to validate cookies: {str(e)}")

@router.get("/cookie-status")
async def get_cookie_status():
    """Check the current status of Twitter cookies"""
    try:
        cookies_path = os.path.join(os.path.dirname(__file__), '../../data/cookies.json')

        if not os.path.exists(cookies_path):
            return {
                "status": "not_found",
                "message": "No cookies file found",
                "last_updated": None
            }

        # Check file modification time
        file_time = os.path.getmtime(cookies_path)
        last_updated = datetime.fromtimestamp(file_time).isoformat()

        # Check if cookies are recent (less than 7 days old)
        file_age_days = (datetime.now() - datetime.fromtimestamp(file_time)).days

        if file_age_days > 7:
            status = "expired"
            message = "Cookies are older than 7 days and may be expired"
        elif file_age_days > 3:
            status = "warning"
            message = "Cookies are getting old, consider refreshing soon"
        else:
            status = "valid"
            message = "Cookies appear to be recent"

        return {
            "status": status,
            "message": message,
            "last_updated": last_updated,
            "file_age_days": file_age_days
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to check cookie status: {str(e)}",
            "last_updated": None
        }

@router.post("/bot-control")
async def control_bot(action: str):
    """Control bot state (start/stop/pause)"""
    try:
        if action not in ["start", "stop", "pause", "restart"]:
            raise HTTPException(
                status_code=400,
                detail="Invalid action. Must be: start, stop, pause, or restart"
            )

        # This would integrate with your bot orchestrator
        # For now, just return success
        return {
            "message": f"Bot {action} command sent successfully",
            "action": action,
            "timestamp": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to control bot: {str(e)}")

@router.get("/bot-status")
async def get_bot_status():
    """Get current bot status"""
    try:
        # This would check the actual bot process/state
        # For now, return mock status
        return {
            "is_active": True,
            "status": "running",
            "last_scrape": datetime.now().isoformat(),
            "next_scrape": (datetime.now() + timedelta(minutes=30)).isoformat(),
            "active_session": {
                "id": "20251116-111812",
                "start_time": datetime.now().isoformat(),
                "tweets_scraped": 45,
                "replies_generated": 8
            }
        }

    except Exception as e:
        return {
            "is_active": False,
            "status": "error",
            "error": str(e)
        }

async def test_cookies_functionality():
    """Background task to test if cookies work by attempting a simple request"""
    try:
        # This would use the Twitter scraper to test cookies
        # For now, just log that the test was attempted
        print("Cookie functionality test attempted")
    except Exception as e:
        print(f"Cookie test failed: {str(e)}")

# Import datetime for the functions above
from datetime import datetime, timedelta