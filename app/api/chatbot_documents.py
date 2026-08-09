from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Chatbot, Document
from app.db.chatbot_document import ChatbotDocument
from app.schemas.chatbot_document import (
    AttachDocumentRequest,
    ChatbotDocumentResponse,
)

router = APIRouter(
    prefix="/chatbots",
    tags=["Chatbot Documents"],
)


@router.post(
    "/{chatbot_id}/documents",
    response_model=ChatbotDocumentResponse,
)
def attach_document(
    chatbot_id: UUID,
    request: AttachDocumentRequest,
    db: Session = Depends(get_db),
):

    chatbot = (
        db.query(Chatbot)
        .filter(Chatbot.id == chatbot_id)
        .first()
    )

    if chatbot is None:
        raise HTTPException(
            status_code=404,
            detail="Chatbot not found",
        )

    document = (
        db.query(Document)
        .filter(Document.id == request.document_id)
        .first()
    )

    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )

    existing = (
        db.query(ChatbotDocument)
        .filter(
            ChatbotDocument.chatbot_id == chatbot_id,
            ChatbotDocument.document_id == request.document_id,
        )
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Document already attached",
        )

    relation = ChatbotDocument(
        chatbot_id=chatbot_id,
        document_id=request.document_id,
    )

    db.add(relation)
    db.commit()
    db.refresh(relation)

    return ChatbotDocumentResponse(
        id=str(relation.id),
        chatbot_id=str(relation.chatbot_id),
        document_id=relation.document_id,
        filename=document.filename,
        created_at=relation.created_at,
    )
@router.get(
    "/{chatbot_id}/documents",
    response_model=list[ChatbotDocumentResponse],
)
def list_chatbot_documents(
    chatbot_id: UUID,
    db: Session = Depends(get_db),
):
    chatbot = (
        db.query(Chatbot)
        .filter(Chatbot.id == chatbot_id)
        .first()
    )

    if chatbot is None:
        raise HTTPException(
            status_code=404,
            detail="Chatbot not found",
        )

    relations = (
        db.query(ChatbotDocument)
        .filter(ChatbotDocument.chatbot_id == chatbot_id)
        .all()
    )

    response = []

    for relation in relations:
        document = (
            db.query(Document)
            .filter(Document.id == relation.document_id)
            .first()
        )

        response.append(
            ChatbotDocumentResponse(
                id=str(relation.id),
                chatbot_id=str(relation.chatbot_id),
                document_id=relation.document_id,
                filename=document.filename if document else "",
                created_at=relation.created_at,
            )
        )

    return response

@router.delete(
    "/{chatbot_id}/documents/{document_id}",
)
def detach_document(
    chatbot_id: UUID,
    document_id: str,
    db: Session = Depends(get_db),
):
    relation = (
        db.query(ChatbotDocument)
        .filter(
            ChatbotDocument.chatbot_id == chatbot_id,
            ChatbotDocument.document_id == document_id,
        )
        .first()
    )

    if relation is None:
        raise HTTPException(
            status_code=404,
            detail="Document is not attached to this chatbot",
        )

    db.delete(relation)
    db.commit()

    return {
        "message": "Document detached successfully"
    }