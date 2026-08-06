"""
Health check API endpoint
"""

from fastapi import APIRouter
from app.models.response_models import HealthResponse
from app.vectorstore.qdrant_client import QdrantManager
from app.vectorstore.collections import CollectionManager
from app.cache.redis_client import get_redis
from app.utils.logger import setup_logger
import os

logger = setup_logger(__name__)

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint (public)."""
    logger.info("Health check requested")

    services = {}

    try:
        qdrant_manager = QdrantManager()
        collection_manager = CollectionManager(qdrant_manager)
        stats = collection_manager.get_collection_stats()
        services["qdrant"] = "connected"
        services["collections"] = stats
    except Exception as e:
        logger.error(f"Qdrant health check failed: {str(e)}")
        services["qdrant"] = "disconnected"

    redis_client = get_redis()
    services["redis"] = "connected" if redis_client.ping() else "disconnected"

    try:
        from app.storage.minio_client import get_storage
        storage = get_storage()
        services["storage"] = "minio" if storage.using_minio else "local_disk"
        services["minio"] = "connected" if storage.ping() else "disconnected"
    except Exception as e:
        services["minio"] = f"error: {e}"

    from app.config import get_settings
    settings = get_settings()
    services["celery"] = "enabled" if settings.celery_enabled else "disabled"
    services["quotas"] = "enabled" if settings.quotas_enabled else "disabled"
    services["prometheus"] = "enabled" if settings.prometheus_enabled else "disabled"
    services["agent"] = "enabled" if settings.agent_enabled else "disabled"

    api_key_set = bool(os.getenv("OPENROUTER_API_KEY"))
    services["llm_api"] = "configured" if api_key_set else "not_configured"

    return HealthResponse(
        status="healthy",
        services=services,
        version="1.4.0",
    )


@router.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check with more information."""
    logger.info("Detailed health check requested")

    redis_client = get_redis()

    return {
        "status": "healthy",
        "version": "1.2.0",
        "components": {
            "api": "running",
            "qdrant": "connected",
            "redis": "connected" if redis_client.ping() else "disconnected",
            "postgres": "configured",
            "embeddings": "ready",
            "llm": "ready",
        },
        "configuration": {
            "embedding_model": os.getenv("TEXT_EMBEDDING_MODEL", "BAAI/bge-m3"),
            "llm_model": os.getenv("LLM_MODEL", "anthropic/claude-3-haiku:beta"),
            "chunk_size": os.getenv("CHUNK_SIZE", "512"),
            "require_auth": os.getenv("REQUIRE_AUTH", "true"),
        },
    }
