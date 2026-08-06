"""
Citation builder for adding source references
"""

from typing import List, Dict, Any, Optional
from app.llm.llm_client import LLMClient
from app.llm.prompt_builder import PromptBuilder
from app.llm.citation_utils import dedupe_citations, format_source_label
from app.utils.logger import setup_logger
import re

logger = setup_logger(__name__)


class CitationBuilder:
    """Build and manage citations for responses"""
    
    def __init__(self, llm_client: Optional[LLMClient] = None, prompt_builder: Optional[PromptBuilder] = None):
        self.llm_client = llm_client or LLMClient()
        self.prompt_builder = prompt_builder or PromptBuilder()
    
    def add_citations_to_answer(
        self,
        answer: str,
        citations: List[Dict[str, Any]],
        use_llm: bool = False
    ) -> Dict[str, Any]:
        """
        Add citations to an answer
        
        Args:
            answer: Generated answer
            citations: Citation information
            use_llm: Whether to use LLM for citation placement
            
        Returns:
            Answer with citations
        """
        logger.info(f"Adding {len(citations)} citations to answer")
        
        if not citations:
            return {
                'answer': answer,
                'citations': [],
                'cited_answer': answer
            }
        
        if use_llm:
            return self._add_citations_with_llm(answer, citations)
        else:
            return self._add_citations_simple(answer, citations)
    
    def _add_citations_simple(self, answer: str, citations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Add citations using simple heuristic."""
        citations = dedupe_citations(citations, max_sources=3)
        if not citations:
            return {"answer": answer, "citations": [], "cited_answer": answer}

        citation_text = "\n\nSources:\n"
        for cit in citations:
            citation_text += f"[{cit.get('index', '?')}] {format_source_label(cit)}\n"

        cited_answer = answer + citation_text

        return {
            "answer": answer,
            "citations": citations,
            "cited_answer": cited_answer,
        }
    
    def _add_citations_with_llm(self, answer: str, citations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Add citations using LLM"""
        prompt = self.prompt_builder.build_citation_prompt(answer, citations)
        
        try:
            cited_answer = self.llm_client.generate_response(prompt=prompt)
            
            return {
                'answer': answer,
                'citations': citations,
                'cited_answer': cited_answer
            }
        except Exception as e:
            logger.error(f"Error adding citations with LLM: {str(e)}")
            return self._add_citations_simple(answer, citations)
    
    def extract_citations_from_text(self, text: str) -> List[int]:
        """
        Extract citation numbers from text
        
        Args:
            text: Text with citations
            
        Returns:
            List of citation numbers
        """
        # Find all [1], [2], etc. patterns
        pattern = r'\[(\d+)\]'
        matches = re.findall(pattern, text)
        return [int(m) for m in matches]
    
    def build_citation_objects(self, citations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Build standardized citation objects
        
        Args:
            citations: Raw citation data
            
        Returns:
            Standardized citation objects
        """
        standardized = []
        
        for i, cit in enumerate(citations):
            standardized.append({
                'index': i + 1,
                'chunk_id': cit.get('chunk_id') or '',
                'document_id': cit.get('document_id') or '',
                'filename': (
                    cit.get('filename')
                    or (cit.get('metadata') or {}).get('filename')
                    or 'Unknown'
                ),
                'page_number': cit.get('page_number') or (cit.get('metadata') or {}).get('page_number'),
                'heading': cit.get('heading') or (cit.get('metadata') or {}).get('heading'),
                'score': cit.get('score'),
                'snippet': (cit.get('snippet') or cit.get('content') or '')[:200]
            })
        
        return standardized
    
    def format_citations_for_display(self, citations: List[Dict[str, Any]]) -> str:
        """
        Format citations for display
        
        Args:
            citations: Citation objects
            
        Returns:
            Formatted citation string
        """
        if not citations:
            return "No sources cited."
        
        lines = ["Sources:"]
        for cit in citations:
            parts = [f"[{cit['index']}]"]
            if cit.get('filename'):
                parts.append(cit['filename'])
            if cit.get('page_number'):
                parts.append(f"Page {cit['page_number']}")
            if cit.get('heading'):
                parts.append(f"- {cit['heading']}")
            lines.append(" ".join(parts))
        
        return "\n".join(lines)
    
    def validate_citations(self, answer: str, citations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate that citations in answer match available citations
        
        Args:
            answer: Answer with citations
            citations: Available citations
            
        Returns:
            Validation results
        """
        cited_numbers = self.extract_citations_from_text(answer)
        available_numbers = list(range(1, len(citations) + 1))
        
        invalid_citations = [n for n in cited_numbers if n not in available_numbers]
        missing_citations = [n for n in available_numbers if n not in cited_numbers]
        
        return {
            'valid': len(invalid_citations) == 0,
            'cited_numbers': cited_numbers,
            'invalid_citations': invalid_citations,
            'missing_citations': missing_citations
        }
