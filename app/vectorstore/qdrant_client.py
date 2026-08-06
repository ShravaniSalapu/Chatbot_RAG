"""
Qdrant client for vector database operations
"""

from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
import os
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class QdrantManager:
    """Manager for Qdrant vector database operations"""
    
    def __init__(self, url: Optional[str] = None, api_key: Optional[str] = None):
        self.url = url or os.getenv("QDRANT_URL", "http://localhost:6333")
        self.api_key = api_key or os.getenv("QDRANT_API_KEY")
        self.client = None
        self._connect()
    
    def _connect(self):
        """Connect to Qdrant"""
        logger.info(f"Connecting to Qdrant at: {self.url}")
        try:
            self.client = QdrantClient(url=self.url, api_key=self.api_key)
            # Test connection
            collections = self.client.get_collections()
            logger.info(f"Connected to Qdrant. Existing collections: {len(collections.collections)}")
        except Exception as e:
            logger.error(f"Error connecting to Qdrant: {str(e)}")
            raise
    
    def create_collection(self, collection_name: str, vector_size: int, distance: str = "Cosine") -> bool:
        """
        Create a new collection
        
        Args:
            collection_name: Name of the collection
            vector_size: Dimension of vectors
            distance: Distance metric (Cosine, Euclid, Dot)
            
        Returns:
            True if successful
        """
        logger.info(f"Creating collection: {collection_name}")
        
        try:
            # Map distance string to Qdrant enum
            distance_map = {
                "Cosine": Distance.COSINE,
                "Euclid": Distance.EUCLID,
                "Dot": Distance.DOT
            }
            distance_metric = distance_map.get(distance, Distance.COSINE)
            
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=vector_size, distance=distance_metric)
            )
            logger.info(f"Collection {collection_name} created successfully")
            return True
        except Exception as e:
            logger.error(f"Error creating collection {collection_name}: {str(e)}")
            return False
    
    def delete_collection(self, collection_name: str) -> bool:
        """
        Delete a collection
        
        Args:
            collection_name: Name of the collection
            
        Returns:
            True if successful
        """
        logger.info(f"Deleting collection: {collection_name}")
        
        try:
            self.client.delete_collection(collection_name=collection_name)
            logger.info(f"Collection {collection_name} deleted successfully")
            return True
        except Exception as e:
            logger.error(f"Error deleting collection {collection_name}: {str(e)}")
            return False
    
    def collection_exists(self, collection_name: str) -> bool:
        """Check if a collection exists"""
        try:
            collections = self.client.get_collections()
            return any(col.name == collection_name for col in collections.collections)
        except Exception as e:
            logger.error(f"Error checking collection existence: {str(e)}")
            return False
    
    def insert_points(self, collection_name: str, points: List[PointStruct]) -> bool:
        """
        Insert points into a collection
        
        Args:
            collection_name: Name of the collection
            points: List of points to insert
            
        Returns:
            True if successful
        """
        logger.info(f"Inserting {len(points)} points into {collection_name}")
        
        try:
            self.client.upsert(
                collection_name=collection_name,
                points=points
            )
            logger.info(f"Successfully inserted {len(points)} points")
            return True
        except Exception as e:
            logger.error(f"Error inserting points: {str(e)}")
            return False
    
    def search(
        self,
        collection_name: str,
        query_vector: List[float],
        limit: int = 10,
        score_threshold: Optional[float] = None,
        filter: Optional[Filter] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar vectors
        
        Args:
            collection_name: Name of the collection
            query_vector: Query vector
            limit: Number of results to return
            score_threshold: Minimum score threshold
            filter: Optional filter for search
            
        Returns:
            List of search results
        """
        try:
            if hasattr(self.client, "query_points"):
                response = self.client.query_points(
                    collection_name=collection_name,
                    query=query_vector,
                    limit=limit,
                    score_threshold=score_threshold,
                    query_filter=filter,
                )
                search_result = response.points
            else:
                search_result = self.client.search(
                    collection_name=collection_name,
                    query_vector=query_vector,
                    limit=limit,
                    score_threshold=score_threshold,
                    query_filter=filter,
                )
            
            results = []
            for hit in search_result:
                results.append({
                    'id': hit.id,
                    'score': hit.score,
                    'payload': hit.payload
                })
            
            return results
        except Exception as e:
            logger.error(f"Error searching collection: {str(e)}")
            return []
    
    def delete_points(self, collection_name: str, point_ids: List[str]) -> bool:
        """
        Delete points from a collection
        
        Args:
            collection_name: Name of the collection
            point_ids: List of point IDs to delete
            
        Returns:
            True if successful
        """
        logger.info(f"Deleting {len(point_ids)} points from {collection_name}")
        
        try:
            self.client.delete(
                collection_name=collection_name,
                points_selector=point_ids
            )
            logger.info(f"Successfully deleted points")
            return True
        except Exception as e:
            logger.error(f"Error deleting points: {str(e)}")
            return False
    
    def get_collection_info(self, collection_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a collection"""
        try:
            info = self.client.get_collection(collection_name)
            return {
                'name': collection_name,
                'vectors_count': getattr(info, 'vectors_count', None),
                'indexed_vectors_count': getattr(info, 'indexed_vectors_count', None),
                'points_count': getattr(info, 'points_count', None),
                'status': str(getattr(info, 'status', 'unknown')),
            }
        except Exception as e:
            logger.error(f"Error getting collection info: {str(e)}")
            return None
    
    def scroll(
        self,
        collection_name: str,
        limit: int = 100,
        offset: Optional[Any] = None,
        filter: Optional[Filter] = None,
        with_vectors: bool = False,
    ) -> Tuple[List[Dict[str, Any]], Optional[Any]]:
        """
        Scroll through points in a collection
        
        Returns:
            Tuple of (points, next_page_offset)
        """
        try:
            results, next_page_offset = self.client.scroll(
                collection_name=collection_name,
                limit=limit,
                offset=offset,
                scroll_filter=filter,
                with_payload=True,
                with_vectors=with_vectors,
            )
            
            points = []
            for point in results:
                points.append({
                    'id': point.id,
                    'vector': point.vector,
                    'payload': point.payload or {},
                })
            
            return points, next_page_offset
        except Exception as e:
            logger.error(f"Error scrolling collection: {str(e)}")
            return [], None

    def list_indexed_documents(
        self, collection_name: str, tenant_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List unique documents and chunk counts stored in a collection."""
        from app.vectorstore.payload_builder import PayloadBuilder

        tenant_filter = PayloadBuilder.build_qdrant_filter(tenant_id=tenant_id)
        documents: Dict[str, Dict[str, Any]] = {}
        offset = None

        while True:
            points, offset = self.scroll(
                collection_name=collection_name,
                limit=100,
                offset=offset,
                filter=tenant_filter,
                with_vectors=False,
            )
            if not points:
                break

            for point in points:
                payload = point.get("payload") or {}
                document_id = payload.get("document_id")
                if not document_id:
                    continue

                if document_id not in documents:
                    raw_filename = payload.get("filename") or self._resolve_filename(document_id)
                    documents[document_id] = {
                        "document_id": document_id,
                        "tenant_id": payload.get("tenant_id"),
                        "filename": self._clean_display_filename(raw_filename, document_id),
                        "chunks_created": 0,
                        "file_type": payload.get("file_type"),
                    }
                elif not documents[document_id].get("filename") or documents[document_id]["filename"] == "Unknown":
                    filename = payload.get("filename")
                    if filename:
                        documents[document_id]["filename"] = self._clean_display_filename(
                            filename, document_id
                        )

                documents[document_id]["chunks_created"] += 1

            if offset is None:
                break

        return list(documents.values())

    def get_document_chunks(
        self,
        collection_name: str,
        document_id: str,
        tenant_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch all searchable chunks for a document from Qdrant."""
        from app.vectorstore.payload_builder import PayloadBuilder

        qdrant_filter = PayloadBuilder.build_qdrant_filter(
            document_id=document_id,
            tenant_id=tenant_id,
        )
        chunks: List[Dict[str, Any]] = []
        offset = None

        while True:
            points, offset = self.scroll(
                collection_name=collection_name,
                limit=100,
                offset=offset,
                filter=qdrant_filter,
                with_vectors=False,
            )
            if not points:
                break

            for point in points:
                payload = point.get("payload") or {}
                chunk_type = payload.get("chunk_type", "text")
                if chunk_type == "parent":
                    continue
                chunks.append({
                    "chunk_id": payload.get("chunk_id") or str(point.get("id")),
                    "document_id": document_id,
                    "tenant_id": payload.get("tenant_id"),
                    "content": payload.get("content", ""),
                    "chunk_type": chunk_type,
                    "filename": payload.get("filename"),
                })

            if offset is None:
                break

        return chunks

    @staticmethod
    def _clean_display_filename(filename: str, document_id: str) -> str:
        """Strip upload prefix (uuid_) from stored filenames."""
        prefix = f"{document_id}_"
        if filename.startswith(prefix):
            return filename[len(prefix):]
        return filename

    @staticmethod
    def _resolve_filename(document_id: str) -> str:
        """Resolve filename from saved raw file on disk."""
        import os
        raw_dir = Path(os.getenv("DATA_DIR", "./data")) / "raw"
        if not raw_dir.exists():
            return "Unknown"

        prefix = f"{document_id}_"
        for path in raw_dir.iterdir():
            if path.is_file() and path.name.startswith(prefix):
                return path.name[len(prefix):]
        return "Unknown"
