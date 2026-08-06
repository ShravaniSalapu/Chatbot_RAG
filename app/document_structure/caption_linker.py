"""
Caption linker for associating captions with figures and tables
"""

from typing import Dict, List, Any, Optional
import re
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class CaptionLinker:
    """Link captions to figures and tables"""
    
    def __init__(self):
        # Patterns for detecting captions
        self.caption_patterns = [
            r'Figure\s+\d+[:\.\-]\s*.+',
            r'Table\s+\d+[:\.\-]\s*.+',
            r'Fig\.\s*\d+[:\.\-]\s*.+',
            r'Chart\s+\d+[:\.\-]\s*.+',
            r'Exhibit\s+\d+[:\.\-]\s*.+',
        ]
        
        self.compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.caption_patterns]
    
    def detect_captions(self, text: str) -> List[Dict[str, Any]]:
        """
        Detect captions in text
        
        Args:
            text: Document text
            
        Returns:
            List of detected captions
        """
        logger.info("Detecting captions in document")
        
        captions = []
        lines = text.split('\n')
        
        for line_num, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            
            caption_info = self._is_caption(line)
            if caption_info:
                caption_info['line_number'] = line_num
                caption_info['position'] = line_num
                captions.append(caption_info)
        
        logger.info(f"Detected {len(captions)} captions")
        return captions
    
    def _is_caption(self, text: str) -> Optional[Dict[str, Any]]:
        """Check if text is a caption"""
        for pattern in self.compiled_patterns:
            match = pattern.match(text)
            if match:
                caption_type = self._determine_caption_type(text)
                return {
                    'text': text,
                    'type': caption_type,
                    'number': self._extract_caption_number(text)
                }
        
        return None
    
    def _determine_caption_type(self, text: str) -> str:
        """Determine caption type (figure, table, etc.)"""
        text_lower = text.lower()
        
        if 'table' in text_lower:
            return 'table'
        elif 'figure' in text_lower or 'fig.' in text_lower:
            return 'figure'
        elif 'chart' in text_lower:
            return 'chart'
        elif 'exhibit' in text_lower:
            return 'exhibit'
        else:
            return 'unknown'
    
    def _extract_caption_number(self, text: str) -> Optional[int]:
        """Extract the number from a caption"""
        match = re.search(r'\d+', text)
        if match:
            return int(match.group())
        return None
    
    def link_caption_to_element(self, caption: Dict[str, Any], elements: List[Dict[str, Any]], max_distance: int = 5) -> Optional[Dict[str, Any]]:
        """
        Link a caption to the nearest element
        
        Args:
            caption: Caption dictionary
            elements: List of elements (tables, images, etc.)
            max_distance: Maximum line distance to search
            
        Returns:
            Linked element or None
        """
        caption_pos = caption['position']
        caption_type = caption['type']
        
        # Find elements of matching type
        matching_elements = [
            elem for elem in elements 
            if elem.get('type') == caption_type or elem.get('element_type') == caption_type.upper()
        ]
        
        # Find the closest element
        closest_element = None
        min_distance = float('inf')
        
        for element in matching_elements:
            elem_pos = element.get('position', element.get('page_number', 0) * 1000)
            distance = abs(elem_pos - caption_pos)
            
            if distance < min_distance and distance <= max_distance:
                min_distance = distance
                closest_element = element
        
        return closest_element
    
    def link_all_captions(self, captions: List[Dict[str, Any]], elements: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Link all captions to their corresponding elements
        
        Args:
            captions: List of captions
            elements: List of elements
            
        Returns:
            Dictionary mapping caption IDs to element IDs
        """
        logger.info("Linking captions to elements")
        
        links = {}
        
        for i, caption in enumerate(captions):
            linked_element = self.link_caption_to_element(caption, elements)
            
            if linked_element:
                links[f"caption_{i}"] = {
                    'caption': caption,
                    'element': linked_element,
                    'distance': abs(caption['position'] - linked_element.get('position', 0))
                }
            else:
                logger.warning(f"Could not link caption: {caption['text']}")
        
        logger.info(f"Linked {len(links)} captions to elements")
        return links
    
    def extract_caption_context(self, caption: Dict[str, Any], text: str, context_lines: int = 2) -> str:
        """
        Extract context around a caption
        
        Args:
            caption: Caption dictionary
            text: Full document text
            context_lines: Number of lines before and after to include
            
        Returns:
            Context string
        """
        lines = text.split('\n')
        caption_line = caption['line_number']
        
        start_line = max(0, caption_line - context_lines)
        end_line = min(len(lines), caption_line + context_lines + 1)
        
        context_lines_list = lines[start_line:end_line]
        return '\n'.join(context_lines_list)
    
    def validate_caption_links(self, links: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate caption links and flag potential issues
        
        Args:
            links: Dictionary of caption links
            
        Returns:
            Validation results
        """
        validation = {
            'total_captions': len(links),
            'linked_captions': 0,
            'unlinked_captions': 0,
            'issues': []
        }
        
        for link_id, link_data in links.items():
            if link_data['element']:
                validation['linked_captions'] += 1
                
                # Check for potential issues
                if link_data['distance'] > 10:
                    validation['issues'].append({
                        'link_id': link_id,
                        'issue': 'large_distance',
                        'distance': link_data['distance']
                    })
            else:
                validation['unlinked_captions'] += 1
                validation['issues'].append({
                    'link_id': link_id,
                    'issue': 'no_link_found'
                })
        
        return validation
