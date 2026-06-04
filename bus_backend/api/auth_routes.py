"""Register, login, and current user."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from bus_backend.app.crud import password_resets as password_resets_crud
from bus_backend.app.crud import users as users_crud
from bus_backend.app.schemas import (
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
    Token,
    UserCreate,
    UserRead,
)
from bus_backend.app.database import get_db
from bus_backend.app.models import User
from bus_backend.core.auth import create_access_token, get_current_user
from bus_backend.core.email import send_password_reset_email

logger = logging.getLogger(__name__)

# Returned for any forgot-password request so attackers can't tell which
# emails are registered (prevents account enumeration).
FORGOT_PASSWORD_MESSAGE = "If this email exists, reset instructions have been sent."

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(data: UserCreate, db: Annotated[Session, Depends(get_db)]) -> User:
    if users_crud.get_by_email(db, str(data.email)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    return users_crud.create_user(db, data)


@router.post("/login", response_model=Token)
def login(data: LoginRequest, db: Annotated[Session, Depends(get_db)]) -> Token:
    user = users_crud.authenticate(db, str(data.email), data.password)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Wrong email or password")
    return Token(access_token=create_access_token(user.id))


@router.post("/forgot-password", response_model=MessageResponse)
def forgot_password(
    data: ForgotPasswordRequest,
    db: Annotated[Session, Depends(get_db)],
) -> MessageResponse:
    """
    Start a password reset. Always returns the same message regardless of whether
    the email exists. If the user is found, a reset token (valid 30 minutes) is
    stored in `password_resets` and a reset email is sent to the user.
    """
    user = users_crud.get_by_email(db, str(data.email))
    if user is not None:
        reset = password_resets_crud.create_for_user(db, user)
        # Send the reset email. If sending fails (bad SMTP config, network,
        # etc.) we log it but still return the same safe message below, so the
        # response never reveals whether the email exists or that sending broke.
        try:
            send_password_reset_email(user.email, reset.token)
        except Exception:
            logger.exception("Failed to send password reset email")
    return MessageResponse(message=FORGOT_PASSWORD_MESSAGE)


@router.get("/me", response_model=UserRead)
def read_me(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    """Protected route — send header: Authorization: Bearer <token>."""
    return current_user
