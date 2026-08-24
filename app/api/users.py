"""
User profile and settings API endpoints.

Rules:
- admin@gmail.com is the permanent main administrator.
- Only admin@gmail.com can manage other users.
- Users created through the admin panel are ALWAYS normal users.
- admin@gmail.com cannot be deleted or demoted.
- Normal users cannot access admin endpoints.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.auth.dependencies import (
    CurrentUser,
    get_current_user,
    require_admin,
)
from app.auth.security import hash_password, verify_password
from app.db.database import get_db
from app.db.models import User


router = APIRouter()


# ============================================================
# MAIN ADMIN
# ============================================================

MAIN_ADMIN_EMAIL = "admin@gmail.com"


def require_main_admin(
    current_user: CurrentUser = Depends(require_admin),
) -> CurrentUser:
    """
    Only the fixed main administrator can perform
    user-management operations.
    """

    if current_user.email.lower() != MAIN_ADMIN_EMAIL:
        raise HTTPException(
            status_code=403,
            detail="Only the main administrator can perform this action",
        )

    return current_user


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
    """
    There is intentionally NO role field.

    Every user created through this endpoint
    is automatically assigned role='user'.
    """

    email: EmailStr
    full_name: str
    password: str


# ============================================================
# GET CURRENT USER
# ============================================================


@router.get("/users/me")
async def get_current_user_profile(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get the currently logged-in user's profile."""

    try:
        user_id = uuid.UUID(current_user.user_id)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid user ID",
        )

    user = (
        db.query(User)
        .filter(User.id == user_id)
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
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Allow a logged-in user to update their own profile."""

    try:
        user_id = uuid.UUID(current_user.user_id)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid user ID",
        )

    user = (
        db.query(User)
        .filter(User.id == user_id)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

    # --------------------------------------------------------
    # EMAIL
    # --------------------------------------------------------

    new_email = str(profile_update.email).strip().lower()

    if new_email != user.email.lower():

        existing_user = (
            db.query(User)
            .filter(User.email == new_email)
            .first()
        )

        if existing_user:
            raise HTTPException(
                status_code=400,
                detail="Email already registered",
            )

        user.email = new_email

    # --------------------------------------------------------
    # FULL NAME
    # --------------------------------------------------------

    if profile_update.full_name is not None:
        user.full_name = profile_update.full_name.strip()

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
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Allow a logged-in user to change their own password."""

    try:
        user_id = uuid.UUID(current_user.user_id)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid user ID",
        )

    user = (
        db.query(User)
        .filter(User.id == user_id)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

    # Verify current password

    if not verify_password(
        password_change.current_password,
        user.hashed_password,
    ):
        raise HTTPException(
            status_code=400,
            detail="Current password is incorrect",
        )

    # Validate new password

    if len(password_change.new_password) < 8:
        raise HTTPException(
            status_code=400,
            detail="New password must be at least 8 characters",
        )

    # Update password

    user.hashed_password = hash_password(
        password_change.new_password
    )

    db.commit()

    return {
        "message": "Password changed successfully"
    }


# ============================================================
# CREATE USER
# ============================================================


@router.post("/users/create")
async def create_user(
    user_request: CreateUserRequest,
    current_user: CurrentUser = Depends(
        require_main_admin
    ),
    db: Session = Depends(get_db),
):
    """
    Create a normal user.

    IMPORTANT:
    - Only admin@gmail.com can call this endpoint.
    - Role is NOT accepted from the request.
    - Every new account is ALWAYS role='user'.
    """

    # --------------------------------------------------------
    # VALIDATE PASSWORD
    # --------------------------------------------------------

    if len(user_request.password) < 8:
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 8 characters",
        )

    # --------------------------------------------------------
    # NORMALIZE EMAIL
    # --------------------------------------------------------

    email = str(user_request.email).strip().lower()

    # --------------------------------------------------------
    # PREVENT USING MAIN ADMIN EMAIL
    # --------------------------------------------------------

    if email == MAIN_ADMIN_EMAIL:
        raise HTTPException(
            status_code=400,
            detail="The main administrator email cannot be used for another account",
        )

    # --------------------------------------------------------
    # CHECK EXISTING USER
    # --------------------------------------------------------

    existing_user = (
        db.query(User)
        .filter(User.email == email)
        .first()
    )

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered",
        )

    # --------------------------------------------------------
    # CREATE USER
    # --------------------------------------------------------

    new_user = User(
        tenant_id=uuid.UUID(
            current_user.tenant_id
        ),
        email=email,
        hashed_password=hash_password(
            user_request.password
        ),
        full_name=user_request.full_name.strip(),
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
        require_main_admin
    ),
    db: Session = Depends(get_db),
):
    """
    Change another user's role.

    Only admin@gmail.com can do this.

    The main administrator:
    - cannot be demoted
    - cannot become a normal user
    """

    # --------------------------------------------------------
    # VALID ROLE
    # --------------------------------------------------------

    role = role.lower().strip()

    if role not in {"admin", "user"}:
        raise HTTPException(
            status_code=400,
            detail="Role must be either 'admin' or 'user'",
        )

    # --------------------------------------------------------
    # PARSE USER ID
    # --------------------------------------------------------

    try:
        target_user_id = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid user ID",
        )

    # --------------------------------------------------------
    # FIND USER IN SAME TENANT
    # --------------------------------------------------------

    user = (
        db.query(User)
        .filter(
            User.id == target_user_id,
            User.tenant_id
            == uuid.UUID(
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
    # PROTECT MAIN ADMIN
    # --------------------------------------------------------

    if user.email.lower() == MAIN_ADMIN_EMAIL:

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
    #
    # NOTE:
    # The UI does not expose this functionality, but this
    # endpoint remains available ONLY to the main admin.
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
        require_main_admin
    ),
    db: Session = Depends(get_db),
):
    """
    Delete a normal user.

    Only admin@gmail.com can delete users.

    admin@gmail.com itself can NEVER be deleted.
    """

    # --------------------------------------------------------
    # PARSE USER ID
    # --------------------------------------------------------

    try:
        target_user_id = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid user ID",
        )

    # --------------------------------------------------------
    # FIND USER IN SAME TENANT
    # --------------------------------------------------------

    user = (
        db.query(User)
        .filter(
            User.id == target_user_id,
            User.tenant_id
            == uuid.UUID(
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

    if user.email.lower() == MAIN_ADMIN_EMAIL:
        raise HTTPException(
            status_code=400,
            detail="The main administrator cannot be deleted",
        )

    # --------------------------------------------------------
    # DELETE NORMAL USER
    # --------------------------------------------------------

    db.delete(user)
    db.commit()

    return {
        "message": "User deleted successfully"
    }