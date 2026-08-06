"""
Text embedding generation using sentence-transformers
"""

from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer
import torch
from app.utils.logger import setup_logger
import os

logger = setup_logger(__name__)


class TextEmbedding:
    """Generate text embeddings using BGE-M3 or similar models"""
    
    def __init__(self, model_name: str = "BAAI/bge-m3", device: Optional[str] = None):
        self.model_name = model_name
        self.device = device or self._get_device()
        self.model = None
        self._load_model()
    
    def _get_device(self) -> str:
        """Determine the device to use"""
        if torch.cuda.is_available():
            return "cuda"
        elif os.getenv("EMBEDDING_DEVICE") == "cpu":
            return "cpu"
        return "cpu"
    
    def _load_model(self):
        """Load the embedding model"""
        logger.info(f"Loading text embedding model: {self.model_name}")
        try:
            self.model = SentenceTransformer(self.model_name, device=self.device)
            logger.info("Text embedding model loaded successfully")
        except Exception as e:
            logger.error(f"Error loading text embedding model: {str(e)}")
            # Fallback to a simpler model
            logger.info("Falling back to all-MiniLM-L6-v2")
            self.model_name = "sentence-transformers/all-MiniLM-L6-v2"
            self.model = SentenceTransformer(self.model_name, device=self.device)
    
    def embed(self, text: str) -> List[float]:
        """
        Generate embedding for a single text
        
        Args:
            text: Input text
            
        Returns:
            Embedding vector as list of floats
        """
        if not self.model:
            raise RuntimeError("Model not loaded")
        
        try:
            embedding = self.model.encode(
                text,
                convert_to_numpy=True,
                show_progress_bar=False,
                normalize_embeddings=True,
            )
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Error generating embedding: {str(e)}")
            raise
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts
        
        Args:
            texts: List of input texts
            
        Returns:
            List of embedding vectors
        """
        if not self.model:
            raise RuntimeError("Model not loaded")
        
        try:
            batch_size = int(os.getenv("EMBEDDING_BATCH_SIZE", "32"))
            embeddings = self.model.encode(
                texts,
                batch_size=batch_size,
                convert_to_numpy=True,
                show_progress_bar=False,
                normalize_embeddings=True,
            )
            return [emb.tolist() for emb in embeddings]
        except Exception as e:
            logger.error(f"Error generating batch embeddings: {str(e)}")
            raise
    
    def embed_query(self, query: str) -> List[float]:
        """
        Generate embedding for a search query (may use different encoding)
        
        Args:
            query: Search query text
            
        Returns:
            Embedding vector
        """
        # For BGE-M3, we might want to add instructions for queries
        if "bge" in self.model_name.lower():
            # Add instruction for better retrieval
            query = f"Represent this sentence for searching relevant passages: {query}"
        
        return self.embed(query)
    
    def get_embedding_dimension(self) -> int:
        """Get the dimension of the embedding vectors"""
        if self.model:
            return self.model.get_sentence_embedding_dimension()
        return 768  # Default for many models
