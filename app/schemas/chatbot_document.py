from pydantic import BaseModel
from datetime import datetime


class AttachDocumentRequest(BaseModel):
    document_id: str


class ChatbotDocumentResponse(BaseModel):
    id: str
    chatbot_id: str
    document_id: str
    filename: str
    created_at: datetime

    class Config:
        from_attributes = True