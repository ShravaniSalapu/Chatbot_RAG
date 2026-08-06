"""
Search API endpoint for document search
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, get_current_user
from app.db.database import get_db
from app.models.response_models import SearchResponse, SearchResult
from app.services.document_service import get_document_for_tenant, list_completed_document_ids_for_tenant
from app.services.usage_service import check_search_quota, record_search
from app.services.audit_service import log_audit, ACTION_SEARCH
from app.utils.request_utils import client_ip
from app.retrieval.hybrid_search import HybridSearch
from app.retrieval.multimodal_retriever import MultimodalRetriever
from app.retrieval.tenant_filter import filter_results_for_tenant
from app.reranking.rerank_pipeline import RerankPipeline
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

router = APIRouter()


class SearchRequest(BaseModel):
    query: str
    search_type: Optional[str] = "hybrid"  # hybrid, dense, bm25, multimodal
    top_k: Optional[int] = None
    use_reranking: bool = True
    document_id: Optional[str] = None


@router.post("/search", response_model=SearchResponse)
async def search(
    request: Request,
    body: SearchRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Search documents within the current tenant."""
    logger.info(
        f"Received search query: {body.query}, type: {body.search_type} "
        f"(tenant={current_user.tenant_id})"
    )

    check_search_quota(db, current_user.tenant_id)

    if body.document_id:
        get_document_for_tenant(db, current_user.tenant_id, body.document_id)
        allowed_document_ids = None
    else:
        allowed_document_ids = list_completed_document_ids_for_tenant(
            db, current_user.tenant_id
        )

    try:
        import time
        start_time = time.time()

        results = []
        tenant_id = current_user.tenant_id

        if body.search_type == "multimodal":
            multimodal_retriever = MultimodalRetriever()
            results = multimodal_retriever.retrieve_combined(
                body.query,
                top_k=body.top_k or 5,
                document_id=body.document_id,
                tenant_id=tenant_id,
            )
        elif body.search_type == "hybrid":
            hybrid_search = HybridSearch()
            results = hybrid_search.search(
                body.query,
                document_id=body.document_id,
                tenant_id=tenant_id,
                allowed_document_ids=allowed_document_ids,
            )
        else:
            hybrid_search = HybridSearch()
            results = hybrid_search.search(
                body.query,
                document_id=body.document_id,
                tenant_id=tenant_id,
                allowed_document_ids=allowed_document_ids,
            )

        if body.use_reranking and results:
            rerank_pipeline = RerankPipeline()
            results = rerank_pipeline.rerank_results(body.query, results, top_k=body.top_k or 5)

        results = filter_results_for_tenant(
            results, tenant_id, allowed_document_ids=allowed_document_ids
        )

        search_results = []
        for result in results[: body.top_k or 5]:
            search_results.append(
                SearchResult(
                    chunk_id=result.get("chunk_id"),
                    document_id=result.get("document_id"),
                    content=result.get("content"),
                    score=result.get("score", result.get("combined_score", 0)),
                    chunk_type=result.get("chunk_type"),
                    metadata=result.get("metadata", {}),
                    page_number=result.get("page_number"),
                    heading=result.get("heading"),
                )
            )

        search_time_ms = (time.time() - start_time) * 1000

        record_search(db, current_user.tenant_id)
        log_audit(
            db,
            tenant_id=current_user.tenant_id,
            user_id=current_user.user_id,
            action=ACTION_SEARCH,
            resource_type="document" if body.document_id else "all",
            resource_id=body.document_id,
            metadata={"search_type": body.search_type, "results": len(search_results)},
            ip_address=client_ip(request),
        )

        return SearchResponse(
            query=body.query,
            results=search_results,
            total_results=len(search_results),
            search_time_ms=search_time_ms,
            retrieval_method=body.search_type,
        )

    except Exception as e:
        logger.error(f"Error in search: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing search request: {str(e)}")


@router.post("/search/similar")
async def search_similar(
    chunk_id: str,
    top_k: int = 5,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Find similar chunks to a given chunk."""
    logger.info(f"Finding similar chunks for: {chunk_id} (tenant={current_user.tenant_id})")
    return {
        "chunk_id": chunk_id,
        "similar_chunks": [],
        "message": "Similarity search not yet implemented",
    }
