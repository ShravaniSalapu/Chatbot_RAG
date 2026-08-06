
"""
Multimodal chunker for handling text, tables, and images together
"""

from typing import Dict, List, Any, Optional
import uuid
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class MultimodalChunker:
    """Implement multimodal chunking preserving table-image relationships"""
    
    def __init__(self, chunk_size: int = 512):
        self.chunk_size = chunk_size
    
    def chunk(self, document: Dict[str, Any], document_id: str) -> List[Dict[str, Any]]:
        """
        Create multimodal chunks from document
        
        Args:
            document: Document object with text, tables, and images
            document_id: Document identifier
            
        Returns:
            List of multimodal chunks
        """
        logger.info(f"Creating multimodal chunks for document: {document_id}")
        
        chunks = []
        
        # Process text chunks
        text_chunks = self._chunk_text(document.get('raw_text', ''), document_id)
        chunks.extend(text_chunks)
        
        # Process table chunks
        table_chunks = self._chunk_tables(document.get('tables', []), document_id)
        chunks.extend(table_chunks)
        
        # Process image chunks
        image_chunks = self._chunk_images(document.get('images', []), document_id)
        chunks.extend(image_chunks)
        
        # Create combined multimodal chunks
        multimodal_chunks = self._create_multimodal_chunks(document, document_id)
        chunks.extend(multimodal_chunks)
        
        logger.info(f"Created {len(chunks)} multimodal chunks")
        return chunks
    
    def _chunk_text(self, text: str, document_id: str) -> List[Dict[str, Any]]:
        """Chunk text content"""
        chunks = []
        words = text.split()
        
        current_chunk = []
        current_length = 0
        
        for word in words:
            word_length = len(word)
            
            if current_length + word_length + 1 > self.chunk_size and current_chunk:
                chunk_text = ' '.join(current_chunk)
                chunk_obj = {
                    'chunk_id': str(uuid.uuid4()),
                    'document_id': document_id,
                    'chunk_type': 'text',
                    'content': chunk_text,
                    'token_count': self._estimate_tokens(chunk_text),
                    'character_count': len(chunk_text),
                    'parent_chunk_id': None,
                    'child_chunk_ids': []
                }
                chunks.append(chunk_obj)
                current_chunk = [word]
                current_length = word_length
            else:
                current_chunk.append(word)
                current_length += word_length + 1
        
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            chunk_obj = {
                'chunk_id': str(uuid.uuid4()),
                'document_id': document_id,
                'chunk_type': 'text',
                'content': chunk_text,
                'token_count': self._estimate_tokens(chunk_text),
                'character_count': len(chunk_text),
                'parent_chunk_id': None,
                'child_chunk_ids': []
            }
            chunks.append(chunk_obj)
        
        return chunks
    
    def _chunk_tables(self, tables: List[Dict[str, Any]], document_id: str) -> List[Dict[str, Any]]:
        """Chunk table content — one full-table chunk plus one chunk per row for retrieval."""
        chunks = []

        for table in tables:
            table_id = table.get('table_id', str(uuid.uuid4()))
            summary = table.get('summary', '')
            context = table.get('context_before', '') or table.get('context', '')
            text_repr = table.get('text_representation', '')
            caption = table.get('caption', '')
            headers = table.get('headers') or []
            rows = table.get('rows') or []
            location = table.get('location') or ''

            chunk_text = f"Table: {caption or summary}\n{summary}\n{text_repr}\nContext: {context}".strip()

            chunks.append({
                'chunk_id': str(uuid.uuid4()),
                'document_id': document_id,
                'chunk_type': 'table',
                'content': chunk_text,
                'token_count': self._estimate_tokens(chunk_text),
                'character_count': len(chunk_text),
                'table_id': table_id,
                'parent_chunk_id': None,
                'child_chunk_ids': [],
                'page_number': table.get('page_number'),
                'slide_number': table.get('slide_number'),
            })

            for row_idx, row in enumerate(rows):
                if not row or not any(str(cell or "").strip() for cell in row):
                    continue
                row_plain = " | ".join(str(cell or "").strip() for cell in row)
                if headers:
                    labeled = " | ".join(
                        f"{headers[i]}: {str(cell or '').strip()}"
                        for i, cell in enumerate(row)
                        if i < len(headers) and (headers[i] or str(cell or "").strip())
                    )
                else:
                    labeled = row_plain

                row_text = (
                    f"Table row at {location or 'document'}: {row_plain}\n"
                    f"{labeled}"
                ).strip()
                if caption:
                    row_text = f"Table: {caption}\n{row_text}"

                chunks.append({
                    'chunk_id': str(uuid.uuid4()),
                    'document_id': document_id,
                    'chunk_type': 'table',
                    'content': row_text,
                    'token_count': self._estimate_tokens(row_text),
                    'character_count': len(row_text),
                    'table_id': table_id,
                    'table_row_index': row_idx,
                    'parent_chunk_id': None,
                    'child_chunk_ids': [],
                    'page_number': table.get('page_number'),
                    'slide_number': table.get('slide_number'),
                })

        return chunks
    
    def _chunk_images(self, images: List[Dict[str, Any]], document_id: str) -> List[Dict[str, Any]]:
        """Chunk image content"""
        chunks = []
        
        for image in images:
            image_id = image.get('image_id', str(uuid.uuid4()))
            description = image.get('description', '')
            caption = image.get('caption', '')
            ocr_text = image.get('ocr_text', '')
            chart_data = image.get('chart_data_text', '')
            location = image.get('location', '')
            
            parts = [f"Image at {location}" if location else ""]
            if caption:
                parts.append(f"Caption: {caption}")
            if chart_data:
                parts.append(f"Chart data: {chart_data}")
            if description:
                parts.append(f"Description: {description}")
            if ocr_text and ocr_text != description:
                parts.append(f"OCR text: {ocr_text}")

            chunk_text = "\n".join(p for p in parts if p)
            
            chunk_obj = {
                'chunk_id': str(uuid.uuid4()),
                'document_id': document_id,
                'chunk_type': 'image',
                'content': chunk_text,
                'token_count': self._estimate_tokens(chunk_text),
                'character_count': len(chunk_text),
                'image_id': image_id,
                'image_bytes': image.get('image_bytes'),
                'parent_chunk_id': None,
                'child_chunk_ids': [],
                'page_number': image.get('page_number'),
                'slide_number': image.get('slide_number'),
                'is_chart': image.get('is_chart', False),
            }
            chunks.append(chunk_obj)
        
        return chunks
    
    def _create_multimodal_chunks(self, document: Dict[str, Any], document_id: str) -> List[Dict[str, Any]]:
        """Create chunks that combine text with nearby tables/images"""
        chunks = []
        
        # This is a simplified implementation
        # In production, you would use spatial and contextual relationships
        
        # Find text near tables
        tables = document.get('tables', [])
        for table in tables:
            context_before = table.get('context_before', '')
            context_after = table.get('context_after', '')
            summary = table.get('summary', '')
            
            combined_text = f"{context_before}\nTable: {summary}\n{context_after}"
            
            chunk_obj = {
                'chunk_id': str(uuid.uuid4()),
                'document_id': document_id,
                'chunk_type': 'multimodal',
                'content': combined_text,
                'token_count': self._estimate_tokens(combined_text),
                'character_count': len(combined_text),
                'table_id': table.get('table_id'),
                'parent_chunk_id': None,
                'child_chunk_ids': []
            }
            chunks.append(chunk_obj)
        
        # Find text near images
        images = document.get('images', [])
        for image in images:
            context_before = image.get('context_before', '')
            context_after = image.get('context_after', '')
            description = image.get('description', '')
            
            combined_text = f"{context_before}\nImage: {description}\n{context_after}"
            
            chunk_obj = {
                'chunk_id': str(uuid.uuid4()),
                'document_id': document_id,
                'chunk_type': 'multimodal',
                'content': combined_text,
                'token_count': self._estimate_tokens(combined_text),
                'character_count': len(combined_text),
                'image_id': image.get('image_id'),
                'parent_chunk_id': None,
                'child_chunk_ids': []
            }
            chunks.append(chunk_obj)
        
        return chunks
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count"""
        word_count = len(text.split())
        return int(word_count / 0.75)
    
    def link_related_chunks(self, chunks: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """Link chunks that are related (e.g., text near tables/images)"""
        links = {}
        
        for chunk in chunks:
            chunk_id = chunk['chunk_id']
            related = []
            
            # Find chunks with same table_id or image_id
            for other_chunk in chunks:
                if other_chunk['chunk_id'] != chunk_id:
                    if (chunk.get('table_id') and chunk.get('table_id') == other_chunk.get('table_id')) or \
                       (chunk.get('image_id') and chunk.get('image_id') == other_chunk.get('image_id')):
                        related.append(other_chunk['chunk_id'])
            
            links[chunk_id] = related
        
        return links
