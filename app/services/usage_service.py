"""
Tenant usage tracking and quota enforcement (Phase 3).
"""

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import Document, Tenant, TenantUsage
from app.services.plan_limits import get_plan_limits


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _maybe_reset_period(usage: TenantUsage) -> None:
    """Reset monthly API counters when the billing period rolls over."""
    period_start = usage.period_start
    if period_start.tzinfo is None:
        period_start = period_start.replace(tzinfo=timezone.utc)
    if _utcnow() - period_start >= timedelta(days=30):
        usage.chat_count = 0
        usage.search_count = 0
        usage.api_call_count = 0
        usage.period_start = _utcnow()


def get_or_create_usage(db: Session, tenant_id: str) -> TenantUsage:
    tid = uuid.UUID(tenant_id)
    usage = db.query(TenantUsage).filter(TenantUsage.tenant_id == tid).first()
    if usage:
        _maybe_reset_period(usage)
        return usage

    usage = TenantUsage(tenant_id=tid)
    db.add(usage)
    db.commit()
    db.refresh(usage)
    return usage


def sync_usage_from_documents(db: Session, tenant_id: str) -> TenantUsage:
    """Reconcile counters from documents table (repair drift)."""
    tid = uuid.UUID(tenant_id)
    rows = db.query(Document).filter(Document.tenant_id == tid).all()
    usage = get_or_create_usage(db, tenant_id)
    usage.document_count = len(rows)
    usage.storage_bytes = sum(r.file_size or 0 for r in rows)
    db.commit()
    db.refresh(usage)
    return usage


def get_usage_summary(db: Session, tenant_id: str) -> dict:
    tenant = db.query(Tenant).filter(Tenant.id == uuid.UUID(tenant_id)).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    usage = sync_usage_from_documents(db, tenant_id)
    limits = get_plan_limits(tenant.plan)

    return {
        "tenant_id": tenant_id,
        "plan": tenant.plan,
        "document_count": usage.document_count,
        "storage_bytes": usage.storage_bytes,
        "upload_count": usage.upload_count,
        "chat_count": usage.chat_count,
        "search_count": usage.search_count,
        "api_call_count": usage.api_call_count,
        "period_start": usage.period_start,
        "limits": {
            "max_documents": limits.max_documents,
            "max_storage_bytes": limits.max_storage_bytes,
            "max_chat_calls_per_month": limits.max_chat_calls_per_month,
            "max_search_calls_per_month": limits.max_search_calls_per_month,
        },
    }


def _quota_disabled() -> bool:
    return not get_settings().quotas_enabled


def _raise_quota(detail: str) -> None:
    raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=detail)


def check_upload_quota(db: Session, tenant_id: str, file_size: int) -> None:
    if _quota_disabled():
        return

    tenant = db.query(Tenant).filter(Tenant.id == uuid.UUID(tenant_id)).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    limits = get_plan_limits(tenant.plan)
    usage = sync_usage_from_documents(db, tenant_id)

    if usage.document_count >= limits.max_documents:
        _raise_quota(
            f"Document limit reached ({limits.max_documents} on {tenant.plan} plan). "
            "Upgrade your plan or delete documents."
        )
    if usage.storage_bytes + file_size > limits.max_storage_bytes:
        _raise_quota(
            f"Storage limit exceeded on {tenant.plan} plan. "
            f"Limit: {limits.max_storage_bytes} bytes."
        )


def check_chat_quota(db: Session, tenant_id: str) -> None:
    if _quota_disabled():
        return

    tenant = db.query(Tenant).filter(Tenant.id == uuid.UUID(tenant_id)).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    limits = get_plan_limits(tenant.plan)
    usage = get_or_create_usage(db, tenant_id)

    if usage.chat_count >= limits.max_chat_calls_per_month:
        _raise_quota(
            f"Monthly chat limit reached ({limits.max_chat_calls_per_month} on {tenant.plan} plan)."
        )


def check_search_quota(db: Session, tenant_id: str) -> None:
    if _quota_disabled():
        return

    tenant = db.query(Tenant).filter(Tenant.id == uuid.UUID(tenant_id)).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    limits = get_plan_limits(tenant.plan)
    usage = get_or_create_usage(db, tenant_id)

    if usage.search_count >= limits.max_search_calls_per_month:
        _raise_quota(
            f"Monthly search limit reached ({limits.max_search_calls_per_month} on {tenant.plan} plan)."
        )


def record_upload(db: Session, tenant_id: str, file_size: int) -> None:
    sync_usage_from_documents(db, tenant_id)
    usage = get_or_create_usage(db, tenant_id)
    usage.upload_count += 1
    usage.api_call_count += 1
    db.commit()


def record_delete(db: Session, tenant_id: str, file_size: int | None) -> None:
    sync_usage_from_documents(db, tenant_id)
    usage = get_or_create_usage(db, tenant_id)
    usage.api_call_count += 1
    db.commit()


def record_chat(db: Session, tenant_id: str) -> None:
    usage = get_or_create_usage(db, tenant_id)
    usage.chat_count += 1
    usage.api_call_count += 1
    db.commit()


def record_search(db: Session, tenant_id: str) -> None:
    usage = get_or_create_usage(db, tenant_id)
    usage.search_count += 1
    usage.api_call_count += 1
    db.commit()


def record_api_call(db: Session, tenant_id: str) -> None:
    usage = get_or_create_usage(db, tenant_id)
    usage.api_call_count += 1
    db.commit()
