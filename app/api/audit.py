"""
Audit log query API (Phase 3).
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, require_admin
from app.db.database import get_db
from app.models.enterprise_models import AuditLogResponse
from app.services.audit_service import list_audit_logs

router = APIRouter()


@router.get("/audit-logs", response_model=list[AuditLogResponse])
async def get_audit_logs(
    action: Optional[str] = Query(default=None, description="Filter by action name"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """List audit logs for the current tenant (admin only)."""
    logs = list_audit_logs(
        db,
        current_user.tenant_id,
        action=action,
        limit=limit,
        offset=offset,
    )
    return [
        AuditLogResponse(
            id=str(entry.id),
            tenant_id=str(entry.tenant_id),
            user_id=str(entry.user_id) if entry.user_id else None,
            action=entry.action,
            resource_type=entry.resource_type,
            resource_id=entry.resource_id,
            metadata=entry.metadata_json,
            ip_address=entry.ip_address,
            created_at=entry.created_at,
        )
        for entry in logs
    ]
