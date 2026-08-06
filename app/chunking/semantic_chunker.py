"""
Semantic chunker for meaning-based chunking
"""

from typing import Dict, List, Any, Optional
import uuid
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class SemanticChunker:
    """Implement semantic chunking based on sentence boundaries and meaning"""
    
    def __init__(self, chunk_size: int = 512, overlap: int = 50):
        self.chunk_size = chunk_size
        self.overlap = overlap
    
    def chunk(self, text: str, document_id: str) -> List[Dict[str, Any]]:
        """
        Create semantic chunks from text
        
        Args:
            text: Input text
            document_id: Document identifier
            
        Returns:
            List of semantic chunks
        """
        logger.info(f"Creating semantic chunks for document: {document_id}")
        
        chunks = []
        
        # Split into sentences
        sentences = self._split_into_sentences(text)
        
        # Group sentences into chunks
        current_chunk = []
        current_length = 0
        
        for sentence in sentences:
            sentence_length = len(sentence)
            
            if current_length + sentence_length > self.chunk_size and current_chunk:
                # Create chunk
                chunk_text = ' '.join(current_chunk)
                chunk_obj = {
                    'chunk_id': str(uuid.uuid4()),
                    'document_id': document_id,
                    'chunk_type': 'semantic',
                    'content': chunk_text,
                    'token_count': self._estimate_tokens(chunk_text),
                    'character_count': len(chunk_text),
                    'parent_chunk_id': None,
                    'child_chunk_ids': []
                }
                chunks.append(chunk_obj)
                
                # Add overlap
                overlap_sentences = self._get_overlap_sentences(current_chunk, sentences)
                current_chunk = overlap_sentences
                current_length = sum(len(s) for s in current_chunk)
            else:
                current_chunk.append(sentence)
                current_length += sentence_length
        
        # Add final chunk
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            chunk_obj = {
                'chunk_id': str(uuid.uuid4()),
                'document_id': document_id,
                'chunk_type': 'semantic',
                'content': chunk_text,
                'token_count': self._estimate_tokens(chunk_text),
                'character_count': len(chunk_text),
                'parent_chunk_id': None,
                'child_chunk_ids': []
            }
            chunks.append(chunk_obj)
        
        logger.info(f"Created {len(chunks)} semantic chunks")
        return chunks
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences"""
        import re
        
        # Simple sentence splitting
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        # Filter out empty sentences
        sentences = [s.strip() for s in sentences if s.strip()]
        
        return sentences
    
    def _get_overlap_sentences(self, current_chunk: List[str], all_sentences: List[str]) -> List[str]:
        """Get overlap sentences from current chunk"""
        if self.overlap == 0:
            return []
        
        # Get last few sentences based on overlap
        overlap_count = max(1, self.overlap // 50)  # Rough estimate
        return current_chunk[-overlap_count:] if len(current_chunk) > overlap_count else current_chunk
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count"""
        word_count = len(text.split())
        return int(word_count / 0.75)
    
    def chunk_with_embeddings(self, text: str, document_id: str, embedding_model) -> List[Dict[str, Any]]:
        """
        Create semantic chunks using embeddings for better boundary detection
        
        Args:
            text: Input text
            document_id: Document identifier
            embedding_model: Embedding model for similarity calculation
            
        Returns:
            List of semantic chunks with embedding-based boundaries
        """
        logger.info(f"Creating semantic chunks with embeddings for document: {document_id}")
        
        # This is a placeholder for embedding-based semantic chunking
        # In production, you would use embeddings to find natural boundaries
        
        # For now, fall back to basic semantic chunking
        return self.chunk(text, document_id)
