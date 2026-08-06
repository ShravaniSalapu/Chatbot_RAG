"""
Hybrid search combining dense and sparse retrieval
"""

from typing import List, Dict, Any, Optional
from app.retrieval.dense_search import DenseSearch
from app.retrieval.bm25_store import get_bm25_search
from app.utils.logger import setup_logger
import os

logger = setup_logger(__name__)


class HybridSearch:
    """Hybrid search combining dense and sparse retrieval"""
    
    def __init__(self, dense_search: Optional[DenseSearch] = None, bm25_search=None):
        self.dense_search = dense_search or DenseSearch()
        self.bm25_search = bm25_search or get_bm25_search()
        self.alpha = 0.5  # Weight for dense search (0-1)
        self.top_k = int(os.getenv("TOP_K", "5"))
    
    def search(self, query: str, document_id: Optional[str] = None, alpha: Optional[float] = None, tenant_id: Optional[str] = None, allowed_document_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Perform hybrid search
        
        Args:
            query: Search query
            document_id: Optional document ID filter
            alpha: Weight for dense search (0-1)
            
        Returns:
            Combined and ranked results
        """
        logger.info(f"Performing hybrid search for query: {query}")
        
        alpha = alpha if alpha is not None else self.alpha
        
        # Get dense results
        if document_id:
            dense_results = self.dense_search.search_with_filter(
                query, document_id, tenant_id=tenant_id
            )
        else:
            dense_results = self.dense_search.search(query, limit=self.top_k * 2, tenant_id=tenant_id)
            if allowed_document_ids is not None:
                allowed = set(allowed_document_ids)
                dense_results = [r for r in dense_results if r.get("document_id") in allowed]
        
        # Get BM25 results (exclude image caption chunks from Q&A search)
        bm25_results = self.bm25_search.search(
            query, document_id, top_k=self.top_k * 2, exclude_image_chunks=True, tenant_id=tenant_id,
            allowed_document_ids=allowed_document_ids,
        )
        
        # Normalize and combine scores
        combined_results = self._combine_results(dense_results, bm25_results, alpha)
        
        # Sort by combined score
        combined_results.sort(key=lambda x: x['combined_score'], reverse=True)

        combined_results = [
            r for r in combined_results if r.get("chunk_type") != "image"
        ]

        if allowed_document_ids is not None:
            allowed = set(allowed_document_ids)
            combined_results = [r for r in combined_results if r.get("document_id") in allowed]
        
        logger.info(f"Found {len(combined_results)} hybrid results")
        return combined_results[:self.top_k]
    
    def _combine_results(self, dense_results: List[Dict[str, Any]], bm25_results: List[Dict[str, Any]], alpha: float) -> List[Dict[str, Any]]:
        """Combine and re-rank results from both methods"""
        # Create a map of chunk_id to results
        result_map = {}
        
        # Process dense results
        if dense_results:
            max_dense_score = max(r['score'] for r in dense_results) if dense_results else 1.0
            for result in dense_results:
                chunk_id = result['chunk_id']
                normalized_dense = result['score'] / max_dense_score if max_dense_score > 0 else 0
                
                if chunk_id not in result_map:
                    result_map[chunk_id] = {
                        'chunk_id': chunk_id,
                        'document_id': result['document_id'],
                        'content': result['content'],
                        'chunk_type': result['chunk_type'],
                        'metadata': result['metadata'],
                        'dense_score': normalized_dense,
                        'bm25_score': 0.0,
                        'combined_score': 0.0
                    }
                else:
                    result_map[chunk_id]['dense_score'] = normalized_dense
        
        # Process BM25 results
        if bm25_results:
            max_bm25_score = max(r['score'] for r in bm25_results) if bm25_results else 1.0
            for result in bm25_results:
                chunk_id = result['chunk_id']
                normalized_bm25 = result['score'] / max_bm25_score if max_bm25_score > 0 else 0
                
                if chunk_id not in result_map:
                    result_map[chunk_id] = {
                        'chunk_id': chunk_id,
                        'document_id': result['document_id'],
                        'content': result['content'],
                        'chunk_type': result['chunk_type'],
                        'metadata': result['metadata'],
                        'dense_score': 0.0,
                        'bm25_score': normalized_bm25,
                        'combined_score': 0.0
                    }
                else:
                    result_map[chunk_id]['bm25_score'] = normalized_bm25
        
        # Calculate combined scores
        for chunk_id, result in result_map.items():
            result['combined_score'] = alpha * result['dense_score'] + (1 - alpha) * result['bm25_score']
        
        return list(result_map.values())
    
    def reciprocal_rank_fusion(self, dense_results: List[Dict[str, Any]], bm25_results: List[Dict[str, Any]], k: int = 60) -> List[Dict[str, Any]]:
        """
        Reciprocal Rank Fusion (RRF) for combining results
        
        Args:
            dense_results: Dense search results
            bm25_results: BM25 search results
            k: RRF constant
            
        Returns:
            Combined results using RRF
        """
        result_map = {}
        
        # Process dense results
        for rank, result in enumerate(dense_results):
            chunk_id = result['chunk_id']
            score = 1.0 / (k + rank + 1)
            
            if chunk_id not in result_map:
                result_map[chunk_id] = {
                    'chunk_id': chunk_id,
                    'document_id': result['document_id'],
                    'content': result['content'],
                    'chunk_type': result['chunk_type'],
                    'metadata': result['metadata'],
                    'rrf_score': score
                }
            else:
                result_map[chunk_id]['rrf_score'] += score
        
        # Process BM25 results
        for rank, result in enumerate(bm25_results):
            chunk_id = result['chunk_id']
            score = 1.0 / (k + rank + 1)
            
            if chunk_id not in result_map:
                result_map[chunk_id] = {
                    'chunk_id': chunk_id,
                    'document_id': result['document_id'],
                    'content': result['content'],
                    'chunk_type': result['chunk_type'],
                    'metadata': result['metadata'],
                    'rrf_score': score
                }
            else:
                result_map[chunk_id]['rrf_score'] += score
        
        # Sort by RRF score
        results = list(result_map.values())
        results.sort(key=lambda x: x['rrf_score'], reverse=True)
        
        return results
