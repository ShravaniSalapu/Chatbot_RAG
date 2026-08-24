"""
Document management API endpoints
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from typing import List, Dict, Any
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, get_current_user
from app.db.database import get_db
from app.services.document_service import (
    delete_document_record,
    get_document_for_tenant,
    list_documents_for_tenant,
)
from app.services.usage_service import record_delete
from app.services.audit_service import log_audit, ACTION_DELETE
from app.utils.request_utils import client_ip
from app.storage.minio_client import get_storage
from app.workflows.document_pipeline import remove_processing_status
from app.workflows.indexing_pipeline import IndexingPipeline
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

router = APIRouter()


@router.get("/documents", response_model=List[Dict[str, Any]])
async def list_documents(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all documents for the current tenant. Admins see all, users see their own."""
    if current_user.role == "admin":
        # Admins see all documents in the tenant
        docs = list_documents_for_tenant(db, current_user.tenant_id)
    else:
        # Regular users only see documents they uploaded
        docs = list_documents_for_tenant(db, current_user.tenant_id)
        docs = [doc for doc in docs if str(doc.uploaded_by) == current_user.user_id]
    
    return [
        {
            "document_id": doc.id,
            "tenant_id": str(doc.tenant_id),
            "filename": doc.filename,
            "status": doc.status,
            "progress": doc.progress,
            "chunks_created": doc.chunks_created,
            "total_chunks": doc.chunks_created,
            "tables_extracted": doc.tables_extracted,
            "images_extracted": doc.images_extracted,
            "error_message": doc.error_message,
            "created_at": doc.created_at.isoformat() if doc.created_at else None,
        }
        for doc in docs
    ]


@router.delete("/documents/{document_id}")
async def delete_document(
    request: Request,
    document_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a document from vector and BM25 indexes (tenant-scoped)."""
    logger.info(f"Deleting document: {document_id} (tenant={current_user.tenant_id})")
    doc = get_document_for_tenant(db, current_user.tenant_id, document_id)

    pipeline = IndexingPipeline()
    success = pipeline.delete_document(document_id, tenant_id=current_user.tenant_id)
    if not success:
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {document_id}")

    if doc.file_path:
        get_storage().delete_object(doc.file_path)

    remove_processing_status(document_id)
    delete_document_record(db, current_user.tenant_id, document_id)
    record_delete(db, current_user.tenant_id, doc.file_size)
    log_audit(
        db,
        tenant_id=current_user.tenant_id,
        user_id=current_user.user_id,
        action=ACTION_DELETE,
        resource_type="document",
        resource_id=document_id,
        metadata={"filename": doc.filename},
        ip_address=client_ip(request),
    )
    return {"success": True, "document_id": document_id, "message": "Document deleted from index"}
