"""Password-reset CRUD."""

import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
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


def get_by_token(db: Session, token: str) -> PasswordReset | None:
    """Look up a reset record by its token (None if no match)."""
    return db.scalar(select(PasswordReset).where(PasswordReset.token == token))


def is_valid(reset: PasswordReset) -> bool:
    """A token is usable only if it has not been used and has not expired."""
    if reset.used:
        return False
    expires_at = reset.expires_at
    # Stored values are timezone-aware, but guard against naive values just in case.
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    return expires_at > datetime.now(UTC)


def mark_used(db: Session, reset: PasswordReset) -> None:
    """Flag the token as consumed so it can never be reused (no commit here)."""
    reset.used = True
    db.add(reset)
