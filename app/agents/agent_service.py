"""
LangChain tool-calling agent orchestration (Phase 4).
Compatible with LangChain 1.x (create_agent API).
"""

from __future__ import annotations

import os
import time
from typing import Any, Optional

from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langgraph.errors import GraphRecursionError
from sqlalchemy.orm import Session

from app.agents.memory import append_turn, load_memory, new_session_id
from app.agents.tools import AgentToolContext, build_agent_tools, resolve_allowed_documents
from app.config import get_settings
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

SYSTEM_PROMPT = """You are an enterprise document assistant for a multi-tenant RAG platform.

Rules:
- Only use information from tools (tenant-scoped documents).
- For ANY Excel/spreadsheet question, use query_spreadsheet only — never answer_with_rag.
- Excel workflow: first operation=columns, then choose the right operation:
  - overview / what is in the file: columns + preview
  - totals/averages: sum/mean with column=
  - how many distinct values in a column: nunique with column=
  - how many rows where column equals X: count with column= and match_value=
  - breakdown per value: value_counts with column=
  - find a row / all fields for an id: lookup with key_value only (returns full row)
- Column names from the user may differ in spacing/case from headers — pass them anyway.
- nunique counts distinct values; it is NOT for "how many rows match X".
- Do NOT use describe on text-only spreadsheets (no numeric columns).
- For factual questions on PDF/DOCX/PPTX, call answer_with_rag once, then respond immediately.
- Use at most 3 tool calls per user question. Never call the same tool twice with the same input.
- For summaries of non-Excel docs, use summarize_document once.
- For exploration of non-Excel docs, use search_documents once, then answer_with_rag if needed.
- If no documents exist, say so clearly.
- Be concise and cite filenames when available.
"""


def _extract_answer(result: dict[str, Any]) -> str:
    messages = result.get("messages") or []
    if not messages:
        return ""
    last = messages[-1]
    content = getattr(last, "content", last)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
            elif isinstance(block, str):
                parts.append(block)
        return "\n".join(p for p in parts if p)
    return str(content)


class AgentService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def _build_llm(self) -> ChatOpenAI:
        return ChatOpenAI(
            model=os.getenv("LLM_MODEL", "anthropic/claude-3-haiku:beta"),
            openai_api_key=os.getenv("OPENROUTER_API_KEY"),
            openai_api_base=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
            temperature=float(os.getenv("AGENT_TEMPERATURE", "0.2")),
            max_tokens=int(os.getenv("AGENT_MAX_TOKENS", "2000")),
            default_headers={
                "HTTP-Referer": "http://localhost:8000",
                "X-Title": "Enterprise RAG Agent",
            },
        )

    def _is_excel_document(self, db: Session, tenant_id: str, doc_id: Optional[str]) -> bool:
        if not doc_id:
            return False
        from app.services.document_service import get_document_for_tenant

        doc = get_document_for_tenant(db, tenant_id, doc_id)
        return (doc.filename or "").lower().endswith((".xlsx", ".xls"))

    def _excel_spreadsheet_fallback(
        self,
        *,
        db: Session,
        tenant_id: str,
        doc_id: str,
        ctx: AgentToolContext,
    ) -> str:
        from app.services.spreadsheet_analyzer import analyze_spreadsheet

        schema = analyze_spreadsheet(db, tenant_id, doc_id, "columns")
        preview = analyze_spreadsheet(db, tenant_id, doc_id, "preview")
        ctx.mark("query_spreadsheet")

        lines = [
            f"Spreadsheet: {schema.get('filename')} "
            f"({schema.get('row_count')} rows, {schema.get('column_count')} columns)",
            f"Columns: {', '.join(schema.get('columns', []))}",
            "Sample rows:",
        ]
        for row in preview.get("rows", [])[:5]:
            lines.append(", ".join(f"{k}: {v}" for k, v in row.items()))
        return "\n".join(lines)

    def _rag_fallback(
        self,
        *,
        query: str,
        doc_id: Optional[str],
        tenant_id: str,
        allowed_ids: Optional[list[str]],
        ctx: AgentToolContext,
    ) -> str:
        from app.workflows.chat_pipeline import ChatPipeline

        logger.info("Falling back to direct RAG for query")
        rag = ChatPipeline().chat(
            query=query,
            document_id=doc_id,
            tenant_id=tenant_id,
            allowed_document_ids=allowed_ids,
        )
        ctx.mark("answer_with_rag")
        return rag.get("answer", "")

    def _build_system_prompt(
        self,
        *,
        db: Session,
        tenant_id: str,
        doc_id: Optional[str],
        allowed_ids: Optional[list[str]],
    ) -> str:
        system_prompt = SYSTEM_PROMPT
        if doc_id:
            from app.services.document_service import get_document_for_tenant

            doc = get_document_for_tenant(db, tenant_id, doc_id)
            is_excel = (doc.filename or "").lower().endswith((".xlsx", ".xls"))
            if is_excel:
                system_prompt += (
                    f"\n\nThe user selected Excel file: \"{doc.filename}\" (id={doc_id}, status={doc.status}). "
                    "Use query_spreadsheet only. Start with columns, then preview/nunique/sum/mean/lookup as needed. "
                    "Never use answer_with_rag or search_documents for this file."
                )
            else:
                system_prompt += (
                    f"\n\nThe user selected document: \"{doc.filename}\" (id={doc_id}, status={doc.status}). "
                    "Call answer_with_rag for factual questions about this document, then stop."
                )
        elif allowed_ids:
            system_prompt += (
                f"\n\nThe tenant has {len(allowed_ids)} completed document(s). "
                "Use answer_with_rag or search_documents as needed, then stop after answering."
            )
        return system_prompt

    def run(
        self,
        *,
        db: Session,
        tenant_id: str,
        user_id: str,
        query: str,
        session_id: Optional[str] = None,
        document_id: Optional[str] = None,
        use_memory: bool = True,
    ) -> dict[str, Any]:
        if not self.settings.agent_enabled:
            raise RuntimeError("Agent mode is disabled. Set AGENT_ENABLED=true in .env")

        if not os.getenv("OPENROUTER_API_KEY"):
            raise RuntimeError("OPENROUTER_API_KEY is not configured")

        sid = session_id or new_session_id()
        doc_id, allowed_ids = resolve_allowed_documents(db, tenant_id, document_id)
        ctx = AgentToolContext(
            tenant_id=tenant_id,
            user_id=user_id,
            db=db,
            document_id=doc_id,
            allowed_document_ids=allowed_ids,
        )
        tools = build_agent_tools(ctx)
        llm = self._build_llm()

        agent = create_agent(
            model=llm,
            tools=tools,
            system_prompt=self._build_system_prompt(
                db=db,
                tenant_id=tenant_id,
                doc_id=doc_id,
                allowed_ids=allowed_ids,
            ),
        )

        messages: list[dict[str, str]] = []
        if use_memory:
            messages.extend(load_memory(tenant_id, user_id, sid))
        messages.append({"role": "user", "content": query})

        recursion_limit = self.settings.agent_recursion_limit
        start = time.time()
        try:
            result = agent.invoke(
                {"messages": messages},
                config={"recursion_limit": recursion_limit},
            )
            answer = _extract_answer(result)
        except GraphRecursionError:
            logger.warning(
                "Agent hit recursion limit (%s); using fallback",
                recursion_limit,
            )
            if doc_id and self._is_excel_document(db, tenant_id, doc_id):
                answer = self._excel_spreadsheet_fallback(
                    db=db, tenant_id=tenant_id, doc_id=doc_id, ctx=ctx
                )
            else:
                answer = self._rag_fallback(
                    query=query,
                    doc_id=doc_id,
                    tenant_id=tenant_id,
                    allowed_ids=allowed_ids,
                    ctx=ctx,
                )

        elapsed_ms = (time.time() - start) * 1000

        if not ctx.tools_used and (doc_id or allowed_ids):
            if doc_id and self._is_excel_document(db, tenant_id, doc_id):
                if not (answer or "").strip():
                    answer = self._excel_spreadsheet_fallback(
                        db=db, tenant_id=tenant_id, doc_id=doc_id, ctx=ctx
                    )
            else:
                answer = self._rag_fallback(
                    query=query,
                    doc_id=doc_id,
                    tenant_id=tenant_id,
                    allowed_ids=allowed_ids,
                    ctx=ctx,
                )

        if use_memory:
            append_turn(tenant_id, user_id, sid, query, answer)

        return {
            "answer": answer,
            "session_id": sid,
            "tools_used": ctx.tools_used,
            "processing_time_ms": elapsed_ms,
            "model_used": os.getenv("LLM_MODEL", "anthropic/claude-3-haiku:beta"),
            "agent_steps": self.settings.agent_max_iterations,
        }
