"""
Chat pipeline for end-to-end RAG chat
"""

from typing import Dict, Any, Optional, List
from app.workflows.retrieval_pipeline import RetrievalPipeline
from app.llm.response_generator import ResponseGenerator
from app.llm.citation_builder import CitationBuilder
from app.llm.hallucination_checker import HallucinationChecker
from app.utils.logger import setup_logger
import os

logger = setup_logger(__name__)


class ChatPipeline:
    """End-to-end pipeline for RAG chat"""
    
    def __init__(self):
        self.retrieval_pipeline = RetrievalPipeline()
        self.response_generator = ResponseGenerator()
        self.citation_builder = CitationBuilder()
        self.hallucination_checker = HallucinationChecker()
    
    def chat(
        self,
        query: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        document_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        allowed_document_ids: Optional[List[str]] = None,
        retrieval_method: str = "hybrid",
        use_reranking: bool = True,
        check_hallucinations: bool = True,
        max_context_tokens: int = int(os.getenv("MAX_CONTEXT_TOKENS", "6000")),
        top_k: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Process a chat query through the complete RAG pipeline
        
        Args:
            query: User query
            conversation_history: Optional conversation history
            retrieval_method: Retrieval method to use
            use_reranking: Whether to rerank results
            check_hallucinations: Whether to check for hallucinations
            max_context_tokens: Maximum tokens in context
            
        Returns:
            Complete chat response
        """
        logger.info(f"Chat pipeline for query: {query}")
        
        # Step 1: Retrieve relevant context
        retrieval_result = self.retrieval_pipeline.retrieve(
            query=query,
            retrieval_method=retrieval_method,
            document_id=document_id,
            tenant_id=tenant_id,
            allowed_document_ids=allowed_document_ids,
            use_reranking=use_reranking,
            max_tokens=max_context_tokens,
            top_k=top_k,
        )
        
        if not retrieval_result['results']:
            return {
                'answer': "I couldn't find relevant information in the documents to answer your question.",
                'sources': [],
                'citations': [],
                'confidence_score': 0.0,
                'processing_time_ms': 0.0,
                'model_used': self.response_generator.llm_client.model,
                'retrieval_method': retrieval_method,
                'has_hallucination': False
            }
        
        # Step 2: Generate response
        # Check if this is a summary-type query
        query_analysis = self.retrieval_pipeline.query_analyzer.analyze_query(query)
        is_summary = query_analysis['is_summary']
        
        if conversation_history:
            response = self.response_generator.generate_chat_response(
                query=query,
                context=retrieval_result['context'],
                conversation_history=conversation_history,
            )
        else:
            response = self.response_generator.generate_rag_response(
                query=query,
                context=retrieval_result['context'],
                citations=retrieval_result['citations'],
                is_summary=is_summary,
            )
        
        # Step 2.5: Improve answer formatting
        if response.get('success'):
            formatted_answer = self.response_generator.format_answer_structure(
                response['answer'], 
                is_summary=is_summary
            )
            response['answer'] = formatted_answer
        
        # Step 3: Build citations
        citation_objects = self.citation_builder.build_citation_objects(retrieval_result['citations'])
        cited_response = self.citation_builder.add_citations_to_answer(
            response['answer'],
            citation_objects
        )
        
        # Step 4: Check for hallucinations
        hallucination_result = None
        if check_hallucinations:
            hallucination_result = self.hallucination_checker.check_hallucination(
                response['answer'],
                retrieval_result['context']
            )
        
        # Step 5: Calculate confidence score
        retrieval_scores = [r.get('score', 0) for r in retrieval_result['results']]
        confidence_score = self.hallucination_checker.calculate_confidence_score(
            response['answer'],
            retrieval_result['context'],
            retrieval_scores
        )
        
        # Step 6: Build sources
        sources = [
            {
                'chunk_id': cit['chunk_id'],
                'document_id': cit['document_id'],
                'filename': cit['filename'],
                'page_number': cit['page_number'],
                'heading': cit['heading'],
                'snippet': cit['snippet']
            }
            for cit in citation_objects
        ]
        
        return {
            'answer': cited_response['cited_answer'],
            'sources': sources,
            'citations': citation_objects,
            'confidence_score': confidence_score,
            'processing_time_ms': response['processing_time_ms'],
            'model_used': response['model_used'],
            'retrieval_method': retrieval_result['retrieval_method'],
            'has_hallucination': hallucination_result['has_hallucination'] if hallucination_result else False,
            'hallucination_details': hallucination_result if hallucination_result else None,
            'context_used': [r['chunk_id'] for r in retrieval_result['results']]
        }
    
    def chat_with_history(
        self,
        query: str,
        conversation_history: List[Dict[str, str]],
        retrieval_method: str = "hybrid",
        max_context_tokens: int = int(os.getenv("MAX_CONTEXT_TOKENS", "6000")),
    ) -> Dict[str, Any]:
        """
        Chat with conversation history
        
        Args:
            query: Current user query
            conversation_history: Previous conversation turns
            retrieval_method: Retrieval method
            max_context_tokens: Maximum context tokens
            
        Returns:
            Chat response
        """
        logger.info(f"Chat with history for query: {query}")
        
        # Retrieve context
        retrieval_result = self.retrieval_pipeline.retrieve(
            query=query,
            retrieval_method=retrieval_method,
            max_tokens=max_context_tokens
        )
        
        if not retrieval_result['results']:
            return {
                'answer': "I couldn't find relevant information.",
                'sources': [],
                'citations': [],
                'confidence_score': 0.0
            }
        
        # Generate response with history
        response = self.response_generator.generate_chat_response(
            query=query,
            context=retrieval_result['context'],
            conversation_history=conversation_history
        )
        
        return {
            'answer': response['answer'],
            'sources': [],
            'citations': retrieval_result['citations'],
            'confidence_score': 0.8,
            'processing_time_ms': response['processing_time_ms'],
            'model_used': response['model_used']
        }
    
    def multimodal_chat(
        self,
        query: str,
        include_tables: bool = True,
        include_images: bool = True,
        max_context_tokens: int = int(os.getenv("MAX_CONTEXT_TOKENS", "6000")),
    ) -> Dict[str, Any]:
        """
        Chat with multimodal context
        
        Args:
            query: User query
            include_tables: Whether to include table context
            include_images: Whether to include image context
            max_context_tokens: Maximum context tokens
            
        Returns:
            Multimodal chat response
        """
        logger.info(f"Multimodal chat for query: {query}")
        
        # Retrieve multimodal context
        retrieval_result = self.retrieval_pipeline.multimodal_retriever.retrieve_with_context(
            query=query,
            include_tables=include_tables,
            include_images=include_images
        )
        
        # Generate multimodal response
        response = self.response_generator.generate_multimodal_response(
            query=query,
            text_context=retrieval_result.get('text_context', ''),
            table_context=retrieval_result.get('table_context', ''),
            image_context=retrieval_result.get('image_context', '')
        )
        
        return {
            'answer': response['answer'],
            'modality': 'multimodal',
            'processing_time_ms': response['processing_time_ms'],
            'model_used': response['model_used']
        }
