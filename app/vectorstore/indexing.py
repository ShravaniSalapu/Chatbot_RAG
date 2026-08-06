"""
Indexing operations for Qdrant
"""

import os
from typing import List, Dict, Any, Optional, Callable
from qdrant_client.models import PointStruct
from app.vectorstore.qdrant_client import QdrantManager
from app.vectorstore.collections import CollectionManager
from app.vectorstore.payload_builder import PayloadBuilder
from app.embeddings.embedding_factory import get_embedding_factory
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

ProgressCallback = Callable[[int, int], None]

# Searchable text chunk types (parent chunks are kept for hierarchy but not indexed)
SEARCHABLE_TEXT_CHUNK_TYPES = {"text", "child", "semantic", "section"}


class Indexer:
    """Handle indexing operations for chunks"""
    
    def __init__(self, qdrant_manager: Optional[QdrantManager] = None):
        self.qdrant = qdrant_manager or QdrantManager()
        self.collection_manager = CollectionManager(self.qdrant)
        self.payload_builder = PayloadBuilder()
        self.embedding_factory = get_embedding_factory()
    
    def index_chunks(
        self,
        chunks: List[Dict[str, Any]],
        document_metadata: Dict[str, Any],
        progress_callback: Optional[ProgressCallback] = None,
    ) -> bool:
        """
        Index chunks into Qdrant
        
        Args:
            chunks: List of chunks to index
            document_metadata: Document metadata
            progress_callback: Optional callback(indexed_count, total_count)
            
        Returns:
            True if successful
        """
        logger.info(f"Indexing {len(chunks)} chunks")

        batch_size = int(os.getenv("EMBEDDING_BATCH_SIZE", "32"))
        
        # Group chunks by type (skip parent chunks — index child/searchable text only)
        text_chunks = [c for c in chunks if c.get("chunk_type") in SEARCHABLE_TEXT_CHUNK_TYPES]
        table_chunks = [c for c in chunks if c.get('chunk_type') == 'table']
        image_chunks = [c for c in chunks if c.get('chunk_type') == 'image']
        multimodal_chunks = [c for c in chunks if c.get('chunk_type') == 'multimodal']

        total_to_index = len(text_chunks) + len(table_chunks) + len(image_chunks) + len(multimodal_chunks)
        indexed_count = 0

        def report_progress(batch_count: int) -> None:
            nonlocal indexed_count
            indexed_count += batch_count
            if progress_callback:
                progress_callback(indexed_count, total_to_index)
            logger.info(f"Indexed {indexed_count}/{total_to_index} chunks")
        
        # Index each type
        success = True
        
        if text_chunks:
            if not self._index_text_chunks(
                text_chunks, document_metadata, batch_size, report_progress
            ):
                success = False
        
        if table_chunks:
            if not self._index_table_chunks(
                table_chunks, document_metadata, batch_size, report_progress
            ):
                success = False
        
        if image_chunks:
            if not self._index_image_chunks(
                image_chunks, document_metadata, batch_size, report_progress
            ):
                success = False
        
        if multimodal_chunks:
            if not self._index_multimodal_chunks(
                multimodal_chunks, document_metadata, batch_size, report_progress
            ):
                success = False
        
        return success
    
    def _index_text_chunks(
        self,
        chunks: List[Dict[str, Any]],
        document_metadata: Dict[str, Any],
        batch_size: int,
        report_progress: Callable[[int], None],
    ) -> bool:
        """Index text chunks in batches."""
        logger.info(f"Indexing {len(chunks)} text chunks in batches of {batch_size}")
        
        text_embedding = self.embedding_factory.get_text_embedding()
        collection_name = self.collection_manager.get_text_collection()

        for start in range(0, len(chunks), batch_size):
            batch = chunks[start:start + batch_size]
            texts = [chunk["content"] for chunk in batch]
            embeddings = text_embedding.embed_batch(texts)

            points = []
            for chunk, embedding in zip(batch, embeddings):
                payload = self.payload_builder.build_chunk_payload(chunk, document_metadata)
                points.append(
                    PointStruct(
                        id=chunk["chunk_id"],
                        vector=embedding,
                        payload=payload,
                    )
                )

            if not self.qdrant.insert_points(collection_name, points):
                return False

            report_progress(len(batch))

        return True
    
    def _index_table_chunks(
        self,
        chunks: List[Dict[str, Any]],
        document_metadata: Dict[str, Any],
        batch_size: int,
        report_progress: Callable[[int], None],
    ) -> bool:
        """Index table chunks in batches."""
        logger.info(f"Indexing {len(chunks)} table chunks in batches of {batch_size}")
        
        table_embedding = self.embedding_factory.get_table_embedding()
        collection_name = self.collection_manager.get_table_collection()

        for start in range(0, len(chunks), batch_size):
            batch = chunks[start:start + batch_size]
            table_payloads = [
                {
                    "summary": chunk["content"],
                    "text_representation": chunk["content"],
                    "context_before": chunk.get("context_before") or chunk.get("context", ""),
                    "caption": chunk.get("caption", ""),
                }
                for chunk in batch
            ]
            embeddings = table_embedding.embed_batch(table_payloads)

            points = []
            for chunk, embedding in zip(batch, embeddings):
                payload = self.payload_builder.build_chunk_payload(chunk, document_metadata)
                points.append(
                    PointStruct(
                        id=chunk["chunk_id"],
                        vector=embedding,
                        payload=payload,
                    )
                )

            if not self.qdrant.insert_points(collection_name, points):
                return False

            report_progress(len(batch))

        return True
    
    def _index_image_chunks(
        self,
        chunks: List[Dict[str, Any]],
        document_metadata: Dict[str, Any],
        batch_size: int,
        report_progress: Callable[[int], None],
    ) -> bool:
        """Index image chunks using CLIP (512-dim) — matches image collection."""
        logger.info(f"Indexing {len(chunks)} image chunks in batches of {batch_size}")

        image_embedding = self.embedding_factory.get_image_embedding()
        collection_name = self.collection_manager.get_image_collection()
        use_pixel_embed = os.getenv("ENABLE_IMAGE_PIXEL_EMBED", "false").lower() in ("1", "true", "yes")

        for start in range(0, len(chunks), batch_size):
            batch = chunks[start:start + batch_size]
            embeddings = []
            for chunk in batch:
                image_bytes = chunk.get("image_bytes")
                if use_pixel_embed and image_bytes:
                    import base64
                    raw = base64.b64decode(image_bytes) if isinstance(image_bytes, str) else image_bytes
                    embeddings.append(image_embedding.embed_from_bytes(raw))
                else:
                    embeddings.append(image_embedding.embed_text_description(chunk["content"]))

            points = []
            for chunk, embedding in zip(batch, embeddings):
                payload = self.payload_builder.build_chunk_payload(chunk, document_metadata)
                points.append(
                    PointStruct(
                        id=chunk["chunk_id"],
                        vector=embedding,
                        payload=payload,
                    )
                )

            if not self.qdrant.insert_points(collection_name, points):
                return False

            report_progress(len(batch))

        return True
    
    def _index_multimodal_chunks(
        self,
        chunks: List[Dict[str, Any]],
        document_metadata: Dict[str, Any],
        batch_size: int,
        report_progress: Callable[[int], None],
    ) -> bool:
        """Index multimodal chunks in batches."""
        logger.info(f"Indexing {len(chunks)} multimodal chunks in batches of {batch_size}")
        
        text_embedding = self.embedding_factory.get_text_embedding()
        collection_name = self.collection_manager.get_multimodal_collection()

        for start in range(0, len(chunks), batch_size):
            batch = chunks[start:start + batch_size]
            texts = [chunk["content"] for chunk in batch]
            embeddings = text_embedding.embed_batch(texts)

            points = []
            for chunk, embedding in zip(batch, embeddings):
                payload = self.payload_builder.build_chunk_payload(chunk, document_metadata)
                points.append(
                    PointStruct(
                        id=chunk["chunk_id"],
                        vector=embedding,
                        payload=payload,
                    )
                )

            if not self.qdrant.insert_points(collection_name, points):
                return False

            report_progress(len(batch))

        return True
    
    def delete_document_chunks(self, document_id: str, tenant_id: Optional[str] = None) -> bool:
        """
        Delete all chunks for a document
        
        Args:
            document_id: Document ID
            
        Returns:
            True if successful
        """
        logger.info(f"Deleting chunks for document: {document_id}")
        
        collections = [
            self.collection_manager.get_text_collection(),
            self.collection_manager.get_table_collection(),
            self.collection_manager.get_image_collection(),
            self.collection_manager.get_multimodal_collection()
        ]
        
        success = True
        for collection_name in collections:
            if self.qdrant.collection_exists(collection_name):
                # Get all points for this document
                qdrant_filter = self.payload_builder.build_qdrant_filter(
                    document_id=document_id,
                    tenant_id=tenant_id,
                )
                
                # Scroll to get all point IDs
                points, _ = self.qdrant.scroll(collection_name, limit=1000, filter=qdrant_filter)
                point_ids = [p['id'] for p in points]
                
                if point_ids:
                    if not self.qdrant.delete_points(collection_name, point_ids):
                        success = False
        
        return success
    
    def get_indexing_stats(self) -> Dict[str, Any]:
        """Get indexing statistics"""
        return self.collection_manager.get_collection_stats()
