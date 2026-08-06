"""
Multimodal retriever for text, tables, and images
"""

from typing import List, Dict, Any, Optional
from app.retrieval.dense_search import DenseSearch
from app.vectorstore.collections import CollectionManager
from app.utils.logger import setup_logger
import os

logger = setup_logger(__name__)


class MultimodalRetriever:
    """Retrieve across text, table, and image collections"""
    
    def __init__(self, dense_search: Optional[DenseSearch] = None):
        self.dense_search = dense_search or DenseSearch()
        self.collection_manager = CollectionManager()
        self.top_k = int(os.getenv("TOP_K", "5"))
    
    def retrieve_all(
        self, query: str, limit_per_type: int = 3, tenant_id: Optional[str] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Retrieve results from all modalities
        
        Args:
            query: Search query
            limit_per_type: Results per modality type
            
        Returns:
            Dictionary with results by type
        """
        logger.info(f"Performing multimodal retrieval for query: {query}")
        
        results = {
            'text': [],
            'table': [],
            'image': [],
            'multimodal': []
        }
        
        # Search in each collection
        text_results = self.dense_search.search(
            query,
            collection_name=self.collection_manager.get_text_collection(),
            limit=limit_per_type,
            tenant_id=tenant_id,
        )
        results['text'] = text_results
        
        table_results = self.dense_search.search(
            query,
            collection_name=self.collection_manager.get_table_collection(),
            limit=limit_per_type,
            tenant_id=tenant_id,
        )
        results['table'] = table_results
        
        image_results = self.dense_search.search(
            query,
            collection_name=self.collection_manager.get_image_collection(),
            limit=limit_per_type,
            tenant_id=tenant_id,
        )
        results['image'] = image_results
        
        multimodal_results = self.dense_search.search(
            query,
            collection_name=self.collection_manager.get_multimodal_collection(),
            limit=limit_per_type,
            tenant_id=tenant_id,
        )
        results['multimodal'] = multimodal_results
        
        logger.info(f"Retrieved {sum(len(v) for v in results.values())} total results")
        return results
    
    def retrieve_combined(
        self,
        query: str,
        top_k: int = 5,
        document_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve and combine results from all modalities
        
        Args:
            query: Search query
            top_k: Total number of results to return
            document_id: Optional document filter
            
        Returns:
            Combined and ranked results
        """
        if document_id:
            combined = self.dense_search.search_all_collections_with_filter(
                query,
                document_id=document_id,
                limit_per_collection=top_k,
                tenant_id=tenant_id,
            )
            for result in combined:
                result['modality'] = result.get('chunk_type', 'text')
            return combined[:top_k]

        all_results = self.retrieve_all(query, limit_per_type=top_k, tenant_id=tenant_id)
        
        combined = []
        for modality, results in all_results.items():
            for result in results:
                result['modality'] = modality
                combined.append(result)
        
        combined.sort(key=lambda x: x['score'], reverse=True)
        
        return combined[:top_k]
    
    def retrieve_with_context(
        self,
        query: str,
        include_tables: bool = True,
        include_images: bool = True,
        document_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve with context from tables and images
        
        Args:
            query: Search query
            include_tables: Whether to include table results
            include_images: Whether to include image results
            document_id: Optional document filter
            
        Returns:
            Results with contextual information
        """
        if document_id:
            return self.retrieve_combined(query, top_k=self.top_k, document_id=document_id)

        results = self.retrieve_all(query, limit_per_type=3)
        
        combined = results['text'][:]
        
        if include_tables and results['table']:
            combined.extend(results['table'])
        
        if include_images and results['image']:
            combined.extend(results['image'])
        
        if results['multimodal']:
            combined.extend(results['multimodal'])
        
        combined.sort(key=lambda x: x['score'], reverse=True)
        
        return combined[:self.top_k]
    
    def retrieve_by_type(self, query: str, chunk_type: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieve results by specific chunk type
        
        Args:
            query: Search query
            chunk_type: Type of chunk (text, table, image, multimodal)
            limit: Number of results
            
        Returns:
            Results of specified type
        """
        collection_map = {
            'text': self.collection_manager.get_text_collection(),
            'table': self.collection_manager.get_table_collection(),
            'image': self.collection_manager.get_image_collection(),
            'multimodal': self.collection_manager.get_multimodal_collection()
        }
        
        collection_name = collection_map.get(chunk_type)
        if not collection_name:
            logger.warning(f"Unknown chunk type: {chunk_type}")
            return []
        
        return self.dense_search.search(query, collection_name=collection_name, limit=limit)
