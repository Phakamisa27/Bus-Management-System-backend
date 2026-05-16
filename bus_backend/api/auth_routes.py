"""Register, login, and current user."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.crud import users as users_crud
from app.schemas import LoginRequest, Token, UserCreate, UserRead
from app.database import get_db
from app.models import User
from core.auth import create_access_token, get_current_user

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


@router.get("/me", response_model=UserRead)
def read_me(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    """Protected route — send header: Authorization: Bearer <token>."""
    return current_user
