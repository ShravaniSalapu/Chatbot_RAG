"""
Redis-backed conversation memory for agent sessions (Phase 4).
"""

import uuid
from typing import Any

from app.cache.redis_client import get_redis
from app.config import get_settings
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


def new_session_id() -> str:
    return str(uuid.uuid4())


def _memory_key(tenant_id: str, user_id: str, session_id: str) -> str:
    return f"agent_memory:{tenant_id}:{user_id}:{session_id}"


def load_memory(tenant_id: str, user_id: str, session_id: str) -> list[dict[str, str]]:
    redis = get_redis()
    messages = redis.get_json(_memory_key(tenant_id, user_id, session_id))
    if isinstance(messages, list):
        return [m for m in messages if isinstance(m, dict) and m.get("role") and m.get("content")]
    return []


def save_memory(
    tenant_id: str,
    user_id: str,
    session_id: str,
    messages: list[dict[str, str]],
) -> None:
    settings = get_settings()
    max_messages = settings.agent_memory_turns * 2
    trimmed = messages[-max_messages:] if max_messages > 0 else messages

    redis = get_redis()
    ttl = settings.agent_memory_ttl_seconds
    redis.set_json(_memory_key(tenant_id, user_id, session_id), trimmed, ex=ttl)


def append_turn(
    tenant_id: str,
    user_id: str,
    session_id: str,
    user_message: str,
    assistant_message: str,
) -> list[dict[str, str]]:
    history = load_memory(tenant_id, user_id, session_id)
    history.append({"role": "user", "content": user_message})
    history.append({"role": "assistant", "content": assistant_message})
    save_memory(tenant_id, user_id, session_id, history)
    return history


def clear_memory(tenant_id: str, user_id: str, session_id: str) -> None:
    get_redis().delete(_memory_key(tenant_id, user_id, session_id))
