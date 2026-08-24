"""
Enterprise Multimodal RAG System
Main entry point for FastAPI application
"""

from pathlib import Path

from dotenv import load_dotenv

# ============================================================
# ENVIRONMENT
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

load_dotenv(BASE_DIR / ".env")


# ============================================================
# FASTAPI
# ============================================================

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse


# ============================================================
# API ROUTERS
# ============================================================

from app.api import (
    upload,
    chat,
    search,
    health,
    documents,
    auth,
    tenants,
    api_keys,
    cache,
    usage,
    audit,
    agent,
    admin,
    users,
)

from app.api import chatbot
from app.api import embed
from app.api.widget import router as widget_router
from app.api import chatbot_documents
from app.api import widget_chat


# ============================================================
# OTHER SERVICES
# ============================================================

from app.monitoring.prometheus import setup_prometheus
from app.utils.logger import setup_logger


logger = setup_logger(__name__)


# ============================================================
# FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title="KNOWA AI",
    description=(
        "Production-ready Multimodal RAG system "
        "with multi-tenant SaaS foundation"
    ),
    version="1.4.0",
)


# ============================================================
# CORS
# ============================================================

# IMPORTANT:
#
# React/Vite:
#   http://localhost:5173
#
# React/Vite using 127.0.0.1:
#   http://127.0.0.1:5173
#
# Local test.html opened directly:
#   Origin: null
#
# "null" is required only because you are currently testing
# the widget using a local file:// HTML page.
#
# For production, remove "null" and use a real hosted domain.

app.add_middleware(
    CORSMiddleware,

    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "null",
    ],

    allow_credentials=True,

    allow_methods=[
        "GET",
        "POST",
        "PUT",
        "DELETE",
        "PATCH",
        "OPTIONS",
    ],

    allow_headers=["*"],

    expose_headers=["*"],
)


# ============================================================
# PUBLIC ROUTES
# ============================================================

app.include_router(
    health.router,
    prefix="/api/v1",
    tags=["health"],
)

app.include_router(
    auth.router,
    prefix="/api/v1",
    tags=["auth"],
)


# ============================================================
# PROTECTED ROUTES
# ============================================================

app.include_router(
    tenants.router,
    prefix="/api/v1",
    tags=["tenants"],
)

app.include_router(
    api_keys.router,
    prefix="/api/v1",
    tags=["api-keys"],
)

app.include_router(
    cache.router,
    prefix="/api/v1",
    tags=["cache"],
)

app.include_router(
    upload.router,
    prefix="/api/v1",
    tags=["upload"],
)

app.include_router(
    chat.router,
    prefix="/api/v1",
    tags=["chat"],
)

app.include_router(
    search.router,
    prefix="/api/v1",
    tags=["search"],
)

app.include_router(
    documents.router,
    prefix="/api/v1",
    tags=["documents"],
)

app.include_router(
    usage.router,
    prefix="/api/v1",
    tags=["usage"],
)

app.include_router(
    audit.router,
    prefix="/api/v1",
    tags=["audit"],
)

app.include_router(
    agent.router,
    prefix="/api/v1",
    tags=["agent"],
)

app.include_router(
    admin.router,
    prefix="/api/v1",
    tags=["admin"],
)

app.include_router(
    users.router,
    prefix="/api/v1",
    tags=["users"],
)


# ============================================================
# CHATBOT ROUTES
# ============================================================

app.include_router(
    chatbot.router,
    prefix="/api/v1",
)

app.include_router(
    embed.router,
    prefix="/api/v1",
)

app.include_router(
    widget_router,
    prefix="/api/v1",
)

app.include_router(
    chatbot_documents.router,
    prefix="/api/v1",
)

app.include_router(
    widget_chat.router,
    prefix="/api/v1",
)


# ============================================================
# STATIC FILES
# ============================================================

STATIC_DIR = BASE_DIR / "app" / "static"

if STATIC_DIR.exists():
    app.mount(
        "/static",
        StaticFiles(directory=str(STATIC_DIR)),
        name="static",
    )


# ============================================================
# ROOT ENDPOINT
# ============================================================

@app.get("/")
async def serve_ui():
    """
    Serve the web UI if available.
    """

    index_path = STATIC_DIR / "index.html"

    if index_path.exists():
        return FileResponse(str(index_path))

    new_test_path = BASE_DIR / "new_test_widget.html"

    if new_test_path.exists():
        return FileResponse(str(new_test_path))

    return {
        "message": "KNOWA AI API",
        "docs": "/docs",
    }


# ============================================================
# PROMETHEUS
# ============================================================

setup_prometheus(app)


# ============================================================
# STARTUP
# ============================================================

@app.on_event("startup")
async def startup_event():
    """
    Initialize all required services when FastAPI starts.
    """

    import os
    import torch

    logger.info("Starting KNOWA AI System")

    # --------------------------------------------------------
    # Torch
    # --------------------------------------------------------

    if os.getenv("EMBEDDING_DEVICE", "cpu") == "cpu":
        torch.set_num_threads(
            int(
                os.getenv(
                    "TORCH_NUM_THREADS",
                    os.cpu_count() or 4,
                )
            )
        )

    # --------------------------------------------------------
    # PostgreSQL
    # --------------------------------------------------------

    try:
        from app.db.database import init_db

        init_db()

        logger.info("PostgreSQL initialized")

    except Exception as exc:
        logger.exception(
            "PostgreSQL initialization failed: %s",
            exc,
        )
        raise

    # --------------------------------------------------------
    # Redis
    # --------------------------------------------------------

    try:
        from app.cache.redis_client import get_redis

        redis_client = get_redis()

        if redis_client.ping():
            logger.info("Redis connected")
        else:
            logger.warning(
                "Redis not available — caching disabled"
            )

    except Exception as exc:
        logger.warning(
            "Redis connection failed: %s",
            exc,
        )

    # --------------------------------------------------------
    # QDRANT
    # --------------------------------------------------------

    try:
        from app.vectorstore.qdrant_client import QdrantManager
        from app.vectorstore.collections import (
            initialize_collections,
        )

        qdrant_manager = QdrantManager()

        await initialize_collections(
            qdrant_manager
        )

        logger.info(
            "Qdrant collections initialized"
        )

    except Exception as exc:
        logger.exception(
            "Qdrant initialization failed: %s",
            exc,
        )
        raise

    # --------------------------------------------------------
    # BM25
    # --------------------------------------------------------

    try:
        from app.retrieval.bm25_store import (
            hydrate_bm25_from_redis,
        )

        from app.workflows.document_pipeline import (
            sync_documents_from_qdrant,
        )

        loaded = hydrate_bm25_from_redis()

        if loaded:
            logger.info(
                "BM25 hydrated from Redis "
                f"({loaded} document(s))"
            )
        else:
            sync_documents_from_qdrant(
                rebuild_bm25=True
            )

            logger.info(
                "BM25 rebuilt from Qdrant "
                "(Redis cache empty)"
            )

    except Exception as exc:
        logger.warning(
            "BM25 initialization failed: %s",
            exc,
        )

    # --------------------------------------------------------
    # MINIO
    # --------------------------------------------------------

    try:
        from app.storage.minio_client import get_storage

        storage = get_storage()

        if storage.using_minio:
            logger.info(
                "MinIO object storage connected"
            )
        else:
            logger.info(
                "Using local disk storage "
                "(MinIO disabled or unavailable)"
            )

    except Exception as exc:
        logger.warning(
            "MinIO initialization failed: %s",
            exc,
        )

    # --------------------------------------------------------
    # COMPLETE
    # --------------------------------------------------------

    logger.info(
        "KNOWA AI System startup complete"
    )


# ============================================================
# SHUTDOWN
# ============================================================

@app.on_event("shutdown")
async def shutdown_event():
    logger.info(
        "Shutting down KNOWA AI System"
    )


# ============================================================
# RUN DIRECTLY
# ============================================================

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
    )