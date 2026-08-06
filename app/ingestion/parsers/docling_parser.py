"""
Docling parser for advanced document parsing
"""

from typing import Dict, List, Any, Optional
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class DoclingParser:
    """Parser using Docling for advanced document parsing"""
    
    def __init__(self):
        try:
            from docling.document import Document as DoclingDocument
            from docling.datamodel.base_models import InputFormat
            from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
            
            self.docling_available = True
            logger.info("Docling parser initialized successfully")
        except ImportError:
            logger.warning("Docling not available")
            self.docling_available = False
    
    def parse(self, file_path: str) -> Dict[str, Any]:
        """
        Parse a document using Docling
        
        Args:
            file_path: Path to the document file
            
        Returns:
            Dictionary containing parsed document structure
        """
        if not self.docling_available:
            return self._fallback_parse(file_path)
        
        logger.info(f"Parsing document with Docling: {file_path}")
        
        try:
            from docling.document import Document as DoclingDocument
            from docling.datamodel.base_models import InputFormat
            from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
            
            # Load document
            doc = DoclingDocument.from_backend(
                PyPdfiumDocumentBackend.from_path(file_path)
            )
            
            # Export to JSON structure
            parsed_data = doc.export_to_dict()
            
            return {
                'success': True,
                'data': parsed_data,
                'method': 'docling'
            }
            
        except Exception as e:
            logger.error(f"Error parsing with Docling: {str(e)}")
            return self._fallback_parse(file_path)
    
    def parse_from_bytes(self, file_bytes: bytes, file_format: str = 'pdf') -> Dict[str, Any]:
        """
        Parse a document from bytes using Docling
        
        Args:
            file_bytes: Document file as bytes
            file_format: Format of the document (pdf, docx, etc.)
            
        Returns:
            Dictionary containing parsed document structure
        """
        if not self.docling_available:
            logger.warning("Docling not available, cannot parse from bytes")
            return {'success': False, 'method': 'none'}
        
        logger.info(f"Parsing document from bytes with Docling: {file_format}")
        
        try:
            import io
            from docling.document import Document as DoclingDocument
            from docling.datamodel.base_models import InputFormat
            from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
            
            # Create a temporary file-like object
            file_obj = io.BytesIO(file_bytes)
            
            # Load document from bytes
            doc = DoclingDocument.from_backend(
                PyPdfiumDocumentBackend.from_stream(file_obj)
            )
            
            parsed_data = doc.export_to_dict()
            
            return {
                'success': True,
                'data': parsed_data,
                'method': 'docling'
            }
            
        except Exception as e:
            logger.error(f"Error parsing from bytes with Docling: {str(e)}")
            return {'success': False, 'method': 'none', 'error': str(e)}
    
    def _fallback_parse(self, file_path: str) -> Dict[str, Any]:
        """Fallback to basic parsing if Docling is not available"""
        logger.info("Using fallback parsing method")
        
        try:
            # Basic text extraction
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
            
            return {
                'success': True,
                'data': {
                    'text': text,
                    'pages': [{'text': text}]
                },
                'method': 'fallback'
            }
        except Exception as e:
            logger.error(f"Fallback parsing failed: {str(e)}")
            return {
                'success': False,
                'method': 'fallback',
                'error': str(e)
            }
    
    def extract_layout(self, parsed_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract layout information from parsed data"""
        layouts = []
        
        if 'data' in parsed_data and 'pages' in parsed_data['data']:
            for page in parsed_data['data']['pages']:
                layout = {
                    'page_number': page.get('page_no', 0),
                    'elements': []
                }
                
                if 'elements' in page:
                    for element in page['elements']:
                        layout['elements'].append({
                            'type': element.get('type', 'unknown'),
                            'text': element.get('text', ''),
                            'bbox': element.get('bbox', None)
                        })
                
                layouts.append(layout)
        
        return layouts
    
    def extract_tables(self, parsed_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract tables from parsed data"""
        tables = []
        
        if 'data' in parsed_data and 'pages' in parsed_data['data']:
            for page in parsed_data['data']['pages']:
                if 'tables' in page:
                    for table in page['tables']:
                        tables.append({
                            'page_number': page.get('page_no', 0),
                            'data': table
                        })
        
        return tables
    
    def extract_images(self, parsed_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract images from parsed data"""
        images = []
        
        if 'data' in parsed_data and 'pages' in parsed_data['data']:
            for page in parsed_data['data']['pages']:
                if 'pictures' in page:
                    for picture in page['pictures']:
                        images.append({
                            'page_number': page.get('page_no', 0),
                            'data': picture
                        })
        
        return images
