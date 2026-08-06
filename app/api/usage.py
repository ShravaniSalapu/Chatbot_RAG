"""
Usage and plan quota API endpoints (Phase 3).
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, get_current_user, require_admin
from app.db.database import get_db
from app.models.enterprise_models import AllPlansResponse, PlanLimitsResponse, UsageResponse
from app.services.plan_limits import PLAN_LIMITS
from app.services.usage_service import get_usage_summary

router = APIRouter()


@router.get("/tenants/me/usage", response_model=UsageResponse)
async def get_my_usage(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Current tenant usage vs plan limits."""
    summary = get_usage_summary(db, current_user.tenant_id)
    return UsageResponse(
        tenant_id=summary["tenant_id"],
        plan=summary["plan"],
        document_count=summary["document_count"],
        storage_bytes=summary["storage_bytes"],
        upload_count=summary["upload_count"],
        chat_count=summary["chat_count"],
        search_count=summary["search_count"],
        api_call_count=summary["api_call_count"],
        period_start=summary["period_start"],
        limits=PlanLimitsResponse(**summary["limits"]),
    )


@router.get("/plans", response_model=AllPlansResponse)
async def list_plans(
    current_user: CurrentUser = Depends(require_admin),
):
    """List available plan tiers and their limits (admin)."""
    return AllPlansResponse(
        plans={
            name: PlanLimitsResponse(
                max_documents=limits.max_documents,
                max_storage_bytes=limits.max_storage_bytes,
                max_chat_calls_per_month=limits.max_chat_calls_per_month,
                max_search_calls_per_month=limits.max_search_calls_per_month,
            )
            for name, limits in PLAN_LIMITS.items()
        }
    )
