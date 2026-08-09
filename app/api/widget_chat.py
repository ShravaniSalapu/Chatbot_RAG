from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import os

from app.db.database import get_db
from app.db.models import Chatbot
from app.db.chatbot_document import ChatbotDocument
from app.schemas.widget_chat import (
    WidgetChatRequest,
    WidgetChatResponse,
)
from app.workflows.chat_pipeline import ChatPipeline
from app.utils.logger import setup_logger


logger = setup_logger(__name__)


router = APIRouter(
    prefix="/widget",
    tags=["Widget Chat"],
)


_chat_pipeline = ChatPipeline()


@router.post(
    "/chat",
    response_model=WidgetChatResponse,
)
async def widget_chat(
    request: WidgetChatRequest,
    db: Session = Depends(get_db),
):
    """Widget chat endpoint with conversation history support."""

    # --------------------------------------------------
    # Log incoming request
    # --------------------------------------------------

    logger.info("=== WIDGET CHAT REQUEST ===")
    logger.info(f"Embed token: {request.embed_token}")
    logger.info(f"Query: {request.query}")

    history = request.conversation_history or []

    logger.info(
        f"Conversation history messages: {len(history)}"
    )

    # --------------------------------------------------
    # Find chatbot
    # --------------------------------------------------

    chatbot = (
        db.query(Chatbot)
        .filter(
            Chatbot.embed_token == request.embed_token
        )
        .first()
    )

    if chatbot is None:
        logger.error(
            f"Chatbot not found for embed token: "
            f"{request.embed_token}"
        )

        raise HTTPException(
            status_code=404,
            detail="Invalid embed token",
        )

    logger.info(
        f"Chatbot found: {chatbot.id}, "
        f"name: {chatbot.name}"
    )

    logger.info(
        f"Chatbot tenant_id: {chatbot.tenant_id}"
    )

    # --------------------------------------------------
    # Find attached document
    # --------------------------------------------------

    relation = (
        db.query(ChatbotDocument)
        .filter(
            ChatbotDocument.chatbot_id == chatbot.id
        )
        .first()
    )

    if relation is None:
        logger.error(
            f"No document attached to chatbot: "
            f"{chatbot.id}"
        )

        raise HTTPException(
            status_code=404,
            detail="No document attached to chatbot",
        )

    logger.info(
        f"Attached document_id: {relation.document_id}"
    )

    # --------------------------------------------------
    # Embedding configuration
    # --------------------------------------------------

    text_model = os.getenv(
        "TEXT_EMBEDDING_MODEL",
        "BAAI/bge-m3",
    )

    logger.info(
        f"Text embedding model: {text_model}"
    )

    try:
        from app.embeddings.embedding_factory import (
            get_embedding_factory,
        )

        factory = get_embedding_factory()

        text_emb = factory.get_text_embedding()

        emb_dim = text_emb.get_embedding_dimension()

        logger.info(
            f"Embedding dimension: {emb_dim}"
        )

    except Exception as e:
        logger.error(
            f"Error getting embedding dimension: {str(e)}"
        )

    # --------------------------------------------------
    # Retrieval configuration
    # --------------------------------------------------

    retrieval_method = os.getenv(
        "RETRIEVAL_METHOD",
        "hybrid",
    )

    top_k = int(
        os.getenv(
            "TOP_K",
            "5",
        )
    )

    logger.info(
        f"Retrieval method: {retrieval_method}"
    )

    logger.info(
        f"TOP_K: {top_k}"
    )

    # --------------------------------------------------
    # Convert conversation history to dictionaries
    # --------------------------------------------------

    conversation_history = [
        {
            "role": message.role,
            "content": message.content,
        }
        for message in history
    ]

    # --------------------------------------------------
    # Call ChatPipeline
    # --------------------------------------------------

    try:

        logger.info(
            "Calling ChatPipeline.chat()..."
        )

        result = _chat_pipeline.chat(
            query=request.query,
            document_id=relation.document_id,
            tenant_id=str(chatbot.tenant_id),
            allowed_document_ids=None,
            conversation_history=(
                conversation_history
                if conversation_history
                else None
            ),
            use_reranking=True,
            top_k=top_k,
            retrieval_method=retrieval_method,
        )

        logger.info(
            f"ChatPipeline result keys: "
            f"{result.keys()}"
        )

        answer = result.get(
            "answer",
            "",
        )

        logger.info(
            f"Answer length: {len(answer)}"
        )

        logger.info(
            f"Answer preview: {answer[:200]}..."
        )

        # --------------------------------------------------
        # Return response
        # --------------------------------------------------

        return WidgetChatResponse(
            answer=answer
        )

    except Exception as e:

        logger.error(
            f"Error in ChatPipeline.chat(): {str(e)}",
            exc_info=True,
        )

        raise HTTPException(
            status_code=500,
            detail=str(e),
        )