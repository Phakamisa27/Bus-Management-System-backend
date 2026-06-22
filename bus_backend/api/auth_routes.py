"""Register, login, and current user."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from bus_backend.app.crud import companies as companies_crud
from bus_backend.app.crud import password_resets as password_resets_crud
from bus_backend.app.crud import users as users_crud
from bus_backend.app.schemas import (
    CompanyRegisterRequest,
    CompanyRegisterResponse,
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
    ResetPasswordRequest,
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


@router.post("/company-register", response_model=CompanyRegisterResponse, status_code=status.HTTP_201_CREATED)
def company_register(
    data: CompanyRegisterRequest,
    db: Annotated[Session, Depends(get_db)],
) -> CompanyRegisterResponse:
    if users_crud.get_by_email(db, str(data.work_email)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user, company = companies_crud.register_with_admin(db, data)
    return CompanyRegisterResponse(
        message="Company account created. Please login.",
        company_id=company.id,
        user_id=user.id,
    )


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
    logger.info("Forgot password requested for email: %s", data.email)
    user = users_crud.get_by_email(db, str(data.email))
    logger.info("User found: %s", user is not None)
    if user is not None:
        reset = password_resets_crud.create_for_user(db, user)
        logger.info("Password reset token created for user_id: %s", user.id)
        # Send the reset email. If sending fails (bad Resend config, network,
        # etc.) we log it but still return the same safe message below, so the
        # response never reveals whether the email exists or that sending broke.
        try:
            logger.info("Calling Resend for password reset email")
            send_password_reset_email(user.email, reset.token)
            logger.info("Resend email send completed")
        except Exception:
            logger.exception("Failed to send password reset email")
    return MessageResponse(message=FORGOT_PASSWORD_MESSAGE)


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(
    data: ResetPasswordRequest,
    db: Annotated[Session, Depends(get_db)],
) -> MessageResponse:
    """
    Complete a password reset using the token emailed to the user.

    The token must exist, be unexpired, and be unused. On success the user's
    password is re-hashed (same scheme as registration), the token is marked
    `used` so it cannot be reused, and both changes are committed together.
    """
    reset = password_resets_crud.get_by_token(db, data.token)
    if reset is None or not password_resets_crud.is_valid(reset):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token.",
        )

    user = users_crud.get_by_id(db, reset.user_id)
    if user is None:
        # User was deleted after the token was issued; treat as invalid.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token.",
        )

    users_crud.set_password(db, user, data.new_password)
    password_resets_crud.mark_used(db, reset)
    db.commit()

    return MessageResponse(message="Password reset successful.")


@router.get("/me", response_model=UserRead)
def read_me(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    """Protected route — send header: Authorization: Bearer <token>."""
    return current_user
