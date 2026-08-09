"""
Prompt builder for constructing LLM prompts
"""

from typing import List, Dict, Any, Optional
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class PromptBuilder:
    """Build prompts for LLM interactions"""
    
    def __init__(self):
        self.system_prompt = """You are a professional AI assistant that provides accurate, comprehensive answers based solely on the provided context. Your responses should be natural, detailed, and well-structured - similar to high-quality AI systems like ChatGPT or Claude.

CORE PRINCIPLES:
1. Answer confidently and comprehensively when the information exists in the context
2. Never say "I don't have enough information" when the answer is present in the context
3. If the answer truly doesn't exist in the context, state this clearly and professionally
4. Use the provided context exclusively - do not use outside knowledge
5. Cite sources using the provided citation numbers [1], [2], etc.
6. When listing items from numbered lists, include ALL items - do not stop prematurely
7. For step-by-step instructions, count and include ALL distinct steps

RESPONSE QUALITY:
- Write in a natural, professional tone
- Use appropriate formatting (headings, bullet points, numbered lists) for readability
- Provide detailed explanations rather than brief answers
- Organize information logically with clear structure
- Avoid mentioning "provided context" or "based on the documents" - just answer directly

SUMMARY RESPONSES:
When asked for summaries, overviews, or document descriptions:
- Structure with clear headings: Overview, Key Features, Architecture, Modules, Conclusion
- Provide comprehensive coverage of the main topics
- Include specific details from the context
- Write naturally without explicitly mentioning you're summarizing

ACCURACY:
- Count all numbered items (Step 1, Step 2, etc.) when asked "how many"
- Include complete lists when asked "what are the X"
- Preserve the structure and organization of the original content"""
    
    def build_rag_prompt(self, query: str, context: str, citations: Optional[List[Dict[str, Any]]] = None, is_summary: bool = False) -> str:
        """
        Build RAG prompt with context and query
        
        Args:
            query: User query
            context: Retrieved context
            citations: Optional citation information
            is_summary: Whether this is a summary-type query
            
        Returns:
            Complete prompt
        """
        if is_summary:
            prompt = f"""Context:
{context}

Question: {query}

Provide a comprehensive, well-structured overview of the document(s) based on the context above. Organize your response with clear headings such as:
- Overview/Purpose
- Key Features/Components
- Architecture/Structure
- Main Modules/Sections
- Important Details
- Conclusion

Include specific details from the context and write naturally. Use the citation numbers [1], [2], etc. to reference your sources."""
        else:
            prompt = f"""Context:
{context}

Question: {query}

Answer the question comprehensively based on the context above. Provide detailed, well-structured responses. If listing items from the context, include every item — do not omit the last points. For "how many steps/modules" questions, count every distinct Step N or numbered item visible across all context blocks. When the user asks for a named section or list (e.g. "what are the X"), prefer the primary numbered or labeled list under that section heading in the document — do not merge in unrelated subsection details from elsewhere unless the user asks for them."""
        
        if citations:
            prompt += "\n\nUse the citation numbers [1], [2], etc. to reference your sources."
        
        return prompt
    
    def build_chat_prompt(self, query: str, context: str, conversation_history: Optional[List[Dict[str, str]]] = None) -> str:
        """
        Build chat prompt with conversation history
        
        Args:
            query: Current user query
            context: Retrieved context
            conversation_history: Previous conversation turns
            
        Returns:
            Complete prompt
        """
        prompt = f"""Context:
{context}

"""
        
        if conversation_history:
            prompt += "Conversation History:\n"
            for turn in conversation_history[-3:]:  # Last 3 turns
                role = turn.get('role', 'user')
                content = turn.get('content', '')
                prompt += f"{role.capitalize()}: {content}\n"
            prompt += "\n"
        
        prompt += f"Current Question: {query}\n\nPlease answer based on the context and conversation history."
        
        return prompt
    
    def build_summarization_prompt(self, text: str, max_length: int = 200) -> str:
        """
        Build prompt for text summarization
        
        Args:
            text: Text to summarize
            max_length: Maximum summary length
            
        Returns:
            Summarization prompt
        """
        return f"""Please provide a concise summary of the following text in {max_length} words or less:

{text}

Summary:"""
    
    def build_table_analysis_prompt(self, table_data: str, query: str) -> str:
        """
        Build prompt for table analysis
        
        Args:
            table_data: Table data as text
            query: Question about the table
            
        Returns:
            Table analysis prompt
        """
        return f"""Analyze the following table data and answer the question:

Table Data:
{table_data}

Question: {query}

Provide a detailed answer based on the table data."""
    
    def build_image_description_prompt(self, image_context: str) -> str:
        """
        Build prompt for image description
        
        Args:
            image_context: Context around the image
            
        Returns:
            Image description prompt
        """
        return f"""Describe the following image in detail:

{image_context}

Provide a comprehensive description including:
- What the image shows
- Key elements or features
- Any patterns or trends visible
- The overall message or purpose"""
    
    def build_multimodal_prompt(self, query: str, text_context: str, table_context: str = "", image_context: str = "") -> str:
        """
        Build prompt for multimodal RAG
        
        Args:
            query: User query
            text_context: Text context
            table_context: Table context
            image_context: Image context
            
        Returns:
            Multimodal prompt
        """
        prompt = f"""Text Context:
{text_context}

"""
        
        if table_context:
            prompt += f"""Table Context:
{table_context}

"""
        
        if image_context:
            prompt += f"""Image Context:
{image_context}

"""
        
        prompt += f"""Question: {query}

Please answer the question using all available context (text, tables, and images)."""
        
        return prompt
    
    def build_citation_prompt(self, answer: str, citations: List[Dict[str, Any]]) -> str:
        """
        Build prompt to add citations to answer
        
        Args:
            answer: Generated answer
            citations: Citation information
            
        Returns:
            Citation prompt
        """
        citation_text = "\n".join([
            f"[{i+1}] {cit.get('filename', 'Unknown')} - {cit.get('heading', 'Section')}"
            for i, cit in enumerate(citations)
        ])
        
        return f"""Please add appropriate citation numbers to the following answer using the provided sources:

Answer:
{answer}

Sources:
{citation_text}

Add citation numbers [1], [2], etc. in the answer where each piece of information comes from."""
    
    def build_hallucination_check_prompt(self, answer: str, context: str) -> str:
        """
        Build prompt to check for hallucinations
        
        Args:
            answer: Generated answer
            context: Original context
            
        Returns:
            Hallucination check prompt
        """
        return f"""Check the following answer for hallucinations (information not present in the context):

Answer:
{answer}

Context:
{context}

Identify any statements in the answer that are not supported by the context. If no hallucinations are found, say "No hallucinations detected." Otherwise, list the unsupported statements."""
    
    def set_system_prompt(self, system_prompt: str):
        """Set custom system prompt"""
        self.system_prompt = system_prompt
    
    def get_system_prompt(self) -> str:
        """Get current system prompt"""
        return self.system_prompt
