"""
Table context builder for preserving table information
"""

from typing import List, Dict, Any, Optional
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class TableContextBuilder:
    """Build context around table data"""
    
    def __init__(self):
        pass
    
    def build_table_context(self, table_results: List[Dict[str, Any]], include_summary: bool = True) -> str:
        """
        Build context from table results
        
        Args:
            table_results: Table search results
            include_summary: Whether to include table summaries
            
        Returns:
            Table context string
        """
        logger.info(f"Building table context from {len(table_results)} results")
        
        if not table_results:
            return ""
        
        context_parts = []
        
        for result in table_results:
            content = result.get('content', '')
            metadata = result.get('metadata', {})
            
            table_part = f"Table Data:\n{content}"
            
            if include_summary and metadata.get('summary'):
                table_part += f"\n\nSummary: {metadata['summary']}"
            
            if metadata.get('context_before'):
                table_part += f"\n\nContext: {metadata['context_before'][:200]}"
            
            context_parts.append(table_part)
        
        return "\n\n---\n\n".join(context_parts)
    
    def build_table_with_headers(self, table_results: List[Dict[str, Any]]) -> str:
        """
        Build context with table headers and structure
        
        Args:
            table_results: Table search results
            
        Returns:
            Table context with headers
        """
        logger.info("Building table context with headers")
        
        context_parts = []
        
        for result in table_results:
            metadata = result.get('metadata', {})
            headers = metadata.get('headers', [])
            rows = metadata.get('rows', [])
            
            if headers:
                table_part = f"Table Headers: {', '.join(headers)}\n\n"
                
                if rows:
                    table_part += "Table Data:\n"
                    for row in rows[:5]:  # Limit to first 5 rows
                        table_part += f"  {', '.join(row)}\n"
                    
                    if len(rows) > 5:
                        table_part += f"  ... and {len(rows) - 5} more rows\n"
                
                context_parts.append(table_part)
        
        return "\n\n---\n\n".join(context_parts)
    
    def build_table_comparison(self, table_results: List[Dict[str, Any]]) -> str:
        """
        Build context for comparing multiple tables
        
        Args:
            table_results: Table search results
            
        Returns:
            Comparison context
        """
        logger.info("Building table comparison context")
        
        if len(table_results) < 2:
            return self.build_table_context(table_results)
        
        comparison_parts = []
        
        for idx, result in enumerate(table_results):
            metadata = result.get('metadata', {})
            comparison_parts.append(f"Table {idx + 1}:")
            comparison_parts.append(result.get('content', ''))
            
            if metadata.get('summary'):
                comparison_parts.append(f"Summary: {metadata['summary']}")
        
        return "\n\n".join(comparison_parts)
    
    def extract_table_insights(self, table_results: List[Dict[str, Any]]) -> List[str]:
        """
        Extract insights from table results
        
        Args:
            table_results: Table search results
            
        Returns:
            List of insights
        """
        insights = []
        
        for result in table_results:
            metadata = result.get('metadata', {})
            
            if metadata.get('summary'):
                insights.append(metadata['summary'])
            
            if metadata.get('insights'):
                insights.extend(metadata['insights'])
        
        return insights
