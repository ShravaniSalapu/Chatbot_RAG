"""
Response models for the Enterprise Multimodal RAG system
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class UploadResponse(BaseModel):
    """Response for document upload"""
    success: bool
    document_id: str
    filename: str
    message: str
    processing_status: str
    chunks_created: Optional[int] = None
    tables_extracted: Optional[int] = None
    images_extracted: Optional[int] = None


class SearchResult(BaseModel):
    """A single search result"""
    chunk_id: str
    document_id: str
    content: str
    score: float
    chunk_type: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    page_number: Optional[int] = None
    heading: Optional[str] = None


class SearchResponse(BaseModel):
    """Response for search queries"""
    query: str
    results: List[SearchResult]
    total_results: int
    search_time_ms: float
    retrieval_method: str


class Citation(BaseModel):
    """A citation reference"""
    chunk_id: str
    document_id: str
    filename: str
    page_number: Optional[int] = None
    heading: Optional[str] = None
    snippet: str


class ChatMessage(BaseModel):
    """A chat message"""
    role: str  # "user", "assistant", "system"
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ChatResponse(BaseModel):
    """Response for chat queries"""
    answer: str
    citations: List[Citation] = Field(default_factory=list)
    sources: List[Dict[str, Any]] = Field(default_factory=list)
    confidence_score: Optional[float] = None
    processing_time_ms: float
    model_used: str
    context_used: List[str] = Field(default_factory=list)


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    services: Dict[str, Any] = Field(default_factory=dict)
    version: str


class ErrorResponse(BaseModel):
    """Error response"""
    error: str
    detail: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class DocumentStatusResponse(BaseModel):
    """Response for document status check"""
    document_id: str
    status: str  # "processing", "completed", "failed"
    progress: Optional[float] = None
    chunks_created: Optional[int] = None
    error_message: Optional[str] = None
