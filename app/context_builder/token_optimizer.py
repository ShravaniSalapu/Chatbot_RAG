"""
Token optimizer for managing context length
"""

from typing import List, Dict, Any, Optional
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class TokenOptimizer:
    """Optimize token usage in context"""
    
    def __init__(self):
        pass
    
    def optimize_context(self, results: List[Dict[str, Any]], max_tokens: int, preserve_structure: bool = True) -> List[Dict[str, Any]]:
        """
        Optimize context to fit within max_tokens
        
        Args:
            results: Search results
            max_tokens: Maximum tokens allowed
            preserve_structure: Whether to preserve document/section structure
            
        Returns:
            Optimized results
        """
        logger.info(f"Optimizing context to fit {max_tokens} tokens")
        
        if not results:
            return results
        
        # Sort by score
        sorted_results = sorted(results, key=lambda x: x.get('score', 0), reverse=True)
        
        if preserve_structure:
            return self._optimize_with_structure(sorted_results, max_tokens)
        else:
            return self._optimize_simple(sorted_results, max_tokens)
    
    def _optimize_simple(self, results: List[Dict[str, Any]], max_tokens: int) -> List[Dict[str, Any]]:
        """Simple optimization by score"""
        optimized = []
        total_tokens = 0
        
        for result in results:
            content = result.get('content', '')
            tokens = self._estimate_tokens(content)
            remaining = max_tokens - total_tokens

            if remaining <= 0:
                break

            if tokens > remaining:
                if not optimized:
                    entry = dict(result)
                    entry['content'] = self.truncate_content(content, remaining)
                    optimized.append(entry)
                    total_tokens += self._estimate_tokens(entry['content'])
                continue

            optimized.append(result)
            total_tokens += tokens
        
        if not optimized and results:
            top = dict(results[0])
            top['content'] = self.truncate_content(top.get('content', ''), max_tokens)
            optimized = [top]
            total_tokens = self._estimate_tokens(top['content'])

        logger.info(f"Optimized from {len(results)} to {len(optimized)} results ({total_tokens} tokens)")
        return optimized
    
    def _optimize_with_structure(self, results: List[Dict[str, Any]], max_tokens: int) -> List[Dict[str, Any]]:
        """Optimize while preserving document structure"""
        # Group by document
        document_groups = {}
        for result in results:
            doc_id = result.get('document_id', 'unknown')
            if doc_id not in document_groups:
                document_groups[doc_id] = []
            document_groups[doc_id].append(result)
        
        # Calculate tokens per document
        doc_tokens = {}
        for doc_id, doc_results in document_groups.items():
            doc_tokens[doc_id] = sum(self._estimate_tokens(r.get('content', '')) for r in doc_results)
        
        # Select documents greedily
        optimized = []
        total_tokens = 0
        
        # Sort documents by total score
        sorted_docs = sorted(
            document_groups.items(),
            key=lambda x: sum(r.get('score', 0) for r in x[1]),
            reverse=True
        )
        
        for doc_id, doc_results in sorted_docs:
            doc_token_count = doc_tokens[doc_id]
            
            if total_tokens + doc_token_count <= max_tokens:
                optimized.extend(doc_results)
                total_tokens += doc_token_count
            else:
                # Try to add partial results from this document
                remaining_tokens = max_tokens - total_tokens
                if remaining_tokens > 0:
                    partial = self._add_partial_results(doc_results, remaining_tokens)
                    optimized.extend(partial)
                    total_tokens += sum(self._estimate_tokens(r.get('content', '')) for r in partial)
                break
        
        logger.info(f"Optimized from {len(results)} to {len(optimized)} results ({total_tokens} tokens)")
        return optimized
    
    def _add_partial_results(self, results: List[Dict[str, Any]], max_tokens: int) -> List[Dict[str, Any]]:
        """Add partial results from a document"""
        partial = []
        total_tokens = 0
        
        for result in results:
            content = result.get('content', '')
            tokens = self._estimate_tokens(content)
            remaining = max_tokens - total_tokens

            if remaining <= 0:
                break

            if tokens > remaining:
                if not partial:
                    entry = dict(result)
                    entry['content'] = self.truncate_content(content, remaining)
                    partial.append(entry)
                break

            partial.append(result)
            total_tokens += tokens
        
        return partial
    
    def truncate_content(self, content: str, max_tokens: int) -> str:
        """
        Truncate content to fit max_tokens
        
        Args:
            content: Content to truncate
            max_tokens: Maximum tokens
            
        Returns:
            Truncated content
        """
        words = content.split()
        target_words = int(max_tokens * 0.75)
        
        if len(words) <= target_words:
            return content
        
        truncated = ' '.join(words[:target_words])
        return truncated + "... [truncated]"
    
    def prioritize_by_type(self, results: List[Dict[str, Any]], type_priority: List[str]) -> List[Dict[str, Any]]:
        """
        Prioritize results by chunk type
        
        Args:
            results: Search results
            type_priority: List of chunk types in priority order
            
        Returns:
            Reordered results
        """
        logger.info(f"Prioritizing by type: {type_priority}")
        
        # Group by type
        type_groups = {}
        for result in results:
            chunk_type = result.get('chunk_type', 'text')
            if chunk_type not in type_groups:
                type_groups[chunk_type] = []
            type_groups[chunk_type].append(result)
        
        # Reorder by priority
        prioritized = []
        for chunk_type in type_priority:
            if chunk_type in type_groups:
                prioritized.extend(type_groups[chunk_type])
        
        # Add any remaining types
        for chunk_type, group in type_groups.items():
            if chunk_type not in type_priority:
                prioritized.extend(group)
        
        return prioritized
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count"""
        return int(len(text.split()) / 0.75)
    
    def calculate_context_stats(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate statistics about context
        
        Args:
            results: Search results
            
        Returns:
            Statistics dictionary
        """
        total_tokens = sum(self._estimate_tokens(r.get('content', '')) for r in results)
        
        type_counts = {}
        for result in results:
            chunk_type = result.get('chunk_type', 'text')
            type_counts[chunk_type] = type_counts.get(chunk_type, 0) + 1
        
        document_counts = {}
        for result in results:
            doc_id = result.get('document_id', 'unknown')
            document_counts[doc_id] = document_counts.get(doc_id, 0) + 1
        
        return {
            'total_results': len(results),
            'total_tokens': total_tokens,
            'type_distribution': type_counts,
            'document_distribution': document_counts
        }
