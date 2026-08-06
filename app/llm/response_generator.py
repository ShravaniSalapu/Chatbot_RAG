"""
Response generator for creating LLM responses
"""

from typing import List, Dict, Any, Optional
from app.llm.llm_client import LLMClient
from app.llm.prompt_builder import PromptBuilder
from app.utils.logger import setup_logger
import time

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
        temperature: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Generate RAG response
        
        Args:
            query: User query
            context: Retrieved context
            citations: Optional citation information
            temperature: Sampling temperature
            
        Returns:
            Response dictionary with answer and metadata
        """
        logger.info(f"Generating RAG response for query: {query}")
        
        start_time = time.time()
        
        # Build prompt
        prompt = self.prompt_builder.build_rag_prompt(query, context, citations)
        
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
