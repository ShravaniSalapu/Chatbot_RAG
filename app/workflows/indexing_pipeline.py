"""
Indexing pipeline for chunking and embedding documents
"""

from typing import Dict, Any, Optional, Callable
from app.chunking.parent_child_chunker import ParentChildChunker
from app.chunking.semantic_chunker import SemanticChunker
from app.chunking.section_chunker import SectionChunker
from app.chunking.multimodal_chunker import MultimodalChunker
from app.vectorstore.indexing import Indexer
from app.ingestion.processors.document_tree_builder import DocumentTreeBuilder
from app.ingestion.processors.table_summarizer import TableSummarizer
from app.ingestion.processors.image_captioning import ImageCaptioning
from app.ingestion.processors.chart_understanding import ChartUnderstanding
from app.retrieval.bm25_store import get_bm25_search
from app.utils.logger import setup_logger
import os

logger = setup_logger(__name__)


class IndexingPipeline:
    """Pipeline for indexing documents into vector database"""
    
    def __init__(self):
        self.parent_child_chunker = ParentChildChunker(
            parent_chunk_size=int(os.getenv("PARENT_CHUNK_SIZE", "2048")),
            child_chunk_size=int(os.getenv("CHUNK_SIZE", "512")),
            overlap=int(os.getenv("CHUNK_OVERLAP", "50"))
        )
        self.semantic_chunker = SemanticChunker(
            chunk_size=int(os.getenv("CHUNK_SIZE", "512")),
            overlap=int(os.getenv("CHUNK_OVERLAP", "50"))
        )
        self.section_chunker = SectionChunker(
            max_chunk_size=int(os.getenv("CHUNK_SIZE", "512"))
        )
        self.multimodal_chunker = MultimodalChunker(
            chunk_size=int(os.getenv("CHUNK_SIZE", "512"))
        )
        
        self.indexer = Indexer()
        self.document_tree_builder = DocumentTreeBuilder()
        self.table_summarizer = TableSummarizer()
        self.image_captioning = ImageCaptioning()
        self.chart_understanding = ChartUnderstanding()
    
    def index_document(
        self,
        document: Dict[str, Any],
        chunking_strategy: str = "parent_child",
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> Dict[str, Any]:
        """
        Index a document into the vector database
        
        Args:
            document: Document object from ingestion pipeline
            chunking_strategy: Chunking strategy to use
            
        Returns:
            Indexing results
        """
        logger.info(f"Starting indexing pipeline for document: {document['document_id']}")
        
        # Step 1: Build document tree
        document_tree = self.document_tree_builder.build_tree(
            document,
            document.get('headings', []),
            document.get('sections', [])
        )
        
        # Step 2: Process tables and images (fast local enrichment by default)
        tables = document.get('tables', [])
        images = document.get('images', [])
        use_llm = os.getenv("USE_LLM_ENRICHMENT", "false").lower() in ("1", "true", "yes")
        
        for table in tables:
            if not table.get('summary'):
                table['summary'] = self.table_summarizer._generate_fallback_summary(table)
            if use_llm and not table.get('llm_summary'):
                table['llm_summary'] = self.table_summarizer.summarize_table(table)
                table['summary'] = table['llm_summary']
        
        for image in images:
            if not image.get('description'):
                image['description'] = self.image_captioning._generate_fallback_caption(image, image.get('context_before', ''))
            if use_llm and not image.get('llm_description'):
                image['description'] = self.image_captioning.caption_image(image, image.get('context_before', ''))
            
            if image.get('is_chart') and use_llm and not image.get('analysis'):
                chart_analysis = self.chart_understanding.analyze_chart(image)
                image['analysis'] = chart_analysis
                insights = chart_analysis.get('key_insights') or chart_analysis.get('data_summary', '')
                if insights:
                    image['description'] = f"{image['description']}\nChart insights: {insights}"
        
        # Step 3: Chunk document (text + table/image/multimodal)
        chunks = self._chunk_document(document, chunking_strategy)
        searchable_chunks = [c for c in chunks if c.get("chunk_type") != "parent"]

        metadata = document['metadata']
        if hasattr(metadata, 'model_dump'):
            document_metadata = metadata.model_dump()
        elif hasattr(metadata, 'dict'):
            document_metadata = metadata.dict()
        else:
            document_metadata = metadata

        filename = document_metadata.get("filename") or "Unknown"
        tenant_id = document_metadata.get("tenant_id")
        for chunk in searchable_chunks:
            chunk.setdefault("filename", filename)
            if tenant_id:
                chunk.setdefault("tenant_id", tenant_id)

        if progress_callback:
            progress_callback(0, len(searchable_chunks))

        # Step 4: Build BM25 index for hybrid search (text/table only — not image captions)
        bm25 = get_bm25_search()
        bm25_chunks = [
            c for c in searchable_chunks if c.get("chunk_type") not in ("image", "parent")
        ]
        bm25.build_index(document["document_id"], bm25_chunks, tenant_id=document_metadata.get("tenant_id"))

        # Step 5: Index chunks into Qdrant
        success = self.indexer.index_chunks(chunks, document_metadata, progress_callback)
        
        logger.info(f"Indexing pipeline completed for document: {document['document_id']}")
        
        return {
            'document_id': document['document_id'],
            'chunks_created': len(searchable_chunks),
            'tables_processed': len(tables),
            'images_processed': len(images),
            'success': success
        }
    
    def _chunk_document(self, document: Dict[str, Any], strategy: str) -> list:
        """Chunk document using specified strategy plus table/image chunks."""
        document_id = document['document_id']
        raw_text = document.get('raw_text', '')
        document['tables'] = document.get('tables', [])
        document['images'] = document.get('images', [])
        
        if strategy == "parent_child":
            text_chunks = self.parent_child_chunker.chunk(raw_text, document_id)
        elif strategy == "semantic":
            text_chunks = self.semantic_chunker.chunk(raw_text, document_id)
        elif strategy == "section":
            sections = document.get('sections', [])
            text_chunks = self.section_chunker.chunk(raw_text, document_id, sections)
        elif strategy == "multimodal":
            return self.multimodal_chunker.chunk(document, document_id)
        else:
            logger.warning(f"Unknown chunking strategy: {strategy}, using parent_child")
            text_chunks = self.parent_child_chunker.chunk(raw_text, document_id)

        mm_chunks = self.multimodal_chunker.chunk(document, document_id)
        extra = [c for c in mm_chunks if c.get('chunk_type') in ('table', 'image', 'multimodal')]
        return text_chunks + extra
    
    def delete_document(self, document_id: str, tenant_id: Optional[str] = None) -> bool:
        """
        Delete a document from the index
        
        Args:
            document_id: Document ID to delete
            
        Returns:
            True if successful
        """
        logger.info(f"Deleting document from index: {document_id}")
        get_bm25_search().delete_index(document_id)
        return self.indexer.delete_document_chunks(document_id, tenant_id=tenant_id)
    
    def get_indexing_stats(self) -> Dict[str, Any]:
        """Get indexing statistics"""
        return self.indexer.get_indexing_stats()
