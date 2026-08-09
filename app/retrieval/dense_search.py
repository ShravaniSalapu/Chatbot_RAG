"""
Dense vector search using embeddings
"""

from typing import List, Dict, Any, Optional
from app.vectorstore.qdrant_client import QdrantManager
from app.vectorstore.collections import CollectionManager
from app.embeddings.embedding_factory import get_embedding_factory
from app.vectorstore.payload_builder import PayloadBuilder
from app.utils.logger import setup_logger
import os

logger = setup_logger(__name__)


class DenseSearch:
    """Dense vector search using embeddings"""
    
    def __init__(self, qdrant_manager: Optional[QdrantManager] = None):
        self.qdrant = qdrant_manager or QdrantManager()
        self.collection_manager = CollectionManager(self.qdrant)
        self.embedding_factory = get_embedding_factory()
        self.payload_builder = PayloadBuilder()
        self.top_k = int(os.getenv("TOP_K", "5"))
    
    def search(
        self,
        query: str,
        collection_name: Optional[str] = None,
        limit: Optional[int] = None,
        tenant_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Perform dense vector search
        
        Args:
            query: Search query
            collection_name: Specific collection to search (default: text collection)
            limit: Number of results to return
            
        Returns:
            List of search results
        """
        logger.info(f"Performing dense search for query: {query}")
        
        # Use text collection by default
        collection_name = collection_name or self.collection_manager.get_text_collection()
        limit = limit or self.top_k
        
        query_vector = self._get_query_vector(query, collection_name)
        qdrant_filter = self.payload_builder.build_qdrant_filter(tenant_id=tenant_id)
        
        # Search in Qdrant
        logger.info(f"Searching Qdrant collection: {collection_name}")
        logger.info(f"Query vector dimension: {len(query_vector)}")
        logger.info(f"Limit: {limit}")
        
        results = self.qdrant.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=limit,
            filter=qdrant_filter,
        )
        
        logger.info(f"Qdrant returned {len(results)} raw results")
        
        # Format results
        formatted_results = []
        for result in results:
            metadata = self.payload_builder.extract_search_metadata(result['payload'])
            formatted_results.append({
                'chunk_id': metadata['chunk_id'],
                'document_id': metadata['document_id'],
                'content': metadata['content'],
                'score': result['score'],
                'chunk_type': metadata['chunk_type'],
                'metadata': metadata,
                'page_number': metadata.get('page_number'),
                'heading': metadata.get('heading')
            })
        
        logger.info(f"Formatted {len(formatted_results)} results")
        return formatted_results
    
    def search_all_collections(
        self, query: str, limit: Optional[int] = None, tenant_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search across all collections
        
        Args:
            query: Search query
            limit: Number of results per collection
            
        Returns:
            Combined results from all collections
        """
        logger.info("Searching across all collections")
        
        limit = limit or self.top_k
        
        collections = [
            self.collection_manager.get_text_collection(),
            self.collection_manager.get_table_collection(),
            self.collection_manager.get_image_collection(),
            self.collection_manager.get_multimodal_collection()
        ]
        
        all_results = []
        for collection_name in collections:
            if self.qdrant.collection_exists(collection_name):
                results = self.search(query, collection_name, limit, tenant_id=tenant_id)
                all_results.extend(results)
        
        # Sort by score
        all_results.sort(key=lambda x: x['score'], reverse=True)
        
        return all_results[:self.top_k]
    
    def search_with_filter(
        self,
        query: str,
        document_id: str,
        chunk_type: Optional[str] = None,
        collection_name: Optional[str] = None,
        limit: Optional[int] = None,
        tenant_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search with document filter
        
        Args:
            query: Search query
            document_id: Document ID to filter by
            chunk_type: Optional chunk type filter
            collection_name: Qdrant collection (default: text collection)
            limit: Number of results
            
        Returns:
            Filtered search results
        """
        logger.info(f"Searching with filter for document: {document_id}")
        
        query_vector = self._get_query_vector(query, collection_name or self.collection_manager.get_text_collection())
        qdrant_filter = self.payload_builder.build_qdrant_filter(
            document_id=document_id,
            chunk_type=chunk_type,
            tenant_id=tenant_id,
        )
        
        collection_name = collection_name or self.collection_manager.get_text_collection()
        limit = limit or self.top_k
        results = self.qdrant.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=limit,
            filter=qdrant_filter,
        )
        
        formatted_results = []
        for result in results:
            metadata = self.payload_builder.extract_search_metadata(result['payload'])
            formatted_results.append({
                'chunk_id': metadata['chunk_id'],
                'document_id': metadata['document_id'],
                'content': metadata['content'],
                'score': result['score'],
                'chunk_type': metadata['chunk_type'],
                'metadata': metadata,
                'page_number': metadata.get('page_number'),
                'heading': metadata.get('heading'),
            })
        
        return formatted_results

    def search_all_collections_with_filter(
        self,
        query: str,
        document_id: str,
        limit_per_collection: Optional[int] = None,
        tenant_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Search text, table, image, and multimodal collections for one document."""
        limit = limit_per_collection or self.top_k
        collections = [
            self.collection_manager.get_text_collection(),
            self.collection_manager.get_table_collection(),
            self.collection_manager.get_image_collection(),
            self.collection_manager.get_multimodal_collection(),
        ]

        all_results = []
        for collection_name in collections:
            if self.qdrant.collection_exists(collection_name):
                results = self.search_with_filter(
                    query,
                    document_id=document_id,
                    collection_name=collection_name,
                    limit=limit,
                    tenant_id=tenant_id,
                )
                all_results.extend(results)

        all_results.sort(key=lambda x: x['score'], reverse=True)
        return all_results[: limit * 2]

    def _get_query_vector(self, query: str, collection_name: str) -> List[float]:
        """Use CLIP text space for image collection; BGE/text model for others."""
        logger.info(f"Getting query vector for collection: {collection_name}")
        
        if collection_name == self.collection_manager.get_image_collection():
            logger.info("Using image embedding for image collection")
            image_embedding = self.embedding_factory.get_image_embedding()
            vector = image_embedding.embed_text_description(query)
            logger.info(f"Image embedding vector dimension: {len(vector)}")
            return vector

        logger.info("Using text embedding for text/table/multimodal collection")
        text_embedding = self.embedding_factory.get_text_embedding()
        logger.info(f"Text embedding model: {text_embedding.model_name}")
        logger.info(f"Text embedding vector dimension: {text_embedding.get_embedding_dimension()}")
        
        vector = text_embedding.embed_query(query)
        logger.info(f"Generated query vector dimension: {len(vector)}")
        
        return vector
