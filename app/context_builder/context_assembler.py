"""
Context assembler for merging retrieved content
"""

from typing import List, Dict, Any, Optional
from app.llm.citation_utils import dedupe_citations, format_source_label
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class ContextAssembler:
    """Assemble context from retrieved chunks"""
    
    def __init__(self):
        pass
    
    def assemble_context(self, results: List[Dict[str, Any]], max_tokens: Optional[int] = None) -> str:
        """
        Assemble context from search results
        
        Args:
            results: Search results
            max_tokens: Maximum tokens in context
            
        Returns:
            Assembled context string
        """
        logger.info(f"Assembling context from {len(results)} results")
        
        if not results:
            return ""
        
        # Sort results by score
        sorted_results = sorted(results, key=lambda x: x.get('score', 0), reverse=True)
        
        # Build context
        context_parts = []
        total_tokens = 0
        
        for result in sorted_results:
            content = result.get('content', '')
            tokens = self._estimate_tokens(content)
            
            if max_tokens and total_tokens + tokens > max_tokens:
                # Truncate if needed
                remaining_tokens = max_tokens - total_tokens
                if remaining_tokens > 0:
                    truncated = self._truncate_to_tokens(content, remaining_tokens)
                    context_parts.append(truncated)
                break
            
            context_parts.append(content)
            total_tokens += tokens
        
        context = "\n\n---\n\n".join(context_parts)
        
        logger.info(f"Assembled context with {total_tokens} tokens")
        return context
    
    def assemble_context_with_citations(self, results: List[Dict[str, Any]], max_tokens: Optional[int] = None) -> Dict[str, Any]:
        """
        Assemble context with citation information, organized by sections
        
        Args:
            results: Search results
            max_tokens: Maximum tokens in context
            
        Returns:
            Dictionary with context and citations
        """
        logger.info(f"Assembling context with citations from {len(results)} results")
        
        # Group results by document and section for better organization
        grouped_results = self._group_by_section(results)
        
        context_parts = []
        total_tokens = 0
        citation_index = 1

        raw_citations = []
        
        # Process each section group
        for section_key, section_results in grouped_results.items():
            section_context = []
            section_heading = section_key[1] if section_key[1] else "General Content"
            document_name = section_key[0] if section_key[0] else "Unknown Document"
            
            # Add section header
            section_header = f"## SECTION: {section_heading} (from {document_name})"
            section_context.append(section_header)
            
            for result in section_results:
                content = result.get('content', '')
                tokens = self._estimate_tokens(content)

                if max_tokens and total_tokens + tokens > max_tokens:
                    remaining_tokens = max_tokens - total_tokens
                    if remaining_tokens > 0:
                        truncated = self._truncate_to_tokens(content, remaining_tokens)
                        section_context.append(f"[{citation_index}] {truncated}")
                        
                        meta = result.get('metadata') or {}
                        raw_citations.append({
                            'index': citation_index,
                            'chunk_id': result.get('chunk_id'),
                            'document_id': result.get('document_id'),
                            'filename': result.get('filename') or meta.get('filename') or document_name,
                            'page_number': result.get('page_number') or meta.get('page_number'),
                            'heading': result.get('heading') or meta.get('heading') or section_heading,
                            'chunk_type': result.get('chunk_type') or meta.get('chunk_type'),
                            'score': result.get('score'),
                            'content': content,
                            'snippet': content[:200],
                        })
                        citation_index += 1
                    break

                section_context.append(f"[{citation_index}] {content}")
                total_tokens += tokens

                meta = result.get('metadata') or {}
                raw_citations.append({
                    'index': citation_index,
                    'chunk_id': result.get('chunk_id'),
                    'document_id': result.get('document_id'),
                    'filename': result.get('filename') or meta.get('filename') or document_name,
                    'page_number': result.get('page_number') or meta.get('page_number'),
                    'heading': result.get('heading') or meta.get('heading') or section_heading,
                    'chunk_type': result.get('chunk_type') or meta.get('chunk_type'),
                    'score': result.get('score'),
                    'content': content,
                    'snippet': content[:200],
                })
                citation_index += 1
            
            # Add section to context if it has content
            if len(section_context) > 1:  # More than just the header
                context_parts.append("\n".join(section_context))

        citations = dedupe_citations(
            raw_citations,
            max_sources=int(__import__("os").getenv("MAX_CITATION_SOURCES", "6")),
        )
        # Keep full context for the LLM — citation dedup is for display only.

        context = "\n\n---\n\n".join(context_parts)
        
        return {
            'context': context,
            'citations': citations,
            'total_tokens': total_tokens
        }
    
    def _group_by_section(self, results: List[Dict[str, Any]]) -> Dict[tuple, List[Dict[str, Any]]]:
        """
        Group results by document and section for organized context
        
        Args:
            results: Search results
            
        Returns:
            Dictionary mapping (document_name, section_heading) to results
        """
        grouped = {}
        
        for result in results:
            meta = result.get('metadata') or {}
            document_name = result.get('filename') or meta.get('filename') or 'Unknown Document'
            section_heading = result.get('heading') or meta.get('heading') or 'General Content'
            
            key = (document_name, section_heading)
            
            if key not in grouped:
                grouped[key] = []
            
            grouped[key].append(result)
        
        # Sort results within each group by score
        for key in grouped:
            grouped[key].sort(key=lambda x: x.get('score', 0), reverse=True)
        
        return grouped
    
    def assemble_by_document(self, results: List[Dict[str, Any]]) -> Dict[str, str]:
        """
        Assemble context grouped by document
        
        Args:
            results: Search results
            
        Returns:
            Dictionary mapping document IDs to context
        """
        logger.info("Assembling context grouped by document")
        
        document_contexts = {}
        
        for result in results:
            doc_id = result.get('document_id')
            if not doc_id:
                continue
            
            if doc_id not in document_contexts:
                document_contexts[doc_id] = []
            
            document_contexts[doc_id].append(result.get('content', ''))
        
        # Join content for each document
        assembled = {}
        for doc_id, contents in document_contexts.items():
            assembled[doc_id] = "\n\n---\n\n".join(contents)
        
        return assembled
    
    def assemble_by_section(self, results: List[Dict[str, Any]]) -> Dict[str, str]:
        """
        Assemble context grouped by section
        
        Args:
            results: Search results
            
        Returns:
            Dictionary mapping section IDs to context
        """
        logger.info("Assembling context grouped by section")
        
        section_contexts = {}
        
        for result in results:
            section_id = result.get('metadata', {}).get('section_id')
            if not section_id:
                continue
            
            if section_id not in section_contexts:
                section_contexts[section_id] = []
            
            section_contexts[section_id].append(result.get('content', ''))
        
        assembled = {}
        for section_id, contents in section_contexts.items():
            assembled[section_id] = "\n\n---\n\n".join(contents)
        
        return assembled
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count"""
        return int(len(text.split()) / 0.75)
    
    def _truncate_to_tokens(self, text: str, max_tokens: int) -> str:
        """Truncate text to approximately max_tokens"""
        words = text.split()
        target_words = int(max_tokens * 0.75)
        if len(words) <= target_words:
            return text
        truncated = ' '.join(words[:target_words])
        return truncated + "\n... [context truncated]"
