"""
Factory for creating embedding instances
"""

from typing import Optional
from app.embeddings.text_embedding import TextEmbedding
from app.embeddings.image_embedding import ImageEmbedding
from app.embeddings.table_embedding import TableEmbedding
from app.utils.logger import setup_logger
import os

logger = setup_logger(__name__)


class EmbeddingFactory:
    """Factory for creating embedding instances"""
    
    def __init__(self):
        self._text_embedding = None
        self._image_embedding = None
        self._table_embedding = None
    
    def get_text_embedding(self, model_name: Optional[str] = None, device: Optional[str] = None) -> TextEmbedding:
        """
        Get or create text embedding instance
        
        Args:
            model_name: Model name (uses env var if not provided)
            device: Device to use (uses env var if not provided)
            
        Returns:
            TextEmbedding instance
        """
        if self._text_embedding is None:
            model_name = model_name or os.getenv("TEXT_EMBEDDING_MODEL", "BAAI/bge-m3")
            device = device or os.getenv("EMBEDDING_DEVICE", "cpu")
            self._text_embedding = TextEmbedding(model_name=model_name, device=device)
            logger.info(f"Created text embedding with model: {model_name}")
        
        return self._text_embedding
    
    def get_image_embedding(self, model_name: Optional[str] = None, device: Optional[str] = None) -> ImageEmbedding:
        """
        Get or create image embedding instance
        
        Args:
            model_name: Model name (uses env var if not provided)
            device: Device to use (uses env var if not provided)
            
        Returns:
            ImageEmbedding instance
        """
        if self._image_embedding is None:
            model_name = model_name or os.getenv("IMAGE_EMBEDDING_MODEL", "clip-ViT-B-32")
            device = device or os.getenv("EMBEDDING_DEVICE", "cpu")
            self._image_embedding = ImageEmbedding(model_name=model_name, device=device)
            logger.info(f"Created image embedding with model: {model_name}")
        
        return self._image_embedding
    
    def get_table_embedding(self, text_embedding: Optional[TextEmbedding] = None) -> TableEmbedding:
        """
        Get or create table embedding instance
        
        Args:
            text_embedding: Text embedding instance to use (creates new if not provided)
            
        Returns:
            TableEmbedding instance
        """
        if self._table_embedding is None:
            text_emb = text_embedding or self.get_text_embedding()
            self._table_embedding = TableEmbedding(text_embedding=text_emb)
            logger.info("Created table embedding")
        
        return self._table_embedding
    
    def reset(self):
        """Reset all embedding instances"""
        self._text_embedding = None
        self._image_embedding = None
        self._table_embedding = None
        logger.info("Reset all embedding instances")


# Global factory instance
_embedding_factory = EmbeddingFactory()


def get_embedding_factory() -> EmbeddingFactory:
    """Get the global embedding factory instance"""
    return _embedding_factory
