"""
Unstructured parser for document parsing
"""

from typing import Dict, List, Any, Optional
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class UnstructuredParser:
    """Parser using Unstructured library for document parsing"""
    
    def __init__(self):
        self.unstructured_available = False
        try:
            from unstructured.partition.pdf import partition_pdf
            from unstructured.partition.docx import partition_docx
            from unstructured.partition.pptx import partition_pptx
            from unstructured.partition.image import partition_image
            
            self.partition_pdf = partition_pdf
            self.partition_docx = partition_docx
            self.partition_pptx = partition_pptx
            self.partition_image = partition_image
            self.unstructured_available = True
            logger.info("Unstructured parser initialized successfully")
        except ImportError:
            logger.warning("Unstructured not available, install with: pip install unstructured[local-inference]")
    
    def parse(self, file_path: str) -> Dict[str, Any]:
        """
        Parse a document using Unstructured
        
        Args:
            file_path: Path to the document file
            
        Returns:
            Dictionary containing parsed document structure
        """
        if not self.unstructured_available:
            return {'success': False, 'method': 'none', 'error': 'Unstructured not available'}
        
        logger.info(f"Parsing document with Unstructured: {file_path}")
        
        try:
            from pathlib import Path
            file_ext = Path(file_path).suffix.lower()
            
            # Choose appropriate partition function
            if file_ext == '.pdf':
                elements = self.partition_pdf(filename=file_path)
            elif file_ext == '.docx':
                elements = self.partition_docx(filename=file_path)
            elif file_ext == '.pptx':
                elements = self.partition_pptx(filename=file_path)
            elif file_ext in ['.png', '.jpg', '.jpeg', '.tiff', '.bmp']:
                elements = self.partition_image(filename=file_path)
            else:
                return {'success': False, 'method': 'unstructured', 'error': f'Unsupported file type: {file_ext}'}
            
            # Process elements
            parsed_data = self._process_elements(elements)
            
            return {
                'success': True,
                'data': parsed_data,
                'method': 'unstructured',
                'element_count': len(elements)
            }
            
        except Exception as e:
            logger.error(f"Error parsing with Unstructured: {str(e)}")
            return {
                'success': False,
                'method': 'unstructured',
                'error': str(e)
            }
    
    def parse_from_bytes(self, file_bytes: bytes, file_format: str = 'pdf') -> Dict[str, Any]:
        """
        Parse a document from bytes using Unstructured
        
        Args:
            file_bytes: Document file as bytes
            file_format: Format of the document (pdf, docx, pptx, image)
            
        Returns:
            Dictionary containing parsed document structure
        """
        if not self.unstructured_available:
            return {'success': False, 'method': 'none', 'error': 'Unstructured not available'}
        
        logger.info(f"Parsing document from bytes with Unstructured: {file_format}")
        
        try:
            import io
            
            # Choose appropriate partition function based on format
            if file_format == 'pdf':
                elements = self.partition_pdf(file=io.BytesIO(file_bytes))
            elif file_format == 'docx':
                elements = self.partition_docx(file=io.BytesIO(file_bytes))
            elif file_format == 'pptx':
                elements = self.partition_pptx(file=io.BytesIO(file_bytes))
            elif file_format == 'image':
                elements = self.partition_image(file=io.BytesIO(file_bytes))
            else:
                return {'success': False, 'method': 'unstructured', 'error': f'Unsupported format: {file_format}'}
            
            parsed_data = self._process_elements(elements)
            
            return {
                'success': True,
                'data': parsed_data,
                'method': 'unstructured',
                'element_count': len(elements)
            }
            
        except Exception as e:
            logger.error(f"Error parsing from bytes with Unstructured: {str(e)}")
            return {
                'success': False,
                'method': 'unstructured',
                'error': str(e)
            }
    
    def _process_elements(self, elements) -> Dict[str, Any]:
        """Process elements from Unstructured"""
        pages = []
        tables = []
        images = []
        
        current_page = {'text': '', 'elements': [], 'page_number': 1}
        
        for element in elements:
            element_type = str(type(element).__name__)
            element_text = str(element).strip()
            
            # Categorize elements
            if 'Table' in element_type:
                tables.append({
                    'data': self._extract_table_data(element),
                    'page_number': getattr(element, 'metadata', {}).get('page_number', 1)
                })
            elif 'Image' in element_type:
                images.append({
                    'data': element_text,
                    'page_number': getattr(element, 'metadata', {}).get('page_number', 1)
                })
            else:
                # Text element
                current_page['text'] += element_text + '\n'
                current_page['elements'].append({
                    'type': element_type,
                    'text': element_text,
                    'metadata': getattr(element, 'metadata', {})
                })
        
        pages.append(current_page)
        
        return {
            'pages': pages,
            'tables': tables,
            'images': images,
            'total_pages': len(pages)
        }
    
    def _extract_table_data(self, table_element) -> List[List[str]]:
        """Extract table data from Unstructured table element"""
        try:
            # Unstructured tables have html attribute
            if hasattr(table_element, 'html'):
                # Parse HTML table
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(table_element.html, 'html.parser')
                rows = []
                
                for tr in soup.find_all('tr'):
                    row_data = []
                    for td in tr.find_all(['td', 'th']):
                        row_data.append(td.get_text(strip=True))
                    if row_data:
                        rows.append(row_data)
                
                return rows
        except Exception as e:
            logger.warning(f"Could not extract table data: {str(e)}")
        
        return []
    
    def extract_text(self, file_path: str) -> str:
        """
        Extract only text from document
        
        Args:
            file_path: Path to the document
            
        Returns:
            Extracted text
        """
        result = self.parse(file_path)
        
        if result.get('success') and 'data' in result:
            text_parts = []
            for page in result['data'].get('pages', []):
                text_parts.append(page.get('text', ''))
            return '\n\n'.join(text_parts)
        
        return ""
