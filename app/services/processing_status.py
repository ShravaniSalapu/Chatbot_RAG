"""
Redis-backed document processing status (shared across API and Celery workers).
"""

from typing import Any, Dict, Optional

from app.cache.redis_client import get_redis
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

_STATUS_PREFIX = "doc:status:"
_STATUS_TTL = 60 * 60 * 24  # 24 hours


def _key(document_id: str) -> str:
    return f"{_STATUS_PREFIX}{document_id}"


def set_processing_status(document_id: str, tenant_id: str, **fields: Any) -> None:
    redis = get_redis()
    existing = get_processing_status(document_id) or {
        "document_id": document_id,
        "tenant_id": tenant_id,
    }
    existing.update(fields)
    existing["document_id"] = document_id
    existing["tenant_id"] = tenant_id
    if redis.available:
        redis.set_json(_key(document_id), existing, ex=_STATUS_TTL)


def get_processing_status(document_id: str) -> Optional[Dict[str, Any]]:
    redis = get_redis()
    if redis.available:
        data = redis.get_json(_key(document_id))
        if data:
            return data
    return None


def clear_processing_status(document_id: str) -> None:
    redis = get_redis()
    if redis.available:
        redis.delete(_key(document_id))
