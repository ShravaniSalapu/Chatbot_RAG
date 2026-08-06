"""
Document models for the Enterprise Multimodal RAG system
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class DocumentType(str, Enum):
    """Supported document types"""
    PDF = "pdf"
    DOCX = "docx"
    PPTX = "pptx"
    IMAGE = "image"
    EXCEL = "excel"
    TEXT = "text"


class ElementType(str, Enum):
    """Types of elements within a document"""
    TEXT = "text"
    TABLE = "table"
    IMAGE = "image"
    CHART = "chart"
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    LIST = "list"


class DocumentMetadata(BaseModel):
    """Metadata for a document"""
    filename: str
    file_type: DocumentType
    file_size: int
    upload_date: datetime = Field(default_factory=datetime.utcnow)
    page_count: Optional[int] = None
    title: Optional[str] = None
    author: Optional[str] = None
    subject: Optional[str] = None
    keywords: Optional[List[str]] = None
    language: Optional[str] = None
    custom_metadata: Optional[Dict[str, Any]] = None


class DocumentElement(BaseModel):
    """A single element within a document (text, table, image, etc.)"""
    element_id: str
    element_type: ElementType
    content: str
    page_number: Optional[int] = None
    bbox: Optional[List[float]] = None  # [x1, y1, x2, y2]
    heading_level: Optional[int] = None
    parent_id: Optional[str] = None
    children_ids: List[str] = Field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = None


class TableData(BaseModel):
    """Structured table data"""
    table_id: str
    headers: List[str]
    rows: List[List[str]]
    caption: Optional[str] = None
    page_number: Optional[int] = None
    bbox: Optional[List[float]] = None
    summary: Optional[str] = None
    context_before: Optional[str] = None
    context_after: Optional[str] = None


class ImageData(BaseModel):
    """Image data with caption and context"""
    image_id: str
    image_bytes: Optional[str] = None  # Base64 encoded
    caption: Optional[str] = None
    description: Optional[str] = None
    page_number: Optional[int] = None
    bbox: Optional[List[float]] = None
    context_before: Optional[str] = None
    context_after: Optional[str] = None
    is_chart: bool = False
    chart_type: Optional[str] = None


class Document(BaseModel):
    """Complete document structure"""
    document_id: str
    metadata: DocumentMetadata
    elements: List[DocumentElement]
    tables: List[TableData] = Field(default_factory=list)
    images: List[ImageData] = Field(default_factory=list)
    document_tree: Optional[Dict[str, Any]] = None
    raw_text: Optional[str] = None
    
    class Config:
        arbitrary_types_allowed = True


class DocumentSection(BaseModel):
    """A section within a document"""
    section_id: str
    heading: str
    level: int
    content: str
    page_range: Optional[List[int]] = None
    parent_section_id: Optional[str] = None
    child_section_ids: List[str] = Field(default_factory=list)
    element_ids: List[str] = Field(default_factory=list)
