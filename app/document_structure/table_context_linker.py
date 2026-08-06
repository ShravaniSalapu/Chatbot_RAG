"""
Table context linker for preserving context around tables
"""

from typing import Dict, List, Any, Optional
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class TableContextLinker:
    """Link tables with their surrounding context"""
    
    def __init__(self, context_lines: int = 3):
        self.context_lines = context_lines
    
    def link_table_context(self, tables: List[Dict[str, Any]], text: str) -> List[Dict[str, Any]]:
        """
        Link tables with their surrounding context
        
        Args:
            tables: List of tables
            text: Full document text
            
        Returns:
            List of tables with context
        """
        logger.info("Linking table context")
        
        lines = text.split('\n')
        
        for table in tables:
            position = self._resolve_line_position(table, len(lines))
            
            # Extract context
            context_before = self._extract_context_before(lines, position)
            context_after = self._extract_context_after(lines, position)
            
            table['context_before'] = context_before
            table['context_after'] = context_after
            table['full_context'] = context_before + '\n' + context_after
        
        logger.info(f"Linked context for {len(tables)} tables")
        return tables
    
    def _resolve_line_position(self, table: Dict[str, Any], total_lines: int) -> int:
        """Estimate line position from page/slide/index metadata."""
        page_number = table.get("page_number") or table.get("slide_number")
        if page_number:
            return self._estimate_position(int(page_number), total_lines)

        table_index = table.get("table_index")
        if table_index is not None:
            return min(int(table_index) * 5, max(total_lines - 1, 0))

        return 0

    def _estimate_position(self, page_number: int, total_lines: int) -> int:
        """Estimate line position from page number"""
        if page_number <= 0 or total_lines <= 0:
            return 0
        lines_per_page = max(total_lines // page_number, 1)
        return min(page_number * lines_per_page, max(total_lines - 1, 0))
    
    def _extract_context_before(self, lines: List[str], position: int) -> str:
        """Extract context before a position"""
        start = max(0, position - self.context_lines)
        context_lines = lines[start:position]
        return '\n'.join(context_lines)
    
    def _extract_context_after(self, lines: List[str], position: int) -> str:
        """Extract context after a position"""
        end = min(len(lines), position + self.context_lines + 1)
        context_lines = lines[position:end]
        return '\n'.join(context_lines)
    
    def find_table_heading(self, table: Dict[str, Any], headings: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Find the heading that introduces a table
        
        Args:
            table: Table dictionary
            headings: List of headings
            
        Returns:
            Heading dictionary or None
        """
        table_position = table.get('position', 0)
        
        # Find the closest heading before the table
        closest_heading = None
        min_distance = float('inf')
        
        for heading in headings:
            heading_position = heading.get('position', 0)
            if heading_position <= table_position:
                distance = table_position - heading_position
                if distance < min_distance:
                    min_distance = distance
                    closest_heading = heading
        
        return closest_heading
    
    def extract_table_description(self, table: Dict[str, Any], context: str) -> str:
        """
        Extract a description of the table from context
        
        Args:
            table: Table dictionary
            context: Context text
            
        Returns:
            Description string
        """
        # Look for sentences that mention the table
        sentences = context.split('.')
        
        description_sentences = []
        for sentence in sentences:
            sentence = sentence.strip()
            if any(keyword in sentence.lower() for keyword in ['table', 'shows', 'displays', 'presents']):
                description_sentences.append(sentence)
        
        if description_sentences:
            return '. '.join(description_sentences[:2])
        
        return context[:200]  # Fallback to first 200 characters
    
    def link_related_tables(self, tables: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """
        Find tables that are related to each other
        
        Args:
            tables: List of tables
            
        Returns:
            Dictionary mapping table IDs to related table IDs
        """
        logger.info("Finding related tables")
        
        relations = {}
        
        for i, table1 in enumerate(tables):
            table1_id = table1.get('table_id', f"table_{i}")
            related = []
            
            for j, table2 in enumerate(tables):
                if i == j:
                    continue
                
                table2_id = table2.get('table_id', f"table_{j}")
                
                # Check if tables are related
                if self._are_tables_related(table1, table2):
                    related.append(table2_id)
            
            relations[table1_id] = related
        
        return relations
    
    def _are_tables_related(self, table1: Dict[str, Any], table2: Dict[str, Any]) -> bool:
        """Check if two tables are related"""
        # Check if they're on the same page
        if table1.get('page_number') == table2.get('page_number'):
            return True
        
        # Check if they have similar headers
        headers1 = table1.get('headers', [])
        headers2 = table2.get('headers', [])
        
        if headers1 and headers2:
            common_headers = set(headers1) & set(headers2)
            if len(common_headers) > len(headers1) * 0.5:
                return True
        
        return False
    
    def build_table_summary(self, table: Dict[str, Any]) -> str:
        """
        Build a summary of a table
        
        Args:
            table: Table dictionary
            
        Returns:
            Summary string
        """
        headers = table.get('headers', [])
        rows = table.get('rows', [])
        
        summary_parts = []
        
        if headers:
            summary_parts.append(f"Table with columns: {', '.join(headers)}")
        
        if rows:
            summary_parts.append(f"Contains {len(rows)} rows")
        
        # Add context if available
        if table.get('context_before'):
            summary_parts.append(f"Context: {table['context_before'][:100]}")
        
        return '. '.join(summary_parts)
