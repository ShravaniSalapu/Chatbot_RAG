"""
FastAPI authentication dependencies.
Supports JWT Bearer tokens and database-backed X-API-Key headers.
"""

import uuid
from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.auth.security import decode_access_token
from app.config import get_settings
from app.db.database import get_db
from app.db.models import User
from app.services.api_key_service import authenticate_api_key

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


@dataclass
class CurrentUser:
    user_id: str
    tenant_id: str
    email: str
    role: str
    full_name: str | None = None
    auth_method: str = "jwt"  # jwt | api_key


async def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    api_key: str | None = Depends(api_key_header),
    db: Session = Depends(get_db),
) -> CurrentUser:
    settings = get_settings()
    if not settings.require_auth:
        return _get_or_create_dev_user(db)

    if api_key:
        return _authenticate_api_key_user(api_key, db)

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Provide Bearer token or X-API-Key header.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == uuid.UUID(user_id), User.is_active.is_(True)).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return CurrentUser(
        user_id=str(user.id),
        tenant_id=str(user.tenant_id),
        email=user.email,
        role=user.role,
        full_name=user.full_name,
        auth_method="jwt",
    )


def _authenticate_api_key_user(raw_key: str, db: Session) -> CurrentUser:
    record, user = authenticate_api_key(db, raw_key)
    if user:
        return CurrentUser(
            user_id=str(user.id),
            tenant_id=str(user.tenant_id),
            email=user.email,
            role=user.role,
            full_name=user.full_name,
            auth_method="api_key",
        )
    return CurrentUser(
        user_id=str(record.id),
        tenant_id=str(record.tenant_id),
        email=f"api-key@{record.key_prefix}",
        role="member",
        full_name=record.name,
        auth_method="api_key",
    )


async def require_admin(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user


def _get_or_create_dev_user(db: Session) -> CurrentUser:
    """Fallback user when REQUIRE_AUTH=false for local development."""
    from app.db.models import Tenant

    user = db.query(User).first()
    if user:
        return CurrentUser(
            user_id=str(user.id),
            tenant_id=str(user.tenant_id),
            email=user.email,
            role=user.role,
            full_name=user.full_name,
        )

    tenant = Tenant(name="Development", slug="dev", plan="free")
    db.add(tenant)
    db.flush()

    from app.auth.security import hash_password

    user = User(
        tenant_id=tenant.id,
        email="dev@localhost",
        hashed_password=hash_password("dev"),
        full_name="Dev User",
        role="admin",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return CurrentUser(
        user_id=str(user.id),
        tenant_id=str(user.tenant_id),
        email=user.email,
        role=user.role,
        full_name=user.full_name,
    )
