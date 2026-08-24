"""
Admin API endpoints for platform management and statistics.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.auth.dependencies import CurrentUser, require_admin
from app.db.database import get_db
from app.db.models import (
    User,
    Chatbot,
    Document,
    AuditLog,
    TenantUsage,
)
from app.services.audit_service import ACTION_CHAT


router = APIRouter()


# ============================================================
# MAIN ADMIN CHECK
# ============================================================

def require_main_admin(current_user: CurrentUser):
    """
    Only admin@gmail.com is the platform administrator.
    """

    if current_user.email.lower() != "admin@gmail.com":
        raise HTTPException(
            status_code=403,
            detail="Only the main administrator can access this resource",
        )

    return current_user


# ============================================================
# ADMIN DASHBOARD STATS
# ============================================================

@router.get("/admin/stats")
async def get_admin_stats(
    current_user: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Get platform-wide statistics.

    Only admin@gmail.com can see platform-wide statistics.
    """

    require_main_admin(current_user)

    # --------------------------------------------------------
    # ALL USERS
    # --------------------------------------------------------

    user_count = (
        db.query(User)
        .count()
    )

    # --------------------------------------------------------
    # ALL CHATBOTS
    # --------------------------------------------------------

    chatbot_count = (
        db.query(Chatbot)
        .count()
    )

    # --------------------------------------------------------
    # ALL DOCUMENTS
    # --------------------------------------------------------

    document_count = (
        db.query(Document)
        .count()
    )

    # --------------------------------------------------------
    # TOTAL CHAT COUNT
    #
    # Count successful chat audit records across
    # the entire platform.
    # --------------------------------------------------------

    conversation_count = (
        db.query(func.count(AuditLog.id))
        .filter(
            AuditLog.action == ACTION_CHAT
        )
        .scalar()
        or 0
    )

    # --------------------------------------------------------
    # USAGE
    #
    # TenantUsage is tenant-level, so sum it across
    # all tenants.
    # --------------------------------------------------------

    message_count = (
        db.query(
            func.coalesce(
                func.sum(
                    TenantUsage.api_call_count
                ),
                0,
            )
        )
        .scalar()
        or 0
    )

    storage_used = (
        db.query(
            func.coalesce(
                func.sum(
                    TenantUsage.storage_bytes
                ),
                0,
            )
        )
        .scalar()
        or 0
    )

    return {
        "users": int(user_count),
        "chatbots": int(chatbot_count),
        "documents": int(document_count),
        "conversations": int(conversation_count),
        "messages": int(message_count),
        "storage_used": int(storage_used),
    }


# ============================================================
# ALL USERS + INDIVIDUAL USAGE
# ============================================================

@router.get("/admin/users")
async def get_users(
    current_user: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Get ALL users across ALL tenants.

    Only admin@gmail.com can access this endpoint.

    Each user includes:

        - id
        - email
        - full_name
        - role
        - tenant_id
        - active status
        - chat_count
        - document_count
    """

    require_main_admin(current_user)

    # --------------------------------------------------------
    # GET ALL USERS
    #
    # IMPORTANT:
    # There is intentionally NO tenant_id filter.
    # --------------------------------------------------------

    users = (
        db.query(User)
        .order_by(User.created_at.asc())
        .all()
    )

    result = []

    for user in users:

        # ----------------------------------------------------
        # USER CHAT COUNT
        # ----------------------------------------------------

        chat_count = (
            db.query(
                func.count(AuditLog.id)
            )
            .filter(
                AuditLog.user_id == user.id,
                AuditLog.action == ACTION_CHAT,
            )
            .scalar()
            or 0
        )

        # ----------------------------------------------------
        # USER DOCUMENT COUNT
        # ----------------------------------------------------

        document_count = (
            db.query(
                func.count(Document.id)
            )
            .filter(
                Document.uploaded_by == user.id
            )
            .scalar()
            or 0
        )

        result.append(
            {
                "id": str(user.id),
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role,
                "tenant_id": str(user.tenant_id),
                "is_active": user.is_active,
                "created_at": user.created_at,

                # Individual usage
                "chat_count": int(chat_count),
                "document_count": int(document_count),
            }
        )

    return result


# ============================================================
# ANALYTICS
# ============================================================

@router.get("/analytics")
async def get_analytics(
    current_user: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Platform-wide analytics.

    Only admin@gmail.com can access this.
    """

    require_main_admin(current_user)

    # --------------------------------------------------------
    # CHATBOTS
    # --------------------------------------------------------

    total_chatbots = (
        db.query(Chatbot)
        .count()
    )

    active_chatbots = (
        db.query(Chatbot)
        .filter(
            Chatbot.status == "active"
        )
        .count()
    )

    # --------------------------------------------------------
    # DOCUMENTS
    # --------------------------------------------------------

    total_documents = (
        db.query(Document)
        .count()
    )

    processing_documents = (
        db.query(Document)
        .filter(
            Document.status == "processing"
        )
        .count()
    )

    # --------------------------------------------------------
    # TOTAL CHATS
    # --------------------------------------------------------

    total_conversations = (
        db.query(
            func.count(AuditLog.id)
        )
        .filter(
            AuditLog.action == ACTION_CHAT
        )
        .scalar()
        or 0
    )

    # --------------------------------------------------------
    # TOTAL API CALLS
    # --------------------------------------------------------

    total_messages = (
        db.query(
            func.coalesce(
                func.sum(
                    TenantUsage.api_call_count
                ),
                0,
            )
        )
        .scalar()
        or 0
    )

    # --------------------------------------------------------
    # STORAGE
    # --------------------------------------------------------

    storage_used = (
        db.query(
            func.coalesce(
                func.sum(
                    TenantUsage.storage_bytes
                ),
                0,
            )
        )
        .scalar()
        or 0
    )

    return {
        "total_chatbots": int(total_chatbots),
        "active_chatbots": int(active_chatbots),
        "total_documents": int(total_documents),
        "processing_documents": int(
            processing_documents
        ),
        "total_conversations": int(
            total_conversations
        ),
        "total_messages": int(
            total_messages
        ),
        "storage_used": int(
            storage_used
        ),
    }


# ============================================================
# RECENT ACTIVITY
# ============================================================

@router.get("/admin/recent-activity")
async def get_recent_activity(
    current_user: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db),
    limit: int = 10,
):
    """
    Get recent activity across the platform.

    Only admin@gmail.com can access this.
    """

    require_main_admin(current_user)

    # Prevent unreasonable values
    limit = max(1, min(limit, 100))

    logs = (
        db.query(AuditLog)
        .order_by(
            AuditLog.created_at.desc()
        )
        .limit(limit)
        .all()
    )

    return [
        {
            "id": str(log.id),
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "user_id": (
                str(log.user_id)
                if log.user_id
                else None
            ),
            "ip_address": log.ip_address,
            "created_at": log.created_at,
        }
        for log in logs
    ]