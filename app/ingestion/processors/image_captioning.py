"""
Image captioning for generating image descriptions using LLM
"""

from typing import Dict, List, Any, Optional
from app.llm.llm_client import LLMClient
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class ImageCaptioning:
    """Generate captions and descriptions for images using LLM"""
    
    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm_client = llm_client or LLMClient()
    
    def caption_image(self, image: Dict[str, Any], context: str = "") -> str:
        """
        Generate a caption/description for an image
        
        Args:
            image: Image data
            context: Surrounding context text
            
        Returns:
            Image description
        """
        logger.info(f"Captioning image: {image.get('image_id', 'unknown')}")
        
        # Build prompt
        prompt = self._build_caption_prompt(image, context)
        
        try:
            description = self.llm_client.generate_response(
                prompt=prompt,
                max_tokens=300,
                temperature=0.5
            )
            
            logger.info(f"Generated description for image: {image.get('image_id')}")
            return description
            
        except Exception as e:
            logger.error(f"Error generating image description: {str(e)}")
            return self._generate_fallback_caption(image, context)
    
    def _build_caption_prompt(self, image: Dict[str, Any], context: str) -> str:
        """Build prompt for image captioning"""
        caption = image.get('caption', '')
        is_chart = image.get('is_chart', False)
        chart_type = image.get('chart_type', '')
        
        prompt = f"""Please provide a detailed description of the following image.

Context: {context}

"""
        
        if caption:
            prompt += f"Image Caption: {caption}\n\n"
        
        if is_chart:
            prompt += f"This is a {chart_type} chart.\n\n"
        
        prompt += """Please describe:
1. What the image shows
2. Key elements or data points
3. Any patterns or trends visible
4. The overall message or purpose

Description:"""
        
        return prompt
    
    def _generate_fallback_caption(self, image: Dict[str, Any], context: str) -> str:
        """Generate a basic caption without LLM"""
        caption = image.get('caption', '')
        is_chart = image.get('is_chart', False)
        chart_type = image.get('chart_type', '')
        
        if caption:
            return caption
        
        if is_chart:
            return f"{chart_type} chart showing data visualization"
        
        if context:
            # Extract relevant context
            sentences = context.split('.')
            for sentence in sentences:
                if any(word in sentence.lower() for word in ['figure', 'image', 'shows', 'displays']):
                    return sentence.strip()
        
        return "Image with no available description"
    
    def extract_visual_elements(self, image: Dict[str, Any]) -> List[str]:
        """
        Extract visual elements from image description
        
        Args:
            image: Image data with description
            
        Returns:
            List of visual elements
        """
        description = image.get('description', '')
        
        if not description:
            return []
        
        # Simple keyword extraction
        visual_keywords = [
            'chart', 'graph', 'bar', 'line', 'pie', 'scatter',
            'axis', 'legend', 'title', 'label', 'data',
            'figure', 'image', 'diagram', 'illustration',
            'blue', 'red', 'green', 'color', 'trend'
        ]
        
        elements = []
        description_lower = description.lower()
        
        for keyword in visual_keywords:
            if keyword in description_lower:
                elements.append(keyword)
        
        return list(set(elements))
    
    def batch_caption_images(self, images: List[Dict[str, Any]], contexts: List[str]) -> List[str]:
        """
        Caption multiple images in batch
        
        Args:
            images: List of images
            contexts: List of context strings (one per image)
            
        Returns:
            List of descriptions
        """
        logger.info(f"Batch captioning {len(images)} images")
        
        descriptions = []
        for i, image in enumerate(images):
            context = contexts[i] if i < len(contexts) else ""
            description = self.caption_image(image, context)
            descriptions.append(description)
        
        return descriptions
    
    def enhance_caption_with_context(self, image: Dict[str, Any], context: str, heading: Optional[str] = None) -> str:
        """
        Enhance image caption with additional context
        
        Args:
            image: Image data
            context: Surrounding context
            heading: Section heading
            
        Returns:
            Enhanced description
        """
        base_description = image.get('description', '')
        
        if not base_description:
            base_description = self.caption_image(image, context)
        
        enhanced_parts = [base_description]
        
        if heading:
            enhanced_parts.append(f"Found in section: {heading}")
        
        if context:
            # Extract relevant context
            context_snippet = context[:200]
            enhanced_parts.append(f"Context: {context_snippet}")
        
        return '. '.join(enhanced_parts)
