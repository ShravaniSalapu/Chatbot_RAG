"""
LangChain tools wrapping existing tenant-scoped RAG operations (Phase 4).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Optional

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.retrieval.hybrid_search import HybridSearch
from app.services.document_service import (
    get_document_for_tenant,
    list_completed_document_ids_for_tenant,
    list_documents_for_tenant,
)
from app.services.spreadsheet_analyzer import analyze_spreadsheet, lookup_spreadsheet_row
from app.services.processing_status import get_processing_status
from app.workflows.chat_pipeline import ChatPipeline
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

_hybrid_search: Optional[HybridSearch] = None
_chat_pipeline: Optional[ChatPipeline] = None


def _get_hybrid_search() -> HybridSearch:
    global _hybrid_search
    if _hybrid_search is None:
        _hybrid_search = HybridSearch()
    return _hybrid_search


def _get_chat_pipeline() -> ChatPipeline:
    global _chat_pipeline
    if _chat_pipeline is None:
        _chat_pipeline = ChatPipeline()
    return _chat_pipeline


@dataclass
class AgentToolContext:
    tenant_id: str
    user_id: str
    db: Session
    document_id: Optional[str] = None
    allowed_document_ids: Optional[list[str]] = None
    tools_used: list[str] = field(default_factory=list)

    def mark(self, name: str) -> None:
        if name not in self.tools_used:
            self.tools_used.append(name)


class SearchInput(BaseModel):
    query: str = Field(description="Natural language search query over tenant documents")
    top_k: int = Field(default=5, ge=1, le=10, description="Number of chunks to return")


class RagAnswerInput(BaseModel):
    question: str = Field(description="Question to answer using retrieved document context and citations")


class DocumentIdInput(BaseModel):
    document_id: str = Field(description="Document UUID to summarize or check status")


class SummarizeInput(BaseModel):
    document_id: Optional[str] = Field(
        default=None,
        description="Optional document UUID. If omitted, summarizes across allowed tenant documents.",
    )


class SpreadsheetInput(BaseModel):
    operation: str = Field(
        description="One of: columns, sum, mean, count, min, max, describe, preview, nunique, value_counts, lookup",
    )
    column: Optional[str] = Field(
        default=None,
        description="Column name from operation=columns (spacing/case may differ from file headers)",
    )
    match_value: Optional[str] = Field(
        default=None,
        description="For count: count rows where column equals this value (e.g. how many rows with a given status)",
    )
    key_column: Optional[str] = Field(
        default=None,
        description="For lookup: column to match on (optional — auto-detected from file if unique)",
    )
    key_value: Optional[str] = Field(
        default=None,
        description="For lookup: value to find in the spreadsheet",
    )
    return_column: Optional[str] = Field(
        default=None,
        description="For lookup: optional column to return; omit to return full matching row(s)",
    )
    document_id: Optional[str] = Field(
        default=None,
        description="Excel document UUID. Uses the selected document if omitted.",
    )


def build_agent_tools(ctx: AgentToolContext) -> list[StructuredTool]:
    hybrid = _get_hybrid_search()
    chat_pipeline = _get_chat_pipeline()

    def search_documents(query: str, top_k: int = 5) -> str:
        """Search indexed document chunks (hybrid BM25 + vector). Returns JSON snippets."""
        ctx.mark("search_documents")
        results = hybrid.search(
            query,
            document_id=ctx.document_id,
            tenant_id=ctx.tenant_id,
            allowed_document_ids=ctx.allowed_document_ids,
        )
        payload = []
        for row in results[:top_k]:
            payload.append(
                {
                    "document_id": row.get("document_id"),
                    "filename": (row.get("metadata") or {}).get("filename"),
                    "heading": row.get("heading"),
                    "page_number": row.get("page_number"),
                    "score": row.get("score", row.get("combined_score")),
                    "snippet": (row.get("content") or "")[:500],
                }
            )
        return json.dumps({"results": payload, "count": len(payload)}, ensure_ascii=False)

    def answer_with_rag(question: str) -> str:
        """Full RAG answer with retrieval, citations, and grounding in tenant documents."""
        ctx.mark("answer_with_rag")
        result = chat_pipeline.chat(
            query=question,
            document_id=ctx.document_id,
            tenant_id=ctx.tenant_id,
            allowed_document_ids=ctx.allowed_document_ids,
        )
        return json.dumps(
            {
                "answer": result.get("answer", ""),
                "confidence_score": result.get("confidence_score"),
                "sources": result.get("sources", [])[:5],
            },
            ensure_ascii=False,
        )

    def list_documents() -> str:
        """List documents belonging to the current tenant with processing status."""
        ctx.mark("list_documents")
        docs = list_documents_for_tenant(ctx.db, ctx.tenant_id)
        payload = [
            {
                "document_id": d.id,
                "filename": d.filename,
                "status": d.status,
                "chunks_created": d.chunks_created,
                "file_size": d.file_size,
            }
            for d in docs
        ]
        return json.dumps({"documents": payload, "count": len(payload)}, ensure_ascii=False)

    def summarize_document(document_id: Optional[str] = None) -> str:
        """Summarize a document or all completed tenant documents."""
        ctx.mark("summarize_document")
        target_id = document_id or ctx.document_id
        question = (
            "Provide a concise summary with key bullet points from this document."
            if target_id
            else "Provide a concise summary with key bullet points across the available documents."
        )
        result = chat_pipeline.chat(
            query=question,
            document_id=target_id,
            tenant_id=ctx.tenant_id,
            allowed_document_ids=ctx.allowed_document_ids if not target_id else None,
        )
        return json.dumps({"summary": result.get("answer", ""), "document_id": target_id}, ensure_ascii=False)

    def query_spreadsheet(
        operation: str,
        column: Optional[str] = None,
        match_value: Optional[str] = None,
        key_column: Optional[str] = None,
        key_value: Optional[str] = None,
        return_column: Optional[str] = None,
        document_id: Optional[str] = None,
    ) -> str:
        """Run exact calculations on an Excel file (sum, mean, column list, etc.)."""
        ctx.mark("query_spreadsheet")
        target_id = document_id or ctx.document_id
        if not target_id:
            return json.dumps({"error": "No Excel document selected or specified"})

        try:
            doc = get_document_for_tenant(ctx.db, ctx.tenant_id, target_id)
            if not (doc.filename or "").lower().endswith((".xlsx", ".xls")):
                return json.dumps({"error": f"Document '{doc.filename}' is not an Excel file"})

            op = operation.strip().lower()

            if op == "lookup":
                if not key_value:
                    schema = analyze_spreadsheet(ctx.db, ctx.tenant_id, target_id, "columns")
                    return json.dumps(
                        {
                            "error": "key_value is required for lookup",
                            "hint": "Pass key_value from the user question. key_column is optional.",
                            "columns": schema.get("columns", []),
                        },
                        ensure_ascii=False,
                    )
                result = lookup_spreadsheet_row(
                    ctx.db,
                    ctx.tenant_id,
                    target_id,
                    key_value=key_value,
                    key_column=key_column,
                    return_column=return_column,
                )
                return json.dumps(result, ensure_ascii=False)

            if op in ("sum", "mean", "min", "max", "nunique", "distinct", "unique_count", "value_counts", "counts") and not column:
                schema = analyze_spreadsheet(ctx.db, ctx.tenant_id, target_id, "columns")
                return json.dumps(
                    {
                        "error": "column is required for this operation",
                        "hint": "Call operation=columns, then pass column= from that list.",
                        "columns": schema.get("columns", []),
                        "numeric_columns": schema.get("numeric_columns", []),
                    },
                    ensure_ascii=False,
                )

            if op == "count" and match_value and not column:
                schema = analyze_spreadsheet(ctx.db, ctx.tenant_id, target_id, "columns")
                return json.dumps(
                    {
                        "error": "column is required when using match_value with count",
                        "columns": schema.get("columns", []),
                    },
                    ensure_ascii=False,
                )

            result = analyze_spreadsheet(
                ctx.db,
                ctx.tenant_id,
                target_id,
                operation=op,
                column=column,
                match_value=match_value,
            )
            return json.dumps(result, ensure_ascii=False)
        except Exception as exc:
            logger.warning(f"query_spreadsheet failed: {exc}")
            return json.dumps({"error": str(exc)})

    def document_status(document_id: str) -> str:
        """Get upload/processing status for a document in the current tenant."""
        ctx.mark("document_status")
        doc = next(
            (d for d in list_documents_for_tenant(ctx.db, ctx.tenant_id) if d.id == document_id),
            None,
        )
        if not doc:
            return json.dumps({"error": "Document not found for this tenant"})
        live = get_processing_status(document_id) or {}
        return json.dumps(
            {
                "document_id": document_id,
                "filename": doc.filename,
                "status": live.get("status", doc.status),
                "progress": live.get("progress", doc.progress),
                "chunks_created": live.get("chunks_created", doc.chunks_created),
                "error_message": live.get("error_message", doc.error_message),
            },
            ensure_ascii=False,
        )

    def _is_excel_context() -> bool:
        target_id = ctx.document_id
        if not target_id:
            return False
        doc = next(
            (d for d in list_documents_for_tenant(ctx.db, ctx.tenant_id) if d.id == target_id),
            None,
        )
        return bool(doc and (doc.filename or "").lower().endswith((".xlsx", ".xls")))

    excel_selected = _is_excel_context()

    spreadsheet_tool = StructuredTool.from_function(
        func=query_spreadsheet,
        name="query_spreadsheet",
        description=(
            "Excel tool. columns=list headers; preview=sample rows; "
            "sum/mean/min/max/nunique/value_counts use column=; "
            "count rows matching a value: count with column= and match_value=; "
            "lookup finds rows by key_value (omit return_column to get full row). "
            "Column spacing/case may differ from headers. Call columns first."
        ),
        args_schema=SpreadsheetInput,
    )
    list_tool = StructuredTool.from_function(
        func=list_documents,
        name="list_documents",
        description="List all documents for the current tenant.",
    )
    status_tool = StructuredTool.from_function(
        func=document_status,
        name="document_status",
        description="Check processing status for a document ID.",
        args_schema=DocumentIdInput,
    )

    if excel_selected:
        return [spreadsheet_tool, list_tool, status_tool]

    return [
        StructuredTool.from_function(
            func=search_documents,
            name="search_documents",
            description="Search tenant document chunks. Use for finding specific facts or passages.",
            args_schema=SearchInput,
        ),
        StructuredTool.from_function(
            func=answer_with_rag,
            name="answer_with_rag",
            description="Answer a question using full RAG pipeline with citations. Prefer for direct Q&A.",
            args_schema=RagAnswerInput,
        ),
        spreadsheet_tool,
        StructuredTool.from_function(
            func=summarize_document,
            name="summarize_document",
            description="Summarize one document or all tenant documents.",
            args_schema=SummarizeInput,
        ),
        list_tool,
        status_tool,
    ]


def resolve_allowed_documents(db: Session, tenant_id: str, document_id: Optional[str]) -> tuple[Optional[str], Optional[list[str]]]:
    if document_id:
        return document_id, None
    ids = list_completed_document_ids_for_tenant(db, tenant_id)
    return None, ids
