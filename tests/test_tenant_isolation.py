"""Tenant isolation and auth unit tests (Phase 1.2 / 1.3)."""

import uuid

import pytest

from app.auth.security import generate_api_key, hash_api_key, verify_api_key
from app.retrieval.bm25_search import BM25Search
from app.vectorstore.payload_builder import PayloadBuilder


TENANT_A = "11111111-1111-1111-1111-111111111111"
TENANT_B = "22222222-2222-2222-2222-222222222222"
DOC_A = "doc-a"
DOC_B = "doc-b"


class TestPayloadBuilderTenantFilter:
    def test_chunk_payload_includes_tenant_id(self):
        payload = PayloadBuilder.build_chunk_payload(
            {"chunk_id": "c1", "document_id": DOC_A, "chunk_type": "text", "content": "hello"},
            {"filename": "f.pdf", "tenant_id": TENANT_A},
        )
        assert payload["tenant_id"] == TENANT_A

    def test_build_filter_requires_tenant_id(self):
        filt = PayloadBuilder.build_filter(tenant_id=TENANT_A, document_id=DOC_A)
        keys = {c["key"] for c in filt["must"]}
        assert "tenant_id" in keys
        assert "document_id" in keys

    def test_qdrant_filter_includes_tenant(self):
        qf = PayloadBuilder.build_qdrant_filter(tenant_id=TENANT_A)
        assert qf is not None
        assert len(qf.must) == 1
        assert qf.must[0].key == "tenant_id"


class TestBM25TenantIsolation:
    def _sample_chunks(self, tenant_id: str, doc_id: str):
        return [
            {
                "chunk_id": f"{doc_id}-1",
                "document_id": doc_id,
                "tenant_id": tenant_id,
                "content": "enterprise rag document content",
                "chunk_type": "text",
            }
        ]

    def setup_method(self):
        self.bm25 = BM25Search()
        self.bm25.build_index(DOC_A, self._sample_chunks(TENANT_A, DOC_A), tenant_id=TENANT_A)
        self.bm25.build_index(DOC_B, self._sample_chunks(TENANT_B, DOC_B), tenant_id=TENANT_B)

    def test_tenant_a_cannot_see_tenant_b_documents(self):
        results = self.bm25.search("rag document", tenant_id=TENANT_A, top_k=10)
        doc_ids = {r["document_id"] for r in results}
        assert DOC_B not in doc_ids
        if doc_ids:
            assert DOC_A in doc_ids

    def test_tenant_b_cannot_see_tenant_a_documents(self):
        results = self.bm25.search("rag document", tenant_id=TENANT_B, top_k=10)
        doc_ids = {r["document_id"] for r in results}
        assert DOC_A not in doc_ids
        if doc_ids:
            assert DOC_B in doc_ids

    def test_wrong_tenant_document_id_returns_empty(self):
        results = self.bm25.search("enterprise", document_id=DOC_B, tenant_id=TENANT_A)
        assert results == []

    def test_doc_ids_for_search_filters_by_tenant(self):
        ids_a = self.bm25._doc_ids_for_search(tenant_id=TENANT_A)
        ids_b = self.bm25._doc_ids_for_search(tenant_id=TENANT_B)
        assert DOC_A in ids_a and DOC_B not in ids_a
        assert DOC_B in ids_b and DOC_A not in ids_b

    def test_no_tenant_returns_empty_when_auth_required(self, monkeypatch):
        monkeypatch.setenv("REQUIRE_AUTH", "true")
        results = self.bm25.search("rag document", tenant_id=None, top_k=10)
        assert results == []


class TestTenantResultFilter:
    def test_filters_other_tenant_chunks(self):
        from app.retrieval.tenant_filter import filter_results_for_tenant

        results = [
            {"chunk_id": "a", "metadata": {"tenant_id": TENANT_A}},
            {"chunk_id": "b", "metadata": {"tenant_id": TENANT_B}},
            {"chunk_id": "legacy", "metadata": {}},
        ]
        filtered = filter_results_for_tenant(results, TENANT_A)
        assert [r["chunk_id"] for r in filtered] == ["a"]

    def test_filters_by_allowed_document_ids(self):
        from app.retrieval.tenant_filter import filter_results_for_tenant

        results = [
            {"chunk_id": "a", "document_id": DOC_A, "metadata": {"tenant_id": TENANT_A}},
            {"chunk_id": "b", "document_id": DOC_B, "metadata": {"tenant_id": TENANT_A}},
        ]
        filtered = filter_results_for_tenant(
            results, TENANT_A, allowed_document_ids=[DOC_A]
        )
        assert [r["chunk_id"] for r in filtered] == ["a"]


class TestApiKeyAuth:
    def test_generate_and_verify_api_key(self):
        raw, key_hash, prefix = generate_api_key()
        assert raw.startswith("rag_")
        assert len(key_hash) == 64
        assert raw.startswith(prefix)
        assert verify_api_key(raw, key_hash)

    def test_wrong_key_fails_verification(self):
        raw, key_hash, _ = generate_api_key()
        assert not verify_api_key(raw + "x", key_hash)

    def test_hash_is_deterministic(self):
        raw, h1, _ = generate_api_key()
        assert hash_api_key(raw) == h1


class TestDocumentServiceIsolation:
    def test_cross_tenant_document_access_raises_404(self):
        from fastapi import HTTPException
        from unittest.mock import MagicMock

        from app.services.document_service import get_document_for_tenant

        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(HTTPException) as exc:
            get_document_for_tenant(db, TENANT_A, "missing-doc-id")
        assert exc.value.status_code == 404
