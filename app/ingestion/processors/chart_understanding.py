"""
Chart understanding for analyzing charts and graphs
"""

from typing import Dict, List, Any, Optional
from app.llm.llm_client import LLMClient
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class ChartUnderstanding:
    """Analyze and understand charts using LLM"""
    
    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm_client = llm_client or LLMClient()
    
    def analyze_chart(self, image: Dict[str, Any], context: str = "") -> Dict[str, Any]:
        """
        Analyze a chart image
        
        Args:
            image: Image data (should be a chart)
            context: Surrounding context text
            
        Returns:
            Chart analysis results
        """
        logger.info(f"Analyzing chart: {image.get('image_id', 'unknown')}")
        
        # Build prompt
        prompt = self._build_analysis_prompt(image, context)
        
        try:
            analysis = self.llm_client.generate_response(
                prompt=prompt,
                max_tokens=500,
                temperature=0.3
            )
            
            # Parse analysis into structured data
            parsed_analysis = self._parse_analysis(analysis)
            
            logger.info(f"Analyzed chart: {image.get('image_id')}")
            return parsed_analysis
            
        except Exception as e:
            logger.error(f"Error analyzing chart: {str(e)}")
            return self._generate_fallback_analysis(image, context)
    
    def _build_analysis_prompt(self, image: Dict[str, Any], context: str) -> str:
        """Build prompt for chart analysis"""
        caption = image.get('caption', '')
        chart_type = image.get('chart_type', '')
        
        prompt = f"""Please analyze the following chart in detail.

Context: {context}

"""
        
        if caption:
            prompt += f"Chart Caption: {caption}\n\n"
        
        if chart_type:
            prompt += f"Chart Type: {chart_type}\n\n"
        
        prompt += """Please provide a structured analysis with the following sections:
1. Chart Type: What type of chart is this?
2. Data Variables: What are the key variables shown?
3. Trends: What trends or patterns are visible?
4. Key Insights: What are the main takeaways?
5. Data Summary: Brief summary of the data shown

Format your response as:
Chart Type: [type]
Data Variables: [variables]
Trends: [trends]
Key Insights: [insights]
Data Summary: [summary]

Analysis:"""
        
        return prompt
    
    def _parse_analysis(self, analysis: str) -> Dict[str, Any]:
        """Parse LLM analysis into structured data"""
        parsed = {
            'chart_type': '',
            'data_variables': [],
            'trends': '',
            'key_insights': '',
            'data_summary': ''
        }
        
        lines = analysis.split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            
            if line.startswith('Chart Type:'):
                parsed['chart_type'] = line.replace('Chart Type:', '').strip()
            elif line.startswith('Data Variables:'):
                parsed['data_variables'] = [v.strip() for v in line.replace('Data Variables:', '').split(',')]
            elif line.startswith('Trends:'):
                parsed['trends'] = line.replace('Trends:', '').strip()
            elif line.startswith('Key Insights:'):
                parsed['key_insights'] = line.replace('Key Insights:', '').strip()
            elif line.startswith('Data Summary:'):
                parsed['data_summary'] = line.replace('Data Summary:', '').strip()
        
        return parsed
    
    def _generate_fallback_analysis(self, image: Dict[str, Any], context: str) -> Dict[str, Any]:
        """Generate basic analysis without LLM"""
        chart_type = image.get('chart_type', 'unknown')
        caption = image.get('caption', '')
        
        return {
            'chart_type': chart_type,
            'data_variables': [],
            'trends': 'Unable to determine trends without detailed analysis',
            'key_insights': caption if caption else 'No insights available',
            'data_summary': f'{chart_type} chart visualization'
        }
    
    def extract_chart_data(self, image: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract structured data from chart analysis
        
        Args:
            image: Image data with analysis
            
        Returns:
            Structured chart data
        """
        analysis = image.get('analysis', {})
        
        return {
            'chart_type': analysis.get('chart_type', image.get('chart_type', 'unknown')),
            'variables': analysis.get('data_variables', []),
            'trends': analysis.get('trends', ''),
            'insights': analysis.get('key_insights', ''),
            'summary': analysis.get('data_summary', '')
        }
    
    def compare_charts(self, chart1: Dict[str, Any], chart2: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compare two charts
        
        Args:
            chart1: First chart data
            chart2: Second chart data
            
        Returns:
            Comparison results
        """
        logger.info("Comparing two charts")
        
        analysis1 = chart1.get('analysis', {})
        analysis2 = chart2.get('analysis', {})
        
        comparison = {
            'chart1_type': analysis1.get('chart_type', 'unknown'),
            'chart2_type': analysis2.get('chart_type', 'unknown'),
            'similar_type': analysis1.get('chart_type') == analysis2.get('chart_type'),
            'shared_variables': set(analysis1.get('data_variables', [])) & set(analysis2.get('data_variables', [])),
            'trend_comparison': self._compare_trends(analysis1.get('trends', ''), analysis2.get('trends', ''))
        }
        
        return comparison
    
    def _compare_trends(self, trend1: str, trend2: str) -> str:
        """Compare trend descriptions"""
        if trend1 == trend2:
            return "Both charts show similar trends"
        
        # Simple keyword comparison
        trend1_lower = trend1.lower()
        trend2_lower = trend2.lower()
        
        if 'increase' in trend1_lower and 'increase' in trend2_lower:
            return "Both charts show increasing trends"
        elif 'decrease' in trend1_lower and 'decrease' in trend2_lower:
            return "Both charts show decreasing trends"
        
        return "Charts show different trends"
    
    def batch_analyze_charts(self, images: List[Dict[str, Any]], contexts: List[str]) -> List[Dict[str, Any]]:
        """
        Analyze multiple charts in batch
        
        Args:
            images: List of chart images
            contexts: List of context strings
            
        Returns:
            List of analysis results
        """
        logger.info(f"Batch analyzing {len(images)} charts")
        
        analyses = []
        for i, image in enumerate(images):
            if image.get('is_chart', False):
                context = contexts[i] if i < len(contexts) else ""
                analysis = self.analyze_chart(image, context)
                analyses.append(analysis)
            else:
                analyses.append({})
        
        return analyses
