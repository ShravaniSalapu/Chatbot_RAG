"""
Image embedding generation using CLIP or similar models
"""

from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer
import torch
from app.utils.logger import setup_logger
import os
import base64
from PIL import Image
import io

logger = setup_logger(__name__)

# Map HuggingFace-style names to sentence-transformers CLIP aliases
CLIP_MODEL_ALIASES = {
    "openai/clip-vit-base-patch32": "clip-ViT-B-32",
    "sentence-transformers/clip-vit-b-32": "clip-ViT-B-32",
}


def resolve_clip_model_name(model_name: str) -> str:
    normalized = model_name.strip()
    return CLIP_MODEL_ALIASES.get(normalized.lower(), normalized)


class ImageEmbedding:
    """Generate image embeddings using CLIP or similar models"""
    
    def __init__(self, model_name: str = "clip-ViT-B-32", device: Optional[str] = None):
        self.model_name = resolve_clip_model_name(model_name)
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
        logger.info(f"Loading image embedding model: {self.model_name}")
        try:
            # Use CLIP model from sentence-transformers
            self.model = SentenceTransformer(self.model_name, device=self.device)
            logger.info("Image embedding model loaded successfully")
        except Exception as e:
            logger.error(f"Error loading image embedding model: {str(e)}")
            # Fallback
            logger.info("Falling back to basic image-text model")
            self.model_name = "sentence-transformers/clip-ViT-B-32"
            self.model = SentenceTransformer(self.model_name, device=self.device)
    
    def embed_from_path(self, image_path: str) -> List[float]:
        """
        Generate embedding for an image from file path
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Embedding vector as list of floats
        """
        if not self.model:
            raise RuntimeError("Model not loaded")
        
        try:
            image = Image.open(image_path)
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            embedding = self.model.encode(
                image, convert_to_numpy=True, show_progress_bar=False, normalize_embeddings=True
            )
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Error generating image embedding from path: {str(e)}")
            raise
    
    def embed_from_bytes(self, image_bytes: bytes) -> List[float]:
        """
        Generate embedding for an image from bytes
        
        Args:
            image_bytes: Image file as bytes
            
        Returns:
            Embedding vector as list of floats
        """
        if not self.model:
            raise RuntimeError("Model not loaded")
        
        try:
            image = Image.open(io.BytesIO(image_bytes))
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            embedding = self.model.encode(
                image, convert_to_numpy=True, show_progress_bar=False, normalize_embeddings=True
            )
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Error generating image embedding from bytes: {str(e)}")
            raise
    
    def embed_from_base64(self, base64_string: str) -> List[float]:
        """
        Generate embedding for an image from base64 string
        
        Args:
            base64_string: Base64 encoded image
            
        Returns:
            Embedding vector as list of floats
        """
        try:
            image_bytes = base64.b64decode(base64_string)
            return self.embed_from_bytes(image_bytes)
        except Exception as e:
            logger.error(f"Error generating image embedding from base64: {str(e)}")
            raise
    
    def embed_batch_from_paths(self, image_paths: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple images from file paths
        
        Args:
            image_paths: List of image file paths
            
        Returns:
            List of embedding vectors
        """
        if not self.model:
            raise RuntimeError("Model not loaded")
        
        try:
            images = []
            for path in image_paths:
                image = Image.open(path)
                if image.mode != 'RGB':
                    image = image.convert('RGB')
                images.append(image)
            
            embeddings = self.model.encode(images, convert_to_numpy=True)
            return [emb.tolist() for emb in embeddings]
        except Exception as e:
            logger.error(f"Error generating batch image embeddings: {str(e)}")
            raise
    
    def embed_text_description(self, description: str) -> List[float]:
        """
        Generate embedding for an image description (text-to-image space)
        
        Args:
            description: Text description of the image
            
        Returns:
            Embedding vector in the same space as images
        """
        if not self.model:
            raise RuntimeError("Model not loaded")
        
        try:
            embedding = self.model.encode(
                description, convert_to_numpy=True, show_progress_bar=False, normalize_embeddings=True
            )
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Error generating text description embedding: {str(e)}")
            raise
    
    def get_embedding_dimension(self) -> int:
        """Get the dimension of the embedding vectors"""
        if self.model:
            return self.model.get_sentence_embedding_dimension()
        return 512  # Default for CLIP ViT-B-32
