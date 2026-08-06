"""Tenant-scoped filtering helpers for retrieval results."""

from typing import Any, Dict, List, Optional


def get_result_tenant_id(result: Dict[str, Any]) -> Optional[str]:
    """Extract tenant_id from a search/retrieval result."""
    metadata = result.get("metadata") or {}
    if isinstance(metadata, dict):
        tenant_id = metadata.get("tenant_id")
        if tenant_id:
            return str(tenant_id)
    tenant_id = result.get("tenant_id")
    return str(tenant_id) if tenant_id else None


def filter_results_for_tenant(
    results: List[Dict[str, Any]],
    tenant_id: Optional[str],
    *,
    allowed_document_ids: Optional[List[str]] = None,
    strict: bool = True,
) -> List[Dict[str, Any]]:
    """
    Drop chunks that belong to another tenant (or have no tenant when strict=True).
    Optionally restrict to an allow-list of document IDs from Postgres.
    """
    if not tenant_id and allowed_document_ids is None:
        return results

    allowed_ids = set(allowed_document_ids) if allowed_document_ids is not None else None
    filtered: List[Dict[str, Any]] = []
    for result in results:
        if tenant_id:
            result_tenant = get_result_tenant_id(result)
            if result_tenant == tenant_id:
                pass
            elif not strict and result_tenant is None:
                pass
            else:
                continue

        if allowed_ids is not None:
            document_id = result.get("document_id")
            if document_id not in allowed_ids:
                continue

        filtered.append(result)
    return filtered
