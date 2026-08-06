"""
Upload API endpoint for document ingestion (Phase 2: MinIO + Celery).
"""

import mimetypes
import uuid

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Depends, Request
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, get_current_user
from app.config import get_settings
from app.db.database import get_db
from app.models.response_models import UploadResponse
from app.services.document_service import create_document_record, get_document_for_tenant
from app.services.processing_status import get_processing_status
from app.services.usage_service import check_upload_quota, record_upload
from app.services.audit_service import log_audit, ACTION_UPLOAD
from app.utils.request_utils import client_ip
from app.storage.minio_client import get_storage
from app.workflows.document_pipeline import process_document
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

router = APIRouter()


def _enqueue_processing(
    document_id: str,
    storage_key: str,
    filename: str,
    tenant_id: str,
    *,
    is_local_path: bool = False,
) -> None:
    settings = get_settings()
    if settings.celery_enabled:
        from app.tasks.document_tasks import process_document_task

        process_document_task.delay(
            document_id,
            storage_key,
            filename,
            tenant_id,
            is_local_path=is_local_path,
        )
        logger.info(f"Enqueued Celery task for document {document_id}")
    else:
        process_document(document_id, storage_key, filename=filename, tenant_id=tenant_id)


def _run_document_pipeline_fallback(
    document_id: str, file_path: str, filename: str, tenant_id: str
) -> None:
    try:
        process_document(document_id, file_path, filename=filename, tenant_id=tenant_id)
    except Exception as exc:
        logger.error(f"Background processing failed for {document_id}: {exc}")


@router.post("/upload", response_model=UploadResponse)
async def upload_document(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload a document for async processing (MinIO + Celery queue)."""
    logger.info(f"Received file upload: {file.filename} (tenant={current_user.tenant_id})")

    try:
        document_id = str(uuid.uuid4())
        filename = file.filename or "document"
        content = await file.read()
        check_upload_quota(db, current_user.tenant_id, len(content))
        storage = get_storage()
        settings = get_settings()

        object_key = storage.build_object_key(
            current_user.tenant_id, document_id, filename
        )
        content_type = file.content_type or mimetypes.guess_type(filename)[0] or "application/octet-stream"
        storage_key = storage.upload_bytes(object_key, content, content_type=content_type)

        create_document_record(
            db,
            document_id=document_id,
            tenant_id=current_user.tenant_id,
            user_id=current_user.user_id,
            filename=filename,
            file_path=storage_key,
            file_size=len(content),
        )
        record_upload(db, current_user.tenant_id, len(content))
        log_audit(
            db,
            tenant_id=current_user.tenant_id,
            user_id=current_user.user_id,
            action=ACTION_UPLOAD,
            resource_type="document",
            resource_id=document_id,
            metadata={"filename": filename, "file_size": len(content)},
            ip_address=client_ip(request),
        )

        if settings.celery_enabled:
            _enqueue_processing(
                document_id,
                storage_key,
                filename,
                current_user.tenant_id,
                is_local_path=not storage.using_minio,
            )
        else:
            background_tasks.add_task(
                _run_document_pipeline_fallback,
                document_id,
                storage_key,
                filename,
                current_user.tenant_id,
            )

        return UploadResponse(
            success=True,
            document_id=document_id,
            filename=filename,
            message="File uploaded successfully. Processing has started.",
            processing_status="processing",
            chunks_created=None,
            tables_extracted=None,
            images_extracted=None,
        )

    except Exception as e:
        logger.error(f"Error uploading file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error uploading file: {str(e)}")


@router.get("/upload/status/{document_id}")
async def get_upload_status(
    document_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get the status of document processing (tenant-scoped)."""
    logger.info(f"Checking status for document: {document_id}")

    get_document_for_tenant(db, current_user.tenant_id, document_id)

    status = get_processing_status(document_id)
    if not status:
        doc = get_document_for_tenant(db, current_user.tenant_id, document_id)
        return {
            "document_id": doc.id,
            "tenant_id": str(doc.tenant_id),
            "filename": doc.filename,
            "status": doc.status,
            "progress": doc.progress,
            "chunks_created": doc.chunks_created,
            "total_chunks": doc.chunks_created,
            "error_message": doc.error_message,
        }

    if status.get("tenant_id") and status["tenant_id"] != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="Document not found")

    return status
