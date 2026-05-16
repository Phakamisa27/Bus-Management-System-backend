"""Company CRUD (owner = logged-in user)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.crud import companies as companies_crud
from app.schemas import CompanyCreate, CompanyRead, CompanyUpdate
from app.database import get_db
from app.models import User
from core.auth import get_current_user

router = APIRouter(prefix="/companies", tags=["companies"])


def _ensure_owner(company, user: User) -> None:
    if company.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")


@router.get("", response_model=list[CompanyRead])
def list_my_companies(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[CompanyRead]:
    return companies_crud.list_for_owner(db, current_user.id)


@router.post("", response_model=CompanyRead, status_code=status.HTTP_201_CREATED)
def create_company(
    data: CompanyCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    return companies_crud.create(db, current_user.id, data)


@router.get("/{company_id}", response_model=CompanyRead)
def get_company(
    company_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    row = companies_crud.get(db, company_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    _ensure_owner(row, current_user)
    return row


@router.patch("/{company_id}", response_model=CompanyRead)
def update_company(
    company_id: uuid.UUID,
    data: CompanyUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    row = companies_crud.get(db, company_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    _ensure_owner(row, current_user)
    return companies_crud.update(db, row, data)


@router.delete("/{company_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_company(
    company_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    row = companies_crud.get(db, company_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    _ensure_owner(row, current_user)
    companies_crud.delete(db, row)
