import uuid
from datetime import datetime

from sqlalchemy import String, Text, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


def _uuid():
    return uuid.uuid4()


class ChatbotSettings(Base):
    __tablename__ = "chatbot_settings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=_uuid,
    )

    chatbot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chatbots.id"),
        nullable=False,
        unique=True,
    )

    primary_color: Mapped[str] = mapped_column(
        String(20),
        default="#2563eb",
    )

    secondary_color: Mapped[str] = mapped_column(
        String(20),
        default="#ffffff",
    )

    logo_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    avatar_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    welcome_message: Mapped[str] = mapped_column(
        Text,
        default="Hi! How can I help you today?",
    )

    placeholder: Mapped[str] = mapped_column(
        String(255),
        default="Ask me anything...",
    )

    position: Mapped[str] = mapped_column(
        String(20),
        default="bottom-right",
    )

    theme: Mapped[str] = mapped_column(
        String(20),
        default="light",
    )

    border_radius: Mapped[str] = mapped_column(
        String(20),
        default="16px",
    )

    widget_width: Mapped[str] = mapped_column(
        String(20),
        default="380px",
    )

    widget_height: Mapped[str] = mapped_column(
        String(20),
        default="600px",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        onupdate=func.now(),
    )

    chatbot = relationship(
        "Chatbot",
        back_populates="settings",
    )