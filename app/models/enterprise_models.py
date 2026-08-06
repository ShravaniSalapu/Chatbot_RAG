"""
Pydantic models for Phase 3 enterprise features.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class PlanLimitsResponse(BaseModel):
    max_documents: int
    max_storage_bytes: int
    max_chat_calls_per_month: int
    max_search_calls_per_month: int


class UsageResponse(BaseModel):
    tenant_id: str
    plan: str
    document_count: int
    storage_bytes: int
    upload_count: int
    chat_count: int
    search_count: int
    api_call_count: int
    period_start: datetime
    limits: PlanLimitsResponse


class AuditLogResponse(BaseModel):
    id: str
    tenant_id: str
    user_id: Optional[str] = None
    action: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None
    ip_address: Optional[str] = None
    created_at: datetime


class PlanInfoResponse(BaseModel):
    plan: str
    limits: PlanLimitsResponse


class AllPlansResponse(BaseModel):
    plans: dict[str, PlanLimitsResponse]
