from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, get_current_user
from app.db.database import get_db

from app.models.chatbot_models import (
    CreateChatbotRequest,
    UpdateChatbotRequest,
    ChatbotResponse,
    ChatbotSettingsResponse,
    UpdateChatbotSettingsRequest,
)

from app.services.chatbot_service import (
    create_chatbot,
    get_chatbots,
    get_chatbot,
    update_chatbot,
    delete_chatbot,
    get_chatbot_settings,
    update_chatbot_settings,
)

router = APIRouter(
    prefix="/chatbots",
    tags=["Chatbots"],
)


@router.post("", response_model=ChatbotResponse)
async def create_new_chatbot(
    body: CreateChatbotRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    chatbot = create_chatbot(
        db=db,
        tenant_id=current_user.tenant_id,
        name=body.name,
        description=body.description,
    )

    return ChatbotResponse(
        id=str(chatbot.id),
        tenant_id=str(chatbot.tenant_id),
        name=chatbot.name,
        description=chatbot.description,
        status=chatbot.status,
        embed_token=chatbot.embed_token,
        created_at=chatbot.created_at,
    )


@router.get("", response_model=list[ChatbotResponse])
async def list_chatbots(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    bots = get_chatbots(db, current_user.tenant_id)

    return [
        ChatbotResponse(
            id=str(bot.id),
            tenant_id=str(bot.tenant_id),
            name=bot.name,
            description=bot.description,
            status=bot.status,
            embed_token=bot.embed_token,
            created_at=bot.created_at,
        )
        for bot in bots
    ]


@router.get("/{chatbot_id}", response_model=ChatbotResponse)
async def get_single_chatbot(
    chatbot_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    bot = get_chatbot(
        db,
        current_user.tenant_id,
        chatbot_id,
    )

    if not bot:
        raise HTTPException(
            status_code=404,
            detail="Chatbot not found",
        )

    return ChatbotResponse(
        id=str(bot.id),
        tenant_id=str(bot.tenant_id),
        name=bot.name,
        description=bot.description,
        status=bot.status,
        embed_token=bot.embed_token,
        created_at=bot.created_at,
    )


@router.put("/{chatbot_id}", response_model=ChatbotResponse)
async def update_existing_chatbot(
    chatbot_id: str,
    body: UpdateChatbotRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    bot = get_chatbot(
        db,
        current_user.tenant_id,
        chatbot_id,
    )

    if not bot:
        raise HTTPException(
            status_code=404,
            detail="Chatbot not found",
        )

    bot = update_chatbot(
        db,
        chatbot=bot,
        name=body.name,
        description=body.description,
        status=body.status,
    )

    return ChatbotResponse(
        id=str(bot.id),
        tenant_id=str(bot.tenant_id),
        name=bot.name,
        description=bot.description,
        status=bot.status,
        embed_token=bot.embed_token,
        created_at=bot.created_at,
    )


@router.delete("/{chatbot_id}")
async def delete_existing_chatbot(
    chatbot_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    bot = get_chatbot(
        db,
        current_user.tenant_id,
        chatbot_id,
    )

    if not bot:
        raise HTTPException(
            status_code=404,
            detail="Chatbot not found",
        )

    delete_chatbot(
        db,
        chatbot=bot,
    )

    return {
        "message": "Chatbot deleted successfully"
    }


@router.get("/{chatbot_id}/settings", response_model=ChatbotSettingsResponse)
async def get_settings(
    chatbot_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    chatbot = get_chatbot(db, current_user.tenant_id, chatbot_id)

    if chatbot is None:
        raise HTTPException(
            status_code=404,
            detail="Chatbot not found",
        )

    settings = get_chatbot_settings(db, chatbot_id)

    return ChatbotSettingsResponse(
        chatbot_id=str(settings.chatbot_id),
        primary_color=settings.primary_color,
        secondary_color=settings.secondary_color,
        logo_url=settings.logo_url,
        avatar_url=settings.avatar_url,
        welcome_message=settings.welcome_message,
        placeholder=settings.placeholder,
        position=settings.position,
        theme=settings.theme,
        border_radius=settings.border_radius,
        widget_width=settings.widget_width,
        widget_height=settings.widget_height,
    )


@router.put("/{chatbot_id}/settings", response_model=ChatbotSettingsResponse)
async def update_settings(
    chatbot_id: str,
    body: UpdateChatbotSettingsRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    chatbot = get_chatbot(db, current_user.tenant_id, chatbot_id)

    if chatbot is None:
        raise HTTPException(
            status_code=404,
            detail="Chatbot not found",
        )

    settings = get_chatbot_settings(db, chatbot_id)

    settings = update_chatbot_settings(
        db,
        settings,
        body,
    )

    return ChatbotSettingsResponse(
        chatbot_id=str(settings.chatbot_id),
        primary_color=settings.primary_color,
        secondary_color=settings.secondary_color,
        logo_url=settings.logo_url,
        avatar_url=settings.avatar_url,
        welcome_message=settings.welcome_message,
        placeholder=settings.placeholder,
        position=settings.position,
        theme=settings.theme,
        border_radius=settings.border_radius,
        widget_width=settings.widget_width,
        widget_height=settings.widget_height,
    )