"""
Celery tasks for document ingestion and indexing.
"""

from app.celery_app import celery_app
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


@celery_app.task(bind=True, name="process_document_task", max_retries=2, default_retry_delay=30)
def process_document_task(
    self,
    document_id: str,
    storage_key: str,
    filename: str,
    tenant_id: str,
    *,
    is_local_path: bool = False,
) -> dict:
    """
    Download file from MinIO (or use local path), run ingestion + indexing.
    """
    from app.workflows.document_pipeline import process_document
    from app.storage.minio_client import get_storage

    storage = get_storage()
    temp_path = None
    file_path = storage_key

    try:
        if not is_local_path:
            file_path = storage.download_to_temp(storage_key)
            temp_path = file_path

        logger.info(f"Celery task processing document {document_id} (tenant={tenant_id})")
        result = process_document(
            document_id,
            file_path,
            filename=filename,
            tenant_id=tenant_id,
        )
        return result
    except Exception as exc:
        logger.error(f"Celery task failed for {document_id}: {exc}", exc_info=True)
        raise self.retry(exc=exc)
    finally:
        if temp_path:
            storage.cleanup_temp(temp_path)
