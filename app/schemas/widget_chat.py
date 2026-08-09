from typing import List, Optional

from pydantic import BaseModel


class ChatHistoryMessage(BaseModel):
    role: str
    content: str


class WidgetChatRequest(BaseModel):
    embed_token: str
    query: str
    conversation_history: Optional[List[ChatHistoryMessage]] = None


class WidgetChatResponse(BaseModel):
    answer: str