"""
Redis client for caching, sessions, and future task queues.
"""

import json
from typing import Any, Optional

import redis

from app.config import get_settings
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class RedisClient:
    """Thin wrapper around redis-py with JSON helpers."""

    def __init__(self, url: Optional[str] = None):
        settings = get_settings()
        self._enabled = settings.redis_enabled
        self._client: Optional[redis.Redis] = None
        if self._enabled:
            try:
                self._client = redis.from_url(url or settings.redis_url, decode_responses=True)
                self._client.ping()
                logger.info("Connected to Redis")
            except Exception as exc:
                logger.warning(f"Redis unavailable: {exc}")
                self._client = None

    @property
    def available(self) -> bool:
        return self._client is not None

    def ping(self) -> bool:
        if not self._client:
            return False
        try:
            return self._client.ping()
        except Exception:
            return False

    def get(self, key: str) -> Optional[str]:
        if not self._client:
            return None
        return self._client.get(key)

    def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        if not self._client:
            return False
        return bool(self._client.set(key, value, ex=ex))

    def delete(self, key: str) -> bool:
        if not self._client:
            return False
        return bool(self._client.delete(key))

    def get_json(self, key: str) -> Any:
        raw = self.get(key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    def set_json(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        return self.set(key, json.dumps(value), ex=ex)

    def cache_get_or_set(self, key: str, factory, ex: int = 300) -> Any:
        """Return cached value or compute, store, and return."""
        cached = self.get_json(key)
        if cached is not None:
            return cached
        value = factory()
        self.set_json(key, value, ex=ex)
        return value


_redis_instance: Optional[RedisClient] = None


def get_redis() -> RedisClient:
    global _redis_instance
    if _redis_instance is None:
        _redis_instance = RedisClient()
    return _redis_instance
