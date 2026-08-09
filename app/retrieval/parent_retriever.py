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
    
    def retrieve_with_siblings(
        self, 
        chunk_id: str, 
        document_id: str,
        include_previous: int = 1,
        include_next: int = 1,
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Retrieve a chunk with its previous and next sibling chunks
        
        Args:
            chunk_id: The target chunk ID
            document_id: Document identifier
            include_previous: Number of previous chunks to include
            include_next: Number of next chunks to include
            tenant_id: Optional tenant filter
            
        Returns:
            Dictionary with main chunk and sibling context
        """
        logger.info(f"Retrieving siblings for chunk: {chunk_id}")
        
        try:
            from qdrant_client.models import Filter, FieldCondition, MatchValue
            
            # Get the main chunk with its position info
            collection_name = self.collection_manager.get_text_collection()
            
            # Search for the chunk to get its metadata
            filter = Filter(
                must=[
                    FieldCondition(key="chunk_id", match=MatchValue(value=chunk_id)),
                    FieldCondition(key="document_id", match=MatchValue(value=document_id))
                ]
            )
            
            if tenant_id:
                filter.must.append(
                    FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id))
                )
            
            results = self.qdrant.search(
                collection_name=collection_name,
                query_vector=[0.0] * 1024,  # Dummy vector
                limit=1,
                filter=filter
            )
            
            if not results:
                return {'main_chunk': None, 'previous_chunks': [], 'next_chunks': []}
            
            main_payload = results[0]['payload']
            main_metadata = self.payload_builder.extract_search_metadata(main_payload)
            
            # Get chunk index/position if available
            chunk_index = main_payload.get('chunk_index')
            
            previous_chunks = []
            next_chunks = []
            
            if chunk_index is not None:
                # Retrieve previous chunks
                if include_previous > 0:
                    prev_filter = Filter(
                        must=[
                            FieldCondition(key="document_id", match=MatchValue(value=document_id)),
                            FieldCondition(key="chunk_index", range={"lt": chunk_index})
                        ]
                    )
                    if tenant_id:
                        prev_filter.must.append(
                            FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id))
                        )
                    
                    prev_results = self.qdrant.search(
                        collection_name=collection_name,
                        query_vector=[0.0] * 1024,
                        limit=include_previous,
                        filter=prev_filter,
                        with_payload=True
                    )
                    
                    # Sort by index descending to get closest previous chunks
                    prev_results.sort(key=lambda x: x.payload.get('chunk_index', 0), reverse=True)
                    
                    for result in prev_results:
                        metadata = self.payload_builder.extract_search_metadata(result['payload'])
                        previous_chunks.append({
                            'chunk_id': metadata['chunk_id'],
                            'document_id': metadata['document_id'],
                            'content': metadata['content'],
                            'metadata': metadata
                        })
                
                # Retrieve next chunks
                if include_next > 0:
                    next_filter = Filter(
                        must=[
                            FieldCondition(key="document_id", match=MatchValue(value=document_id)),
                            FieldCondition(key="chunk_index", range={"gt": chunk_index})
                        ]
                    )
                    if tenant_id:
                        next_filter.must.append(
                            FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id))
                        )
                    
                    next_results = self.qdrant.search(
                        collection_name=collection_name,
                        query_vector=[0.0] * 1024,
                        limit=include_next,
                        filter=next_filter,
                        with_payload=True
                    )
                    
                    # Sort by index ascending to get closest next chunks
                    next_results.sort(key=lambda x: x.payload.get('chunk_index', float('inf')))
                    
                    for result in next_results:
                        metadata = self.payload_builder.extract_search_metadata(result['payload'])
                        next_chunks.append({
                            'chunk_id': metadata['chunk_id'],
                            'document_id': metadata['document_id'],
                            'content': metadata['content'],
                            'metadata': metadata
                        })
            
            return {
                'main_chunk': {
                    'chunk_id': main_metadata['chunk_id'],
                    'document_id': main_metadata['document_id'],
                    'content': main_metadata['content'],
                    'metadata': main_metadata
                },
                'previous_chunks': previous_chunks,
                'next_chunks': next_chunks
            }
            
        except Exception as e:
            logger.error(f"Error retrieving siblings: {str(e)}")
            return {'main_chunk': None, 'previous_chunks': [], 'next_chunks': []}
    
    def enhance_results_with_siblings(
        self,
        results: List[Dict[str, Any]],
        include_previous: int = 1,
        include_next: int = 1,
        tenant_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Enhance retrieval results with sibling chunks for better context
        
        Args:
            results: Original retrieval results
            include_previous: Number of previous chunks to include
            include_next: Number of next chunks to include
            tenant_id: Optional tenant filter
            
        Returns:
            Enhanced results with sibling context
        """
        logger.info(f"Enhancing {len(results)} results with sibling context")
        
        enhanced_results = []
        for result in results:
            chunk_id = result.get('chunk_id')
            document_id = result.get('document_id')
            
            if not chunk_id or not document_id:
                enhanced_results.append(result)
                continue
            
            sibling_data = self.retrieve_with_siblings(
                chunk_id=chunk_id,
                document_id=document_id,
                include_previous=include_previous,
                include_next=include_next,
                tenant_id=tenant_id
            )
            
            # Combine content with siblings
            combined_content_parts = []
            
            # Add previous chunks
            for prev_chunk in sibling_data['previous_chunks']:
                combined_content_parts.append(prev_chunk['content'])
            
            # Add main chunk
            combined_content_parts.append(result.get('content', ''))
            
            # Add next chunks
            for next_chunk in sibling_data['next_chunks']:
                combined_content_parts.append(next_chunk['content'])
            
            enhanced_result = result.copy()
            enhanced_result['content'] = '\n\n'.join(combined_content_parts)
            enhanced_result['has_sibling_context'] = True
            enhanced_result['sibling_count'] = len(sibling_data['previous_chunks']) + len(sibling_data['next_chunks'])
            
            enhanced_results.append(enhanced_result)
        
        return enhanced_results
    
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
