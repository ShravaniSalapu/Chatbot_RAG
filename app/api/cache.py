"""
Redis cache verification endpoint (Phase 1.4).
"""

import time

from fastapi import APIRouter, Depends

from app.auth.dependencies import CurrentUser, get_current_user
from app.cache.redis_client import get_redis

router = APIRouter()


@router.get("/cache/test")
async def test_cache(current_user: CurrentUser = Depends(get_current_user)):
    """
    Verify Redis read/write for the current tenant.
    Writes a value, reads it back, and reports latency.
    """
    redis_client = get_redis()
    if not redis_client.available:
        return {
            "success": False,
            "redis": "unavailable",
            "message": "Redis is not connected. Start with: docker compose up -d redis",
        }

    key = f"cache_test:{current_user.tenant_id}"
    payload = {"tenant_id": current_user.tenant_id, "ts": time.time()}

    start = time.perf_counter()
    redis_client.set_json(key, payload, ex=60)
    cached = redis_client.get_json(key)
    elapsed_ms = round((time.perf_counter() - start) * 1000, 2)

    return {
        "success": cached == payload,
        "redis": "connected",
        "key": key,
        "written": payload,
        "read_back": cached,
        "round_trip_ms": elapsed_ms,
    }
