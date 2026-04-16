from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.repositories import company as company_repo
from app.schemas.company import CompanyCreate, CompanyUpdate
from app.models.company import Company


def get_company_or_404(db: Session, company_id: int) -> Company:
    company = company_repo.get_company(db, company_id)
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empresa não encontrada")
    return company


def register_company(db: Session, data: CompanyCreate) -> Company:
    if company_repo.get_by_cnpj(db, data.cnpj):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="CNPJ já cadastrado",
        )
    return company_repo.create_company(db, data)


def update_company(db: Session, company_id: int, data: CompanyUpdate) -> Company:
    company = get_company_or_404(db, company_id)
    return company_repo.update_company(db, company, data)
