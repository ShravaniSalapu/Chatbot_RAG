"""
Payload builder for constructing Qdrant point payloads
"""

from typing import Dict, Any, List, Optional
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class PayloadBuilder:
    """Build payloads for Qdrant points"""
    
    @staticmethod
    def build_chunk_payload(chunk: Dict[str, Any], document_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build payload for a chunk
        
        Args:
            chunk: Chunk data
            document_metadata: Document metadata
            
        Returns:
            Payload dictionary
        """
        payload = {
            # Tenant isolation
            'tenant_id': document_metadata.get('tenant_id') or chunk.get('tenant_id'),

            # Chunk information
            'chunk_id': chunk.get('chunk_id'),
            'document_id': chunk.get('document_id'),
            'chunk_type': chunk.get('chunk_type'),
            'content': chunk.get('content'),
            'token_count': chunk.get('token_count'),
            'character_count': chunk.get('character_count'),
            
            # Document information
            'filename': document_metadata.get('filename'),
            'file_type': document_metadata.get('file_type'),
            
            # Structural information
            'section_id': chunk.get('section_id'),
            'heading': chunk.get('heading'),
            'page_number': chunk.get('page_number'),
            
            # Hierarchy
            'parent_chunk_id': chunk.get('parent_chunk_id'),
            'child_chunk_ids': chunk.get('child_chunk_ids', []),
            
            # Element references
            'table_id': chunk.get('table_id'),
            'image_id': chunk.get('image_id'),
            
            # Timestamp
            'created_at': chunk.get('created_at')
        }
        
        return payload
    
    @staticmethod
    def build_document_payload(document: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build payload for document-level metadata
        
        Args:
            document: Document data
            
        Returns:
            Payload dictionary
        """
        metadata = document.get('metadata', {})
        
        payload = {
            'tenant_id': metadata.get('tenant_id') or document.get('tenant_id'),
            'document_id': document.get('document_id'),
            'filename': metadata.get('filename'),
            'file_type': metadata.get('file_type'),
            'file_size': metadata.get('file_size'),
            'upload_date': metadata.get('upload_date'),
            'total_pages': metadata.get('total_pages'),
            'total_sections': metadata.get('total_sections'),
            'total_headings': metadata.get('total_headings'),
            'total_paragraphs': metadata.get('total_paragraphs'),
            'total_tables': metadata.get('total_tables'),
            'total_images': metadata.get('total_images'),
            'total_characters': metadata.get('total_characters'),
            'total_words': metadata.get('total_words'),
            'language': metadata.get('language'),
            'document_type': metadata.get('document_type')
        }
        
        return payload
    
    @staticmethod
    def build_filter(
        document_id: Optional[str] = None,
        chunk_type: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Build a filter for Qdrant queries
        
        Args:
            document_id: Filter by document ID
            chunk_type: Filter by chunk type
            tenant_id: Filter by tenant ID (required for multi-tenant isolation)
            
        Returns:
            Filter dictionary
        """
        conditions = []

        if tenant_id:
            conditions.append({
                'key': 'tenant_id',
                'match': {'value': tenant_id}
            })
        
        if document_id:
            conditions.append({
                'key': 'document_id',
                'match': {'value': document_id}
            })
        
        if chunk_type:
            conditions.append({
                'key': 'chunk_type',
                'match': {'value': chunk_type}
            })
        
        if conditions:
            return {'must': conditions}
        
        return {}

    @staticmethod
    def build_qdrant_filter(
        document_id: Optional[str] = None,
        chunk_type: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ):
        """Build a Qdrant Filter object for queries."""
        from qdrant_client.models import Filter, FieldCondition, MatchValue

        conditions = []
        if tenant_id:
            conditions.append(FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id)))
        if document_id:
            conditions.append(FieldCondition(key="document_id", match=MatchValue(value=document_id)))
        if chunk_type:
            conditions.append(FieldCondition(key="chunk_type", match=MatchValue(value=chunk_type)))

        if conditions:
            return Filter(must=conditions)
        return None
    
    @staticmethod
    def extract_search_metadata(payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract relevant metadata from payload for search results
        
        Args:
            payload: Qdrant point payload
            
        Returns:
            Simplified metadata dictionary
        """
        return {
            'chunk_id': payload.get('chunk_id'),
            'document_id': payload.get('document_id'),
            'chunk_type': payload.get('chunk_type'),
            'content': payload.get('content'),
            'filename': payload.get('filename'),
            'file_type': payload.get('file_type'),
            'section_id': payload.get('section_id'),
            'heading': payload.get('heading'),
            'page_number': payload.get('page_number'),
            'token_count': payload.get('token_count'),
            'tenant_id': payload.get('tenant_id'),
        }
