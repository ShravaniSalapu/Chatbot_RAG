"""
Plan tier limits for per-tenant quotas (Phase 3).
"""

from dataclasses import dataclass

VALID_PLANS = frozenset({"free", "pro", "enterprise"})


@dataclass(frozen=True)
class PlanLimits:
    max_documents: int
    max_storage_bytes: int
    max_chat_calls_per_month: int
    max_search_calls_per_month: int


PLAN_LIMITS: dict[str, PlanLimits] = {
    "free": PlanLimits(
        max_documents=10,
        max_storage_bytes=100 * 1024 * 1024,  # 100 MB
        max_chat_calls_per_month=500,
        max_search_calls_per_month=1000,
    ),
    "pro": PlanLimits(
        max_documents=100,
        max_storage_bytes=5 * 1024 * 1024 * 1024,  # 5 GB
        max_chat_calls_per_month=10_000,
        max_search_calls_per_month=20_000,
    ),
    "enterprise": PlanLimits(
        max_documents=10_000,
        max_storage_bytes=100 * 1024 * 1024 * 1024,  # 100 GB
        max_chat_calls_per_month=1_000_000,
        max_search_calls_per_month=1_000_000,
    ),
}


def get_plan_limits(plan: str) -> PlanLimits:
    return PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])
