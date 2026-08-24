import uuid

from sqlalchemy.orm import Session

from app.db.models import Chatbot
from app.db.chatbot_settings import ChatbotSettings


# ============================================================
# CREATE CHATBOT
# ============================================================

def create_chatbot(
    db: Session,
    tenant_id: str,
    name: str,
    description: str | None,
    created_by: str | None = None,
):
    """
    Create a chatbot for a tenant.

    created_by identifies the user who created the chatbot.
    """

    chatbot = Chatbot(
        id=uuid.uuid4(),
        tenant_id=uuid.UUID(tenant_id),
        created_by=(
            uuid.UUID(created_by)
            if created_by
            else None
        ),
        name=name,
        description=description,
        status="active",
    )

    db.add(chatbot)
    db.flush()

    # Create default settings for the chatbot
    settings = ChatbotSettings(
        chatbot_id=chatbot.id
    )

    db.add(settings)

    db.commit()
    db.refresh(chatbot)

    return chatbot


# ============================================================
# GET CHATBOTS
# ============================================================

def get_chatbots(
    db: Session,
    tenant_id: str,
    user_id: str | None = None,
):
    """
    Admin:
        user_id=None
        -> sees all chatbots in tenant

    Normal user:
        user_id=<their user id>
        -> sees only their own chatbots
    """

    query = (
        db.query(Chatbot)
        .filter(
            Chatbot.tenant_id == uuid.UUID(tenant_id)
        )
    )

    if user_id is not None:
        query = query.filter(
            Chatbot.created_by == uuid.UUID(user_id)
        )

    return (
        query
        .order_by(Chatbot.created_at.desc())
        .all()
    )


# ============================================================
# GET SINGLE CHATBOT
# ============================================================

def get_chatbot(
    db: Session,
    tenant_id: str,
    chatbot_id: str,
    user_id: str | None = None,
):
    """
    Get one chatbot.

    Tenant isolation is always applied.

    If user_id is supplied, the chatbot must also
    belong to that user.
    """

    query = (
        db.query(Chatbot)
        .filter(
            Chatbot.id == uuid.UUID(chatbot_id),
            Chatbot.tenant_id == uuid.UUID(tenant_id),
        )
    )

    if user_id is not None:
        query = query.filter(
            Chatbot.created_by == uuid.UUID(user_id)
        )

    return query.first()


# ============================================================
# UPDATE CHATBOT
# ============================================================

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


# ============================================================
# DELETE CHATBOT
# ============================================================

def delete_chatbot(
    db: Session,
    chatbot: Chatbot,
):
    db.delete(chatbot)
    db.commit()


# ============================================================
# GET CHATBOT SETTINGS
# ============================================================

def get_chatbot_settings(
    db: Session,
    chatbot_id: str,
):
    return (
        db.query(ChatbotSettings)
        .filter(
            ChatbotSettings.chatbot_id
            == uuid.UUID(chatbot_id)
        )
        .first()
    )


# ============================================================
# UPDATE CHATBOT SETTINGS
# ============================================================

def update_chatbot_settings(
    db: Session,
    settings: ChatbotSettings,
    body,
):
    for key, value in body.model_dump(
        exclude_unset=True
    ).items():
        setattr(
            settings,
            key,
            value,
        )

    db.commit()
    db.refresh(settings)

    return settings