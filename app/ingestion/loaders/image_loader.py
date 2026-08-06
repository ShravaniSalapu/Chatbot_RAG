"""
Image document loader
"""

from typing import Dict, Any
from pathlib import Path
from PIL import Image
import base64
import io
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class ImageLoader:
    """Loader for image documents"""
    
    def __init__(self):
        self.supported_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp']
    
    def load(self, file_path: str) -> Dict[str, Any]:
        """
        Load an image file and extract its content
        
        Args:
            file_path: Path to the image file
            
        Returns:
            Dictionary containing image content and metadata
        """
        logger.info(f"Loading image file: {file_path}")
        
        try:
            img = Image.open(file_path)
            
            # Convert to RGB if necessary
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Get image bytes
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='PNG')
            img_bytes.seek(0)
            
            # Base64 encode
            img_base64 = base64.b64encode(img_bytes.getvalue()).decode('utf-8')
            
            # Extract metadata
            metadata = self._extract_metadata(img, file_path)
            
            return {
                'image_bytes': img_base64,
                'format': img.format,
                'mode': img.mode,
                'size': img.size,
                'width': img.width,
                'height': img.height,
                'metadata': metadata
            }
            
        except Exception as e:
            logger.error(f"Error loading image file {file_path}: {str(e)}")
            raise
    
    def load_from_bytes(self, file_bytes: bytes) -> Dict[str, Any]:
        """
        Load an image from bytes
        
        Args:
            file_bytes: Image file as bytes
            
        Returns:
            Dictionary containing image content and metadata
        """
        logger.info("Loading image from bytes")
        
        try:
            img = Image.open(io.BytesIO(file_bytes))
            
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            img_bytes_io = io.BytesIO()
            img.save(img_bytes_io, format='PNG')
            img_bytes_io.seek(0)
            
            img_base64 = base64.b64encode(img_bytes_io.getvalue()).decode('utf-8')
            
            metadata = self._extract_metadata(img)
            
            return {
                'image_bytes': img_base64,
                'format': img.format,
                'mode': img.mode,
                'size': img.size,
                'width': img.width,
                'height': img.height,
                'metadata': metadata
            }
            
        except Exception as e:
            logger.error(f"Error loading image from bytes: {str(e)}")
            raise
    
    def _extract_metadata(self, img: Image.Image, file_path: str = None) -> Dict[str, Any]:
        """Extract metadata from image"""
        try:
            metadata = {
                'format': img.format,
                'mode': img.mode,
                'size': img.size,
                'width': img.width,
                'height': img.height
            }
            
            # Extract EXIF data if available
            if hasattr(img, '_getexif') and img._getexif() is not None:
                exif = img._getexif()
                metadata['exif'] = exif
            
            return metadata
        except Exception as e:
            logger.warning(f"Could not extract image metadata: {str(e)}")
            return {}
    
    def is_supported(self, file_path: str) -> bool:
        """Check if file is supported"""
        return Path(file_path).suffix.lower() in self.supported_extensions
