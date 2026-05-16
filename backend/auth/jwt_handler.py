"""JWT create / verify helpers."""

from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import UUID

from jose import JWTError, jwt
from pydantic import BaseModel

from configs.settings import settings


class TokenPayload(BaseModel):
    sub: str
    email: str
    role: str
    exp: int


def create_access_token(
    user_id: UUID,
    email: str,
    role: str,
    expires_minutes: Optional[int] = None,
) -> str:
    """Create a signed JWT access token."""
    expire_delta = timedelta(minutes=expires_minutes or settings.JWT_EXPIRE_MINUTES)
    expire = datetime.now(timezone.utc) + expire_delta
    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "exp": expire,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> TokenPayload:
    """Decode and validate JWT; raises JWTError on failure."""
    data: dict[str, Any] = jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
    )
    return TokenPayload(
        sub=data["sub"],
        email=data["email"],
        role=data["role"],
        exp=data["exp"],
    )


def verify_access_token(token: str) -> Optional[TokenPayload]:
    """Return payload if valid, else None."""
    try:
        return decode_access_token(token)
    except JWTError:
        return None
