"""
Section detector for identifying document sections
"""

from typing import Dict, List, Any, Optional
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class SectionDetector:
    """Detect sections in documents based on headings and content"""
    
    def __init__(self):
        pass
    
    def detect_sections(self, text: str, headings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Detect sections based on headings
        
        Args:
            text: Document text
            headings: List of detected headings
            
        Returns:
            List of detected sections
        """
        logger.info("Detecting document sections")
        
        if not headings:
            # No headings, treat entire document as one section
            return [{
                'section_id': 'section_0',
                'heading': 'Document',
                'level': 0,
                'start_position': 0,
                'end_position': len(text),
                'content': text,
                'parent_section_id': None
            }]
        
        sections = []
        lines = text.split('\n')
        
        # Create sections from headings
        for i, heading in enumerate(headings):
            start_pos = heading['position']
            
            # End position is the next heading's position or end of document
            if i + 1 < len(headings):
                end_pos = headings[i + 1]['position']
            else:
                end_pos = len(lines)
            
            # Extract section content
            section_lines = lines[start_pos:end_pos]
            section_content = '\n'.join(section_lines)
            
            # Find parent section
            parent_section_id = self._find_parent_section(heading, headings, i)
            
            section = {
                'section_id': f"section_{i}",
                'heading': heading['text'],
                'level': heading['level'],
                'start_position': start_pos,
                'end_position': end_pos,
                'content': section_content,
                'parent_section_id': parent_section_id
            }
            
            sections.append(section)
        
        logger.info(f"Detected {len(sections)} sections")
        return sections
    
    def _find_parent_section(self, heading: Dict[str, Any], headings: List[Dict[str, Any]], current_idx: int) -> Optional[str]:
        """Find the parent section for a heading"""
        current_level = heading.get('level') or 1
        
        # Look backwards for a heading with lower level
        for i in range(current_idx - 1, -1, -1):
            if (headings[i].get('level') or 1) < current_level:
                return f"section_{i}"
        
        return None
    
    def build_section_tree(self, sections: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Build a tree structure from sections
        
        Args:
            sections: List of sections
            
        Returns:
            Tree structure
        """
        logger.info("Building section tree")
        
        # Create a map of section_id to section
        section_map = {s['section_id']: s for s in sections}
        
        # Build tree
        tree = {
            'section_id': 'root',
            'heading': 'Root',
            'level': 0,
            'children': []
        }
        
        for section in sections:
            parent_id = section.get('parent_section_id', 'root')
            
            if parent_id == 'root':
                tree['children'].append(section)
            elif parent_id in section_map:
                parent = section_map[parent_id]
                if 'children' not in parent:
                    parent['children'] = []
                parent['children'].append(section)
        
        return tree
    
    def get_section_for_position(self, sections: List[Dict[str, Any]], position: int) -> Optional[Dict[str, Any]]:
        """
        Get the section containing a given position
        
        Args:
            sections: List of sections
            position: Position in document
            
        Returns:
            Section dictionary or None
        """
        for section in sections:
            if section['start_position'] <= position < section['end_position']:
                return section
        
        return None
    
    def merge_small_sections(self, sections: List[Dict[str, Any]], min_length: int = 100) -> List[Dict[str, Any]]:
        """
        Merge sections that are too small with their parent
        
        Args:
            sections: List of sections
            min_length: Minimum section length in characters
            
        Returns:
            List of merged sections
        """
        logger.info(f"Merging sections smaller than {min_length} characters")
        
        merged_sections = []
        i = 0
        
        while i < len(sections):
            current_section = sections[i]
            
            if len(current_section['content']) < min_length and i > 0:
                # Merge with previous section
                prev_section = merged_sections[-1]
                prev_section['content'] += '\n' + current_section['content']
                prev_section['end_position'] = current_section['end_position']
            else:
                merged_sections.append(current_section)
            
            i += 1
        
        logger.info(f"Merged to {len(merged_sections)} sections")
        return merged_sections
    
    def extract_section_metadata(self, section: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract metadata from a section
        
        Args:
            section: Section dictionary
            
        Returns:
            Metadata dictionary
        """
        content = section['content']
        
        metadata = {
            'character_count': len(content),
            'word_count': len(content.split()),
            'line_count': len(content.split('\n')),
            'has_tables': 'table' in content.lower(),
            'has_images': 'figure' in content.lower() or 'image' in content.lower(),
            'first_line': content.split('\n')[0] if content else '',
            'last_line': content.split('\n')[-1] if content else ''
        }
        
        return metadata
