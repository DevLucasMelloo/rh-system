from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.core.dependencies import get_current_user, require_admin
from app.schemas.company import CompanyCreate, CompanyRead, CompanyUpdate
from app.services import company as company_service
from app.models.user import User

router = APIRouter(prefix="/company", tags=["Empresa"])


@router.post("", response_model=CompanyRead, status_code=201)
def register_company(data: CompanyCreate, db: Session = Depends(get_db)):
    """Registra a empresa. Executado uma única vez na configuração inicial."""
    return company_service.register_company(db, data)


@router.get("", response_model=CompanyRead)
def get_company(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return company_service.get_company_or_404(db, current_user.company_id)


@router.patch("", response_model=CompanyRead)
def update_company(
    data: CompanyUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return company_service.update_company(db, current_user.company_id, data)
