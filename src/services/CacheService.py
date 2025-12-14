"""
Redis-based caching service for analytics and frequently accessed data
Eliminates redundant database queries and improves dashboard performance
"""
import json
import logging
from typing import Any, Optional, Union, Dict, List
from datetime import datetime, timedelta
import redis
import os
from functools import wraps

logger = logging.getLogger(__name__)

class CacheService:
    """Redis caching service with TTL support and intelligent cache invalidation"""

    def __init__(self):
        self.redis_client = None
        self.default_ttl = 300  # 5 minutes
        self.long_ttl = 3600   # 1 hour
        self.short_ttl = 60    # 1 minute
        self._initialize_redis()

    def _initialize_redis(self):
        """Initialize Redis connection with fallback to mock cache"""
        try:
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
            redis_password = os.getenv('REDIS_PASSWORD')

            self.redis_client = redis.from_url(
                redis_url,
                password=redis_password,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True
            )

            # Test connection
            self.redis_client.ping()
            logger.info("Redis cache service initialized successfully")

        except Exception as e:
            logger.warning(f"Redis connection failed, using memory cache: {e}")
            self.redis_client = None
            self._memory_cache = {}

    def _get_cache_key(self, prefix: str, *args) -> str:
        """Generate standardized cache key"""
        key_parts = [prefix] + [str(arg) for arg in args if arg is not None]
        return ":".join(key_parts)

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            if self.redis_client:
                cached_value = self.redis_client.get(key)
                if cached_value:
                    return json.loads(cached_value)
            else:
                # Fallback to memory cache
                if key in self._memory_cache:
                    data, timestamp = self._memory_cache[key]
                    if datetime.now().timestamp() - timestamp < self.default_ttl:
                        return data
                    else:
                        del self._memory_cache[key]
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache with TTL"""
        try:
            ttl = ttl or self.default_ttl
            serialized_value = json.dumps(value, default=str)

            if self.redis_client:
                return self.redis_client.setex(key, ttl, serialized_value)
            else:
                # Fallback to memory cache
                self._memory_cache[key] = (value, datetime.now().timestamp())
                return True

        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False

    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        try:
            if self.redis_client:
                return bool(self.redis_client.delete(key))
            else:
                # Fallback to memory cache
                return self._memory_cache.pop(key, None) is not None
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            return False

    def delete_pattern(self, pattern: str) -> int:
        """Delete keys matching pattern"""
        try:
            if self.redis_client:
                keys = self.redis_client.keys(pattern)
                if keys:
                    return self.redis_client.delete(*keys)
                return 0
            else:
                # Fallback to memory cache pattern matching
                keys_to_delete = [k for k in self._memory_cache.keys() if pattern.replace('*', '') in k]
                for key in keys_to_delete:
                    del self._memory_cache[key]
                return len(keys_to_delete)
        except Exception as e:
            logger.error(f"Cache delete pattern error for pattern {pattern}: {e}")
            return 0

    def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        try:
            if self.redis_client:
                return bool(self.redis_client.exists(key))
            else:
                # Fallback to memory cache
                if key in self._memory_cache:
                    data, timestamp = self._memory_cache[key]
                    if datetime.now().timestamp() - timestamp < self.default_ttl:
                        return True
                    else:
                        del self._memory_cache[key]
                return False
        except Exception as e:
            logger.error(f"Cache exists error for key {key}: {e}")
            return False

    def clear_all(self) -> bool:
        """Clear all cache"""
        try:
            if self.redis_client:
                return self.redis_client.flushdb()
            else:
                self._memory_cache.clear()
                return True
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            return False

    def cache_function(self, ttl: Optional[int] = None, key_prefix: str = ""):
        """Decorator to cache function results"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Generate cache key
                cache_key = self._get_cache_key(
                    f"func:{key_prefix}:{func.__name__}",
                    *args,
                    *[f"{k}:{v}" for k, v in sorted(kwargs.items())]
                )

                # Try to get from cache
                cached_result = self.get(cache_key)
                if cached_result is not None:
                    logger.debug(f"Cache hit for {func.__name__}")
                    return cached_result

                # Execute function and cache result
                try:
                    result = func(*args, **kwargs)
                    self.set(cache_key, result, ttl)
                    logger.debug(f"Cached result for {func.__name__}")
                    return result
                except Exception as e:
                    logger.error(f"Error executing {func.__name__}: {e}")
                    raise

            return wrapper
        return decorator

    # Specific cache methods for different data types
    def cache_dashboard_stats(self, user_id: str = None) -> tuple:
        """Get cache key and TTL for dashboard stats"""
        key = self._get_cache_key("dashboard_stats", user_id)
        return key, self.short_ttl

    def cache_analytics_summary(self, days: int = 30, user_id: str = None) -> tuple:
        """Get cache key and TTL for analytics summary"""
        key = self._get_cache_key("analytics_summary", days, user_id)
        return key, self.short_ttl

    def cache_reply_queue(self, user_id: str = None) -> tuple:
        """Get cache key and TTL for reply queue"""
        key = self._get_cache_key("reply_queue", user_id)
        return key, self.short_ttl

    def cache_performance_metrics(self, days: int, user_id: str = None) -> tuple:
        """Get cache key and TTL for performance metrics"""
        key = self._get_cache_key("performance_metrics", days, user_id)
        return key, self.long_ttl

    def cache_activity_feed(self, limit: int = 10, user_id: str = None) -> tuple:
        """Get cache key and TTL for activity feed"""
        key = self._get_cache_key("activity_feed", limit, user_id)
        return key, self.short_ttl

    def cache_commercial_categories(self, days: int = 30, user_id: str = None) -> tuple:
        """Get cache key and TTL for commercial categories"""
        key = self._get_cache_key("commercial_categories", days, user_id)
        return key, self.long_ttl

    # Cache invalidation methods
    def invalidate_reply_cache(self):
        """Invalidate all reply-related cache entries"""
        patterns = [
            "*reply_queue*",
            "*dashboard_stats*",
            "*activity_feed*"
        ]
        deleted = 0
        for pattern in patterns:
            deleted += self.delete_pattern(pattern)
        logger.info(f"Invalidated {deleted} reply cache entries")
        return deleted

    def invalidate_analytics_cache(self):
        """Invalidate all analytics cache entries"""
        patterns = [
            "*analytics_*",
            "*performance_*",
            "*commercial_*"
        ]
        deleted = 0
        for pattern in patterns:
            deleted += self.delete_pattern(pattern)
        logger.info(f"Invalidated {deleted} analytics cache entries")
        return deleted

    def invalidate_user_cache(self, user_id: str):
        """Invalidate all cache entries for a specific user"""
        pattern = f"*{user_id}*"
        deleted = self.delete_pattern(pattern)
        logger.info(f"Invalidated {deleted} cache entries for user {user_id}")
        return deleted

    # Health check
    def health_check(self) -> Dict[str, Any]:
        """Check cache service health"""
        health = {
            "status": "healthy",
            "redis_connected": False,
            "memory_cache_size": 0,
            "test_key_result": None
        }

        try:
            if self.redis_client:
                # Test Redis connection
                test_key = "health_check_test"
                self.redis_client.set(test_key, "test", ex=10)
                result = self.redis_client.get(test_key)
                self.redis_client.delete(test_key)

                health["redis_connected"] = True
                health["test_key_result"] = result
            else:
                health["status"] = "degraded"
                health["message"] = "Using memory cache fallback"

            # Check memory cache size
            if hasattr(self, '_memory_cache'):
                health["memory_cache_size"] = len(self._memory_cache)

        except Exception as e:
            health["status"] = "unhealthy"
            health["error"] = str(e)

        return health

    # Cache statistics
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        stats = {
            "redis_connected": False,
            "memory_cache_size": 0,
            "estimated_keys": 0
        }

        try:
            if self.redis_client:
                info = self.redis_client.info()
                stats["redis_connected"] = True
                stats["estimated_keys"] = info.get("db0", {}).get("keys", 0)
            else:
                if hasattr(self, '_memory_cache'):
                    stats["memory_cache_size"] = len(self._memory_cache)

        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")

        return stats

# Global cache service instance
cache_service = CacheService()