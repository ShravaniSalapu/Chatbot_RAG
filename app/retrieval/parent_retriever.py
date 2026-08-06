"""
Parent-child retriever for context-preserving retrieval
"""

from typing import List, Dict, Any, Optional
from app.retrieval.dense_search import DenseSearch
from app.vectorstore.qdrant_client import QdrantManager
from app.vectorstore.collections import CollectionManager
from app.vectorstore.payload_builder import PayloadBuilder
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class ParentRetriever:
    """Retrieve parent chunks for better context"""
    
    def __init__(self, qdrant_manager: Optional[QdrantManager] = None):
        self.qdrant = qdrant_manager or QdrantManager()
        self.collection_manager = CollectionManager(self.qdrant)
        self.payload_builder = PayloadBuilder()
        self.dense_search = DenseSearch(self.qdrant)
    
    def retrieve_with_parent(
        self, query: str, top_k: int = 5, tenant_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve child chunks and their parent chunks
        
        Args:
            query: Search query
            top_k: Number of results
            
        Returns:
            Results with parent context
        """
        logger.info(f"Retrieving with parent context for query: {query}")
        
        # First, get child chunk results
        child_results = self.dense_search.search(query, limit=top_k, tenant_id=tenant_id)
        
        # Get parent chunks for each child
        results_with_parent = []
        for child_result in child_results:
            parent_chunk = self._get_parent_chunk(child_result['chunk_id'])
            
            result = {
                'child_chunk': child_result,
                'parent_chunk': parent_chunk,
                'combined_content': self._combine_content(child_result, parent_chunk)
            }
            results_with_parent.append(result)
        
        return results_with_parent
    
    def _get_parent_chunk(self, child_chunk_id: str) -> Optional[Dict[str, Any]]:
        """Get parent chunk for a child chunk"""
        try:
            # Search for the child chunk to get its parent_id
            from qdrant_client.models import Filter, FieldCondition, MatchValue
            
            filter = Filter(
                must=[FieldCondition(key="chunk_id", match=MatchValue(value=child_chunk_id))]
            )
            
            collection_name = self.collection_manager.get_text_collection()
            results = self.qdrant.search(
                collection_name=collection_name,
                query_vector=[0.0] * 1024,  # Dummy vector, we're filtering by ID
                limit=1,
                filter=filter
            )
            
            if results:
                parent_id = results[0]['payload'].get('parent_chunk_id')
                if parent_id:
                    # Get parent chunk
                    parent_filter = Filter(
                        must=[FieldCondition(key="chunk_id", match=MatchValue(value=parent_id))]
                    )
                    parent_results = self.qdrant.search(
                        collection_name=collection_name,
                        query_vector=[0.0] * 1024,
                        limit=1,
                        filter=parent_filter
                    )
                    
                    if parent_results:
                        metadata = self.payload_builder.extract_search_metadata(parent_results[0]['payload'])
                        return {
                            'chunk_id': metadata['chunk_id'],
                            'document_id': metadata['document_id'],
                            'content': metadata['content'],
                            'metadata': metadata
                        }
        
        except Exception as e:
            logger.error(f"Error getting parent chunk: {str(e)}")
        
        return None
    
    def _combine_content(self, child: Dict[str, Any], parent: Optional[Dict[str, Any]]) -> str:
        """Combine child and parent content"""
        if parent:
            return f"{parent['content']}\n\n[Relevant Section]\n{child['content']}"
        return child['content']
    
    def retrieve_children_for_parent(self, parent_chunk_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieve all child chunks for a parent
        
        Args:
            parent_chunk_id: Parent chunk ID
            limit: Maximum number of children
            
        Returns:
            List of child chunks
        """
        logger.info(f"Retrieving children for parent: {parent_chunk_id}")
        
        try:
            from qdrant_client.models import Filter, FieldCondition, MatchValue
            
            filter = Filter(
                must=[FieldCondition(key="parent_chunk_id", match=MatchValue(value=parent_chunk_id))]
            )
            
            collection_name = self.collection_manager.get_text_collection()
            results = self.qdrant.search(
                collection_name=collection_name,
                query_vector=[0.0] * 1024,
                limit=limit,
                filter=filter
            )
            
            child_chunks = []
            for result in results:
                metadata = self.payload_builder.extract_search_metadata(result['payload'])
                child_chunks.append({
                    'chunk_id': metadata['chunk_id'],
                    'document_id': metadata['document_id'],
                    'content': metadata['content'],
                    'metadata': metadata
                })
            
            return child_chunks
        
        except Exception as e:
            logger.error(f"Error retrieving children: {str(e)}")
            return []
