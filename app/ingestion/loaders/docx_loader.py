"""
DOCX document loader
"""

import base64
import uuid
import zipfile
from typing import Dict, List, Any, Optional
from pathlib import Path
from docx import Document
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class DOCXLoader:
    """Loader for DOCX documents"""
    
    def __init__(self):
        self.supported_extensions = ['.docx']
    
    def load(self, file_path: str) -> Dict[str, Any]:
        """
        Load a DOCX file and extract its content
        
        Args:
            file_path: Path to the DOCX file
            
        Returns:
            Dictionary containing DOCX content and metadata
        """
        logger.info(f"Loading DOCX file: {file_path}")
        
        try:
            doc = Document(file_path)
            
            # Extract paragraphs
            paragraphs = []
            for para in doc.paragraphs:
                if para.text.strip():
                    paragraphs.append({
                        'text': para.text,
                        'style': para.style.name if para.style else 'Normal',
                        'level': self._get_heading_level(para)
                    })
            
            # Extract tables
            tables = []
            for table_idx, table in enumerate(doc.tables):
                table_data = []
                for row in table.rows:
                    row_data = [cell.text for cell in row.cells]
                    table_data.append(row_data)
                tables.append({
                    'table_id': str(uuid.uuid4()),
                    'table_index': table_idx,
                    'data': table_data,
                    'location': f"Table {table_idx + 1}",
                })

            images = self._extract_images(file_path)

            metadata = self._extract_metadata(doc)

            return {
                'paragraphs': paragraphs,
                'tables': tables,
                'images': images,
                'metadata': metadata
            }
            
        except Exception as e:
            logger.error(f"Error loading DOCX file {file_path}: {str(e)}")
            raise
    
    def load_from_bytes(self, file_bytes: bytes) -> Dict[str, Any]:
        """
        Load a DOCX from bytes
        
        Args:
            file_bytes: DOCX file as bytes
            
        Returns:
            Dictionary containing DOCX content and metadata
        """
        logger.info("Loading DOCX from bytes")
        
        try:
            import io
            doc = Document(io.BytesIO(file_bytes))
            
            paragraphs = []
            for para in doc.paragraphs:
                if para.text.strip():
                    paragraphs.append({
                        'text': para.text,
                        'style': para.style.name if para.style else 'Normal',
                        'level': self._get_heading_level(para)
                    })
            
            tables = []
            for table_idx, table in enumerate(doc.tables):
                table_data = []
                for row in table.rows:
                    row_data = [cell.text for cell in row.cells]
                    table_data.append(row_data)
                tables.append({
                    'table_id': str(uuid.uuid4()),
                    'table_index': table_idx,
                    'data': table_data,
                    'location': f"Table {table_idx + 1}",
                })

            metadata = self._extract_metadata(doc)

            return {
                'paragraphs': paragraphs,
                'tables': tables,
                'images': [],
                'metadata': metadata
            }
            
        except Exception as e:
            logger.error(f"Error loading DOCX from bytes: {str(e)}")
            raise
    
    def _get_heading_level(self, paragraph) -> int:
        """Get heading level from paragraph style"""
        style_name = paragraph.style.name if paragraph.style else ''
        if 'Heading' in style_name:
            try:
                return int(style_name.split()[-1])
            except (ValueError, IndexError):
                return 1
        return 0
    
    def _extract_metadata(self, doc: Document) -> Dict[str, Any]:
        """Extract metadata from DOCX"""
        try:
            core_props = doc.core_properties
            return {
                'title': core_props.title or '',
                'author': core_props.author or '',
                'subject': core_props.subject or '',
                'keywords': core_props.keywords or '',
                'created': core_props.created,
                'modified': core_props.modified,
                'last_modified_by': core_props.last_modified_by or ''
            }
        except Exception as e:
            logger.warning(f"Could not extract DOCX metadata: {str(e)}")
            return {}
    
    def _extract_images(self, file_path: str) -> List[Dict[str, Any]]:
        """Extract embedded images from DOCX (zip archive)."""
        images: List[Dict[str, Any]] = []
        try:
            with zipfile.ZipFile(file_path, "r") as archive:
                media_files = [
                    name for name in archive.namelist()
                    if name.startswith("word/media/") and not name.endswith("/")
                ]
                for media_name in media_files:
                    blob = archive.read(media_name)
                    filename = media_name.split("/")[-1]
                    images.append({
                        "image_id": str(uuid.uuid4()),
                        "image_bytes": base64.b64encode(blob).decode("utf-8"),
                        "caption": filename,
                        "location": f"Embedded image: {filename}",
                        "is_chart": any(k in filename.lower() for k in ("chart", "graph", "plot")),
                    })
        except Exception as exc:
            logger.warning(f"Could not extract DOCX images: {exc}")
        return images

    def is_supported(self, file_path: str) -> bool:
        """Check if file is supported"""
        return Path(file_path).suffix.lower() in self.supported_extensions
