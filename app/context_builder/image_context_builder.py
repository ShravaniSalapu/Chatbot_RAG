"""
Image context builder for preserving image information
"""

from typing import List, Dict, Any, Optional
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class ImageContextBuilder:
    """Build context around image data"""
    
    def __init__(self):
        pass
    
    def build_image_context(self, image_results: List[Dict[str, Any]], include_description: bool = True) -> str:
        """
        Build context from image results
        
        Args:
            image_results: Image search results
            include_description: Whether to include image descriptions
            
        Returns:
            Image context string
        """
        logger.info(f"Building image context from {len(image_results)} results")
        
        if not image_results:
            return ""
        
        context_parts = []
        
        for result in image_results:
            content = result.get('content', '')
            metadata = result.get('metadata', {})
            
            image_part = f"Image Information:\n{content}"
            
            if include_description and metadata.get('description'):
                image_part += f"\n\nDescription: {metadata['description']}"
            
            if metadata.get('caption'):
                image_part += f"\n\nCaption: {metadata['caption']}"
            
            if metadata.get('is_chart'):
                image_part += f"\n\nChart Type: {metadata.get('chart_type', 'unknown')}"
            
            context_parts.append(image_part)
        
        return "\n\n---\n\n".join(context_parts)
    
    def build_image_with_context(self, image_results: List[Dict[str, Any]]) -> str:
        """
        Build context with surrounding text for images
        
        Args:
            image_results: Image search results
            
        Returns:
            Image context with surrounding text
        """
        logger.info("Building image context with surrounding text")
        
        context_parts = []
        
        for result in image_results:
            metadata = result.get('metadata', {})
            
            context_part = ""
            
            if metadata.get('context_before'):
                context_part += f"Before:\n{metadata['context_before']}\n\n"
            
            context_part += f"Image: {result.get('content', '')}"
            
            if metadata.get('context_after'):
                context_part += f"\n\nAfter:\n{metadata['context_after']}"
            
            context_parts.append(context_part)
        
        return "\n\n---\n\n".join(context_parts)
    
    def build_chart_analysis(self, image_results: List[Dict[str, Any]]) -> str:
        """
        Build context specifically for chart analysis
        
        Args:
            image_results: Image search results (charts)
            
        Returns:
            Chart analysis context
        """
        logger.info("Building chart analysis context")
        
        context_parts = []
        
        for result in image_results:
            metadata = result.get('metadata', {})
            
            if not metadata.get('is_chart'):
                continue
            
            chart_part = f"Chart Analysis:\n"
            chart_part += f"Type: {metadata.get('chart_type', 'unknown')}\n"
            chart_part += f"Description: {result.get('content', '')}\n"
            
            if metadata.get('analysis'):
                analysis = metadata['analysis']
                chart_part += f"\nTrends: {analysis.get('trends', '')}\n"
                chart_part += f"Key Insights: {analysis.get('key_insights', '')}\n"
            
            context_parts.append(chart_part)
        
        return "\n\n---\n\n".join(context_parts)
    
    def extract_visual_descriptions(self, image_results: List[Dict[str, Any]]) -> List[str]:
        """
        Extract visual descriptions from image results
        
        Args:
            image_results: Image search results
            
        Returns:
            List of descriptions
        """
        descriptions = []
        
        for result in image_results:
            metadata = result.get('metadata', {})
            
            if metadata.get('description'):
                descriptions.append(metadata['description'])
            
            if metadata.get('caption'):
                descriptions.append(metadata['caption'])
        
        return descriptions
