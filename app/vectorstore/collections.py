"""
Collection management for Qdrant
"""

from typing import Dict, Any, Optional
from app.vectorstore.qdrant_client import QdrantManager
from app.utils.logger import setup_logger
import os

logger = setup_logger(__name__)


class CollectionManager:
    """Manage Qdrant collections for the RAG system"""
    
    # Collection names
    TEXT_COLLECTION = "text_chunks"
    IMAGE_COLLECTION = "image_chunks"
    TABLE_COLLECTION = "table_chunks"
    MULTIMODAL_COLLECTION = "multimodal_chunks"
    
    def __init__(self, qdrant_manager: Optional[QdrantManager] = None):
        self.qdrant = qdrant_manager or QdrantManager()
    
    def initialize_all_collections(
        self,
        vector_size: int = 1024,
        image_vector_size: Optional[int] = None,
    ) -> bool:
        """
        Initialize all required collections
        
        Args:
            vector_size: Dimension of text/table/multimodal vectors
            image_vector_size: Dimension of image vectors (CLIP, default 512)
            
        Returns:
            True if all collections initialized successfully
        """
        logger.info("Initializing all collections")

        image_size = image_vector_size or 512
        
        collections = [
            (self.TEXT_COLLECTION, vector_size),
            (self.IMAGE_COLLECTION, image_size),
            (self.TABLE_COLLECTION, vector_size),
            (self.MULTIMODAL_COLLECTION, vector_size)
        ]
        
        success = True
        for collection_name, size in collections:
            if not self.qdrant.collection_exists(collection_name):
                if not self.qdrant.create_collection(collection_name, size):
                    logger.error(f"Failed to create collection: {collection_name}")
                    success = False
            else:
                logger.info(f"Collection {collection_name} already exists")
        
        return success
    
    def get_text_collection(self) -> str:
        """Get the text chunks collection name"""
        return self.TEXT_COLLECTION
    
    def get_image_collection(self) -> str:
        """Get the image chunks collection name"""
        return self.IMAGE_COLLECTION
    
    def get_table_collection(self) -> str:
        """Get the table chunks collection name"""
        return self.TABLE_COLLECTION
    
    def get_multimodal_collection(self) -> str:
        """Get the multimodal chunks collection name"""
        return self.MULTIMODAL_COLLECTION
    
    def clear_all_collections(self) -> bool:
        """Delete all collections"""
        logger.warning("Clearing all collections")
        
        collections = [
            self.TEXT_COLLECTION,
            self.IMAGE_COLLECTION,
            self.TABLE_COLLECTION,
            self.MULTIMODAL_COLLECTION
        ]
        
        success = True
        for collection_name in collections:
            if self.qdrant.collection_exists(collection_name):
                if not self.qdrant.delete_collection(collection_name):
                    logger.error(f"Failed to delete collection: {collection_name}")
                    success = False
        
        return success
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics for all collections"""
        stats = {}
        
        collections = [
            self.TEXT_COLLECTION,
            self.IMAGE_COLLECTION,
            self.TABLE_COLLECTION,
            self.MULTIMODAL_COLLECTION
        ]
        
        for collection_name in collections:
            if self.qdrant.collection_exists(collection_name):
                info = self.qdrant.get_collection_info(collection_name)
                stats[collection_name] = info
            else:
                stats[collection_name] = None
        
        return stats


async def initialize_collections(qdrant_manager: QdrantManager) -> bool:
    """
    Initialize collections (async wrapper for startup event)
    
    Args:
        qdrant_manager: QdrantManager instance
        
    Returns:
        True if successful
    """
    from app.embeddings.embedding_factory import get_embedding_factory

    factory = get_embedding_factory()
    text_dim = factory.get_text_embedding().get_embedding_dimension()
    image_dim = factory.get_image_embedding().get_embedding_dimension()

    manager = CollectionManager(qdrant_manager)
    return manager.initialize_all_collections(vector_size=text_dim, image_vector_size=image_dim)
