"""
Shared BM25 search instance so indexes built during upload are visible at query time.
"""

from typing import Optional

from app.retrieval.bm25_search import BM25Search
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

_bm25_instance: Optional[BM25Search] = None


def get_bm25_search() -> BM25Search:
    """Return the process-wide BM25 search instance."""
    global _bm25_instance
    if _bm25_instance is None:
        _bm25_instance = BM25Search()
    return _bm25_instance


def hydrate_bm25_from_redis() -> int:
    """Load BM25 corpora from Redis into memory. Returns number of documents loaded."""
    from app.retrieval.bm25_redis import get_bm25_redis

    store = get_bm25_redis()
    bm25 = get_bm25_search()
    loaded = 0
    for document_id in store.list_document_ids():
        chunks = store.load_corpus(document_id)
        if not chunks:
            continue
        tenant_id = store.load_tenant_id(document_id)
        bm25.build_index(document_id, chunks, tenant_id=tenant_id, persist_redis=False)
        loaded += 1
    if loaded:
        logger.info(f"Hydrated {loaded} BM25 index(es) from Redis")
    return loaded
