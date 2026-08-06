"""
Heading detector for identifying document headings
"""

from typing import Dict, List, Any, Optional
import re
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class HeadingDetector:
    """Detect headings in document text"""
    
    def __init__(self):
        # Patterns for detecting headings
        self.heading_patterns = [
            # Numbered headings: 1. Title, 1.1 Subtitle, etc.
            r'^\d+\.\s+[A-Z][^\n]{1,100}$',
            r'^\d+\.\d+\s+[A-Z][^\n]{1,100}$',
            r'^\d+\.\d+\.\d+\s+[A-Z][^\n]{1,100}$',
            
            # All caps headings
            r'^[A-Z][A-Z\s]{5,80}$',
            
            # Common heading styles
            r'^#{1,6}\s+.+$',  # Markdown style
            r'^[A-Z][a-z]+:\s+.+$',  # Colon followed by text
            
            # Roman numerals
            r'^[IVXLCDM]+\.\s+[A-Z][^\n]{1,100}$',
            
            # Letter headings: A., B., etc.
            r'^[A-Z]\.\s+[A-Z][^\n]{1,100}$',
        ]
        
        self.compiled_patterns = [re.compile(pattern) for pattern in self.heading_patterns]
    
    def detect_headings(self, text: str) -> List[Dict[str, Any]]:
        """
        Detect headings in text
        
        Args:
            text: Document text
            
        Returns:
            List of detected headings with metadata
        """
        logger.info("Detecting headings in document")
        
        headings = []
        lines = text.split('\n')
        
        for line_num, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            
            heading_info = self._is_heading(line)
            if heading_info:
                heading_info['line_number'] = line_num
                heading_info['position'] = line_num
                headings.append(heading_info)
        
        logger.info(f"Detected {len(headings)} headings")
        return headings
    
    def _is_heading(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Check if text is a heading and return heading info
        
        Args:
            text: Text to check
            
        Returns:
            Dictionary with heading info or None
        """
        for pattern_idx, pattern in enumerate(self.compiled_patterns):
            if pattern.match(text):
                level = self._determine_level(text, pattern_idx)
                return {
                    'text': text,
                    'level': level,
                    'pattern_index': pattern_idx,
                    'type': self._get_heading_type(text)
                }
        
        # Additional heuristics
        if self._is_heading_by_heuristics(text):
            return {
                'text': text,
                'level': self._estimate_level(text),
                'pattern_index': -1,
                'type': 'heuristic'
            }
        
        return None
    
    def _determine_level(self, text: str, pattern_idx: int) -> int:
        """Determine heading level based on pattern and text"""
        # Numbered headings
        if pattern_idx in [0, 1, 2]:
            # Count dots to determine level
            dot_count = text.count('.')
            return min(dot_count, 6)
        
        # Markdown style
        if pattern_idx == 3:
            hash_count = text.count('#')
            return hash_count
        
        # Default to level 1 or 2
        return 1 if len(text) < 50 else 2
    
    def _get_heading_type(self, text: str) -> str:
        """Get heading type"""
        if text.startswith('#'):
            return 'markdown'
        elif re.match(r'^\d+\.', text):
            return 'numbered'
        elif text.isupper():
            return 'uppercase'
        elif re.match(r'^[IVXLCDM]+\.', text):
            return 'roman'
        elif re.match(r'^[A-Z]\.', text):
            return 'letter'
        else:
            return 'other'
    
    def _is_heading_by_heuristics(self, text: str) -> bool:
        """Check if text is a heading using heuristics"""
        if not text:
            return False
        # Short, capitalized lines
        if len(text) < 80 and text[0].isupper() and text[-1] not in '.!?;:':
            # Check if it's not a sentence
            if not any(word in text.lower() for word in ['the', 'and', 'is', 'are', 'was', 'were']):
                return True
        
        # Lines ending with colon
        if text.endswith(':') and len(text) < 100:
            return True
        
        return False
    
    def _estimate_level(self, text: str) -> int:
        """Estimate heading level based on text characteristics"""
        # Shorter text is likely higher level
        if len(text) < 30:
            return 1
        elif len(text) < 60:
            return 2
        else:
            return 3
    
    def build_heading_hierarchy(self, headings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Build hierarchy from detected headings
        
        Args:
            headings: List of detected headings
            
        Returns:
            Dictionary with heading hierarchy
        """
        logger.info("Building heading hierarchy")
        
        hierarchy = {
            'root': {
                'children': [],
                'level': 0
            }
        }
        
        stack = [hierarchy['root']]
        
        for heading in headings:
            level = heading['level']
            
            # Find the appropriate parent
            while len(stack) > 1 and stack[-1]['level'] >= level:
                stack.pop()
            
            parent = stack[-1]
            
            # Add heading as child
            heading_node = {
                'text': heading['text'],
                'level': level,
                'position': heading['position'],
                'children': []
            }
            
            parent['children'].append(heading_node)
            stack.append(heading_node)
        
        return hierarchy
    
    def get_heading_at_position(self, headings: List[Dict[str, Any]], position: int) -> Optional[Dict[str, Any]]:
        """
        Get the most relevant heading for a given position
        
        Args:
            headings: List of headings
            position: Position in document
            
        Returns:
            Heading dictionary or None
        """
        # Find the last heading before this position
        relevant_heading = None
        for heading in headings:
            if heading['position'] <= position:
                relevant_heading = heading
            else:
                break
        
        return relevant_heading
