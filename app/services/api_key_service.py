"""
Tenant API key management (database-driven programmatic auth).
"""

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.auth.security import generate_api_key, hash_api_key
from app.db.models import ApiKey, User


def create_api_key(
    db: Session,
    *,
    tenant_id: str,
    user_id: str,
    name: str,
) -> tuple[ApiKey, str]:
    """Create and persist an API key. Returns (record, raw_key)."""
    raw_key, key_hash, key_prefix = generate_api_key()
    record = ApiKey(
        tenant_id=uuid.UUID(tenant_id),
        created_by=uuid.UUID(user_id),
        name=name,
        key_hash=key_hash,
        key_prefix=key_prefix,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record, raw_key


def list_api_keys(db: Session, tenant_id: str) -> list[ApiKey]:
    return (
        db.query(ApiKey)
        .filter(ApiKey.tenant_id == uuid.UUID(tenant_id), ApiKey.is_active.is_(True))
        .order_by(ApiKey.created_at.desc())
        .all()
    )


def revoke_api_key(db: Session, tenant_id: str, key_id: str) -> None:
    record = (
        db.query(ApiKey)
        .filter(
            ApiKey.id == uuid.UUID(key_id),
            ApiKey.tenant_id == uuid.UUID(tenant_id),
        )
        .first()
    )
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")
    record.is_active = False
    db.commit()


def authenticate_api_key(db: Session, raw_key: str) -> tuple[ApiKey, User | None]:
    """Validate raw API key and return key record + optional creating user."""
    if not raw_key or not raw_key.startswith("rag_"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    key_hash = hash_api_key(raw_key)
    record = (
        db.query(ApiKey)
        .filter(ApiKey.key_hash == key_hash, ApiKey.is_active.is_(True))
        .first()
    )
    if not record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked API key",
        )

    record.last_used_at = datetime.now(timezone.utc)
    db.commit()

    user = None
    if record.created_by:
        user = db.query(User).filter(User.id == record.created_by, User.is_active.is_(True)).first()

    return record, user
