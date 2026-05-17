"""Company CRUD."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from bus_backend.app.schemas import CompanyCreate, CompanyUpdate
from bus_backend.app.models import Company


def list_for_owner(db: Session, owner_id: uuid.UUID) -> list[Company]:
    q = select(Company).where(Company.owner_id == owner_id).order_by(Company.name)
    return list(db.scalars(q).all())


def list_all(db: Session, skip: int = 0, limit: int = 100) -> list[Company]:
    q = select(Company).order_by(Company.created_at.desc()).offset(skip).limit(limit)
    return list(db.scalars(q).all())


def get(db: Session, company_id: uuid.UUID) -> Company | None:
    return db.get(Company, company_id)


def create(db: Session, owner_id: uuid.UUID, data: CompanyCreate) -> Company:
    row = Company(
        owner_id=owner_id,
        name=data.name,
        address=data.address,
        phone=data.phone,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update(db: Session, company: Company, data: CompanyUpdate) -> Company:
    if data.name is not None:
        company.name = data.name
    if data.address is not None:
        company.address = data.address
    if data.phone is not None:
        company.phone = data.phone
    db.commit()
    db.refresh(company)
    return company


def delete(db: Session, company: Company) -> None:
    db.delete(company)
    db.commit()
