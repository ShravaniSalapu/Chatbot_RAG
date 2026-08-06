from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CreateChatbotRequest(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    description: Optional[str] = None


class UpdateChatbotRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


class ChatbotResponse(BaseModel):
    id: str
    tenant_id: str
    name: str
    description: Optional[str]
    status: str
    embed_token: str
    created_at: datetime

class ChatbotSettingsResponse(BaseModel):
    chatbot_id: str
    primary_color: str
    secondary_color: str
    logo_url: Optional[str]
    avatar_url: Optional[str]
    welcome_message: str
    placeholder: str
    position: str
    theme: str
    border_radius: str
    widget_width: str
    widget_height: str


class UpdateChatbotSettingsRequest(BaseModel):
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None
    logo_url: Optional[str] = None
    avatar_url: Optional[str] = None
    welcome_message: Optional[str] = None
    placeholder: Optional[str] = None
    position: Optional[str] = None
    theme: Optional[str] = None
    border_radius: Optional[str] = None
    widget_width: Optional[str] = None
    widget_height: Optional[str] = None