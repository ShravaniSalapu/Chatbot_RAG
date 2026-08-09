"""
Enterprise Multimodal RAG System
Main entry point for FastAPI application
"""

from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.api import upload, chat, search, health, documents, auth, tenants, api_keys, cache, usage, audit, agent
from app.monitoring.prometheus import setup_prometheus
from app.utils.logger import setup_logger
from app.api import chatbot, embed
from app.api.widget import router as widget_router
from app.api import chatbot_documents
from app.api import widget_chat

logger = setup_logger(__name__)

app = FastAPI(
    title="KNOWA AI",
    description="Production-ready Multimodal RAG system with multi-tenant SaaS foundation",
    version="1.4.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Public routes
app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(auth.router, prefix="/api/v1", tags=["auth"])

# Protected routes (JWT required unless REQUIRE_AUTH=false)
app.include_router(tenants.router, prefix="/api/v1", tags=["tenants"])
app.include_router(api_keys.router, prefix="/api/v1", tags=["api-keys"])
app.include_router(cache.router, prefix="/api/v1", tags=["cache"])
app.include_router(upload.router, prefix="/api/v1", tags=["upload"])
app.include_router(chat.router, prefix="/api/v1", tags=["chat"])
app.include_router(search.router, prefix="/api/v1", tags=["search"])
app.include_router(documents.router, prefix="/api/v1", tags=["documents"])
app.include_router(usage.router, prefix="/api/v1", tags=["usage"])
app.include_router(audit.router, prefix="/api/v1", tags=["audit"])
app.include_router(agent.router, prefix="/api/v1", tags=["agent"])
app.include_router(chatbot.router, prefix="/api/v1")
app.include_router(embed.router, prefix="/api/v1")
app.include_router(
    widget_router,
    prefix="/api/v1",
)
app.include_router(chatbot_documents.router, prefix="/api/v1")
app.include_router(widget_chat.router, prefix="/api/v1")

STATIC_DIR = Path(__file__).parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
async def serve_ui():
    """Serve the web UI."""
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    # Try serving new_test_widget.html as fallback
    new_test_path = Path(__file__).parent / "new_test_widget.html"
    if new_test_path.exists():
        return FileResponse(str(new_test_path))
    return {"message": "KNOWA AI API", "docs": "/docs"}


setup_prometheus(app)


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    import os
    import torch

    if os.getenv("EMBEDDING_DEVICE", "cpu") == "cpu":
        torch.set_num_threads(int(os.getenv("TORCH_NUM_THREADS", os.cpu_count() or 4)))

    logger.info("Starting KNOWA AI System")

    from app.db.database import init_db
    init_db()
    logger.info("PostgreSQL initialized")

    from app.cache.redis_client import get_redis
    redis_client = get_redis()
    if redis_client.ping():
        logger.info("Redis connected")
    else:
        logger.warning("Redis not available — caching disabled")

    from app.vectorstore.qdrant_client import QdrantManager
    from app.vectorstore.collections import initialize_collections

    qdrant_manager = QdrantManager()
    await initialize_collections(qdrant_manager)
    logger.info("Collections initialized successfully")

    from app.retrieval.bm25_store import hydrate_bm25_from_redis
    from app.workflows.document_pipeline import sync_documents_from_qdrant

    loaded = hydrate_bm25_from_redis()
    if loaded:
        logger.info(f"BM25 hydrated from Redis ({loaded} document(s))")
    else:
        sync_documents_from_qdrant(rebuild_bm25=True)
        logger.info("BM25 rebuilt from Qdrant (Redis cache empty)")

    from app.storage.minio_client import get_storage
    storage = get_storage()
    if storage.using_minio:
        logger.info("MinIO object storage connected")
    else:
        logger.info("Using local disk storage (MinIO disabled or unavailable)")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down KNOWA AI System")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
