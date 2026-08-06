"""
PDF document loader
"""

import io
import base64
import uuid
from typing import Dict, List, Any, Optional
from pathlib import Path
import pdfplumber
from PyPDF2 import PdfReader
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class PDFLoader:
    """Loader for PDF documents"""
    
    def __init__(self):
        self.supported_extensions = ['.pdf']
    
    def load(self, file_path: str) -> Dict[str, Any]:
        """
        Load a PDF file and extract its content
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            Dictionary containing PDF content and metadata
        """
        logger.info(f"Loading PDF file: {file_path}")
        
        try:
            with pdfplumber.open(file_path) as pdf:
                pages_content = []
                tables = []
                images = []
                
                for page_num, page in enumerate(pdf.pages):
                    text = page.extract_text() or ""

                    page_tables = page.extract_tables()
                    for table in page_tables:
                        inline_text = self._table_data_to_text(table)
                        table_entry = {
                            'table_id': str(uuid.uuid4()),
                            'page_number': page_num + 1,
                            'data': table,
                            'inline_text': inline_text,
                            'location': f"Page {page_num + 1}",
                        }
                        tables.append(table_entry)
                        text += "\n" + inline_text

                    if hasattr(page, 'images'):
                        for img in page.images:
                            images.append({
                                'image_id': str(uuid.uuid4()),
                                'page_number': page_num + 1,
                                'bbox': img.get('bbox', None),
                                'location': f"Page {page_num + 1}",
                            })

                    pages_content.append({
                        'page_number': page_num + 1,
                        'text': text,
                        'width': page.width,
                        'height': page.height
                    })

                images = self._extract_pdf_images(file_path, images)
                metadata = self._extract_metadata(file_path)
                
                return {
                    'pages': pages_content,
                    'tables': tables,
                    'images': images,
                    'metadata': metadata,
                    'total_pages': len(pages_content)
                }
                
        except Exception as e:
            logger.error(f"Error loading PDF file {file_path}: {str(e)}")
            raise
    
    def load_from_bytes(self, file_bytes: bytes) -> Dict[str, Any]:
        """
        Load a PDF from bytes
        
        Args:
            file_bytes: PDF file as bytes
            
        Returns:
            Dictionary containing PDF content and metadata
        """
        logger.info("Loading PDF from bytes")
        
        try:
            pdf_file = io.BytesIO(file_bytes)
            
            with pdfplumber.open(pdf_file) as pdf:
                pages_content = []
                tables = []
                images = []
                
                for page_num, page in enumerate(pdf.pages):
                    text = page.extract_text() or ""

                    page_tables = page.extract_tables()
                    for table in page_tables:
                        inline_text = self._table_data_to_text(table)
                        table_entry = {
                            'table_id': str(uuid.uuid4()),
                            'page_number': page_num + 1,
                            'data': table,
                            'inline_text': inline_text,
                            'location': f"Page {page_num + 1}",
                        }
                        tables.append(table_entry)
                        text += "\n" + inline_text

                    if hasattr(page, 'images'):
                        for img in page.images:
                            images.append({
                                'image_id': str(uuid.uuid4()),
                                'page_number': page_num + 1,
                                'bbox': img.get('bbox', None),
                                'location': f"Page {page_num + 1}",
                            })

                    pages_content.append({
                        'page_number': page_num + 1,
                        'text': text,
                        'width': page.width,
                        'height': page.height
                    })

                return {
                    'pages': pages_content,
                    'tables': tables,
                    'images': images,
                    'metadata': {},
                    'total_pages': len(pages_content)
                }
                
        except Exception as e:
            logger.error(f"Error loading PDF from bytes: {str(e)}")
            raise
    
    def _extract_metadata(self, file_path: str) -> Dict[str, Any]:
        """Extract metadata from PDF using PyPDF2"""
        try:
            with open(file_path, 'rb') as f:
                reader = PdfReader(f)
                metadata = reader.metadata or {}
                
                return {
                    'title': metadata.get('/Title', ''),
                    'author': metadata.get('/Author', ''),
                    'subject': metadata.get('/Subject', ''),
                    'creator': metadata.get('/Creator', ''),
                    'producer': metadata.get('/Producer', ''),
                    'creation_date': metadata.get('/CreationDate', ''),
                    'modification_date': metadata.get('/ModDate', '')
                }
        except Exception as e:
            logger.warning(f"Could not extract PDF metadata: {str(e)}")
            return {}
    
    def _table_data_to_text(self, table_data: List[List[Any]]) -> str:
        lines = []
        for row in table_data or []:
            if row:
                lines.append(" | ".join(str(cell or "") for cell in row))
        return "\n".join(lines)

    def _extract_pdf_images(self, file_path: str, existing_images: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract embedded image bytes from PDF using PyMuPDF when available."""
        try:
            import fitz
        except ImportError:
            logger.debug("PyMuPDF not installed; skipping PDF image byte extraction")
            return existing_images

        extracted = list(existing_images)
        try:
            doc = fitz.open(file_path)
            for page_index in range(len(doc)):
                page = doc[page_index]
                for img_index, img in enumerate(page.get_images(full=True)):
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image.get("image")
                    if not image_bytes:
                        continue
                    extracted.append({
                        "image_id": str(uuid.uuid4()),
                        "page_number": page_index + 1,
                        "image_bytes": base64.b64encode(image_bytes).decode("utf-8"),
                        "caption": f"Image {img_index + 1}",
                        "location": f"Page {page_index + 1}",
                        "is_chart": False,
                    })
            doc.close()
        except Exception as exc:
            logger.warning(f"PyMuPDF image extraction failed: {exc}")

        return extracted

    def is_supported(self, file_path: str) -> bool:
        """Check if file is supported"""
        return Path(file_path).suffix.lower() in self.supported_extensions
