"""
Layout parser for document structure analysis
"""

from typing import Dict, List, Any, Optional
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class LayoutParser:
    """Parser for analyzing document layout and structure"""
    
    def __init__(self):
        pass
    
    def parse(self, document_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse document layout from loaded document data
        
        Args:
            document_data: Dictionary containing document content
            
        Returns:
            Dictionary containing layout information
        """
        logger.info("Parsing document layout")
        
        layout_info = {
            'pages': [],
            'sections': [],
            'headings': [],
            'paragraphs': [],
            'lists': []
        }
        
        # Handle PDF documents
        if 'pages' in document_data:
            for page in document_data['pages']:
                page_layout = self._parse_page(page)
                layout_info['pages'].append(page_layout)
        
        # Handle DOCX documents
        elif 'paragraphs' in document_data:
            doc_layout = self._parse_docx(document_data)
            layout_info.update(doc_layout)
        
        # Handle PPTX documents
        elif 'slides' in document_data:
            ppt_layout = self._parse_pptx(document_data)
            layout_info.update(ppt_layout)
        
        return layout_info
    
    def _parse_page(self, page: Dict[str, Any]) -> Dict[str, Any]:
        """Parse a single page"""
        page_layout = {
            'page_number': page.get('page_number', 0),
            'text': page.get('text', ''),
            'elements': [],
            'dimensions': {
                'width': page.get('width', 0),
                'height': page.get('height', 0)
            }
        }
        
        # Analyze text structure
        text = page.get('text', '')
        if text:
            elements = self._analyze_text_structure(text)
            page_layout['elements'] = elements
        
        return page_layout
    
    def _parse_docx(self, document_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse DOCX document structure"""
        layout = {
            'headings': [],
            'paragraphs': [],
            'sections': []
        }
        
        paragraphs = document_data.get('paragraphs', [])
        current_section = None
        
        for para in paragraphs:
            text = para.get('text', '')
            level = para.get('level', 0)
            
            if level > 0:
                # This is a heading
                heading = {
                    'text': text,
                    'level': level,
                    'position': len(layout['headings'])
                }
                layout['headings'].append(heading)
                
                # Start a new section
                current_section = {
                    'heading': text,
                    'level': level,
                    'content': []
                }
                layout['sections'].append(current_section)
            else:
                # This is a paragraph
                paragraph = {
                    'text': text,
                    'position': len(layout['paragraphs'])
                }
                layout['paragraphs'].append(paragraph)
                
                if current_section:
                    current_section['content'].append(text)
        
        return layout
    
    def _parse_pptx(self, document_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse PPTX document structure"""
        layout = {
            'slides': [],
            'headings': [],
            'paragraphs': []
        }
        
        slides = document_data.get('slides', [])
        
        for slide in slides:
            slide_layout = {
                'slide_number': slide.get('slide_number', 0),
                'text': slide.get('text', ''),
                'shapes': slide.get('shapes', []),
                'tables': slide.get('tables', [])
            }
            layout['slides'].append(slide_layout)
            
            # Extract potential headings from slide text
            text = slide.get('text', '')
            if text:
                lines = text.strip().split('\n')
                if lines:
                    # First line is often a title
                    layout['headings'].append({
                        'text': lines[0],
                        'level': 1,
                        'slide_number': slide.get('slide_number', 0)
                    })
        
        return layout
    
    def _analyze_text_structure(self, text: str) -> List[Dict[str, Any]]:
        """Analyze text structure and identify elements"""
        elements = []
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Detect headings (all caps, or numbered, etc.)
            if self._is_heading(line):
                elements.append({
                    'type': 'heading',
                    'text': line,
                    'level': self._get_heading_level(line)
                })
            # Detect list items
            elif self._is_list_item(line):
                elements.append({
                    'type': 'list',
                    'text': line
                })
            # Regular paragraph
            else:
                elements.append({
                    'type': 'paragraph',
                    'text': line
                })
        
        return elements
    
    def _is_heading(self, text: str) -> bool:
        """Check if text is likely a heading"""
        if not text:
            return False

        # All caps
        if text.isupper() and len(text) < 100:
            return True

        # Numbered heading
        if text[0].isdigit() and len(text) > 1 and ('.' in text or ')' in text):
            return True

        # Short and on its own line
        if len(text) < 50 and text[0].isupper():
            return True

        return False

    def _get_heading_level(self, text: str) -> int:
        """Determine heading level"""
        if not text:
            return 1
        # Numbered headings
        if text[0].isdigit():
            parts = text.split('.')
            if len(parts) > 1 and parts[0].isdigit():
                return int(parts[0])

        # Default to level 1
        return 1

    def _is_list_item(self, text: str) -> bool:
        """Check if text is a list item"""
        if not text:
            return False

        # Bullet points
        if text.startswith(('•', '-', '*', '○')):
            return True

        # Numbered list (need at least "1." or "1)")
        if len(text) >= 2 and text[0].isdigit() and text[1] in '.))':
            return True

        # Lettered list (need at least "a." or "a)")
        if len(text) >= 2 and text[0].isalpha() and text[1] in '.))':
            return True

        return False
    
    def detect_columns(self, page: Dict[str, Any]) -> int:
        """Detect number of columns in a page"""
        # This is a simplified implementation
        # In production, you'd use more sophisticated analysis
        text = page.get('text', '')
        
        # Simple heuristic: check for multiple columns based on line patterns
        lines = text.split('\n')
        if len(lines) > 10:
            # Check if there are patterns suggesting columns
            return 1
        
        return 1
