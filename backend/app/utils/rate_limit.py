"""
Rate limiting for AI endpoints using Redis.
Max 30 AI calls per user per hour.
"""
import time
import redis
from typing import Tuple
from app.config import settings

# Initialize Redis connection
# We use a distinct pool or connection for rate limiting if needed, 
# but sharing the URL is fine.
redis_client = redis.from_url(settings.redis_url, decode_responses=True)

RATE_LIMIT_CALLS = 30
RATE_LIMIT_WINDOW_SECONDS = 3600  # 1 hour


def check_rate_limit(user_id: int) -> Tuple[bool, int]:
    """
    Check if user has exceeded AI call rate limit using Redis.
    Uses a simple fixed window counter with identifying key.
    
    Returns:
        (allowed: bool, remaining_calls: int)
    """
    key = f"rate_limit:ai:{user_id}"
    
    try:
        # Atomic increment
        current = redis_client.incr(key)
        
        # Set expiration on first increment
        if current == 1:
            redis_client.expire(key, RATE_LIMIT_WINDOW_SECONDS)
            
        if current > RATE_LIMIT_CALLS:
            return False, 0
            
        return True, RATE_LIMIT_CALLS - current
        
    except redis.RedisError:
        # Fail open if Redis is down (allow request)
        # In strict envs, might want to fail closed.
        return True, 1
