"""
OCR parser for extracting text from images and scanned documents
"""

from typing import Dict, List, Any, Optional
from pathlib import Path
import base64
import io
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class OCRParser:
    """Parser for OCR text extraction supporting Tesseract, EasyOCR, and PaddleOCR"""
    
    def __init__(self, ocr_engine: str = "auto"):
        """
        Initialize OCR parser with specified engine
        
        Args:
            ocr_engine: OCR engine to use ('tesseract', 'easyocr', 'paddleocr', 'auto')
        """
        self.ocr_engine = ocr_engine
        self.easyocr_reader = None
        self.paddleocr_reader = None
        self.tesseract_available = False
        
        # Initialize available OCR engines
        self._initialize_engines(ocr_engine)
    
    def _initialize_engines(self, ocr_engine: str):
        """Initialize available OCR engines"""
        # Try EasyOCR
        try:
            import easyocr
            self.easyocr_reader = easyocr.Reader(['en'], gpu=False)
            logger.info("EasyOCR initialized successfully")
        except ImportError:
            logger.warning("EasyOCR not available")
        
        # Try PaddleOCR
        try:
            from paddleocr import PaddleOCR
            try:
                self.paddleocr_reader = PaddleOCR(lang="en")
            except (TypeError, ValueError):
                # Older PaddleOCR versions used different constructor args
                self.paddleocr_reader = PaddleOCR(use_angle_cls=True, lang="en", use_gpu=False)
            logger.info("PaddleOCR initialized successfully")
        except ImportError:
            logger.warning("PaddleOCR not available")
        except Exception as exc:
            logger.warning(f"PaddleOCR initialization failed: {exc}")
        
        # Check Tesseract
        try:
            import pytesseract
            pytesseract.get_tesseract_version()
            self.tesseract_available = True
            logger.info("Tesseract available")
        except Exception as e:
            logger.warning(f"Tesseract not available: {str(e)}")
        
        # Select engine based on preference and availability
        if ocr_engine == "auto":
            # Auto-select best available
            if self.paddleocr_reader:
                self.active_engine = "paddleocr"
            elif self.easyocr_reader:
                self.active_engine = "easyocr"
            elif self.tesseract_available:
                self.active_engine = "tesseract"
            else:
                self.active_engine = None
                logger.error("No OCR engine available")
        else:
            # Use specified engine if available
            if ocr_engine == "paddleocr" and self.paddleocr_reader:
                self.active_engine = "paddleocr"
            elif ocr_engine == "easyocr" and self.easyocr_reader:
                self.active_engine = "easyocr"
            elif ocr_engine == "tesseract" and self.tesseract_available:
                self.active_engine = "tesseract"
            else:
                logger.warning(f"Requested OCR engine {ocr_engine} not available, falling back")
                self._initialize_engines("auto")
        
        logger.info(f"Active OCR engine: {self.active_engine}")
    
    def parse_image(self, image_path: str) -> Dict[str, Any]:
        """
        Extract text from an image using OCR
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Dictionary containing extracted text and metadata
        """
        logger.info(f"Performing OCR on image: {image_path} using {self.active_engine}")
        
        if not self.active_engine:
            return {
                'success': False,
                'text': '',
                'error': 'No OCR engine available'
            }
        
        try:
            if self.active_engine == "paddleocr":
                return self._ocr_with_paddleocr(image_path)
            elif self.active_engine == "easyocr":
                return self._ocr_with_easyocr(image_path)
            elif self.active_engine == "tesseract":
                return self._ocr_with_tesseract(image_path)
            else:
                return {
                    'success': False,
                    'text': '',
                    'error': 'No active OCR engine'
                }
        except Exception as e:
            logger.error(f"Error performing OCR on {image_path}: {str(e)}")
            return {
                'success': False,
                'text': '',
                'error': str(e)
            }
    
    def _ocr_with_paddleocr(self, image_path: str) -> Dict[str, Any]:
        """Perform OCR using PaddleOCR"""
        result = self.paddleocr_reader.ocr(image_path, cls=True)
        
        text_lines = []
        full_text_parts = []
        
        if result and result[0]:
            for line in result[0]:
                bbox = line[0]
                text_info = line[1]
                text = text_info[0]
                confidence = text_info[1]
                
                text_lines.append({
                    'text': text,
                    'confidence': float(confidence),
                    'bbox': bbox
                })
                full_text_parts.append(text)
        
        full_text = '\n'.join(full_text_parts)
        
        return {
            'success': True,
            'text': full_text,
            'text_lines': text_lines,
            'method': 'paddleocr'
        }
    
    def _ocr_with_easyocr(self, image_path: str) -> Dict[str, Any]:
        """Perform OCR using EasyOCR"""
        result = self.easyocr_reader.readtext(image_path)
        
        text_lines = []
        for detection in result:
            bbox, text, confidence = detection
            text_lines.append({
                'text': text,
                'confidence': confidence,
                'bbox': bbox
            })
        
        full_text = '\n'.join([line['text'] for line in text_lines])
        
        return {
            'success': True,
            'text': full_text,
            'text_lines': text_lines,
            'method': 'easyocr'
        }
    
    def _ocr_with_tesseract(self, image_path: str) -> Dict[str, Any]:
        """Perform OCR using Tesseract"""
        import pytesseract
        from PIL import Image
        
        image = Image.open(image_path)
        text = pytesseract.image_to_string(image)
        
        # Get detailed data with confidence
        data = pytesseract.image_to_data(image, output_type=pytesseract.OutputType.DICT)
        
        text_lines = []
        for i in range(len(data['text'])):
            if data['text'][i].strip():
                text_lines.append({
                    'text': data['text'][i],
                    'confidence': data['conf'][i],
                    'bbox': [data['left'][i], data['top'][i], data['left'][i] + data['width'][i], data['top'][i] + data['height'][i]]
                })
        
        return {
            'success': True,
            'text': text,
            'text_lines': text_lines,
            'method': 'tesseract'
        }
    
    def parse_image_from_bytes(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Extract text from image bytes using OCR
        
        Args:
            image_bytes: Image file as bytes
            
        Returns:
            Dictionary containing extracted text and metadata
        """
        logger.info(f"Performing OCR on image bytes using {self.active_engine}")
        
        if not self.active_engine:
            return {
                'success': False,
                'text': '',
                'error': 'No OCR engine available'
            }
        
        try:
            # Save bytes to temp file and use existing method
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
                temp_file.write(image_bytes)
                temp_path = temp_file.name
            
            result = self.parse_image(temp_path)
            
            # Clean up
            import os
            os.unlink(temp_path)
            
            return result
            
        except Exception as e:
            logger.error(f"Error performing OCR on image bytes: {str(e)}")
            return {
                'success': False,
                'text': '',
                'error': str(e)
            }
    
    def parse_document_page(self, page_image: Any) -> Dict[str, Any]:
        """
        Extract text from a document page image
        
        Args:
            page_image: PIL Image object or image path
            
        Returns:
            Dictionary containing extracted text and metadata
        """
        logger.info(f"Performing OCR on document page using {self.active_engine}")
        
        if not self.active_engine:
            return {
                'success': False,
                'text': '',
                'error': 'OCR not available'
            }
        
        try:
            # Save to temp file if needed
            if isinstance(page_image, str):
                return self.parse_image(page_image)
            else:
                # PIL Image object
                import tempfile
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
                    page_image.save(temp_file.name)
                    temp_path = temp_file.name
                
                result = self.parse_image(temp_path)
                
                import os
                os.unlink(temp_path)
                
                return result
            
        except Exception as e:
            logger.error(f"Error performing OCR on document page: {str(e)}")
            return {
                'success': False,
                'text': '',
                'error': str(e)
            }
    
    def extract_text_with_layout(self, image_path: str) -> Dict[str, Any]:
        """
        Extract text with layout information
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Dictionary containing extracted text with layout
        """
        logger.info(f"Extracting text with layout from: {image_path} using {self.active_engine}")
        
        if not self.active_engine:
            return {
                'success': False,
                'text': '',
                'layout': [],
                'error': 'OCR not available'
            }
        
        try:
            if self.active_engine == "paddleocr":
                result = self.paddleocr_reader.ocr(image_path, cls=True)
                
                layout_elements = []
                full_text_parts = []
                
                if result and result[0]:
                    for line in result[0]:
                        bbox = line[0]
                        text_info = line[1]
                        text = text_info[0]
                        confidence = text_info[1]
                        
                        x_min = min([point[0] for point in bbox])
                        y_min = min([point[1] for point in bbox])
                        x_max = max([point[0] for point in bbox])
                        y_max = max([point[1] for point in bbox])
                        
                        layout_elements.append({
                            'text': text,
                            'confidence': float(confidence),
                            'bbox': [x_min, y_min, x_max, y_max],
                            'position': {
                                'x': x_min,
                                'y': y_min,
                                'width': x_max - x_min,
                                'height': y_max - y_min
                            }
                        })
                        full_text_parts.append(text)
                
                full_text = '\n'.join(full_text_parts)
                
                return {
                    'success': True,
                    'text': full_text,
                    'layout': layout_elements,
                    'method': 'paddleocr'
                }
            
            elif self.active_engine == "easyocr":
                result = self.easyocr_reader.readtext(image_path, detail=1)
                
                result.sort(key=lambda x: x[0][0][1])
                
                layout_elements = []
                for detection in result:
                    bbox, text, confidence = detection
                    
                    x_min = min([point[0] for point in bbox])
                    y_min = min([point[1] for point in bbox])
                    x_max = max([point[0] for point in bbox])
                    y_max = max([point[1] for point in bbox])
                    
                    layout_elements.append({
                        'text': text,
                        'confidence': confidence,
                        'bbox': [x_min, y_min, x_max, y_max],
                        'position': {
                            'x': x_min,
                            'y': y_min,
                            'width': x_max - x_min,
                            'height': y_max - y_min
                        }
                    })
                
                full_text = '\n'.join([elem['text'] for elem in layout_elements])
                
                return {
                    'success': True,
                    'text': full_text,
                    'layout': layout_elements,
                    'method': 'easyocr'
                }
            
            elif self.active_engine == "tesseract":
                import pytesseract
                from PIL import Image
                
                image = Image.open(image_path)
                data = pytesseract.image_to_data(image, output_type=pytesseract.OutputType.DICT)
                
                layout_elements = []
                full_text_parts = []
                
                for i in range(len(data['text'])):
                    if data['text'][i].strip():
                        layout_elements.append({
                            'text': data['text'][i],
                            'confidence': data['conf'][i],
                            'bbox': [data['left'][i], data['top'][i], data['left'][i] + data['width'][i], data['top'][i] + data['height'][i]],
                            'position': {
                                'x': data['left'][i],
                                'y': data['top'][i],
                                'width': data['width'][i],
                                'height': data['height'][i]
                            }
                        })
                        full_text_parts.append(data['text'][i])
                
                full_text = '\n'.join(full_text_parts)
                
                return {
                    'success': True,
                    'text': full_text,
                    'layout': layout_elements,
                    'method': 'tesseract'
                }
            
        except Exception as e:
            logger.error(f"Error extracting text with layout: {str(e)}")
            return {
                'success': False,
                'text': '',
                'layout': [],
                'error': str(e)
            }
