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
        self.alpha = 0.6  # Weight for dense search (0-1) - prioritize semantic relevance
        self.top_k = int(os.getenv("TOP_K", "5"))
        self.use_rrf = os.getenv("USE_RRF", "false").lower() == "true"
    
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
        logger.info(f"=== HYBRID SEARCH START ===")
        logger.info(f"Query: {query}")
        logger.info(f"Document ID: {document_id}")
        logger.info(f"Tenant ID: {tenant_id}")
        logger.info(f"Alpha: {alpha if alpha is not None else self.alpha}")
        
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
        
        # Normalize and combine scores using improved method
        if self.use_rrf:
            combined_results = self.reciprocal_rank_fusion(dense_results, bm25_results)
            # Add combined_score field for compatibility
            for result in combined_results:
                result['combined_score'] = result['rrf_score']
        else:
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
        """Combine and re-rank results from both methods using improved normalization"""
        # Create a map of chunk_id to results
        result_map = {}
        
        # Process dense results with min-max normalization
        if dense_results:
            dense_scores = [r['score'] for r in dense_results]
            min_dense, max_dense = min(dense_scores), max(dense_scores)
            dense_range = max_dense - min_dense if max_dense != min_dense else 1.0
            
            for result in dense_results:
                chunk_id = result['chunk_id']
                # Min-max normalization
                normalized_dense = (result['score'] - min_dense) / dense_range
                
                if chunk_id not in result_map:
                    result_map[chunk_id] = {
                        'chunk_id': chunk_id,
                        'document_id': result['document_id'],
                        'content': result['content'],
                        'chunk_type': result['chunk_type'],
                        'metadata': result['metadata'],
                        'filename': result.get('filename'),
                        'page_number': result.get('page_number'),
                        'heading': result.get('heading'),
                        'dense_score': normalized_dense,
                        'bm25_score': 0.0,
                        'combined_score': 0.0
                    }
                else:
                    result_map[chunk_id]['dense_score'] = normalized_dense
        
        # Process BM25 results with min-max normalization
        if bm25_results:
            bm25_scores = [r['score'] for r in bm25_results]
            min_bm25, max_bm25 = min(bm25_scores), max(bm25_scores)
            bm25_range = max_bm25 - min_bm25 if max_bm25 != min_bm25 else 1.0
            
            for result in bm25_results:
                chunk_id = result['chunk_id']
                # Min-max normalization
                normalized_bm25 = (result['score'] - min_bm25) / bm25_range
                
                if chunk_id not in result_map:
                    result_map[chunk_id] = {
                        'chunk_id': chunk_id,
                        'document_id': result['document_id'],
                        'content': result['content'],
                        'chunk_type': result['chunk_type'],
                        'metadata': result['metadata'],
                        'filename': result.get('filename'),
                        'page_number': result.get('page_number'),
                        'heading': result.get('heading'),
                        'dense_score': 0.0,
                        'bm25_score': normalized_bm25,
                        'combined_score': 0.0
                    }
                else:
                    result_map[chunk_id]['bm25_score'] = normalized_bm25
                    # Preserve additional metadata from BM25 if not present
                    if not result_map[chunk_id].get('filename'):
                        result_map[chunk_id]['filename'] = result.get('filename')
                    if not result_map[chunk_id].get('page_number'):
                        result_map[chunk_id]['page_number'] = result.get('page_number')
                    if not result_map[chunk_id].get('heading'):
                        result_map[chunk_id]['heading'] = result.get('heading')
        
        # Calculate combined scores with weighted average
        for chunk_id, result in result_map.items():
            # Use weighted average favoring semantic relevance (dense search)
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
