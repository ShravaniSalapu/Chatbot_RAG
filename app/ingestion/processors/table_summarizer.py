"""
Table summarizer for generating table summaries using LLM
"""

from typing import Dict, List, Any, Optional
from app.llm.llm_client import LLMClient
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class TableSummarizer:
    """Generate summaries for tables using LLM"""
    
    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm_client = llm_client or LLMClient()
    
    def summarize_table(self, table: Dict[str, Any], context: str = "") -> str:
        """
        Generate a summary for a table
        
        Args:
            table: Table data with headers and rows
            context: Surrounding context text
            
        Returns:
            Table summary
        """
        logger.info(f"Summarizing table: {table.get('table_id', 'unknown')}")
        
        # Build prompt
        prompt = self._build_summary_prompt(table, context)
        
        try:
            summary = self.llm_client.generate_response(
                prompt=prompt,
                max_tokens=500,
                temperature=0.3
            )
            
            logger.info(f"Generated summary for table: {table.get('table_id')}")
            return summary
            
        except Exception as e:
            logger.error(f"Error generating table summary: {str(e)}")
            return self._generate_fallback_summary(table)
    
    def _build_summary_prompt(self, table: Dict[str, Any], context: str) -> str:
        """Build prompt for table summarization"""
        headers = table.get('headers', [])
        rows = table.get('rows', [])
        caption = table.get('caption', '')
        
        # Limit rows for prompt
        sample_rows = rows[:10] if len(rows) > 10 else rows
        
        prompt = f"""Please provide a concise summary of the following table.

Context: {context}

Table Caption: {caption}

Table Headers: {', '.join(headers)}

Table Data (first {len(sample_rows)} rows):
"""
        
        for i, row in enumerate(sample_rows):
            prompt += f"Row {i+1}: {', '.join(row)}\n"
        
        if len(rows) > len(sample_rows):
            prompt += f"... and {len(rows) - len(sample_rows)} more rows\n"
        
        prompt += """
Provide a summary that:
1. Describes what the table shows
2. Highlights key trends or patterns
3. Mentions important data points
4. Is concise (2-3 sentences)

Summary:"""
        
        return prompt
    
    def _generate_fallback_summary(self, table: Dict[str, Any]) -> str:
        """Generate a basic summary without LLM"""
        headers = table.get('headers', [])
        rows = table.get('rows', [])
        caption = table.get('caption', '')
        
        summary_parts = []
        
        if caption:
            summary_parts.append(f"Table: {caption}")
        
        if headers:
            summary_parts.append(f"Columns: {', '.join(headers)}")
        
        if rows:
            summary_parts.append(f"Contains {len(rows)} rows of data")
        
        return '. '.join(summary_parts) if summary_parts else "Table with no available description"
    
    def extract_key_insights(self, table: Dict[str, Any]) -> List[str]:
        """
        Extract key insights from a table
        
        Args:
            table: Table data
            
        Returns:
            List of key insights
        """
        logger.info(f"Extracting insights from table: {table.get('table_id', 'unknown')}")
        
        insights = []
        headers = table.get('headers', [])
        rows = table.get('rows', [])
        
        if not headers or not rows:
            return insights
        
        # Simple statistical insights
        try:
            # Find numeric columns
            numeric_cols = []
            for col_idx, header in enumerate(headers):
                if col_idx < len(rows[0]):
                    try:
                        # Check if first few values are numeric
                        numeric = True
                        for row in rows[:5]:
                            val = row[col_idx].replace(',', '').replace('$', '').strip()
                            if val and not val.replace('.', '').replace('-', '').isdigit():
                                numeric = False
                                break
                        if numeric:
                            numeric_cols.append((col_idx, header))
                    except (IndexError, ValueError):
                        pass
            
            # Extract insights from numeric columns
            for col_idx, header in numeric_cols:
                values = []
                for row in rows:
                    try:
                        val = float(row[col_idx].replace(',', '').replace('$', '').strip())
                        values.append(val)
                    except (ValueError, IndexError):
                        pass
                
                if values:
                    avg = sum(values) / len(values)
                    max_val = max(values)
                    min_val = min(values)
                    
                    insights.append(f"{header}: Average={avg:.2f}, Max={max_val:.2f}, Min={min_val:.2f}")
        
        except Exception as e:
            logger.warning(f"Error extracting insights: {str(e)}")
        
        return insights
    
    def batch_summarize_tables(self, tables: List[Dict[str, Any]], contexts: List[str]) -> List[str]:
        """
        Summarize multiple tables in batch
        
        Args:
            tables: List of tables
            contexts: List of context strings (one per table)
            
        Returns:
            List of summaries
        """
        logger.info(f"Batch summarizing {len(tables)} tables")
        
        summaries = []
        for i, table in enumerate(tables):
            context = contexts[i] if i < len(contexts) else ""
            summary = self.summarize_table(table, context)
            summaries.append(summary)
        
        return summaries
