"""Phase 4 agent foundation tests."""

from app.agents.memory import new_session_id
from app.services.audit_service import ACTION_AGENT


class TestPhase4Basics:
    def test_session_id_format(self):
        sid = new_session_id()
        assert len(sid) == 36
        assert sid.count("-") == 4

    def test_agent_audit_action(self):
        assert ACTION_AGENT == "agent"

    def test_agent_tools_import(self):
        from app.agents.tools import AgentToolContext, build_agent_tools

        assert AgentToolContext is not None
        assert callable(build_agent_tools)
