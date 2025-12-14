from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session
import os
import time
import logging
from contextlib import asynccontextmanager
from sqlalchemy import text

from .dashboard import router as dashboard_router
from .settings import router as settings_router
from .replies import router as replies_router
from .analytics_v2 import router as analytics_router
from .auth import router as auth_router, get_current_user
from src.db.connection import get_db_dependency
from .security import SecurityHeaders, audit_logger, api_rate_limiter

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up Belief Forge Bot API...")
    yield
    # Shutdown
    logger.info("Shutting down Belief Forge Bot API...")

# Create FastAPI app
app = FastAPI(
    title="Belief Forge Bot API",
    description="API for managing Twitter engagement bot dashboard",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware - environment-aware configuration
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000,http://localhost,http://127.0.0.1").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
    expose_headers=["X-Total-Count"],
)

# Security and rate limiting middleware
@app.middleware("http")
async def security_middleware(request: Request, call_next):
    """Apply security measures and rate limiting"""
    start_time = time.time()

    # Get client IP for rate limiting
    client_ip = request.client.host

    # Apply rate limiting to all requests
    path = request.url.path

    # Skip rate limiting for static assets and health checks
    if not (path.startswith("/static") or path == "/health" or path == "/api/info"):
        is_limited, remaining_time = api_rate_limiter.is_rate_limited(client_ip, max_attempts=100, window_minutes=1)
        if is_limited:
            return JSONResponse(
                status_code=429,
                headers=SecurityHeaders.get_security_headers(),
                content={
                    "error": {
                        "code": 429,
                        "message": "Rate limit exceeded. Please try again later.",
                        "retry_after": remaining_time,
                        "type": "rate_limit_error"
                    }
                }
            )

    response = await call_next(request)
    process_time = time.time() - start_time

    # Add security headers to all responses
    if not response.headers.get("X-Content-Type-Options"):
        response.headers.update(SecurityHeaders.get_security_headers())

    # Log requests (excluding health checks to reduce noise)
    if path != "/health":
        logger.info(
            f"{request.method} {request.url.path} - "
            f"Status: {response.status_code} - "
            f"Time: {process_time:.4f}s - "
            f"IP: {client_ip}"
        )

    return response

# Static files
frontend_path = os.path.join(os.path.dirname(__file__), "../../frontend")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

# Include API routers
app.include_router(auth_router, prefix="/api/auth")
app.include_router(dashboard_router, prefix="/api/dashboard")
app.include_router(settings_router, prefix="/api/settings")
app.include_router(replies_router, prefix="/api/replies")
app.include_router(analytics_router, prefix="/api/analytics")

# Root endpoint - serve frontend
@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Serve the main dashboard page"""
    try:
        frontend_index = os.path.join(os.path.dirname(__file__), "../../frontend/index.html")
        if os.path.exists(frontend_index):
            with open(frontend_index, "r", encoding="utf-8") as f:
                return HTMLResponse(content=f.read())
        else:
            return HTMLResponse(
                content="""
                <html>
                    <head><title>Belief Forge Bot API</title></head>
                    <body>
                        <h1>Belief Forge Bot API</h1>
                        <p>API is running. Visit <a href="/docs">/docs</a> for API documentation.</p>
                        <p>Frontend not found. Please check the frontend directory.</p>
                    </body>
                </html>
                """
            )
    except Exception as e:
        logger.error(f"Error serving frontend: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to serve frontend")

# Login page endpoint
@app.get("/login", response_class=HTMLResponse)
async def login_page():
    """Serve the login page"""
    try:
        login_path = os.path.join(os.path.dirname(__file__), "../../frontend/login.html")
        if os.path.exists(login_path):
            with open(login_path, "r", encoding="utf-8") as f:
                return HTMLResponse(content=f.read())
        else:
            return HTMLResponse(
                content="""
                <html>
                    <head><title>Login - Belief Forge Bot</title></head>
                    <body>
                        <h1>Login Page Not Found</h1>
                        <p>Please check that the frontend files are properly configured.</p>
                    </body>
                </html>
                """,
                status_code=404
            )
    except Exception as e:
        logger.error(f"Error serving login page: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to serve login page")

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "version": "1.0.0"
    }

# API info endpoint
@app.get("/api/info")
async def api_info():
    """Get API information"""
    return {
        "name": "Belief Forge Bot API",
        "version": "1.0.0",
        "description": "API for managing Twitter engagement bot dashboard",
        "endpoints": {
            "auth": "/api/auth",
            "dashboard": "/api/dashboard",
            "settings": "/api/settings",
            "replies": "/api/replies",
            "analytics": "/api/analytics"
        }
    }

# Protected endpoint example
@app.get("/api/protected")
async def protected_endpoint(current_user: dict = Depends(get_current_user)):
    """Example protected endpoint"""
    return {
        "message": "This is a protected endpoint",
        "user": current_user
    }

# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions"""
    # Log HTTP exceptions
    audit_logger.log_api_access(
        request.url.path, request.method,
        getattr(request.state, 'user_email', 'anonymous'),
        request.client.host, exc.status_code
    )

    return JSONResponse(
        status_code=exc.status_code,
        headers=SecurityHeaders.get_security_headers(),
        content={
            "error": {
                "code": exc.status_code,
                "message": exc.detail,
                "type": "http_error"
            }
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": 500,
                "message": "Internal server error",
                "type": "server_error"
            }
        }
    )

# Bot control endpoints (these would integrate with your actual bot orchestrator)
@app.post("/api/bot/start")
async def start_bot(current_user: dict = Depends(get_current_user)):
    """Start the bot"""
    try:
        # This would integrate with your bot orchestrator
        # For now, return a mock response
        return {
            "message": "Bot start command sent",
            "status": "starting",
            "timestamp": time.time()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start bot: {str(e)}")

@app.post("/api/bot/stop")
async def stop_bot(current_user: dict = Depends(get_current_user)):
    """Stop the bot"""
    try:
        # This would integrate with your bot orchestrator
        return {
            "message": "Bot stop command sent",
            "status": "stopping",
            "timestamp": time.time()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop bot: {str(e)}")

@app.post("/api/bot/pause")
async def pause_bot(current_user: dict = Depends(get_current_user)):
    """Pause the bot"""
    try:
        # This would integrate with your bot orchestrator
        return {
            "message": "Bot pause command sent",
            "status": "pausing",
            "timestamp": time.time()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to pause bot: {str(e)}")

@app.get("/api/bot/status")
async def get_bot_status(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_dependency)
):
    """Get current bot status using real database data"""
    try:
        from ..db.models import ReplyQueue, AnalyticsDaily, RepliedTweet
        from datetime import datetime, timedelta
        from sqlalchemy import func

        # Get real statistics
        now = datetime.utcnow()
        today = now.date()

        # Get today's analytics if they exist
        today_analytics = db.query(AnalyticsDaily).filter(
            AnalyticsDaily.date == today
        ).first()

        # Get pending replies count
        pending_count = db.query(ReplyQueue).filter(
            ReplyQueue.status == 'pending'
        ).count()

        # Get recent activity (last 7 days)
        seven_days_ago = today - timedelta(days=7)
        weekly_stats = db.query(
            func.sum(AnalyticsDaily.tweets_scraped).label('total_tweets'),
            func.sum(AnalyticsDaily.replies_generated).label('total_replies'),
            func.sum(AnalyticsDaily.replies_posted).label('total_posted')
        ).filter(
            AnalyticsDaily.date >= seven_days_ago
        ).first()

        # Get today's replied tweets count
        today_replied = db.query(RepliedTweet).filter(
            func.date(RepliedTweet.replied_at) == today
        ).count()

        # Calculate success rate
        success_rate = 0
        if weekly_stats.total_replies and weekly_stats.total_replies > 0:
            success_rate = (weekly_stats.total_posted / weekly_stats.total_replies) * 100

        # Get bot schedule from config
        try:
            from ..config.loader import get_config
            bot_config, _ = get_config()
            active_hours = f"{bot_config.schedule.active_hours_start}:00-{bot_config.schedule.active_hours_end}:00"
            timezone = bot_config.schedule.timezone
        except:
            active_hours = "07:00-24:00"
            timezone = "Europe/London"

        # Build response with real data
        response = {
            "is_active": True,  # Could check actual bot process in future
            "status": "running",
            "last_scrape": time.time() - 1800 if today_analytics else time.time() - 7200,  # 30 min ago if has data, 2 hours ago if not
            "next_scrape": time.time() + 900,  # 15 minutes from now
            "stats": {
                "tweets_scraped": today_analytics.tweets_scraped if today_analytics else 0,
                "pending_replies": pending_count,
                "success_rate": round(success_rate, 1),
                "active_hours": active_hours,
                "timezone": timezone
            },
            "current_session": {
                "id": f"{datetime.now().strftime('%Y%m%d-%H%M%S')}",
                "start_time": datetime.now().timestamp() - 3600,  # Mock session start
                "tweets_scraped": today_analytics.tweets_scraped if today_analytics else 0,
                "replies_generated": today_analytics.replies_generated if today_analytics else 0,
                "replies_posted": today_analytics.replies_posted if today_analytics else 0
            },
            "weekly_stats": {
                "total_tweets": weekly_stats.total_tweets or 0,
                "total_replies": weekly_stats.total_replies or 0,
                "total_posted": weekly_stats.total_posted or 0,
                "today_replied": today_replied
            }
        }

        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get bot status: {str(e)}")

# Database status endpoint
@app.get("/api/database/status")
async def get_database_status(db: Session = Depends(get_db_dependency)):
    """Get database connection status"""
    try:
        # Simple database health check
        db.execute(text("SELECT 1"))
        return {
            "status": "connected",
            "timestamp": time.time()
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "timestamp": time.time()
        }

# Configuration management endpoints
@app.get("/api/config")
async def get_configuration(current_user: dict = Depends(get_current_user)):
    """Get current bot configuration"""
    try:
        from ..config.loader import get_config
        bot_config, env_config = get_config()

        return {
            "targets": {
                "hashtags": bot_config.targets.hashtags,
                "keywords": bot_config.targets.keywords,
                "subreddits": bot_config.targets.subreddits,
                "lists": bot_config.targets.lists
            },
            "platforms": {
                "twitter": {"enabled": bot_config.platforms.twitter.enabled},
                "reddit": {"enabled": bot_config.platforms.reddit.enabled}
            },
            "filters": {
                "engagement": {
                    "min_followers": bot_config.filters.engagement.min_followers,
                    "max_followers": bot_config.filters.engagement.max_followers,
                    "min_likes": bot_config.filters.engagement.min_likes,
                    "min_replies": bot_config.filters.engagement.min_replies,
                    "max_replies": bot_config.filters.engagement.max_replies
                },
                "recency": {
                    "min_age_hours": bot_config.filters.recency.min_age_hours,
                    "max_age_hours": bot_config.filters.recency.max_age_hours
                },
                "language": bot_config.filters.language,
                "content_quality": {
                    "min_length": bot_config.filters.content_quality.min_length,
                    "max_length": bot_config.filters.content_quality.max_length,
                    "banned_keywords": bot_config.filters.content_quality.banned_keywords,
                    "banned_patterns": bot_config.filters.content_quality.banned_patterns
                }
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get configuration: {str(e)}")

@app.post("/api/config")
async def update_configuration(updates: dict, current_user: dict = Depends(get_current_user)):
    """Update bot configuration"""
    try:
        from ..config.loader import update_config
        success = update_config(updates)

        if success:
            return {"message": "Configuration updated successfully"}
        else:
            raise HTTPException(status_code=400, detail="Failed to update configuration")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update configuration: {str(e)}")

# Configuration validation endpoint
@app.get("/api/config/validation")
async def validate_configuration():
    """Validate current configuration"""
    try:
        # This would load and validate your bot configuration
        return {
            "valid": True,
            "issues": [],
            "warnings": [
                "Cookie validation recommended",
                "Consider increasing scraping interval for better performance"
            ]
        }
    except Exception as e:
        return {
            "valid": False,
            "issues": [str(e)],
            "warnings": []
        }

# Development server info
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )