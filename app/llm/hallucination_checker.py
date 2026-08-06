"""
Hallucination checker for validating LLM responses
"""

from typing import Dict, Any, Optional
from app.llm.llm_client import LLMClient
from app.llm.prompt_builder import PromptBuilder
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class HallucinationChecker:
    """Check LLM responses for hallucinations"""
    
    def __init__(self, llm_client: Optional[LLMClient] = None, prompt_builder: Optional[PromptBuilder] = None):
        self.llm_client = llm_client or LLMClient()
        self.prompt_builder = prompt_builder or PromptBuilder()
    
    def check_hallucination(self, answer: str, context: str, use_llm: bool = True) -> Dict[str, Any]:
        """
        Check answer for hallucinations
        
        Args:
            answer: Generated answer
            context: Original context
            use_llm: Whether to use LLM for checking
            
        Returns:
            Hallucination check results
        """
        logger.info("Checking for hallucinations")
        
        if use_llm:
            return self._check_with_llm(answer, context)
        else:
            return self._check_simple(answer, context)
    
    def _check_with_llm(self, answer: str, context: str) -> Dict[str, Any]:
        """Check for hallucinations using LLM"""
        prompt = self.prompt_builder.build_hallucination_check_prompt(answer, context)
        
        try:
            check_result = self.llm_client.generate_response(prompt=prompt)
            
            # Parse the result
            has_hallucination = "no hallucinations" not in check_result.lower()
            
            return {
                'has_hallucination': has_hallucination,
                'check_result': check_result,
                'method': 'llm'
            }
        except Exception as e:
            logger.error(f"Error checking hallucinations with LLM: {str(e)}")
            return self._check_simple(answer, context)
    
    def _check_simple(self, answer: str, context: str) -> Dict[str, Any]:
        """Simple heuristic check for hallucinations"""
        # Extract key terms from answer
        answer_words = set(answer.lower().split())
        context_words = set(context.lower().split())
        
        # Check overlap
        overlap = answer_words & context_words
        overlap_ratio = len(overlap) / len(answer_words) if answer_words else 0
        
        # Low overlap might indicate hallucination
        has_hallucination = overlap_ratio < 0.3
        
        return {
            'has_hallucination': has_hallucination,
            'overlap_ratio': overlap_ratio,
            'method': 'heuristic'
        }
    
    def check_factual_consistency(self, answer: str, context: str) -> Dict[str, Any]:
        """
        Check factual consistency between answer and context
        
        Args:
            answer: Generated answer
            context: Original context
            
        Returns:
            Consistency check results
        """
        # Extract numerical values and named entities
        answer_numbers = self._extract_numbers(answer)
        context_numbers = self._extract_numbers(context)
        
        # Check if numbers in answer exist in context
        inconsistent_numbers = []
        for num in answer_numbers:
            if num not in context_numbers:
                inconsistent_numbers.append(num)
        
        return {
            'consistent': len(inconsistent_numbers) == 0,
            'inconsistent_numbers': inconsistent_numbers,
            'answer_numbers': answer_numbers,
            'context_numbers': context_numbers
        }
    
    def _extract_numbers(self, text: str) -> set:
        """Extract numerical values from text"""
        import re
        # Find numbers (including decimals, percentages, etc.)
        pattern = r'\d+\.?\d*%?'
        numbers = re.findall(pattern, text)
        return set(numbers)
    
    def calculate_confidence_score(self, answer: str, context: str, retrieval_scores: list) -> float:
        """
        Calculate confidence score for the answer
        
        Args:
            answer: Generated answer
            context: Original context
            retrieval_scores: Scores from retrieval
            
        Returns:
            Confidence score (0-1)
        """
        # Base confidence from retrieval scores
        if retrieval_scores:
            avg_retrieval_score = sum(retrieval_scores) / len(retrieval_scores)
            base_confidence = min(avg_retrieval_score, 1.0)
        else:
            base_confidence = 0.5
        
        # Adjust based on hallucination check
        hallucination_check = self.check_hallucination(answer, context, use_llm=False)
        if hallucination_check['has_hallucination']:
            base_confidence *= 0.7
        
        # Adjust based on factual consistency
        consistency_check = self.check_factual_consistency(answer, context)
        if not consistency_check['consistent']:
            base_confidence *= 0.8
        
        return max(0.0, min(1.0, base_confidence))
    
    def flag_potential_hallucinations(self, answer: str, context: str) -> list:
        """
        Flag specific parts of answer that might be hallucinated
        
        Args:
            answer: Generated answer
            context: Original context
            
        Returns:
            List of potentially hallucinated phrases
        """
        # Split answer into sentences
        sentences = answer.split('.')
        
        flagged = []
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            # Check each sentence
            sentence_words = set(sentence.lower().split())
            context_words = set(context.lower().split())
            
            overlap = sentence_words & context_words
            overlap_ratio = len(overlap) / len(sentence_words) if sentence_words else 0
            
            if overlap_ratio < 0.2:
                flagged.append(sentence)
        
        return flagged
