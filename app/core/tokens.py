from datetime import UTC, datetime, timedelta

import jwt

from app.core.config import settings


def create_access_token(subject: str) -> str:
    now = datetime.now(UTC)
    exp = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    payload = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": exp,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
