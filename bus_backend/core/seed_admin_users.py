"""Ensure designated admin accounts have the admin role on startup."""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from bus_backend.app.crud import users as users_crud
from bus_backend.app.models import UserRole
from bus_backend.core.database import SessionLocal

logger = logging.getLogger(__name__)

ADMIN_EMAILS: tuple[str, ...] = ("sibisiphakamani5@gmail.com",)


def _promote_to_admin(db: Session, email: str) -> None:
    user = users_crud.get_by_email(db, email)
    if user is None:
        logger.info("seed_admin_users: %s is not registered yet", email)
        return
    if user.role == UserRole.admin:
        return
    user.role = UserRole.admin
    db.commit()
    logger.info("seed_admin_users: promoted %s to admin", email)


def seed_admin_users_if_registered() -> None:
    """Promote configured emails to admin when those accounts already exist."""
    db = SessionLocal()
    try:
        for email in ADMIN_EMAILS:
            _promote_to_admin(db, email)
    except Exception:
        db.rollback()
        logger.exception("seed_admin_users: failed (API will still run)")
    finally:
        db.close()
