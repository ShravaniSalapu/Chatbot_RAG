import uuid

from sqlalchemy.orm import Session

from app.db.models import Chatbot
from app.db.chatbot_settings import ChatbotSettings



def create_chatbot(
    db: Session,
    tenant_id: str,
    name: str,
    description: str | None,
):
    chatbot = Chatbot(
        id=uuid.uuid4(),
        tenant_id=uuid.UUID(tenant_id),
        name=name,
        description=description,
        status="active",
    )

    db.add(chatbot)
    db.flush()

    settings = ChatbotSettings(
        chatbot_id=chatbot.id
    )

    db.add(settings)

    db.commit()

    db.refresh(chatbot)

    return chatbot


def get_chatbots(db: Session, tenant_id: str):
    return (
        db.query(Chatbot)
        .filter(Chatbot.tenant_id == uuid.UUID(tenant_id))
        .order_by(Chatbot.created_at.desc())
        .all()
    )


def get_chatbot(db: Session, tenant_id: str, chatbot_id: str):
    return (
        db.query(Chatbot)
        .filter(
            Chatbot.id == uuid.UUID(chatbot_id),
            Chatbot.tenant_id == uuid.UUID(tenant_id),
        )
        .first()
    )


def update_chatbot(
    db: Session,
    chatbot: Chatbot,
    name: str | None,
    description: str | None,
    status: str | None,
):
    if name is not None:
        chatbot.name = name

    if description is not None:
        chatbot.description = description

    if status is not None:
        chatbot.status = status

    db.commit()
    db.refresh(chatbot)

    return chatbot


def delete_chatbot(db: Session, chatbot: Chatbot):
    db.delete(chatbot)
    db.commit()
    
def get_chatbot_settings(
    db: Session,
    chatbot_id: str,
):
    return (
        db.query(ChatbotSettings)
        .filter(
            ChatbotSettings.chatbot_id == uuid.UUID(chatbot_id)
        )
        .first()
    )


def update_chatbot_settings(
    db: Session,
    settings: ChatbotSettings,
    body,
):
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(settings, key, value)

    db.commit()
    db.refresh(settings)

    return settings