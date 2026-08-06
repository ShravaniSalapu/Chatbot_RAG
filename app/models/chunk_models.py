"""
Chunk models for the Enterprise Multimodal RAG system
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class ChunkType(str, Enum):
    """Types of chunks"""
    TEXT = "text"
    TABLE = "table"
    IMAGE = "image"
    MULTIMODAL = "multimodal"
    PARENT = "parent"
    CHILD = "child"


class ChunkMetadata(BaseModel):
    """Metadata for a chunk"""
    chunk_id: str
    document_id: str
    chunk_type: ChunkType
    page_number: Optional[int] = None
    section_id: Optional[str] = None
    heading: Optional[str] = None
    token_count: int
    character_count: int
    created_at: datetime = Field(default_factory=datetime.utcnow)
    parent_chunk_id: Optional[str] = None
    child_chunk_ids: List[str] = Field(default_factory=list)
    related_element_ids: List[str] = Field(default_factory=list)


class TextChunk(BaseModel):
    """A text chunk"""
    metadata: ChunkMetadata
    content: str
    embedding: Optional[List[float]] = None
    sparse_embedding: Optional[Dict[str, float]] = None


class TableChunk(BaseModel):
    """A table chunk with summary and context"""
    metadata: ChunkMetadata
    table_data: Dict[str, Any]
    summary: str
    context: str
    embedding: Optional[List[float]] = None
    sparse_embedding: Optional[Dict[str, float]] = None


class ImageChunk(BaseModel):
    """An image chunk with description"""
    metadata: ChunkMetadata
    image_data: Dict[str, Any]
    description: str
    caption: Optional[str] = None
    embedding: Optional[List[float]] = None
    sparse_embedding: Optional[Dict[str, float]] = None


class MultimodalChunk(BaseModel):
    """A chunk containing multiple modalities (text + table, text + image, etc.)"""
    metadata: ChunkMetadata
    text_content: Optional[str] = None
    table_data: Optional[Dict[str, Any]] = None
    image_data: Optional[Dict[str, Any]] = None
    combined_description: str
    embedding: Optional[List[float]] = None
    sparse_embedding: Optional[Dict[str, float]] = None


class ParentChunk(BaseModel):
    """A parent chunk containing larger context"""
    metadata: ChunkMetadata
    content: str
    child_chunks: List[str] = Field(default_factory=list)
    embedding: Optional[List[float]] = None
    sparse_embedding: Optional[Dict[str, float]] = None


class ChildChunk(BaseModel):
    """A child chunk with reference to parent"""
    metadata: ChunkMetadata
    content: str
    parent_chunk_id: str
    embedding: Optional[List[float]] = None
    sparse_embedding: Optional[Dict[str, float]] = None


class Chunk(BaseModel):
    """Generic chunk model that can be any type"""
    chunk_id: str
    document_id: str
    chunk_type: ChunkType
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    embedding: Optional[List[float]] = None
    sparse_embedding: Optional[Dict[str, float]] = None
    parent_chunk_id: Optional[str] = None
    related_chunks: List[str] = Field(default_factory=list)
