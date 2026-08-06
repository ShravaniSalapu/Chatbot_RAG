"""
Tenant management API endpoints.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, get_current_user, require_admin
from app.db.database import get_db
from app.db.models import Tenant
from app.models.auth_models import TenantResponse, TenantUpdateRequest
from app.services.plan_limits import VALID_PLANS
from app.services.audit_service import log_audit, ACTION_PLAN_CHANGE, ACTION_TENANT_UPDATE
from app.utils.request_utils import client_ip

router = APIRouter()


@router.get("/tenants/me", response_model=TenantResponse)
async def get_my_tenant(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get the current user's tenant (cached in Redis when available)."""
    from app.cache.redis_client import get_redis

    cache_key = f"tenant:{current_user.tenant_id}"
    redis_client = get_redis()
    cached = redis_client.get_json(cache_key)
    if cached:
        return TenantResponse(**cached)

    tenant = db.query(Tenant).filter(Tenant.id == uuid.UUID(current_user.tenant_id)).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    response = TenantResponse(
        id=str(tenant.id),
        name=tenant.name,
        slug=tenant.slug,
        plan=tenant.plan,
        is_active=tenant.is_active,
        created_at=tenant.created_at,
    )
    redis_client.set_json(cache_key, response.model_dump(mode="json"), ex=300)
    return response


@router.patch("/tenants/me", response_model=TenantResponse)
async def update_my_tenant(
    request: Request,
    body: TenantUpdateRequest,
    current_user: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Update tenant settings (admin only)."""
    tenant = db.query(Tenant).filter(Tenant.id == uuid.UUID(current_user.tenant_id)).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    old_plan = tenant.plan
    if body.name is not None:
        tenant.name = body.name
    if body.plan is not None:
        if body.plan not in VALID_PLANS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid plan. Choose one of: {', '.join(sorted(VALID_PLANS))}",
            )
        tenant.plan = body.plan

    db.commit()
    db.refresh(tenant)

    from app.cache.redis_client import get_redis
    get_redis().delete(f"tenant:{current_user.tenant_id}")

    if body.name is not None:
        log_audit(
            db,
            tenant_id=current_user.tenant_id,
            user_id=current_user.user_id,
            action=ACTION_TENANT_UPDATE,
            resource_type="tenant",
            resource_id=current_user.tenant_id,
            metadata={"name": tenant.name},
            ip_address=client_ip(request),
        )
    if body.plan is not None and body.plan != old_plan:
        log_audit(
            db,
            tenant_id=current_user.tenant_id,
            user_id=current_user.user_id,
            action=ACTION_PLAN_CHANGE,
            resource_type="tenant",
            resource_id=current_user.tenant_id,
            metadata={"old_plan": old_plan, "new_plan": body.plan},
            ip_address=client_ip(request),
        )

    return TenantResponse(
        id=str(tenant.id),
        name=tenant.name,
        slug=tenant.slug,
        plan=tenant.plan,
        is_active=tenant.is_active,
        created_at=tenant.created_at,
    )
