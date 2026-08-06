"""Pydantic models for Phase 4 agent API."""

from typing import Optional

from pydantic import BaseModel, Field


class AgentChatRequest(BaseModel):
    query: str = Field(min_length=1, max_length=8000)
    session_id: Optional[str] = None
    document_id: Optional[str] = None
    use_memory: bool = True


class AgentChatResponse(BaseModel):
    answer: str
    session_id: str
    tools_used: list[str] = Field(default_factory=list)
    processing_time_ms: float
    model_used: str
    mode: str = "agent"
