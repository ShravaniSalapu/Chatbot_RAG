"""
Metadata builder for constructing comprehensive document metadata
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class MetadataBuilder:
    """Build comprehensive metadata for documents"""
    
    def __init__(self):
        pass
    
    def build_document_metadata(self, document_data: Dict[str, Any], file_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build comprehensive document metadata
        
        Args:
            document_data: Parsed document data
            file_info: File information (name, size, type, etc.)
            
        Returns:
            Comprehensive metadata dictionary
        """
        logger.info("Building document metadata")
        
        metadata = {
            # Basic file information
            'filename': file_info.get('filename', ''),
            'file_type': file_info.get('file_type', ''),
            'file_size': file_info.get('file_size', 0),
            'upload_date': datetime.utcnow().isoformat(),
            
            # Document structure statistics
            'total_pages': self._count_pages(document_data),
            'total_sections': self._count_sections(document_data),
            'total_headings': self._count_headings(document_data),
            'total_paragraphs': self._count_paragraphs(document_data),
            'total_tables': self._count_tables(document_data),
            'total_images': self._count_images(document_data),
            
            # Content statistics
            'total_characters': self._count_characters(document_data),
            'total_words': self._count_words(document_data),
            'estimated_tokens': self._estimate_tokens(document_data),
            
            # Language detection (simplified)
            'language': self._detect_language(document_data),
            
            # Document type classification
            'document_type': self._classify_document(document_data),
            
            # Extracted metadata from document
            'extracted_metadata': document_data.get('metadata', {}),
            
            # Processing information
            'processing_timestamp': datetime.utcnow().isoformat(),
            'processing_version': '1.0.0'
        }
        
        logger.info(f"Built metadata for document: {metadata['filename']}")
        return metadata
    
    def _count_pages(self, document_data: Dict[str, Any]) -> int:
        """Count pages in document"""
        if 'pages' in document_data:
            return len(document_data['pages'])
        elif 'slides' in document_data:
            return len(document_data['slides'])
        elif 'sheets' in document_data:
            return len(document_data['sheets'])
        return 1
    
    def _count_sections(self, document_data: Dict[str, Any]) -> int:
        """Count sections in document"""
        if 'sections' in document_data:
            return len(document_data['sections'])
        return 0
    
    def _count_headings(self, document_data: Dict[str, Any]) -> int:
        """Count headings in document"""
        if 'headings' in document_data:
            return len(document_data['headings'])
        return 0
    
    def _count_paragraphs(self, document_data: Dict[str, Any]) -> int:
        """Count paragraphs in document"""
        if 'paragraphs' in document_data:
            return len(document_data['paragraphs'])
        
        # Count from pages
        if 'pages' in document_data:
            count = 0
            for page in document_data['pages']:
                if 'elements' in page:
                    count += len([e for e in page['elements'] if e.get('type') == 'paragraph'])
            return count
        
        return 0
    
    def _count_tables(self, document_data: Dict[str, Any]) -> int:
        """Count tables in document"""
        if 'tables' in document_data:
            return len(document_data['tables'])

        if 'sheets' in document_data:
            return sum(1 for s in document_data['sheets'] if s.get('rows'))
        
        # Count from pages
        if 'pages' in document_data:
            count = 0
            for page in document_data['pages']:
                if 'tables' in page:
                    count += len(page['tables'])
            return count
        
        return 0
    
    def _count_images(self, document_data: Dict[str, Any]) -> int:
        """Count images in document"""
        if 'images' in document_data:
            return len(document_data['images'])
        
        # Count from pages
        if 'pages' in document_data:
            count = 0
            for page in document_data['pages']:
                if 'images' in page:
                    count += len(page['images'])
            return count
        
        return 0
    
    def _count_characters(self, document_data: Dict[str, Any]) -> int:
        """Count total characters in document"""
        text = self._extract_full_text(document_data)
        return len(text)
    
    def _count_words(self, document_data: Dict[str, Any]) -> int:
        """Count total words in document"""
        text = self._extract_full_text(document_data)
        return len(text.split())
    
    def _estimate_tokens(self, document_data: Dict[str, Any]) -> int:
        """Estimate token count (roughly 0.75 words per token)"""
        word_count = self._count_words(document_data)
        return int(word_count / 0.75)
    
    def _extract_full_text(self, document_data: Dict[str, Any]) -> str:
        """Extract full text from document"""
        text_parts = []
        
        if 'pages' in document_data:
            for page in document_data['pages']:
                text_parts.append(page.get('text', ''))
        elif 'paragraphs' in document_data:
            for para in document_data['paragraphs']:
                text_parts.append(para.get('text', ''))
        elif 'slides' in document_data:
            for slide in document_data['slides']:
                text_parts.append(slide.get('text', ''))
        elif 'sheets' in document_data:
            for sheet in document_data['sheets']:
                for row in sheet.get('rows') or []:
                    text_parts.append(' | '.join(str(cell) for cell in row))
        
        return ' '.join(text_parts)
    
    def _detect_language(self, document_data: Dict[str, Any]) -> str:
        """Detect document language (simplified)"""
        text = self._extract_full_text(document_data)
        
        # Very simple language detection based on common words
        # In production, use a proper language detection library
        english_words = ['the', 'and', 'is', 'in', 'to', 'of', 'a', 'for', 'with', 'on']
        text_lower = text.lower()
        
        english_count = sum(1 for word in english_words if word in text_lower)
        
        if english_count > 5:
            return 'en'
        
        return 'unknown'
    
    def _classify_document(self, document_data: Dict[str, Any]) -> str:
        """Classify document type"""
        file_type = document_data.get('metadata', {}).get('file_type', '')
        
        if file_type == 'pdf':
            return 'pdf_document'
        elif file_type == 'docx':
            return 'word_document'
        elif file_type == 'pptx':
            return 'presentation'
        elif file_type == 'image':
            return 'image_document'
        
        return 'unknown'
    
    def build_element_metadata(self, element: Dict[str, Any], element_type: str) -> Dict[str, Any]:
        """
        Build metadata for a specific element
        
        Args:
            element: Element data
            element_type: Type of element
            
        Returns:
            Element metadata
        """
        metadata = {
            'element_type': element_type,
            'character_count': len(str(element.get('content', ''))),
            'word_count': len(str(element.get('content', '')).split()),
            'created_at': datetime.utcnow().isoformat()
        }
        
        # Add type-specific metadata
        if element_type == 'table':
            metadata['row_count'] = len(element.get('rows', []))
            metadata['column_count'] = len(element.get('headers', [])) if element.get('headers') else 0
        elif element_type == 'image':
            metadata['width'] = element.get('width', 0)
            metadata['height'] = element.get('height', 0)
        
        return metadata
    
    def update_metadata_with_analysis(self, metadata: Dict[str, Any], analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update metadata with analysis results
        
        Args:
            metadata: Existing metadata
            analysis: Analysis results
            
        Returns:
            Updated metadata
        """
        metadata['analysis'] = {
            'timestamp': datetime.utcnow().isoformat(),
            'results': analysis
        }
        
        return metadata
    
    def build_search_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build metadata optimized for search
        
        Args:
            metadata: Full metadata
            
        Returns:
            Search-optimized metadata
        """
        search_metadata = {
            'document_id': metadata.get('document_id', ''),
            'filename': metadata.get('filename', ''),
            'file_type': metadata.get('file_type', ''),
            'total_pages': metadata.get('total_pages', 0),
            'total_tables': metadata.get('total_tables', 0),
            'total_images': metadata.get('total_images', 0),
            'language': metadata.get('language', 'unknown'),
            'document_type': metadata.get('document_type', 'unknown')
        }
        
        return search_metadata
