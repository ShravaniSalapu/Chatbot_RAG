"""
Document ownership and database operations.
"""

import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.db.models import Document


def get_document_for_tenant(db: Session, tenant_id: str, document_id: str) -> Document:
    doc = (
        db.query(Document)
        .filter(Document.id == document_id, Document.tenant_id == uuid.UUID(tenant_id))
        .first()
    )
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return doc


def list_documents_for_tenant(db: Session, tenant_id: str) -> list[Document]:
    return (
        db.query(Document)
        .filter(Document.tenant_id == uuid.UUID(tenant_id))
        .order_by(Document.created_at.desc())
        .all()
    )


def list_completed_document_ids_for_tenant(db: Session, tenant_id: str) -> list[str]:
    """Return document IDs that belong to this tenant and finished indexing."""
    docs = (
        db.query(Document.id)
        .filter(
            Document.tenant_id == uuid.UUID(tenant_id),
            Document.status == "completed",
        )
        .all()
    )
    return [str(doc.id) for doc in docs]


def create_document_record(
    db: Session,
    *,
    document_id: str,
    tenant_id: str,
    user_id: str,
    filename: str,
    file_path: str,
    file_size: int | None = None,
) -> Document:
    doc = Document(
        id=document_id,
        tenant_id=uuid.UUID(tenant_id),
        uploaded_by=uuid.UUID(user_id),
        filename=filename,
        file_path=file_path,
        file_size=file_size,
        status="processing",
        progress=0.1,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def update_document_status(
    db: Session,
    document_id: str,
    *,
    status: str | None = None,
    progress: float | None = None,
    chunks_created: int | None = None,
    tables_extracted: int | None = None,
    images_extracted: int | None = None,
    error_message: str | None = None,
) -> None:
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        return
    if status is not None:
        doc.status = status
    if progress is not None:
        doc.progress = progress
    if chunks_created is not None:
        doc.chunks_created = chunks_created
    if tables_extracted is not None:
        doc.tables_extracted = tables_extracted
    if images_extracted is not None:
        doc.images_extracted = images_extracted
    if error_message is not None:
        doc.error_message = error_message
    db.commit()


def delete_document_record(db: Session, tenant_id: str, document_id: str) -> None:
    doc = get_document_for_tenant(db, tenant_id, document_id)
    db.delete(doc)
    db.commit()
