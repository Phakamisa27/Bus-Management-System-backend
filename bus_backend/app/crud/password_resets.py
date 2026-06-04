"""Password-reset CRUD."""

import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from bus_backend.app.models import PasswordReset, User

# How long a reset token stays valid after being issued.
RESET_TOKEN_TTL_MINUTES = 30


def create_for_user(db: Session, user: User) -> PasswordReset:
    """Generate a secure single-use token for the user and persist it."""
    reset = PasswordReset(
        user_id=user.id,
        token=secrets.token_urlsafe(48),
        expires_at=datetime.now(UTC) + timedelta(minutes=RESET_TOKEN_TTL_MINUTES),
    )
    db.add(reset)
    db.commit()
    db.refresh(reset)
    return reset
