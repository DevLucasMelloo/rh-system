from sqlalchemy.orm import Session
from app.models.company import Company
from app.schemas.company import CompanyCreate, CompanyUpdate


def get_company(db: Session, company_id: int) -> Company | None:
    return db.get(Company, company_id)


def get_first_company(db: Session) -> Company | None:
    return db.query(Company).first()


def get_by_cnpj(db: Session, cnpj: str) -> Company | None:
    return db.query(Company).filter(Company.cnpj == cnpj).first()


def create_company(db: Session, data: CompanyCreate) -> Company:
    company = Company(**data.model_dump())
    db.add(company)
    db.commit()
    db.refresh(company)
    return company


def update_company(db: Session, company: Company, data: CompanyUpdate) -> Company:
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(company, field, value)
    db.commit()
    db.refresh(company)
    return company
