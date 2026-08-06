"""
Persist BM25 corpus metadata in Redis so indexes survive restarts without full Qdrant rebuild.
"""

from typing import Any, Dict, List, Optional, Set

from app.cache.redis_client import get_redis
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

_CORPUS_PREFIX = "bm25:corpus:"
_TENANT_PREFIX = "bm25:tenant:"
_INDEX_SET = "bm25:document_ids"


class BM25RedisStore:
    def save_index(
        self,
        document_id: str,
        chunks: List[Dict[str, Any]],
        tenant_id: Optional[str],
    ) -> bool:
        redis = get_redis()
        if not redis.available:
            return False
        try:
            redis.set_json(f"{_CORPUS_PREFIX}{document_id}", chunks)
            if tenant_id:
                redis.set(f"{_TENANT_PREFIX}{document_id}", tenant_id)
            client = redis._client
            if client:
                client.sadd(_INDEX_SET, document_id)
            return True
        except Exception as exc:
            logger.warning(f"BM25 Redis save failed for {document_id}: {exc}")
            return False

    def load_corpus(self, document_id: str) -> Optional[List[Dict[str, Any]]]:
        redis = get_redis()
        if not redis.available:
            return None
        return redis.get_json(f"{_CORPUS_PREFIX}{document_id}")

    def load_tenant_id(self, document_id: str) -> Optional[str]:
        redis = get_redis()
        if not redis.available:
            return None
        return redis.get(f"{_TENANT_PREFIX}{document_id}")

    def delete_index(self, document_id: str) -> bool:
        redis = get_redis()
        if not redis.available:
            return False
        try:
            redis.delete(f"{_CORPUS_PREFIX}{document_id}")
            redis.delete(f"{_TENANT_PREFIX}{document_id}")
            client = redis._client
            if client:
                client.srem(_INDEX_SET, document_id)
            return True
        except Exception as exc:
            logger.warning(f"BM25 Redis delete failed for {document_id}: {exc}")
            return False

    def list_document_ids(self) -> Set[str]:
        redis = get_redis()
        if not redis.available or not redis._client:
            return set()
        try:
            return set(redis._client.smembers(_INDEX_SET))
        except Exception:
            return set()


_bm25_redis: Optional[BM25RedisStore] = None


def get_bm25_redis() -> BM25RedisStore:
    global _bm25_redis
    if _bm25_redis is None:
        _bm25_redis = BM25RedisStore()
    return _bm25_redis
