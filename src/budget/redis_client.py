"""Redis connection and operations."""
import redis
from typing import Optional
from src.config.settings import settings


class RedisClient:
    """Manages Redis connection for budget tracking."""
    
    def __init__(self, redis_url: Optional[str] = None):
        """Initialize Redis client."""
        self.redis_url = redis_url or settings.redis_url
        self._client: Optional[redis.Redis] = None
    
    @property
    def client(self) -> redis.Redis:
        """Get or create Redis client."""
        if self._client is None:
            self._client = redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
        return self._client
    
    def ping(self) -> bool:
        """Check if Redis is available."""
        try:
            return self.client.ping()
        except Exception:
            return False
    
    def close(self):
        """Close Redis connection."""
        if self._client:
            self._client.close()
            self._client = None


# Global Redis client instance
redis_client = RedisClient()

