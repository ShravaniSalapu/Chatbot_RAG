"""
Table embedding generation using text embeddings on table summaries
"""

from typing import List, Dict, Any, Optional
from app.embeddings.text_embedding import TextEmbedding
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class TableEmbedding:
    """Generate embeddings for tables using their summaries and context"""
    
    def __init__(self, text_embedding: Optional[TextEmbedding] = None):
        self.text_embedding = text_embedding or TextEmbedding()
    
    def embed_table(self, table: Dict[str, Any]) -> List[float]:
        """
        Generate embedding for a table
        
        Args:
            table: Table data with summary and context
            
        Returns:
            Embedding vector
        """
        # Create a text representation of the table
        table_text = self._table_to_text(table)
        
        # Generate embedding using text embedding model
        return self.text_embedding.embed(table_text)
    
    def embed_batch(self, tables: List[Dict[str, Any]]) -> List[List[float]]:
        """
        Generate embeddings for multiple tables
        
        Args:
            tables: List of table data
            
        Returns:
            List of embedding vectors
        """
        table_texts = [self._table_to_text(table) for table in tables]
        return self.text_embedding.embed_batch(table_texts)
    
    def _table_to_text(self, table: Dict[str, Any]) -> str:
        """
        Convert table data to text representation
        
        Args:
            table: Table data
            
        Returns:
            Text representation
        """
        parts = []
        
        # Add summary if available
        if table.get('summary'):
            parts.append(f"Summary: {table['summary']}")

        if table.get('text_representation'):
            parts.append(table['text_representation'])
        
        # Add headers
        headers = table.get('headers', [])
        if headers:
            parts.append(f"Columns: {', '.join(headers)}")
        
        # Add context
        if table.get('context_before'):
            parts.append(f"Context: {table['context_before'][:200]}")
        
        # Add caption
        if table.get('caption'):
            parts.append(f"Caption: {table['caption']}")
        
        return ' '.join(parts) if parts else "Table data"
    
    def embed_table_with_structure(self, table: Dict[str, Any]) -> List[float]:
        """
        Generate embedding that captures table structure
        
        Args:
            table: Table data
            
        Returns:
            Embedding vector
        """
        parts = []
        
        # Add structural information
        headers = table.get('headers', [])
        rows = table.get('rows', [])
        
        if headers:
            parts.append(f"Table with {len(headers)} columns: {', '.join(headers)}")
        
        if rows:
            parts.append(f"Contains {len(rows)} rows")
        
        # Add sample data
        if rows and headers:
            sample_rows = rows[:3]
            for i, row in enumerate(sample_rows):
                row_text = ' | '.join(row)
                parts.append(f"Row {i+1}: {row_text}")
        
        # Add summary and context
        if table.get('summary'):
            parts.append(table['summary'])
        
        if table.get('context_before'):
            parts.append(table['context_before'][:200])
        
        table_text = ' '.join(parts)
        return self.text_embedding.embed(table_text)
    
    def get_embedding_dimension(self) -> int:
        """Get the dimension of the embedding vectors"""
        return self.text_embedding.get_embedding_dimension()
