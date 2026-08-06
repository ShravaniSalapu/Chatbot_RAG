"""
End-to-end document processing: ingest then index.
Phase 2: no processing lock — parallel workers via Celery.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from app.workflows.ingestion_pipeline import IngestionPipeline
from app.workflows.indexing_pipeline import IndexingPipeline
from app.vectorstore.qdrant_client import QdrantManager
from app.vectorstore.collections import CollectionManager
from app.retrieval.bm25_store import get_bm25_search
from app.services.processing_status import (
    set_processing_status,
    get_processing_status,
    clear_processing_status,
)
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


def remove_processing_status(document_id: str) -> None:
    """Remove live processing status from Redis."""
    clear_processing_status(document_id)


def get_all_processing_statuses(tenant_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Return tracked documents for a tenant from Qdrant sync metadata."""
    sync_documents_from_qdrant(tenant_id=tenant_id)
    return []


def sync_documents_from_qdrant(
    rebuild_bm25: bool = False,
    tenant_id: Optional[str] = None,
) -> None:
    """
    Ensure Qdrant-indexed documents have BM25 indexes.
    Phase 2: prefer Redis hydration; rebuild from Qdrant only when missing.
    """
    from app.retrieval.bm25_store import hydrate_bm25_from_redis

    hydrated = hydrate_bm25_from_redis()
    if hydrated and not rebuild_bm25:
        logger.info(f"BM25 ready from Redis ({hydrated} document(s))")
        return

    try:
        qdrant = QdrantManager()
        collection = CollectionManager(qdrant).get_text_collection()
        if not qdrant.collection_exists(collection):
            return

        indexed_docs = qdrant.list_indexed_documents(collection, tenant_id=tenant_id)
        bm25 = get_bm25_search()

        for doc in indexed_docs:
            document_id = doc["document_id"]
            doc_tenant_id = doc.get("tenant_id")

            if not doc_tenant_id:
                logger.warning(f"Skipping legacy document without tenant_id: {document_id}")
                continue

            if document_id in bm25.corpus and not rebuild_bm25:
                continue

            if not rebuild_bm25:
                continue

            bm25_chunks: List[Dict[str, Any]] = []
            cm = CollectionManager(qdrant)
            for coll in (cm.get_text_collection(), cm.get_table_collection()):
                if not qdrant.collection_exists(coll):
                    continue
                for chunk in qdrant.get_document_chunks(coll, document_id, tenant_id=doc_tenant_id):
                    if chunk.get("chunk_type") not in ("image", "parent"):
                        bm25_chunks.append(chunk)
            if bm25_chunks:
                bm25.build_index(document_id, bm25_chunks, tenant_id=doc_tenant_id)

        if indexed_docs:
            logger.info(f"Synced BM25 for {len(indexed_docs)} document(s) from Qdrant")
    except Exception as exc:
        logger.warning(f"Could not sync documents from Qdrant: {exc}")


def _extract_filename(file_path: str) -> str:
    name = Path(file_path).name
    if "_" in name:
        return name.split("_", 1)[1]
    return name


def _to_plain(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "dict"):
        return value.dict()
    return value


def _prepare_for_indexing(
    ingestion_result: Dict[str, Any],
    tenant_id: str,
) -> Dict[str, Any]:
    document = ingestion_result["document"]
    tables = [_to_plain(table) for table in (document.tables or [])]
    images = [_to_plain(image) for image in (document.images or [])]

    metadata = document.metadata
    if hasattr(metadata, "model_dump"):
        document_metadata = metadata.model_dump()
    elif hasattr(metadata, "dict"):
        document_metadata = metadata.dict()
    else:
        document_metadata = dict(metadata) if metadata else {}

    document_metadata["tenant_id"] = tenant_id

    return {
        "document_id": document.document_id,
        "metadata": document_metadata,
        "tables": tables,
        "images": images,
        "raw_text": document.raw_text or "",
        "headings": ingestion_result.get("headings", []),
        "sections": ingestion_result.get("sections", []),
    }


def _update_db_status(document_id: str, **kwargs) -> None:
    try:
        from app.db.database import SessionLocal
        from app.services.document_service import update_document_status

        db = SessionLocal()
        try:
            update_document_status(db, document_id, **kwargs)
        finally:
            db.close()
    except Exception as exc:
        logger.warning(f"Could not update document status in database: {exc}")


def process_document(
    document_id: str,
    file_path: str,
    filename: Optional[str] = None,
    tenant_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Run ingestion and indexing for an uploaded file (no global lock)."""
    if not tenant_id:
        raise ValueError("tenant_id is required for document processing")

    display_name = filename or _extract_filename(file_path)

    set_processing_status(
        document_id,
        tenant_id,
        filename=display_name,
        status="processing",
        progress=0.1,
        chunks_created=0,
        total_chunks=0,
        tables_extracted=0,
        images_extracted=0,
        error_message=None,
    )
    _update_db_status(document_id, status="processing", progress=0.1)

    try:
        logger.info(f"Starting document pipeline for {document_id} (tenant={tenant_id})")

        ingestion_pipeline = IngestionPipeline()
        ingestion_result = ingestion_pipeline.ingest_document(file_path, document_id=document_id)

        document = ingestion_result["document"]
        set_processing_status(
            document_id,
            tenant_id,
            progress=0.5,
            filename=display_name,
            tables_extracted=len(document.tables or []),
            images_extracted=len(document.images or []),
        )
        _update_db_status(
            document_id,
            progress=0.5,
            tables_extracted=len(document.tables or []),
            images_extracted=len(document.images or []),
        )

        def on_indexing_progress(indexed: int, total: int) -> None:
            if total <= 0:
                return
            indexing_progress = 0.5 + (indexed / total) * 0.49
            set_processing_status(
                document_id,
                tenant_id,
                progress=round(indexing_progress, 3),
                chunks_created=indexed,
                total_chunks=total,
            )

        indexing_pipeline = IndexingPipeline()
        index_result = indexing_pipeline.index_document(
            _prepare_for_indexing(ingestion_result, tenant_id),
            progress_callback=on_indexing_progress,
        )

        chunks_created = index_result.get("chunks_created", 0)
        tables_extracted = index_result.get("tables_processed", 0)
        indexing_ok = bool(index_result.get("success")) and chunks_created > 0
        error_message = None
        if not indexing_ok:
            if chunks_created == 0:
                if tables_extracted > 0:
                    error_message = "Extracted content could not be indexed into searchable chunks"
                else:
                    error_message = "No content could be extracted from this file"
            else:
                error_message = "Indexing failed"

        result = {
            "document_id": document_id,
            "tenant_id": tenant_id,
            "filename": display_name,
            "status": "completed" if indexing_ok else "failed",
            "chunks_created": chunks_created,
            "tables_extracted": tables_extracted,
            "images_extracted": index_result.get("images_processed", 0),
            "error_message": error_message,
        }

        set_processing_status(
            document_id,
            tenant_id,
            status=result["status"],
            progress=1.0,
            chunks_created=result["chunks_created"],
            total_chunks=result["chunks_created"],
            tables_extracted=result["tables_extracted"],
            images_extracted=result["images_extracted"],
            error_message=result["error_message"],
        )
        _update_db_status(
            document_id,
            status=result["status"],
            progress=1.0,
            chunks_created=result["chunks_created"],
            tables_extracted=result["tables_extracted"],
            images_extracted=result["images_extracted"],
            error_message=result["error_message"],
        )

        logger.info(f"Document pipeline completed for {document_id}: {result}")
        return result

    except Exception as exc:
        logger.error(f"Document pipeline failed for {document_id}: {exc}", exc_info=True)
        set_processing_status(
            document_id,
            tenant_id,
            filename=display_name,
            status="failed",
            progress=1.0,
            chunks_created=0,
            total_chunks=0,
            tables_extracted=0,
            images_extracted=0,
            error_message=str(exc),
        )
        _update_db_status(document_id, status="failed", progress=1.0, error_message=str(exc))
        raise
