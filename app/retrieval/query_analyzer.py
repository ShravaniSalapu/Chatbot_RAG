"""
Query analyzer for detecting query intent and type
"""

from typing import Dict, Any, Optional
from app.utils.logger import setup_logger
import re

logger = setup_logger(__name__)


class QueryAnalyzer:
    """Analyze query to detect intent and determine optimal retrieval strategy"""
    
    def __init__(self):
        # Summary/overview query patterns
        self.summary_patterns = [
            r'\b(tell me about|what is this|describe|explain|overview|summary|summarize)\b',
            r'\b(this document|this file|this paper|this report)\b',
            r'\b(what are the main|key points|highlights)\b',
            r'\b(give me an overview|provide an overview)\b',
            r'\b(what does this document|what does this file)\b',
            r'\b(document summary|file summary|report summary)\b',
        ]
        
        # Specific fact query patterns
        self.fact_patterns = [
            r'\b(what is|define|what are|who is|when did|where did)\b\s+\w+',  # Specific definitions
            r'\b(how does|how do)\s+\w+',  # Specific how questions
            r'\b(what is the|what are the)\s+\w+\s+\w+',  # Specific what questions
        ]
        
    def analyze_query(self, query: str) -> Dict[str, Any]:
        """
        Analyze query to determine intent and optimal retrieval parameters
        
        Args:
            query: User query
            
        Returns:
            Dictionary with analysis results
        """
        query_lower = query.lower().strip()
        
        is_summary = self._is_summary_query(query_lower)
        is_fact = self._is_fact_query(query_lower) and not is_summary
        
        # Determine retrieval parameters based on query type
        if is_summary:
            retrieval_config = {
                'candidate_count': 30,  # More candidates for summaries
                'final_count': 12,      # Keep more chunks for summaries
                'use_parent_context': True,
                'context_window': 'wide',
                'priority_sections': True
            }
        elif is_fact:
            retrieval_config = {
                'candidate_count': 15,  # Moderate for specific facts
                'final_count': 6,       # Fewer, more focused chunks
                'use_parent_context': True,
                'context_window': 'focused',
                'priority_sections': False
            }
        else:
            # General query
            retrieval_config = {
                'candidate_count': 20,
                'final_count': 8,
                'use_parent_context': True,
                'context_window': 'balanced',
                'priority_sections': False
            }
        
        analysis = {
            'query': query,
            'is_summary': is_summary,
            'is_fact': is_fact,
            'query_type': 'summary' if is_summary else ('fact' if is_fact else 'general'),
            'retrieval_config': retrieval_config
        }
        
        logger.info(f"Query analysis: {analysis}")
        return analysis
    
    def _is_summary_query(self, query: str) -> bool:
        """Check if query is asking for a summary/overview"""
        for pattern in self.summary_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                return True
        return False
    
    def _is_fact_query(self, query: str) -> bool:
        """Check if query is asking for specific facts"""
        for pattern in self.fact_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                return True
        return False
    
    def get_retrieval_params(self, query: str) -> Dict[str, Any]:
        """
        Get retrieval parameters based on query analysis
        
        Args:
            query: User query
            
        Returns:
            Dictionary with retrieval parameters
        """
        analysis = self.analyze_query(query)
        return analysis['retrieval_config']
