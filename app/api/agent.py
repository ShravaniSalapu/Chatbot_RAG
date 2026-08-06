"""
Agentic AI chat API (Phase 4).
"""

import asyncio

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.agents.agent_service import AgentService
from app.agents.memory import clear_memory, new_session_id
from app.auth.dependencies import CurrentUser, get_current_user
from app.db.database import get_db
from app.models.agent_models import AgentChatRequest, AgentChatResponse
from app.services.audit_service import ACTION_AGENT, log_audit
from app.services.document_service import get_document_for_tenant
from app.services.usage_service import check_chat_quota, record_chat
from app.utils.request_utils import client_ip
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

router = APIRouter()
_agent_service = AgentService()


@router.post("/agent/chat", response_model=AgentChatResponse)
async def agent_chat(
    request: Request,
    body: AgentChatRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Multi-step agent chat with LangChain tools (tenant-scoped)."""
    logger.info(f"Agent query: {body.query} (tenant={current_user.tenant_id})")

    check_chat_quota(db, current_user.tenant_id)

    if body.document_id:
        get_document_for_tenant(db, current_user.tenant_id, body.document_id)

    try:
        result = await asyncio.to_thread(
            _agent_service.run,
            db=db,
            tenant_id=current_user.tenant_id,
            user_id=current_user.user_id,
            query=body.query,
            session_id=body.session_id,
            document_id=body.document_id,
            use_memory=body.use_memory,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        logger.error(f"Agent error: {exc}")
        raise HTTPException(status_code=500, detail=f"Agent failed: {exc}") from exc

    record_chat(db, current_user.tenant_id)
    log_audit(
        db,
        tenant_id=current_user.tenant_id,
        user_id=current_user.user_id,
        action=ACTION_AGENT,
        resource_type="document" if body.document_id else "all",
        resource_id=body.document_id,
        metadata={"tools_used": result.get("tools_used", []), "session_id": result["session_id"]},
        ip_address=client_ip(request),
    )

    return AgentChatResponse(
        answer=result["answer"],
        session_id=result["session_id"],
        tools_used=result.get("tools_used", []),
        processing_time_ms=result["processing_time_ms"],
        model_used=result["model_used"],
    )


@router.post("/agent/session")
async def create_agent_session(
    current_user: CurrentUser = Depends(get_current_user),
):
    """Start a new agent conversation session."""
    return {"session_id": new_session_id()}


@router.delete("/agent/session/{session_id}")
async def delete_agent_session(
    session_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Clear Redis memory for an agent session."""
    clear_memory(current_user.tenant_id, current_user.user_id, session_id)
    return {"success": True, "session_id": session_id}
