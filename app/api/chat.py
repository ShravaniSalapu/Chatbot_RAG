"""
Chat API endpoint for RAG-based chat
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, get_current_user
from app.db.database import get_db
from app.models.response_models import ChatResponse, ChatMessage, Citation
from app.services.document_service import get_document_for_tenant, list_completed_document_ids_for_tenant
from app.services.usage_service import check_chat_quota, record_chat
from app.services.audit_service import log_audit, ACTION_CHAT
from app.utils.request_utils import client_ip
from app.workflows.chat_pipeline import ChatPipeline
from app.utils.logger import setup_logger
import os

logger = setup_logger(__name__)

router = APIRouter()
_chat_pipeline = ChatPipeline()


class ChatRequest(BaseModel):
    query: str
    document_id: Optional[str] = None
    conversation_history: Optional[List[ChatMessage]] = None
    use_reranking: bool = True
    top_k: Optional[int] = None


def _history_to_dicts(history: Optional[List[ChatMessage]]) -> Optional[List[dict]]:
    if not history:
        return None
    return [{"role": msg.role, "content": msg.content} for msg in history]


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: Request,
    body: ChatRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Chat with the RAG system using the full chat pipeline (tenant-scoped)."""
    logger.info(f"Received chat query: {body.query} (tenant={current_user.tenant_id})")

    check_chat_quota(db, current_user.tenant_id)

    if body.document_id:
        get_document_for_tenant(db, current_user.tenant_id, body.document_id)
        allowed_document_ids = None
    else:
        allowed_document_ids = list_completed_document_ids_for_tenant(
            db, current_user.tenant_id
        )

    try:
        result = _chat_pipeline.chat(
            query=body.query,
            document_id=body.document_id,
            tenant_id=current_user.tenant_id,
            allowed_document_ids=allowed_document_ids,
            conversation_history=_history_to_dicts(body.conversation_history),
            use_reranking=body.use_reranking,
            top_k=body.top_k,
            retrieval_method=os.getenv("RETRIEVAL_METHOD", "hybrid"),
        )

        citations = [
            Citation(
                chunk_id=cit.get("chunk_id") or "",
                document_id=cit.get("document_id") or "",
                filename=cit.get("filename") or "Unknown",
                page_number=cit.get("page_number"),
                heading=cit.get("heading"),
                snippet=cit.get("snippet") or "",
            )
            for cit in result.get("citations", [])
        ]

        record_chat(db, current_user.tenant_id)
        log_audit(
            db,
            tenant_id=current_user.tenant_id,
            user_id=current_user.user_id,
            action=ACTION_CHAT,
            resource_type="document" if body.document_id else "all",
            resource_id=body.document_id,
            metadata={"query_length": len(body.query)},
            ip_address=client_ip(request),
        )

        return ChatResponse(
            answer=result.get("answer", ""),
            citations=citations,
            sources=result.get("sources", []),
            confidence_score=result.get("confidence_score"),
            processing_time_ms=result.get("processing_time_ms", 0.0),
            model_used=result.get("model_used", "unknown"),
            context_used=result.get("context_used", []),
        )

    except Exception as e:
        logger.error(f"Error in chat: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing chat request: {str(e)}")


@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Stream chat response (placeholder)."""
    return {"message": "Streaming not yet implemented", "tenant_id": current_user.tenant_id}
