"""
Section chunker for section-based chunking
"""

from typing import Dict, List, Any, Optional
import uuid
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class SectionChunker:
    """Implement section-based chunking using document structure"""
    
    def __init__(self, max_chunk_size: int = 512):
        self.max_chunk_size = max_chunk_size
    
    def chunk(self, text: str, document_id: str, sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Create chunks based on document sections
        
        Args:
            text: Input text
            document_id: Document identifier
            sections: List of document sections
            
        Returns:
            List of section-based chunks
        """
        logger.info(f"Creating section-based chunks for document: {document_id}")
        
        chunks = []
        
        if not sections:
            # Fall back to simple chunking
            return self._simple_chunk(text, document_id)
        
        for section in sections:
            section_content = section.get('content', '')
            section_id = section.get('section_id', '')
            heading = section.get('heading', '')
            
            if not section_content:
                continue
            
            # Split section into chunks if too large
            section_chunks = self._split_section(section_content, self.max_chunk_size)
            
            for chunk_idx, chunk_text in enumerate(section_chunks):
                chunk_obj = {
                    'chunk_id': str(uuid.uuid4()),
                    'document_id': document_id,
                    'chunk_type': 'section',
                    'content': chunk_text,
                    'token_count': self._estimate_tokens(chunk_text),
                    'character_count': len(chunk_text),
                    'section_id': section_id,
                    'heading': heading,
                    'parent_chunk_id': None,
                    'child_chunk_ids': []
                }
                chunks.append(chunk_obj)
        
        logger.info(f"Created {len(chunks)} section-based chunks")
        return chunks
    
    def _split_section(self, section_text: str, max_size: int) -> List[str]:
        """Split a section into multiple chunks if needed"""
        if len(section_text) <= max_size:
            return [section_text]
        
        chunks = []
        words = section_text.split()
        
        current_chunk = []
        current_length = 0
        
        for word in words:
            word_length = len(word)
            
            if current_length + word_length + 1 > max_size and current_chunk:
                chunks.append(' '.join(current_chunk))
                current_chunk = [word]
                current_length = word_length
            else:
                current_chunk.append(word)
                current_length += word_length + 1
        
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks
    
    def _simple_chunk(self, text: str, document_id: str) -> List[Dict[str, Any]]:
        """Simple chunking as fallback"""
        chunks = []
        words = text.split()
        
        current_chunk = []
        current_length = 0
        
        for word in words:
            word_length = len(word)
            
            if current_length + word_length + 1 > self.max_chunk_size and current_chunk:
                chunk_text = ' '.join(current_chunk)
                chunk_obj = {
                    'chunk_id': str(uuid.uuid4()),
                    'document_id': document_id,
                    'chunk_type': 'section',
                    'content': chunk_text,
                    'token_count': self._estimate_tokens(chunk_text),
                    'character_count': len(chunk_text),
                    'section_id': None,
                    'heading': None,
                    'parent_chunk_id': None,
                    'child_chunk_ids': []
                }
                chunks.append(chunk_obj)
                current_chunk = [word]
                current_length = word_length
            else:
                current_chunk.append(word)
                current_length += word_length + 1
        
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            chunk_obj = {
                'chunk_id': str(uuid.uuid4()),
                'document_id': document_id,
                'chunk_type': 'section',
                'content': chunk_text,
                'token_count': self._estimate_tokens(chunk_text),
                'character_count': len(chunk_text),
                'section_id': None,
                'heading': None,
                'parent_chunk_id': None,
                'child_chunk_ids': []
            }
            chunks.append(chunk_obj)
        
        return chunks
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count"""
        word_count = len(text.split())
        return int(word_count / 0.75)
    
    def get_chunks_by_section(self, chunks: List[Dict[str, Any]], section_id: str) -> List[Dict[str, Any]]:
        """Get all chunks belonging to a section"""
        return [chunk for chunk in chunks if chunk.get('section_id') == section_id]
