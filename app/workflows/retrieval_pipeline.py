"""
Retrieval pipeline for searching documents
"""

from typing import Dict, Any, Optional, List
import os

from app.retrieval.dense_search import DenseSearch
from app.retrieval.bm25_store import get_bm25_search
from app.retrieval.hybrid_search import HybridSearch
from app.retrieval.parent_retriever import ParentRetriever
from app.retrieval.multimodal_retriever import MultimodalRetriever
from app.retrieval.tenant_filter import filter_results_for_tenant
from app.reranking.rerank_pipeline import RerankPipeline
from app.context_builder.context_assembler import ContextAssembler
from app.context_builder.token_optimizer import TokenOptimizer
from app.retrieval.query_boost import (
    boost_results_by_query,
    prefer_substantive_chunks,
    filter_qa_chunks,
    is_visual_query,
    is_table_metric_query,
    is_table_lookup_query,
    is_section_definition_query,
    is_list_query,
    is_requirements_list_query,
    is_counting_query,
    is_superlative_query,
    normalize_query,
)
from app.retrieval.query_analyzer import QueryAnalyzer
from app.vectorstore.collections import CollectionManager
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class RetrievalPipeline:
    """Pipeline for retrieving relevant chunks"""

    def __init__(self):
        self.bm25_search = get_bm25_search()
        self.dense_search = DenseSearch()
        self.hybrid_search = HybridSearch(bm25_search=self.bm25_search)
        self.parent_retriever = ParentRetriever()
        self.multimodal_retriever = MultimodalRetriever()
        self.rerank_pipeline = RerankPipeline()
        self.context_assembler = ContextAssembler()
        self.token_optimizer = TokenOptimizer()
        self.query_analyzer = QueryAnalyzer()

        self.top_k = int(os.getenv("TOP_K", "8"))
        self.rerank_top_k = int(os.getenv("RERANK_TOP_K", "5"))

    def retrieve(
        self,
        query: str,
        retrieval_method: str = "hybrid",
        document_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        use_reranking: bool = True,
        use_parent_context: bool = False,
        max_tokens: Optional[int] = None,
        top_k: Optional[int] = None,
        allowed_document_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Retrieve relevant chunks for a query."""
        query = normalize_query(query)
        method = os.getenv("RETRIEVAL_METHOD", retrieval_method or "hybrid")
        
        # Analyze query to determine optimal retrieval parameters
        query_analysis = self.query_analyzer.analyze_query(query)
        retrieval_config = query_analysis['retrieval_config']
        
        logger.info(f"=== RETRIEVAL PIPELINE START ===")
        logger.info(f"Query: {query}")
        logger.info(f"Method: {method}")
        logger.info(f"Query type: {query_analysis['query_type']}")
        logger.info(f"Document ID: {document_id}")
        logger.info(f"Tenant ID: {tenant_id}")
        logger.info(f"Allowed document IDs: {allowed_document_ids}")

        if allowed_document_ids is not None and not document_id and not allowed_document_ids:
            logger.warning("No allowed document IDs and no specific document - returning empty")
            return {
                "query": query,
                "results": [],
                "context": "",
                "citations": [],
                "total_results": 0,
                "retrieval_method": method,
            }

        # Use adaptive retrieval parameters based on query analysis
        candidate_count = retrieval_config['candidate_count']
        final_count = top_k or retrieval_config['final_count']
        use_parent_context = use_parent_context or retrieval_config['use_parent_context']
        
        limit = candidate_count  # Retrieve more candidates initially
        logger.info(f"Retrieval config: candidate_count={candidate_count}, final_count={final_count}, use_parent_context={use_parent_context}")
        allow_images = is_visual_query(query)
        counting_q = is_counting_query(query)
        superlative_q = is_superlative_query(query)
        list_q = is_list_query(query) or is_section_definition_query(query)
        priority_hits: List[Dict[str, Any]] = []

        results = self._retrieve_chunks(
            query, method, document_id=document_id, top_k=limit, allow_images=allow_images, tenant_id=tenant_id, allowed_document_ids=allowed_document_ids
        )
        results = filter_qa_chunks(results, allow_images=allow_images)

        if list_q:
            section_hits = self.bm25_search.search_section_context(
                query, document_id=document_id, top_k=limit + 4, tenant_id=tenant_id, allowed_document_ids=allowed_document_ids
            )
            continuation_hits = self.bm25_search.search_section_continuations(
                section_hits, document_id=document_id, top_k=1, tenant_id=tenant_id, allowed_document_ids=allowed_document_ids
            )
            requirements_q = is_requirements_list_query(query)
            canonical_section = (
                requirements_q
                and section_hits
                and section_hits[0].get("score", 0) >= 55.0
            )

            if canonical_section:
                top = section_hits[0]
                content = (top.get("content") or "").rstrip()
                needs_continuation = (
                    content
                    and not content.endswith((".", "!", "?", ";"))
                    and continuation_hits
                )
                focused_hits = [top] + (continuation_hits[:1] if needs_continuation else [])
                priority_hits.extend(focused_hits)
                results = focused_hits
            else:
                phrase_hits = self.bm25_search.search_by_phrase(
                    query, document_id=document_id, top_k=limit, tenant_id=tenant_id, allowed_document_ids=allowed_document_ids
                )
                priority_hits.extend(section_hits + continuation_hits)
                results = self._merge_retrieval_results(
                    results, section_hits + continuation_hits + phrase_hits, limit * 2
                )
            results = filter_qa_chunks(results, allow_images=allow_images)

        if counting_q:
            count_hits = self.bm25_search.search_counting_context(
                query, document_id=document_id, top_k=limit + 5, tenant_id=tenant_id, allowed_document_ids=allowed_document_ids
            )
            priority_hits.extend(count_hits)
            results = self._merge_retrieval_results(results, count_hits, limit + 5)
            results = filter_qa_chunks(results, allow_images=allow_images)

        if superlative_q:
            ranking_hits = self.bm25_search.search_superlative_context(
                query, document_id=document_id, top_k=limit, tenant_id=tenant_id, allowed_document_ids=allowed_document_ids
            )
            priority_hits.extend(ranking_hits)
            table_hits = self._search_table_chunks(
                query, document_id, limit, tenant_id, allowed_document_ids
            )
            results = self._merge_retrieval_results(
                results, ranking_hits + table_hits, limit * 2
            )
            results = filter_qa_chunks(results, allow_images=allow_images)

        if is_table_lookup_query(query):
            row_hits = self.bm25_search.search_table_rows(
                query, document_id=document_id, top_k=limit, tenant_id=tenant_id, allowed_document_ids=allowed_document_ids
            )
            results = self._merge_retrieval_results(results, row_hits, limit * 2)
            results = filter_qa_chunks(results, allow_images=allow_images)

        if is_table_metric_query(query):
            table_hits = self._search_table_chunks(
                query, document_id, limit, tenant_id, allowed_document_ids
            )
            metric_hits = self.bm25_search.search_model_metric(
                query, document_id=document_id, top_k=limit, tenant_id=tenant_id, allowed_document_ids=allowed_document_ids
            )
            results = self._merge_retrieval_results(
                results, table_hits + metric_hits, limit * 2
            )
            results = filter_qa_chunks(results, allow_images=allow_images)

        if is_visual_query(query):
            figure_hits = self.bm25_search.search_figure_caption(
                query, document_id=document_id, top_k=limit, tenant_id=tenant_id, allowed_document_ids=allowed_document_ids
            )
            image_hits = self._search_image_chunks(
                query, document_id, limit, tenant_id, allowed_document_ids
            )
            mm_hits = self._search_multimodal_chunks(
                query, document_id, limit, tenant_id, allowed_document_ids
            )
            results = self._merge_retrieval_results(
                results, figure_hits + image_hits + mm_hits, limit * 2
            )
            results = filter_qa_chunks(results, allow_images=True)

        if not results:
            results = self._phrase_fallback_search(
                query, document_id, limit, tenant_id, allowed_document_ids
            )

        if not results:
            return {
                "query": query,
                "results": [],
                "context": "",
                "citations": [],
                "total_results": 0,
                "retrieval_method": method,
            }

        results = filter_results_for_tenant(
            results, tenant_id, allowed_document_ids=allowed_document_ids
        )

        results = boost_results_by_query(query, results)

        # Reranking often drops split numbered-item / multi-section list chunks.
        skip_rerank = counting_q or list_q
        
        # For summary queries, rerank all candidates, then keep top final_count
        # For other queries, use adaptive limits
        if query_analysis['is_summary']:
            result_limit = candidate_count  # Rerank all candidates
        elif counting_q:
            result_limit = max(self.rerank_top_k + 5, limit + 5)
        elif list_q:
            result_limit = max(self.rerank_top_k + 6, limit + 4)
            if is_requirements_list_query(query) and priority_hits:
                result_limit = min(result_limit, len(priority_hits) + 1)
        elif superlative_q:
            result_limit = max(self.rerank_top_k + 2, limit)
        else:
            result_limit = candidate_count  # Rerank all candidates for better quality

        if use_reranking and not skip_rerank:
            results = self.rerank_pipeline.rerank_results(query, results, top_k=result_limit)
            results = boost_results_by_query(query, results)
            # After reranking, keep only the final_count best results
            results = results[:final_count]
        else:
            results = results[:final_count]

        if priority_hits:
            results = self._pin_priority_results(results, priority_hits, result_limit)

        results = prefer_substantive_chunks(query, results)
        results = filter_qa_chunks(results, allow_images=allow_images)

        results = filter_results_for_tenant(
            results, tenant_id, allowed_document_ids=allowed_document_ids
        )

        if use_parent_context:
            # Use sibling context enhancement for better continuity
            results = self.parent_retriever.enhance_results_with_siblings(
                results,
                include_previous=1,
                include_next=1,
                tenant_id=tenant_id
            )
            results = self._apply_document_scope(results, allowed_document_ids)

        if max_tokens and not counting_q and not list_q:
            results = self.token_optimizer.optimize_context(
                results, max_tokens, preserve_structure=False
            )

        context_data = self.context_assembler.assemble_context_with_citations(
            results, max_tokens=max_tokens
        )

        return {
            "query": query,
            "results": results,
            "context": context_data["context"],
            "citations": context_data["citations"],
            "total_results": len(results),
            "retrieval_method": method,
        }

    def _apply_document_scope(
        self,
        results: List[Dict[str, Any]],
        allowed_document_ids: Optional[List[str]],
    ) -> List[Dict[str, Any]]:
        if allowed_document_ids is None:
            return results
        allowed = set(allowed_document_ids)
        return [r for r in results if r.get("document_id") in allowed]

    def _retrieve_chunks(
        self,
        query: str,
        method: str,
        document_id: Optional[str] = None,
        top_k: Optional[int] = None,
        allow_images: bool = False,
        tenant_id: Optional[str] = None,
        allowed_document_ids: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve chunks using specified method."""
        limit = top_k or self.top_k

        if method == "full" and not allow_images:
            method = "hybrid"

        if method in ("hybrid", "full"):
            if document_id:
                self.hybrid_search.top_k = limit
            text_results = self.hybrid_search.search(query, document_id=document_id, tenant_id=tenant_id, allowed_document_ids=allowed_document_ids)
            table_results = self._search_table_chunks(
                query, document_id, limit, tenant_id, allowed_document_ids
            )
            merged = self._merge_retrieval_results(text_results, table_results, limit * 2)

            if method != "full":
                return self._apply_document_scope(merged, allowed_document_ids)

            mm_results = self.multimodal_retriever.retrieve_combined(
                query, top_k=limit, document_id=document_id, tenant_id=tenant_id
            ) if document_id else self.multimodal_retriever.retrieve_combined(
                query, top_k=limit, tenant_id=tenant_id
            )
            mm_results = self._apply_document_scope(mm_results, allowed_document_ids)

            mm_results = [
                r for r in mm_results
                if r.get("chunk_type") in ("table", "multimodal")
            ]
            return self._merge_retrieval_results(merged, mm_results, limit)

        if method == "dense":
            if document_id:
                results = self.dense_search.search_with_filter(
                    query, document_id, tenant_id=tenant_id
                )
            else:
                results = self.dense_search.search(query, limit=limit, tenant_id=tenant_id)
            return self._apply_document_scope(results, allowed_document_ids)

        if method == "bm25":
            return self.bm25_search.search(
                query, document_id=document_id, top_k=limit, exclude_image_chunks=True,
                tenant_id=tenant_id, allowed_document_ids=allowed_document_ids,
            )

        if method == "parent":
            parent_results = self.parent_retriever.retrieve_with_parent(
                query, top_k=limit, tenant_id=tenant_id
            )
            child_chunks = [r["child_chunk"] for r in parent_results]
            return self._apply_document_scope(child_chunks, allowed_document_ids)

        if method == "multimodal":
            results = self.multimodal_retriever.retrieve_combined(
                query, top_k=limit, document_id=document_id, tenant_id=tenant_id
            )
            return self._apply_document_scope(results, allowed_document_ids)

        logger.warning(f"Unknown retrieval method: {method}, using hybrid")
        return self._retrieve_chunks(
            query, "hybrid", document_id=document_id, top_k=limit, allow_images=allow_images, tenant_id=tenant_id, allowed_document_ids=allowed_document_ids
        )

    def _phrase_fallback_search(
        self,
        query: str,
        document_id: Optional[str],
        limit: int,
        tenant_id: Optional[str] = None,
        allowed_document_ids: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Directly find chunks whose text contains the query phrase."""
        phrase_hits = self.bm25_search.search_by_phrase(
            query, document_id=document_id, top_k=limit, tenant_id=tenant_id, allowed_document_ids=allowed_document_ids
        )
        if phrase_hits:
            logger.info(f"Phrase fallback found {len(phrase_hits)} text chunks")
            return phrase_hits

        tc_hits = self.bm25_search.search_table_rows(
            query, document_id=document_id, top_k=limit, tenant_id=tenant_id, allowed_document_ids=allowed_document_ids
        )
        if tc_hits:
            logger.info(f"Table-row fallback found {len(tc_hits)} chunks")
            return tc_hits

        metric_hits = self.bm25_search.search_model_metric(
            query, document_id=document_id, top_k=limit, tenant_id=tenant_id, allowed_document_ids=allowed_document_ids
        )
        if metric_hits:
            logger.info(f"Model-metric fallback found {len(metric_hits)} chunks")
            return metric_hits

        bm25_hits = self.bm25_search.search(
            query, document_id=document_id, top_k=limit * 2, exclude_image_chunks=True, tenant_id=tenant_id, allowed_document_ids=allowed_document_ids
        )
        return filter_qa_chunks(bm25_hits)

    def _search_table_chunks(
        self,
        query: str,
        document_id: Optional[str],
        limit: int,
        tenant_id: Optional[str] = None,
        allowed_document_ids: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Search the dedicated table collection in Qdrant."""
        collection = CollectionManager().get_table_collection()
        if not self.dense_search.qdrant.collection_exists(collection):
            return []

        if document_id:
            results = self.dense_search.search_with_filter(
                query,
                document_id=document_id,
                collection_name=collection,
                limit=limit,
                tenant_id=tenant_id,
            )
        else:
            results = self.dense_search.search(
                query, collection_name=collection, limit=limit, tenant_id=tenant_id
            )
        return self._apply_document_scope(results, allowed_document_ids)

    def _search_image_chunks(
        self,
        query: str,
        document_id: Optional[str],
        limit: int,
        tenant_id: Optional[str] = None,
        allowed_document_ids: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        collection = CollectionManager().get_image_collection()
        if not self.dense_search.qdrant.collection_exists(collection):
            return []
        if document_id:
            results = self.dense_search.search_with_filter(
                query, document_id=document_id, collection_name=collection, limit=limit, tenant_id=tenant_id
            )
        else:
            results = self.dense_search.search(
                query, collection_name=collection, limit=limit, tenant_id=tenant_id
            )
        return self._apply_document_scope(results, allowed_document_ids)

    def _search_multimodal_chunks(
        self,
        query: str,
        document_id: Optional[str],
        limit: int,
        tenant_id: Optional[str] = None,
        allowed_document_ids: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        collection = CollectionManager().get_multimodal_collection()
        if not self.dense_search.qdrant.collection_exists(collection):
            return []
        if document_id:
            results = self.dense_search.search_with_filter(
                query, document_id=document_id, collection_name=collection, limit=limit, tenant_id=tenant_id
            )
        else:
            results = self.dense_search.search(
                query, collection_name=collection, limit=limit, tenant_id=tenant_id
            )
        return self._apply_document_scope(results, allowed_document_ids)

    def _merge_retrieval_results(
        self,
        primary: List[Dict[str, Any]],
        secondary: List[Dict[str, Any]],
        limit: int,
    ) -> List[Dict[str, Any]]:
        """Merge and deduplicate retrieval results, keeping best score per chunk."""
        merged: Dict[str, Dict[str, Any]] = {}

        for result in primary + secondary:
            chunk_id = result.get("chunk_id")
            if not chunk_id:
                continue
            score = result.get("combined_score", result.get("score", 0))
            existing = merged.get(chunk_id)
            if not existing or score > existing.get("combined_score", existing.get("score", 0)):
                entry = dict(result)
                entry["score"] = score
                entry["combined_score"] = score
                merged[chunk_id] = entry

        results = list(merged.values())
        results.sort(key=lambda x: x.get("combined_score", x.get("score", 0)), reverse=True)
        return results[:limit]

    def _pin_priority_results(
        self,
        results: List[Dict[str, Any]],
        priority: List[Dict[str, Any]],
        limit: int,
    ) -> List[Dict[str, Any]]:
        """Keep specialist retrieval hits at the front of the context."""
        if not priority:
            return results

        pinned: Dict[str, Dict[str, Any]] = {}
        for hit in priority:
            chunk_id = hit.get("chunk_id")
            if not chunk_id:
                continue
            score = hit.get("combined_score", hit.get("score", 0))
            existing = pinned.get(chunk_id)
            if not existing or score > existing.get("combined_score", existing.get("score", 0)):
                entry = dict(hit)
                entry["score"] = score + 50.0
                entry["combined_score"] = entry["score"]
                pinned[chunk_id] = entry

        rest = [r for r in results if r.get("chunk_id") not in pinned]
        merged = list(pinned.values()) + rest
        merged.sort(key=lambda x: x.get("combined_score", x.get("score", 0)), reverse=True)
        return merged[:limit]

    def build_bm25_index(self, document_id: str, chunks: List[Dict[str, Any]]) -> bool:
        """Build BM25 index for a document."""
        logger.info(f"Building BM25 index for document: {document_id}")
        return self.bm25_search.build_index(document_id, chunks)

    def delete_bm25_index(self, document_id: str) -> bool:
        """Delete BM25 index for a document."""
        return self.bm25_search.delete_index(document_id)

    def get_retrieval_stats(self) -> Dict[str, Any]:
        """Get retrieval statistics."""
        return {"bm25_stats": self.bm25_search.get_index_stats()}
