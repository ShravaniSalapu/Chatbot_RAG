"""
Document tree builder for creating structured document objects
"""

from typing import Dict, List, Any, Optional
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class DocumentTreeBuilder:
    """Build structured document tree from parsed data"""
    
    def __init__(self):
        pass
    
    def build_tree(self, document_data: Dict[str, Any], headings: List[Dict[str, Any]], sections: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Build a hierarchical document tree
        
        Args:
            document_data: Parsed document data
            headings: List of detected headings
            sections: List of detected sections
            
        Returns:
            Document tree structure
        """
        logger.info("Building document tree")
        
        tree = {
            'document_id': document_data.get('document_id', ''),
            'type': 'root',
            'children': [],
            'metadata': {
                'total_sections': len(sections),
                'total_headings': len(headings)
            }
        }
        
        # Build section hierarchy
        section_hierarchy = self._build_section_hierarchy(sections)
        
        # Add elements to tree
        if 'pages' in document_data:
            self._add_pages_to_tree(tree, document_data['pages'])
        elif 'paragraphs' in document_data:
            self._add_paragraphs_to_tree(tree, document_data['paragraphs'])
        
        # Add tables and images
        if 'tables' in document_data:
            self._add_tables_to_tree(tree, document_data['tables'])
        
        if 'images' in document_data:
            self._add_images_to_tree(tree, document_data['images'])
        
        tree['section_hierarchy'] = section_hierarchy
        
        logger.info("Document tree built successfully")
        return tree
    
    def _build_section_hierarchy(self, sections: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build hierarchical structure from sections"""
        hierarchy = {
            'root': {
                'section_id': 'root',
                'heading': 'Root',
                'level': 0,
                'children': []
            }
        }
        
        section_map = {s['section_id']: s for s in sections}
        stack = [hierarchy['root']]
        
        for section in sorted(sections, key=lambda x: x['start_position']):
            level = section['level']
            
            # Find appropriate parent
            while len(stack) > 1 and stack[-1]['level'] >= level:
                stack.pop()
            
            parent = stack[-1]
            
            section_node = {
                'section_id': section['section_id'],
                'heading': section['heading'],
                'level': level,
                'start_position': section['start_position'],
                'end_position': section['end_position'],
                'children': []
            }
            
            parent['children'].append(section_node)
            stack.append(section_node)
        
        return hierarchy
    
    def _add_pages_to_tree(self, tree: Dict[str, Any], pages: List[Dict[str, Any]]) -> None:
        """Add pages to document tree"""
        for page in pages:
            page_node = {
                'type': 'page',
                'page_number': page.get('page_number', 0),
                'children': []
            }
            
            # Add elements from page
            if 'elements' in page:
                for element in page['elements']:
                    element_node = {
                        'type': element.get('type', 'unknown'),
                        'content': element.get('text', ''),
                        'metadata': element
                    }
                    page_node['children'].append(element_node)
            
            tree['children'].append(page_node)
    
    def _add_paragraphs_to_tree(self, tree: Dict[str, Any], paragraphs: List[Dict[str, Any]]) -> None:
        """Add paragraphs to document tree"""
        for para in paragraphs:
            para_node = {
                'type': 'paragraph',
                'content': para.get('text', ''),
                'style': para.get('style', 'Normal'),
                'level': para.get('level', 0),
                'metadata': para
            }
            tree['children'].append(para_node)
    
    def _add_tables_to_tree(self, tree: Dict[str, Any], tables: List[Dict[str, Any]]) -> None:
        """Add tables to document tree"""
        for table in tables:
            table_node = {
                'type': 'table',
                'table_id': table.get('table_id', ''),
                'headers': table.get('headers', []),
                'rows': table.get('rows', []),
                'caption': table.get('caption', ''),
                'metadata': table
            }
            tree['children'].append(table_node)
    
    def _add_images_to_tree(self, tree: Dict[str, Any], images: List[Dict[str, Any]]) -> None:
        """Add images to document tree"""
        for image in images:
            image_node = {
                'type': 'image',
                'image_id': image.get('image_id', ''),
                'caption': image.get('caption', ''),
                'description': image.get('description', ''),
                'is_chart': image.get('is_chart', False),
                'metadata': image
            }
            tree['children'].append(image_node)
    
    def flatten_tree(self, tree: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Flatten the document tree into a list of nodes
        
        Args:
            tree: Document tree
            
        Returns:
            List of flattened nodes
        """
        nodes = []
        
        def traverse(node, parent_id=None):
            node_copy = node.copy()
            node_copy['parent_id'] = parent_id
            nodes.append(node_copy)
            
            if 'children' in node:
                for child in node['children']:
                    traverse(child, node.get('section_id', node.get('page_number', '')))
        
        traverse(tree)
        return nodes
    
    def get_element_by_id(self, tree: Dict[str, Any], element_id: str) -> Optional[Dict[str, Any]]:
        """
        Get an element by its ID from the tree
        
        Args:
            tree: Document tree
            element_id: Element ID to search for
            
        Returns:
            Element node or None
        """
        def search(node):
            if node.get('section_id') == element_id or node.get('table_id') == element_id or node.get('image_id') == element_id:
                return node
            
            if 'children' in node:
                for child in node['children']:
                    result = search(child)
                    if result:
                        return result
            
            return None
        
        return search(tree)
    
    def get_path_to_element(self, tree: Dict[str, Any], element_id: str) -> List[str]:
        """
        Get the path (list of section IDs) to an element
        
        Args:
            tree: Document tree
            element_id: Element ID
            
        Returns:
            List of section IDs in the path
        """
        path = []
        
        def find_path(node, target_id, current_path):
            current_path = current_path + [node.get('section_id', node.get('page_number', ''))]
            
            if node.get('section_id') == target_id or node.get('table_id') == target_id or node.get('image_id') == target_id:
                return current_path
            
            if 'children' in node:
                for child in node['children']:
                    result = find_path(child, target_id, current_path)
                    if result:
                        return result
            
            return None
        
        result = find_path(tree, element_id, [])
        return result if result else []
