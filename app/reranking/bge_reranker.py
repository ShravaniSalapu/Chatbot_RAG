"""
BGE reranker for reranking search results
"""

from typing import List, Dict, Any, Optional
from sentence_transformers import CrossEncoder
import torch
from app.utils.logger import setup_logger
import os

logger = setup_logger(__name__)

_reranker_instance: Optional["BGEReranker"] = None


def get_bge_reranker() -> "BGEReranker":
    """Return the process-wide BGE reranker instance."""
    global _reranker_instance
    if _reranker_instance is None:
        _reranker_instance = BGEReranker()
    return _reranker_instance


class BGEReranker:
    """Reranker using BGE cross-encoder model"""
    
    def __init__(self, model_name: str = "BAAI/bge-reranker-base", device: Optional[str] = None):
        self.model_name = model_name
        self.device = device or self._get_device()
        self.model = None
        self._load_model()
    
    def _get_device(self) -> str:
        """Determine the device to use"""
        if torch.cuda.is_available():
            return "cuda"
        elif os.getenv("EMBEDDING_DEVICE") == "cpu":
            return "cpu"
        return "cpu"
    
    def _load_model(self):
        """Load the reranker model"""
        logger.info(f"Loading reranker model: {self.model_name}")
        try:
            self.model = CrossEncoder(self.model_name, device=self.device)
            logger.info("Reranker model loaded successfully")
        except Exception as e:
            logger.error(f"Error loading reranker model: {str(e)}")
            # Fallback to a simpler model
            logger.info("Falling back to ms-marco-MiniLM-L-6-v2")
            self.model_name = "cross-encoder/ms-marco-MiniLM-L-6-v2"
            self.model = CrossEncoder(self.model_name, device=self.device)
    
    def rerank(self, query: str, results: List[Dict[str, Any]], top_k: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Rerank search results
        
        Args:
            query: Search query
            results: List of search results
            top_k: Number of top results to return
            
        Returns:
            Reranked results
        """
        logger.info(f"Reranking {len(results)} results")
        
        if not results:
            return results
        
        # Prepare pairs for reranking
        pairs = [[query, result['content']] for result in results]
        
        # Compute scores
        try:
            scores = self.model.predict(pairs)
        except Exception as e:
            logger.error(f"Error computing rerank scores: {str(e)}")
            # Return original results if reranking fails
            return results
        
        # Add scores to results
        for i, result in enumerate(results):
            result['rerank_score'] = float(scores[i])
        
        # Sort by rerank score
        reranked = sorted(results, key=lambda x: x['rerank_score'], reverse=True)
        
        # Return top_k results
        if top_k:
            reranked = reranked[:top_k]
        
        logger.info(f"Reranked to {len(reranked)} results")
        return reranked
    
    def rerank_with_original_score(self, query: str, results: List[Dict[str, Any]], alpha: float = 0.7, top_k: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Rerank combining original and rerank scores
        
        Args:
            query: Search query
            results: List of search results with original scores
            alpha: Weight for rerank score (0-1)
            top_k: Number of top results to return
            
        Returns:
            Reranked results with combined scores
        """
        logger.info(f"Reranking with combined scores (alpha={alpha})")
        
        if not results:
            return results
        
        # Get rerank scores
        pairs = [[query, result['content']] for result in results]
        
        try:
            rerank_scores = self.model.predict(pairs)
        except Exception as e:
            logger.error(f"Error computing rerank scores: {str(e)}")
            return results
        
        # Normalize original scores
        original_scores = [r.get('score', 0) for r in results]
        max_original = max(original_scores) if original_scores else 1.0
        normalized_original = [s / max_original if max_original > 0 else 0 for s in original_scores]
        
        # Normalize rerank scores
        max_rerank = max(rerank_scores) if rerank_scores else 1.0
        normalized_rerank = [s / max_rerank if max_rerank > 0 else 0 for s in rerank_scores]
        
        # Combine scores
        for i, result in enumerate(results):
            result['rerank_score'] = float(rerank_scores[i])
            result['combined_score'] = alpha * normalized_rerank[i] + (1 - alpha) * normalized_original[i]
        
        # Sort by combined score
        reranked = sorted(results, key=lambda x: x['combined_score'], reverse=True)
        
        if top_k:
            reranked = reranked[:top_k]
        
        return reranked
