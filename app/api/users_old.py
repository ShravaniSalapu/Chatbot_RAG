"""
User profile and settings API endpoints.
"""

import uuid

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.auth.dependencies import (
    CurrentUser,
    get_current_user,
    require_admin,
)
from app.auth.security import (
    hash_password,
    verify_password,
)
from app.db.database import get_db
from app.db.models import User


router = APIRouter()


# ============================================================
# REQUEST MODELS
# ============================================================

class UserProfileUpdate(BaseModel):
    full_name: str | None = None
    email: EmailStr


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


class CreateUserRequest(BaseModel):
    email: EmailStr
    full_name: str
    password: str


# ============================================================
# GET CURRENT USER
# ============================================================

@router.get("/users/me")
async def get_current_user_profile(
    current_user: CurrentUser = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db),
):
    """Get current user profile."""

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
            status_code=404,
            detail="User not found",
        )


    return {
        "id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "tenant_id": str(user.tenant_id),
        "is_active": user.is_active,
        "created_at": user.created_at,
    }


# ============================================================
# UPDATE CURRENT USER
# ============================================================

@router.put("/users/me")
async def update_user_profile(
    profile_update: UserProfileUpdate,
    current_user: CurrentUser = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db),
):
    """Update current user's profile."""

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
            status_code=404,
            detail="User not found",
        )


    # --------------------------------------------------------
    # EMAIL CHANGE
    # --------------------------------------------------------

    if (
        profile_update.email
        and profile_update.email != user.email
    ):

        existing_user = (
            db.query(User)
            .filter(
                User.email ==
                profile_update.email
            )
            .first()
        )

        if existing_user:
            raise HTTPException(
                status_code=400,
                detail="Email already registered",
            )

        user.email = profile_update.email


    # --------------------------------------------------------
    # NAME CHANGE
    # --------------------------------------------------------

    if profile_update.full_name is not None:
        user.full_name = (
            profile_update.full_name
        )


    db.commit()
    db.refresh(user)


    return {
        "id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "tenant_id": str(user.tenant_id),
        "is_active": user.is_active,
        "created_at": user.created_at,
    }


# ============================================================
# CHANGE PASSWORD
# ============================================================

@router.put("/users/me/password")
async def change_password(
    password_change: PasswordChange,
    current_user: CurrentUser = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db),
):
    """Change current user's password."""

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
            status_code=404,
            detail="User not found",
        )


    if not verify_password(
        password_change.current_password,
        user.hashed_password,
    ):
        raise HTTPException(
            status_code=400,
            detail="Current password is incorrect",
        )


    if len(
        password_change.new_password
    ) < 8:

        raise HTTPException(
            status_code=400,
            detail="New password must be at least 8 characters",
        )


    user.hashed_password = hash_password(
        password_change.new_password
    )

    db.commit()


    return {
        "message":
            "Password changed successfully"
    }


# ============================================================
# CREATE USER
# ============================================================

@router.post("/users/create")
async def create_user(
    user_request: CreateUserRequest,
    current_user: CurrentUser = Depends(
        require_admin
    ),
    db: Session = Depends(get_db),
):
    """
    Create a normal user.

    ONLY an admin can use this endpoint.

    Users created here are ALWAYS role='user'.
    """

    # --------------------------------------------------------
    # CHECK EMAIL
    # --------------------------------------------------------

    existing_user = (
        db.query(User)
        .filter(
            User.email ==
            user_request.email
        )
        .first()
    )

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered",
        )


    # --------------------------------------------------------
    # CREATE NORMAL USER
    # --------------------------------------------------------

    new_user = User(
        tenant_id=uuid.UUID(
            current_user.tenant_id
        ),
        email=user_request.email,
        hashed_password=hash_password(
            user_request.password
        ),
        full_name=user_request.full_name,
        role="user",
        is_active=True,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)


    return {
        "id": str(new_user.id),
        "email": new_user.email,
        "full_name": new_user.full_name,
        "role": "user",
        "tenant_id": str(new_user.tenant_id),
        "is_active": new_user.is_active,
        "created_at": new_user.created_at,
    }


# ============================================================
# UPDATE USER ROLE
# ============================================================

@router.put("/users/{user_id}/role")
async def update_user_role(
    user_id: str,
    role: str,
    current_user: CurrentUser = Depends(
        require_admin
    ),
    db: Session = Depends(get_db),
):
    """
    Change a user's role.

    Only the fixed admin account can do this.

    The fixed admin itself cannot be changed.
    """

    # --------------------------------------------------------
    # ONLY admin@gmail.com CAN CHANGE ROLES
    # --------------------------------------------------------

    if current_user.email.lower() != "admin@gmail.com":
        raise HTTPException(
            status_code=403,
            detail="Only the main administrator can change user roles",
        )


    # --------------------------------------------------------
    # VALID ROLE
    # --------------------------------------------------------

    if role not in [
        "admin",
        "user",
    ]:
        raise HTTPException(
            status_code=400,
            detail="Role must be either 'admin' or 'user'",
        )


    # --------------------------------------------------------
    # FIND USER
    # --------------------------------------------------------

    try:
        target_user_id = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid user ID",
        )


    user = (
        db.query(User)
        .filter(
            User.id == target_user_id,
            User.tenant_id ==
            uuid.UUID(
                current_user.tenant_id
            ),
        )
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )


    # --------------------------------------------------------
    # PROTECT admin@gmail.com
    # --------------------------------------------------------

    if user.email.lower() == "admin@gmail.com":

        if role != "admin":
            raise HTTPException(
                status_code=400,
                detail="The main administrator must remain an admin",
            )

        return {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "role": "admin",
            "tenant_id": str(user.tenant_id),
            "is_active": user.is_active,
        }


    # --------------------------------------------------------
    # UPDATE ROLE
    # --------------------------------------------------------

    user.role = role

    db.commit()
    db.refresh(user)


    return {
        "id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "tenant_id": str(user.tenant_id),
        "is_active": user.is_active,
    }


# ============================================================
# DELETE USER
# ============================================================

@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    current_user: CurrentUser = Depends(
        require_admin
    ),
    db: Session = Depends(get_db),
):
    """
    Delete a user.

    The main admin account cannot be deleted.
    """

    # --------------------------------------------------------
    # ONLY MAIN ADMIN CAN DELETE USERS
    # --------------------------------------------------------

    if current_user.email.lower() != "admin@gmail.com":
        raise HTTPException(
            status_code=403,
            detail="Only the main administrator can delete users",
        )


    # --------------------------------------------------------
    # FIND USER
    # --------------------------------------------------------

    try:
        target_user_id = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid user ID",
        )


    user = (
        db.query(User)
        .filter(
            User.id == target_user_id,
            User.tenant_id ==
            uuid.UUID(
                current_user.tenant_id
            ),
        )
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )


    # --------------------------------------------------------
    # NEVER DELETE MAIN ADMIN
    # --------------------------------------------------------

    if user.email.lower() == "admin@gmail.com":
        raise HTTPException(
            status_code=400,
            detail="The main administrator cannot be deleted",
        )


    # --------------------------------------------------------
    # DELETE
    # --------------------------------------------------------

    db.delete(user)
    db.commit()


    return {
        "message":
            "User deleted successfully"
    }