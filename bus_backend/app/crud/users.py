"""User CRUD."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from bus_backend.app.schemas import UserCreate
from bus_backend.core.auth import hash_password
from bus_backend.app.models import User


def get_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email))


def get_by_id(db: Session, user_id: uuid.UUID) -> User | None:
    return db.get(User, user_id)


def create_user(db: Session, data: UserCreate) -> User:
    user = User(
        email=str(data.email),
        full_name=data.full_name,
        hashed_password=hash_password(data.password),
        role=data.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def set_password(db: Session, user: User, new_password: str) -> User:
    """Hash and store a new password (same hashing used at registration)."""
    user.hashed_password = hash_password(new_password)
    db.add(user)
    return user


def authenticate(db: Session, email: str, password: str) -> User | None:
    user = get_by_email(db, email)
    if user is None:
        return None
    from bus_backend.core.auth import verify_password

    if not verify_password(password, user.hashed_password):
        return None
    return user
