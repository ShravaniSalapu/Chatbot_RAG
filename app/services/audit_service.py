"""
Audit logging for tenant/user actions (Phase 3).
"""

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import AuditLog
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

# Standard action names
ACTION_REGISTER = "register"
ACTION_LOGIN = "login"
ACTION_UPLOAD = "upload"
ACTION_DELETE = "delete"
ACTION_CHAT = "chat"
ACTION_SEARCH = "search"
ACTION_API_KEY_CREATE = "api_key_create"
ACTION_API_KEY_REVOKE = "api_key_revoke"
ACTION_TENANT_UPDATE = "tenant_update"
ACTION_PLAN_CHANGE = "plan_change"
ACTION_AGENT = "agent"


def log_audit(
    db: Session,
    *,
    tenant_id: str,
    user_id: str | None,
    action: str,
    resource_type: str | None = None,
    resource_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    ip_address: str | None = None,
) -> AuditLog:
    entry = AuditLog(
        tenant_id=uuid.UUID(tenant_id),
        user_id=uuid.UUID(user_id) if user_id else None,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        metadata_json=metadata,
        ip_address=ip_address,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    logger.info(
        "audit action={} tenant={} user={} resource={}/{}",
        action,
        tenant_id,
        user_id,
        resource_type,
        resource_id,
    )
    return entry


def list_audit_logs(
    db: Session,
    tenant_id: str,
    *,
    action: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[AuditLog]:
    q = db.query(AuditLog).filter(AuditLog.tenant_id == uuid.UUID(tenant_id))
    if action:
        q = q.filter(AuditLog.action == action)
    return (
        q.order_by(AuditLog.created_at.desc())
        .offset(offset)
        .limit(min(limit, 200))
        .all()
    )
