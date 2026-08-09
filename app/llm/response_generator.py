"""
Response generator for creating LLM responses
"""

from typing import List, Dict, Any, Optional
from app.llm.llm_client import LLMClient
from app.llm.prompt_builder import PromptBuilder
from app.utils.logger import setup_logger
import time
import re

logger = setup_logger(__name__)


class ResponseGenerator:
    """Generate responses using LLM"""
    
    def __init__(self, llm_client: Optional[LLMClient] = None, prompt_builder: Optional[PromptBuilder] = None):
        self.llm_client = llm_client or LLMClient()
        self.prompt_builder = prompt_builder or PromptBuilder()
    
    def generate_rag_response(
        self,
        query: str,
        context: str,
        citations: Optional[List[Dict[str, Any]]] = None,
        temperature: Optional[float] = None,
        is_summary: bool = False
    ) -> Dict[str, Any]:
        """
        Generate RAG response
        
        Args:
            query: User query
            context: Retrieved context
            citations: Optional citation information
            temperature: Sampling temperature
            is_summary: Whether this is a summary-type query
            
        Returns:
            Response dictionary with answer and metadata
        """
        logger.info(f"Generating RAG response for query: {query}, is_summary: {is_summary}")
        
        start_time = time.time()
        
        # Build prompt
        prompt = self.prompt_builder.build_rag_prompt(query, context, citations, is_summary)
        
        try:
            # Generate response
            answer = self.llm_client.generate_response(
                prompt=prompt,
                system_prompt=self.prompt_builder.get_system_prompt(),
                temperature=temperature
            )
            
            processing_time = time.time() - start_time
            
            logger.info(f"Generated response in {processing_time:.2f}s")
            
            return {
                'answer': answer,
                'context_used': context,
                'citations': citations or [],
                'processing_time_ms': processing_time * 1000,
                'model_used': self.llm_client.model,
                'success': True
            }
        
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            processing_time = time.time() - start_time
            error_text = str(e)
            if "401" in error_text or "Unauthorized" in error_text:
                answer = (
                    "Could not generate an answer because the OpenRouter API key is invalid "
                    "or expired. Update OPENROUTER_API_KEY in your .env file and restart the server."
                )
            else:
                answer = "I apologize, but I encountered an error generating a response. Please try again."
            
            return {
                'answer': answer,
                'context_used': context,
                'citations': citations or [],
                'processing_time_ms': processing_time * 1000,
                'model_used': self.llm_client.model,
                'success': False,
                'error': str(e)
            }
    
    def generate_chat_response(
        self,
        query: str,
        context: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        temperature: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Generate chat response with conversation history
        
        Args:
            query: Current user query
            context: Retrieved context
            conversation_history: Previous conversation turns
            temperature: Sampling temperature
            
        Returns:
            Response dictionary
        """
        logger.info(f"Generating chat response for query: {query}")
        
        start_time = time.time()
        
        # Build prompt with conversation history
        prompt = self.prompt_builder.build_chat_prompt(query, context, conversation_history)
        
        try:
            answer = self.llm_client.generate_response(
                prompt=prompt,
                system_prompt=self.prompt_builder.get_system_prompt(),
                temperature=temperature
            )
            
            processing_time = time.time() - start_time
            
            return {
                'answer': answer,
                'context_used': context,
                'conversation_history': conversation_history,
                'processing_time_ms': processing_time * 1000,
                'model_used': self.llm_client.model,
                'success': True
            }
        
        except Exception as e:
            logger.error(f"Error generating chat response: {str(e)}")
            processing_time = time.time() - start_time
            
            return {
                'answer': "I apologize, but I encountered an error. Please try again.",
                'context_used': context,
                'processing_time_ms': processing_time * 1000,
                'model_used': self.llm_client.model,
                'success': False,
                'error': str(e)
            }
    
    def generate_multimodal_response(
        self,
        query: str,
        text_context: str,
        table_context: str = "",
        image_context: str = "",
        temperature: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Generate multimodal response
        
        Args:
            query: User query
            text_context: Text context
            table_context: Table context
            image_context: Image context
            temperature: Sampling temperature
            
        Returns:
            Response dictionary
        """
        logger.info(f"Generating multimodal response for query: {query}")
        
        start_time = time.time()
        
        # Build multimodal prompt
        prompt = self.prompt_builder.build_multimodal_prompt(
            query, text_context, table_context, image_context
        )
        
        try:
            answer = self.llm_client.generate_response(
                prompt=prompt,
                system_prompt=self.prompt_builder.get_system_prompt(),
                temperature=temperature
            )
            
            processing_time = time.time() - start_time
            
            return {
                'answer': answer,
                'text_context': text_context,
                'table_context': table_context,
                'image_context': image_context,
                'processing_time_ms': processing_time * 1000,
                'model_used': self.llm_client.model,
                'success': True
            }
        
        except Exception as e:
            logger.error(f"Error generating multimodal response: {str(e)}")
            processing_time = time.time() - start_time
            
            return {
                'answer': "I apologize, but I encountered an error. Please try again.",
                'processing_time_ms': processing_time * 1000,
                'model_used': self.llm_client.model,
                'success': False,
                'error': str(e)
            }
    
    def generate_summary(self, text: str, max_length: int = 200) -> str:
        """
        Generate summary of text
        
        Args:
            text: Text to summarize
            max_length: Maximum summary length
            
        Returns:
            Summary text
        """
        logger.info("Generating summary")
        
        prompt = self.prompt_builder.build_summarization_prompt(text, max_length)
        
        try:
            summary = self.llm_client.generate_response(prompt=prompt)
            return summary
        except Exception as e:
            logger.error(f"Error generating summary: {str(e)}")
            return text[:max_length]
    
    def format_answer_structure(self, answer: str, is_summary: bool = False) -> str:
        """
        Improve answer structure and formatting
        
        Args:
            answer: Raw answer from LLM
            is_summary: Whether this is a summary-type answer
            
        Returns:
            Formatted answer with better structure
        """
        if not answer:
            return answer
        
        # For summary answers, ensure proper structure
        if is_summary:
            return self._format_summary_structure(answer)
        
        # For general answers, improve readability
        return self._improve_readability(answer)
    
    def _format_summary_structure(self, answer: str) -> str:
        """Format summary with proper headings and structure"""
        lines = answer.split('\n')
        formatted_lines = []
        
        # Ensure key sections exist for summaries
        has_overview = any('overview' in line.lower() for line in lines)
        has_features = any('feature' in line.lower() or 'component' in line.lower() for line in lines)
        has_architecture = any('architecture' in line.lower() or 'structure' in line.lower() for line in lines)
        has_conclusion = any('conclusion' in line.lower() for line in lines)
        
        # Add missing section headers if content suggests they should exist
        if not has_overview and len(lines) > 3:
            formatted_lines.append("## Overview")
            formatted_lines.append("")
        
        current_section = "Overview"
        for line in lines:
            line = line.strip()
            if not line:
                formatted_lines.append("")
                continue
            
            # Detect potential section headers
            if any(keyword in line.lower() for keyword in ['overview', 'purpose', 'introduction']):
                if not line.startswith('#'):
                    line = f"## {line}"
                current_section = "Overview"
            elif any(keyword in line.lower() for keyword in ['feature', 'component', 'module', 'key aspect']):
                if not line.startswith('#') and has_features:
                    line = f"### {line}"
                current_section = "Features"
            elif any(keyword in line.lower() for keyword in ['architecture', 'structure', 'design']):
                if not line.startswith('#'):
                    line = f"## {line}"
                current_section = "Architecture"
            elif any(keyword in line.lower() for keyword in ['conclusion', 'summary', 'final']):
                if not line.startswith('#'):
                    line = f"## {line}"
                current_section = "Conclusion"
            
            formatted_lines.append(line)
        
        # Add conclusion if missing and answer is substantial
        if not has_conclusion and len(formatted_lines) > 10:
            formatted_lines.append("")
            formatted_lines.append("## Conclusion")
        
        return '\n'.join(formatted_lines)
    
    def _improve_readability(self, answer: str) -> str:
        """Improve general answer readability"""
        lines = answer.split('\n')
        formatted_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                formatted_lines.append("")
                continue
            
            # Convert numbered lists to proper format
            if re.match(r'^\d+\.', line) and not line.startswith('  '):
                # Ensure numbered lists are properly formatted
                formatted_lines.append(line)
            # Convert bullet points
            elif line.startswith('-') or line.startswith('*'):
                formatted_lines.append(line)
            # Detect potential headings (short, capitalized lines)
            elif len(line) < 100 and line.isupper() and not line.startswith('#'):
                formatted_lines.append(f"### {line}")
            else:
                formatted_lines.append(line)
        
        return '\n'.join(formatted_lines)
