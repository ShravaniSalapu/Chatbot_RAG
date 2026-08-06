"""
Image context linker for preserving context around images
"""

from typing import Dict, List, Any, Optional
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class ImageContextLinker:
    """Link images with their surrounding context"""
    
    def __init__(self, context_lines: int = 3):
        self.context_lines = context_lines
    
    def link_image_context(self, images: List[Dict[str, Any]], text: str) -> List[Dict[str, Any]]:
        """
        Link images with their surrounding context
        
        Args:
            images: List of images
            text: Full document text
            
        Returns:
            List of images with context
        """
        logger.info("Linking image context")
        
        lines = text.split('\n')
        
        for image in images:
            position = self._resolve_line_position(image, len(lines))
            
            # Extract context
            context_before = self._extract_context_before(lines, position)
            context_after = self._extract_context_after(lines, position)
            
            image['context_before'] = context_before
            image['context_after'] = context_after
            image['full_context'] = context_before + '\n' + context_after
        
        logger.info(f"Linked context for {len(images)} images")
        return images
    
    def _resolve_line_position(self, image: Dict[str, Any], total_lines: int) -> int:
        """Estimate line position from page/slide metadata."""
        page_number = image.get("page_number") or image.get("slide_number")
        if page_number:
            return self._estimate_position(int(page_number), total_lines)
        return 0

    def _estimate_position(self, page_number: int, total_lines: int) -> int:
        """Estimate line position from page number"""
        if page_number <= 0 or total_lines <= 0:
            return 0
        lines_per_page = max(total_lines // page_number, 1)
        return min(page_number * lines_per_page, max(total_lines - 1, 0))
    
    def _extract_context_before(self, lines: List[str], position: int) -> str:
        """Extract context before a position"""
        start = max(0, position - self.context_lines)
        context_lines = lines[start:position]
        return '\n'.join(context_lines)
    
    def _extract_context_after(self, lines: List[str], position: int) -> str:
        """Extract context after a position"""
        end = min(len(lines), position + self.context_lines + 1)
        context_lines = lines[position:end]
        return '\n'.join(context_lines)
    
    def find_image_heading(self, image: Dict[str, Any], headings: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Find the heading that introduces an image
        
        Args:
            image: Image dictionary
            headings: List of headings
            
        Returns:
            Heading dictionary or None
        """
        image_position = image.get('position', 0)
        
        # Find the closest heading before the image
        closest_heading = None
        min_distance = float('inf')
        
        for heading in headings:
            heading_position = heading.get('position', 0)
            if heading_position <= image_position:
                distance = image_position - heading_position
                if distance < min_distance:
                    min_distance = distance
                    closest_heading = heading
        
        return closest_heading
    
    def detect_chart_type(self, image: Dict[str, Any], context: str) -> Optional[str]:
        """
        Detect if an image is a chart and determine its type
        
        Args:
            image: Image dictionary
            context: Context text
            
        Returns:
            Chart type or None
        """
        context_lower = context.lower()
        
        chart_keywords = {
            'bar': ['bar chart', 'bar graph', 'column chart'],
            'line': ['line chart', 'line graph', 'trend'],
            'pie': ['pie chart', 'pie graph'],
            'scatter': ['scatter plot', 'scatter chart'],
            'area': ['area chart'],
            'histogram': ['histogram', 'distribution'],
            'box': ['box plot', 'boxplot']
        }
        
        for chart_type, keywords in chart_keywords.items():
            if any(keyword in context_lower for keyword in keywords):
                return chart_type
        
        return None
    
    def extract_image_description(self, image: Dict[str, Any], context: str) -> str:
        """
        Extract a description of the image from context
        
        Args:
            image: Image dictionary
            context: Context text
            
        Returns:
            Description string
        """
        # Look for sentences that mention the image
        sentences = context.split('.')
        
        description_sentences = []
        for sentence in sentences:
            sentence = sentence.strip()
            if any(keyword in sentence.lower() for keyword in ['figure', 'image', 'shows', 'displays', 'illustrates']):
                description_sentences.append(sentence)
        
        if description_sentences:
            return '. '.join(description_sentences[:2])
        
        return context[:200]  # Fallback to first 200 characters
    
    def link_related_images(self, images: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """
        Find images that are related to each other
        
        Args:
            images: List of images
            
        Returns:
            Dictionary mapping image IDs to related image IDs
        """
        logger.info("Finding related images")
        
        relations = {}
        
        for i, image1 in enumerate(images):
            image1_id = image1.get('image_id', f"image_{i}")
            related = []
            
            for j, image2 in enumerate(images):
                if i == j:
                    continue
                
                image2_id = image2.get('image_id', f"image_{j}")
                
                # Check if images are related
                if self._are_images_related(image1, image2):
                    related.append(image2_id)
            
            relations[image1_id] = related
        
        return relations
    
    def _are_images_related(self, image1: Dict[str, Any], image2: Dict[str, Any]) -> bool:
        """Check if two images are related"""
        # Check if they're on the same page
        if image1.get('page_number') == image2.get('page_number'):
            return True
        
        # Check if they have similar captions
        caption1 = image1.get('caption', '').lower()
        caption2 = image2.get('caption', '').lower()
        
        if caption1 and caption2:
            words1 = set(caption1.split())
            words2 = set(caption2.split())
            common_words = words1 & words2
            
            if len(common_words) > min(len(words1), len(words2)) * 0.3:
                return True
        
        return False
    
    def build_image_summary(self, image: Dict[str, Any]) -> str:
        """
        Build a summary of an image
        
        Args:
            image: Image dictionary
            
        Returns:
            Summary string
        """
        summary_parts = []
        
        if image.get('caption'):
            summary_parts.append(f"Caption: {image['caption']}")
        
        if image.get('is_chart'):
            summary_parts.append(f"Chart type: {image.get('chart_type', 'unknown')}")
        
        # Add context if available
        if image.get('context_before'):
            summary_parts.append(f"Context: {image['context_before'][:100]}")
        
        return '. '.join(summary_parts) if summary_parts else "Image with no available description"
