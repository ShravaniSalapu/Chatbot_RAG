"""
Helpers for deduplicating and formatting citations.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List


def _clean_filename(filename: str, document_id: str = "") -> str:
    name = filename or "Unknown"
    prefix = f"{document_id}_" if document_id else ""
    if prefix and name.startswith(prefix):
        name = name[len(prefix):]
    return name


def format_source_label(citation: Dict[str, Any]) -> str:
    """Build a human-readable source label (page, figure caption, table, etc.)."""
    meta = citation.get("metadata") or {}
    filename = _clean_filename(
        citation.get("filename") or meta.get("filename") or "Unknown",
        citation.get("document_id") or "",
    )
    page = citation.get("page_number") or meta.get("page_number")
    chunk_type = citation.get("chunk_type") or meta.get("chunk_type") or ""
    content = (citation.get("content") or citation.get("snippet") or "").strip()

    for line in content.splitlines():
        line = line.strip()
        if re.match(r"^(figure|fig\.?|table|chart)\s", line, re.IGNORECASE):
            return f"{filename} — {line[:100]}"

    if page:
        if chunk_type == "table":
            return f"{filename} — Page {page}, Table"
        if chunk_type == "image":
            return f"{filename} — Page {page}, Figure"
        return f"{filename} — Page {page}"

    if chunk_type == "table":
        return f"{filename} — Table data"
    if chunk_type == "image":
        return f"{filename} — Figure/Image"
    if chunk_type == "multimodal":
        return f"{filename} — Figure & text"

    heading = citation.get("heading") or meta.get("heading")
    if heading and heading != "Section":
        return f"{filename} — {heading}"

    preview = re.sub(r"\s+", " ", content)[:80]
    if preview:
        return f"{filename} — {preview}"
    return filename


def dedupe_citations(citations: List[Dict[str, Any]], max_sources: int = 3) -> List[Dict[str, Any]]:
    """Remove duplicate sources and re-index citations."""
    seen_labels = set()
    seen_chunks = set()
    unique: List[Dict[str, Any]] = []

    for citation in citations:
        chunk_id = citation.get("chunk_id")
        if chunk_id and chunk_id in seen_chunks:
            continue

        label = format_source_label(citation)
        if label in seen_labels:
            continue

        if chunk_id:
            seen_chunks.add(chunk_id)
        seen_labels.add(label)
        unique.append(dict(citation))

        if len(unique) >= max_sources:
            break

    for idx, citation in enumerate(unique):
        citation["index"] = idx + 1

    return unique
