"""
Authentication API: registration and login.
"""

import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, get_current_user
from app.auth.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.db.database import get_db
from app.db.models import Tenant, User
from app.models.auth_models import (
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.services.usage_service import get_or_create_usage
from app.services.audit_service import (
    log_audit,
    ACTION_LOGIN,
    ACTION_REGISTER,
)
from app.utils.request_utils import client_ip


router = APIRouter()


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def _slugify(name: str) -> str:
    slug = re.sub(
        r"[^a-z0-9]+",
        "-",
        name.lower(),
    ).strip("-")

    return slug or "tenant"


def _unique_slug(
    db: Session,
    base: str,
) -> str:

    slug = base
    counter = 1

    while db.query(Tenant).filter(
        Tenant.slug == slug
    ).first():

        slug = f"{base}-{counter}"
        counter += 1

    return slug


# ============================================================
# REGISTER
# ============================================================

@router.post(
    "/auth/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    request: Request,
    body: RegisterRequest,
    db: Session = Depends(get_db),
):
    """
    Register a new tenant and normal user.

    IMPORTANT:
    Public signup NEVER creates an admin.

    The only fixed admin account is:
        admin@gmail.com
    """

    # --------------------------------------------------------
    # CHECK EMAIL
    # --------------------------------------------------------

    existing_user = (
        db.query(User)
        .filter(User.email == body.email)
        .first()
    )

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )


    # --------------------------------------------------------
    # CREATE TENANT
    # --------------------------------------------------------

    slug = _unique_slug(
        db,
        _slugify(body.tenant_name),
    )

    tenant = Tenant(
        name=body.tenant_name,
        slug=slug,
        plan="free",
    )

    db.add(tenant)
    db.flush()


    # --------------------------------------------------------
    # CREATE USER
    # --------------------------------------------------------
    #
    # IMPORTANT:
    # Every account created through public signup
    # is ALWAYS a normal user.
    #
    # Never use "first user = admin".
    # --------------------------------------------------------

    user = User(
        tenant_id=tenant.id,
        email=body.email,
        hashed_password=hash_password(
            body.password
        ),
        full_name=body.full_name,
        role="user",
    )

    db.add(user)

    db.commit()
    db.refresh(user)


    # --------------------------------------------------------
    # CREATE USAGE RECORD
    # --------------------------------------------------------

    get_or_create_usage(
        db,
        str(tenant.id),
    )


    # --------------------------------------------------------
    # AUDIT LOG
    # --------------------------------------------------------

    log_audit(
        db,
        tenant_id=str(tenant.id),
        user_id=str(user.id),
        action=ACTION_REGISTER,
        resource_type="tenant",
        resource_id=str(tenant.id),
        metadata={
            "email": body.email,
            "tenant_name": body.tenant_name,
            "role": "user",
        },
        ip_address=client_ip(request),
    )


    # --------------------------------------------------------
    # CREATE TOKEN
    # --------------------------------------------------------

    token = create_access_token(
        str(user.id),
        extra_claims={
            "tenant_id": str(tenant.id),
            "role": user.role,
        },
    )


    return TokenResponse(
        access_token=token,
        user_id=str(user.id),
        tenant_id=str(tenant.id),
        email=user.email,
        role=user.role,
    )


# ============================================================
# LOGIN
# ============================================================

@router.post(
    "/auth/login",
    response_model=TokenResponse,
)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """
    Login with email and password.
    """

    user = (
        db.query(User)
        .filter(
            User.email == form_data.username
        )
        .first()
    )


    # --------------------------------------------------------
    # INVALID LOGIN
    # --------------------------------------------------------

    if (
        not user
        or not verify_password(
            form_data.password,
            user.hashed_password,
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={
                "WWW-Authenticate": "Bearer"
            },
        )


    # --------------------------------------------------------
    # ACCOUNT DISABLED
    # --------------------------------------------------------

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account disabled",
        )


    # --------------------------------------------------------
    # CREATE TOKEN
    # --------------------------------------------------------

    token = create_access_token(
        str(user.id),
        extra_claims={
            "tenant_id": str(user.tenant_id),
            "role": user.role,
        },
    )


    # --------------------------------------------------------
    # AUDIT
    # --------------------------------------------------------

    log_audit(
        db,
        tenant_id=str(user.tenant_id),
        user_id=str(user.id),
        action=ACTION_LOGIN,
        resource_type="user",
        resource_id=str(user.id),
        ip_address=client_ip(request),
    )


    return TokenResponse(
        access_token=token,
        user_id=str(user.id),
        tenant_id=str(user.tenant_id),
        email=user.email,
        role=user.role,
    )


# ============================================================
# CURRENT USER
# ============================================================

@router.get(
    "/auth/me",
    response_model=UserResponse,
)
async def get_me(
    current_user: CurrentUser = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db),
):
    """
    Get the current authenticated user.
    """

    user = (
        db.query(User)
        .filter(
            User.id ==
            uuid.UUID(
                current_user.user_id
            )
        )
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )


    return UserResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        tenant_id=str(user.tenant_id),
        created_at=user.created_at,
    )