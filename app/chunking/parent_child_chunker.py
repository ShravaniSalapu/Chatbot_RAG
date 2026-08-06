"""
Parent-child chunker for hierarchical chunking strategy
"""

from typing import Dict, List, Any, Optional
import uuid
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class ParentChildChunker:
    """Implement parent-child chunking strategy"""
    
    def __init__(self, parent_chunk_size: int = 2048, child_chunk_size: int = 512, overlap: int = 50):
        self.parent_chunk_size = parent_chunk_size
        self.child_chunk_size = child_chunk_size
        self.overlap = overlap
    
    def chunk(self, text: str, document_id: str) -> List[Dict[str, Any]]:
        """
        Create parent-child chunks from text
        
        Args:
            text: Input text
            document_id: Document identifier
            
        Returns:
            List of parent and child chunks
        """
        logger.info(f"Creating parent-child chunks for document: {document_id}")
        
        chunks = []
        
        # Create parent chunks
        parent_chunks = self._create_parent_chunks(text)
        
        # Create child chunks from each parent
        for parent_idx, parent_chunk in enumerate(parent_chunks):
            parent_id = str(uuid.uuid4())
            
            # Create parent chunk object
            parent_chunk_obj = {
                'chunk_id': parent_id,
                'document_id': document_id,
                'chunk_type': 'parent',
                'content': parent_chunk,
                'token_count': self._estimate_tokens(parent_chunk),
                'character_count': len(parent_chunk),
                'parent_chunk_id': None,
                'child_chunk_ids': []
            }
            
            # Create child chunks
            child_chunks = self._create_child_chunks(parent_chunk)
            child_ids = []
            
            for child_chunk in child_chunks:
                child_id = str(uuid.uuid4())
                child_ids.append(child_id)
                
                child_chunk_obj = {
                    'chunk_id': child_id,
                    'document_id': document_id,
                    'chunk_type': 'child',
                    'content': child_chunk,
                    'token_count': self._estimate_tokens(child_chunk),
                    'character_count': len(child_chunk),
                    'parent_chunk_id': parent_id,
                    'child_chunk_ids': []
                }
                
                chunks.append(child_chunk_obj)
            
            parent_chunk_obj['child_chunk_ids'] = child_ids
            chunks.append(parent_chunk_obj)
        
        logger.info(f"Created {len(chunks)} chunks ({len(parent_chunks)} parent, {len(chunks) - len(parent_chunks)} child)")
        return chunks
    
    def _create_parent_chunks(self, text: str) -> List[str]:
        """Create parent chunks from text"""
        parent_chunks = []
        words = text.split()
        
        current_chunk = []
        current_length = 0
        
        for word in words:
            word_length = len(word)
            
            if current_length + word_length + 1 > self.parent_chunk_size and current_chunk:
                parent_chunks.append(' '.join(current_chunk))
                current_chunk = [word]
                current_length = word_length
            else:
                current_chunk.append(word)
                current_length += word_length + 1
        
        if current_chunk:
            parent_chunks.append(' '.join(current_chunk))
        
        return parent_chunks
    
    def _create_child_chunks(self, parent_text: str) -> List[str]:
        """Create child chunks from parent text"""
        child_chunks = []
        words = parent_text.split()
        
        current_chunk = []
        current_length = 0
        
        for word in words:
            word_length = len(word)
            
            if current_length + word_length + 1 > self.child_chunk_size and current_chunk:
                child_chunks.append(' '.join(current_chunk))
                # Add overlap
                overlap_words = words[max(0, len(current_chunk) - self.overlap):]
                current_chunk = overlap_words
                current_length = sum(len(w) + 1 for w in current_chunk)
            else:
                current_chunk.append(word)
                current_length += word_length + 1
        
        if current_chunk:
            child_chunks.append(' '.join(current_chunk))
        
        return child_chunks
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count (roughly 0.75 words per token)"""
        word_count = len(text.split())
        return int(word_count / 0.75)
    
    def get_parent_for_child(self, chunks: List[Dict[str, Any]], child_id: str) -> Optional[Dict[str, Any]]:
        """Get parent chunk for a given child chunk"""
        for chunk in chunks:
            if chunk['chunk_id'] == child_id:
                parent_id = chunk.get('parent_chunk_id')
                if parent_id:
                    for parent in chunks:
                        if parent['chunk_id'] == parent_id:
                            return parent
        return None
    
    def get_children_for_parent(self, chunks: List[Dict[str, Any]], parent_id: str) -> List[Dict[str, Any]]:
        """Get all child chunks for a given parent chunk"""
        children = []
        for chunk in chunks:
            if chunk.get('parent_chunk_id') == parent_id:
                children.append(chunk)
        return children
