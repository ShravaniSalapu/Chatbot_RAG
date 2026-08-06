"""
Tenant API key management endpoints (database-driven auth).
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, require_admin
from app.db.database import get_db
from app.models.auth_models import ApiKeyCreateRequest, ApiKeyCreateResponse, ApiKeyResponse
from app.services.api_key_service import create_api_key, list_api_keys, revoke_api_key
from app.services.audit_service import log_audit, ACTION_API_KEY_CREATE, ACTION_API_KEY_REVOKE
from app.utils.request_utils import client_ip

router = APIRouter()


@router.post("/api-keys", response_model=ApiKeyCreateResponse, status_code=201)
async def create_tenant_api_key(
    request: Request,
    body: ApiKeyCreateRequest,
    current_user: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Create a new API key for the current tenant (admin only). Raw key returned once."""
    record, raw_key = create_api_key(
        db,
        tenant_id=current_user.tenant_id,
        user_id=current_user.user_id,
        name=body.name,
    )
    log_audit(
        db,
        tenant_id=current_user.tenant_id,
        user_id=current_user.user_id,
        action=ACTION_API_KEY_CREATE,
        resource_type="api_key",
        resource_id=str(record.id),
        metadata={"name": body.name, "key_prefix": record.key_prefix},
        ip_address=client_ip(request),
    )
    return ApiKeyCreateResponse(
        id=str(record.id),
        name=record.name,
        key_prefix=record.key_prefix,
        api_key=raw_key,
    )


@router.get("/api-keys", response_model=list[ApiKeyResponse])
async def list_tenant_api_keys(
    current_user: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """List active API keys for the current tenant (prefix only, not full key)."""
    keys = list_api_keys(db, current_user.tenant_id)
    return [
        ApiKeyResponse(
            id=str(k.id),
            name=k.name,
            key_prefix=k.key_prefix,
            is_active=k.is_active,
            last_used_at=k.last_used_at,
            created_at=k.created_at,
        )
        for k in keys
    ]


@router.delete("/api-keys/{key_id}")
async def revoke_tenant_api_key(
    request: Request,
    key_id: str,
    current_user: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Revoke an API key (admin only)."""
    revoke_api_key(db, current_user.tenant_id, key_id)
    log_audit(
        db,
        tenant_id=current_user.tenant_id,
        user_id=current_user.user_id,
        action=ACTION_API_KEY_REVOKE,
        resource_type="api_key",
        resource_id=key_id,
        ip_address=client_ip(request),
    )
    return {"success": True, "message": "API key revoked"}
