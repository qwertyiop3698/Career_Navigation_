import hmac

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.core.config import get_env
from app.db import get_db
from app.models import User


def require_admin_or_internal_api_key(
    authorization: str | None = Header(default=None),
    x_internal_api_key: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User | None:
    internal_api_key = (get_env("INTERNAL_API_KEY") or "").strip()
    provided_api_key = (x_internal_api_key or "").strip()
    if internal_api_key and provided_api_key:
        if hmac.compare_digest(provided_api_key, internal_api_key):
            return None

    current_user = get_current_user(authorization=authorization, db=db)
    if (current_user.role or "").lower() != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges are required.",
        )
    return current_user
