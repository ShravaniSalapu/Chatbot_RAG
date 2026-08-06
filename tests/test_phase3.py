"""Phase 3 enterprise feature tests."""

from app.services.plan_limits import PLAN_LIMITS, VALID_PLANS, get_plan_limits


class TestPlanLimits:
    def test_all_plans_defined(self):
        assert VALID_PLANS == {"free", "pro", "enterprise"}
        assert set(PLAN_LIMITS.keys()) == VALID_PLANS

    def test_free_tier_limits(self):
        limits = get_plan_limits("free")
        assert limits.max_documents == 10
        assert limits.max_storage_bytes == 100 * 1024 * 1024
        assert limits.max_chat_calls_per_month == 500

    def test_pro_tier_higher_than_free(self):
        free = get_plan_limits("free")
        pro = get_plan_limits("pro")
        assert pro.max_documents > free.max_documents
        assert pro.max_storage_bytes > free.max_storage_bytes
        assert pro.max_chat_calls_per_month > free.max_chat_calls_per_month

    def test_unknown_plan_falls_back_to_free(self):
        limits = get_plan_limits("unknown")
        assert limits == get_plan_limits("free")

    def test_enterprise_is_highest(self):
        enterprise = get_plan_limits("enterprise")
        pro = get_plan_limits("pro")
        assert enterprise.max_documents >= pro.max_documents
        assert enterprise.max_storage_bytes >= pro.max_storage_bytes


class TestAuditActions:
    def test_action_constants(self):
        from app.services import audit_service

        assert audit_service.ACTION_UPLOAD == "upload"
        assert audit_service.ACTION_CHAT == "chat"
        assert audit_service.ACTION_PLAN_CHANGE == "plan_change"
