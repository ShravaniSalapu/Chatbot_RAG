"""
Reranking pipeline for improving retrieval quality
"""

from typing import List, Dict, Any, Optional
from app.reranking.bge_reranker import get_bge_reranker
from app.utils.logger import setup_logger
import os

logger = setup_logger(__name__)


class RerankPipeline:
    """Pipeline for reranking search results"""
    
    def __init__(self, reranker=None):
        self.reranker = reranker or get_bge_reranker()
        self.rerank_top_k = int(os.getenv("RERANK_TOP_K", "3"))
    
    def rerank_results(self, query: str, results: List[Dict[str, Any]], top_k: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Rerank search results
        
        Args:
            query: Search query
            results: Search results to rerank
            top_k: Number of results to return
            
        Returns:
            Reranked results
        """
        logger.info(f"Reranking pipeline processing {len(results)} results")
        
        if not results:
            return results
        
        top_k = top_k or self.rerank_top_k
        
        # Rerank using BGE
        reranked = self.reranker.rerank(query, results, top_k=len(results))
        
        # Return top_k results
        return reranked[:top_k]
    
    def rerank_with_diversity(self, query: str, results: List[Dict[str, Any]], top_k: int = 5, diversity_lambda: float = 0.5) -> List[Dict[str, Any]]:
        """
        Rerank with diversity (MMR - Maximal Marginal Relevance)
        
        Args:
            query: Search query
            results: Search results
            top_k: Number of results to return
            diversity_lambda: Trade-off between relevance and diversity (0-1)
            
        Returns:
            Diversified reranked results
        """
        logger.info(f"Reranking with diversity (lambda={diversity_lambda})")
        
        if not results:
            return results
        
        # First, rerank by relevance
        reranked = self.reranker.rerank(query, results, top_k=len(results))
        
        # Apply MMR for diversity
        diversified = self._mmr(reranked, query, top_k, diversity_lambda)
        
        return diversified
    
    def _mmr(self, results: List[Dict[str, Any]], query: str, k: int, lambda_param: float) -> List[Dict[str, Any]]:
        """
        Maximal Marginal Relevance algorithm
        
        Args:
            results: Reranked results
            query: Search query
            k: Number of results to select
            lambda_param: Trade-off parameter
            
        Returns:
            Diversified results
        """
        if not results or k <= 0:
            return results
        
        selected = []
        remaining = results.copy()
        
        # Select first result (highest relevance)
        if remaining:
            selected.append(remaining.pop(0))
        
        # Select remaining results using MMR
        while len(selected) < k and remaining:
            best_idx = 0
            best_score = -float('inf')
            
            for i, candidate in enumerate(remaining):
                # Relevance score
                relevance = candidate.get('rerank_score', candidate.get('score', 0))
                
                # Diversity score (minimum similarity to selected)
                diversity = self._compute_diversity(candidate, selected)
                
                # MMR score
                mmr_score = lambda_param * relevance - (1 - lambda_param) * diversity
                
                if mmr_score > best_score:
                    best_score = mmr_score
                    best_idx = i
            
            selected.append(remaining.pop(best_idx))
        
        return selected
    
    def _compute_diversity(self, candidate: Dict[str, Any], selected: List[Dict[str, Any]]) -> float:
        """Compute diversity score (maximum similarity to selected items)"""
        if not selected:
            return 0.0
        
        max_similarity = 0.0
        
        candidate_text = candidate.get('content', '').lower()
        
        for item in selected:
            selected_text = item.get('content', '').lower()
            
            # Simple Jaccard similarity
            candidate_words = set(candidate_text.split())
            selected_words = set(selected_text.split())
            
            if candidate_words and selected_words:
                intersection = candidate_words & selected_words
                union = candidate_words | selected_words
                similarity = len(intersection) / len(union) if union else 0.0
                max_similarity = max(max_similarity, similarity)
        
        return max_similarity
    
    def rerank_by_document(self, query: str, results: List[Dict[str, Any]], max_per_document: int = 2) -> List[Dict[str, Any]]:
        """
        Rerank ensuring diversity across documents
        
        Args:
            query: Search query
            results: Search results
            max_per_document: Maximum results per document
            
        Returns:
            Reranked results with document diversity
        """
        logger.info(f"Reranking with document diversity (max {max_per_document} per document)")
        
        # Group by document
        document_groups = {}
        for result in results:
            doc_id = result.get('document_id')
            if doc_id not in document_groups:
                document_groups[doc_id] = []
            document_groups[doc_id].append(result)
        
        # Rerank within each document
        for doc_id, doc_results in document_groups.items():
            document_groups[doc_id] = self.reranker.rerank(query, doc_results, top_k=len(doc_results))
        
        # Interleave results from different documents
        final_results = []
        doc_ids = list(document_groups.keys())
        idx = 0
        
        while len(final_results) < len(results) and any(document_groups[doc_id] for doc_id in doc_ids):
            for doc_id in doc_ids:
                if document_groups[doc_id] and len([r for r in final_results if r.get('document_id') == doc_id]) < max_per_document:
                    final_results.append(document_groups[doc_id].pop(0))
            
            idx += 1
        
        return final_results
