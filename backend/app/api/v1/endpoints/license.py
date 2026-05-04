from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.core.dependencies import get_current_user
from app.core.config import settings
from app.models.user import User
from app.models.license import License

router = APIRouter(prefix="/license", tags=["Licença"])

GRACE_DAYS = 3  # dias de carência após vencimento


class RenewRequest(BaseModel):
    master_password: str
    months: int = 1


class LicenseRead(BaseModel):
    valid_until: date
    is_active: bool
    days_remaining: int
    expired: bool

    model_config = {"from_attributes": True}


def get_or_create_license(db: Session, company_id: int) -> License:
    license = db.query(License).filter(License.company_id == company_id).first()
    if not license:
        license = License(
            company_id=company_id,
            valid_until=date.today() + timedelta(days=30),
            is_active=True,
        )
        db.add(license)
        db.commit()
        db.refresh(license)
    return license


def check_license_active(db: Session, company_id: int) -> bool:
    license = db.query(License).filter(License.company_id == company_id).first()
    if not license:
        return True  # sem licença cadastrada = período de graça inicial
    if not license.is_active:
        return False
    return date.today() <= license.valid_until + timedelta(days=GRACE_DAYS)


@router.get("", response_model=LicenseRead)
def get_license(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    license = get_or_create_license(db, current_user.company_id)
    days_remaining = (license.valid_until - date.today()).days
    return LicenseRead(
        valid_until=license.valid_until,
        is_active=license.is_active,
        days_remaining=days_remaining,
        expired=days_remaining < -GRACE_DAYS or not license.is_active,
    )


@router.post("/renew", status_code=200)
def renew_license(
    data: RenewRequest,
    db: Session = Depends(get_db),
):
    if data.master_password != settings.MASTER_PASSWORD:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Senha master incorreta")
    if data.months < 1 or data.months > 12:
        raise HTTPException(status_code=400, detail="Meses deve ser entre 1 e 12")

    license = db.query(License).first()
    if not license:
        raise HTTPException(status_code=404, detail="Nenhuma empresa cadastrada")

    base = max(license.valid_until, date.today())
    license.valid_until = base + timedelta(days=30 * data.months)
    license.is_active = True
    db.commit()

    return {
        "message": f"Licença renovada por {data.months} mês(es)",
        "valid_until": license.valid_until.isoformat(),
    }


@router.post("/deactivate", status_code=200)
def deactivate_license(
    data: RenewRequest,
    db: Session = Depends(get_db),
):
    if data.master_password != settings.MASTER_PASSWORD:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Senha master incorreta")

    license = db.query(License).first()
    if not license:
        raise HTTPException(status_code=404, detail="Nenhuma empresa cadastrada")

    license.is_active = False
    db.commit()
    return {"message": "Licença desativada"}
