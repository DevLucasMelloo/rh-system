from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.core.dependencies import get_current_user, require_rh_or_admin
from app.schemas.seamstress import (
    SeamstressCreate, SeamstressUpdate, SeamstressRead,
    SeamstressPaymentCreate, SeamstressPaymentUpdate, SeamstressPaymentRead,
)
from app.services import seamstress as seamstress_service
from app.models.user import User

router = APIRouter(prefix="/seamstresses", tags=["Costureiras"])


# ── Costureira ────────────────────────────────────────────────────────────────

@router.post("", response_model=SeamstressRead, status_code=201)
def create_seamstress(
    data: SeamstressCreate,
    current_user: User = Depends(require_rh_or_admin),
    db: Session = Depends(get_db),
):
    return seamstress_service.create_seamstress(db, data, current_user.company_id, current_user.id)


@router.get("", response_model=list[SeamstressRead])
def list_seamstresses(
    inactive: bool = Query(False, description="True para incluir inativas"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return seamstress_service.list_seamstresses(db, current_user.company_id, active_only=not inactive)


@router.get("/{seamstress_id}", response_model=SeamstressRead)
def get_seamstress(
    seamstress_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return seamstress_service.get_seamstress(db, seamstress_id, current_user.company_id)


@router.patch("/{seamstress_id}", response_model=SeamstressRead)
def update_seamstress(
    seamstress_id: int,
    data: SeamstressUpdate,
    current_user: User = Depends(require_rh_or_admin),
    db: Session = Depends(get_db),
):
    return seamstress_service.update_seamstress(db, seamstress_id, data, current_user.company_id, current_user.id)


# ── Pagamentos ────────────────────────────────────────────────────────────────

@router.post("/{seamstress_id}/payments", response_model=SeamstressPaymentRead, status_code=201)
def add_payment(
    seamstress_id: int,
    data: SeamstressPaymentCreate,
    current_user: User = Depends(require_rh_or_admin),
    db: Session = Depends(get_db),
):
    return seamstress_service.add_payment(db, seamstress_id, data, current_user.company_id, current_user.id)


@router.get("/{seamstress_id}/payments", response_model=list[SeamstressPaymentRead])
def list_payments(
    seamstress_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return seamstress_service.list_payments_by_seamstress(db, seamstress_id, current_user.company_id)


@router.patch("/payments/{payment_id}", response_model=SeamstressPaymentRead)
def update_payment(
    payment_id: int,
    data: SeamstressPaymentUpdate,
    current_user: User = Depends(require_rh_or_admin),
    db: Session = Depends(get_db),
):
    return seamstress_service.update_payment(db, payment_id, data, current_user.company_id, current_user.id)


@router.delete("/payments/{payment_id}", status_code=204)
def delete_payment(
    payment_id: int,
    current_user: User = Depends(require_rh_or_admin),
    db: Session = Depends(get_db),
):
    seamstress_service.delete_payment(db, payment_id, current_user.company_id, current_user.id)


# ── Relatório mensal ──────────────────────────────────────────────────────────

@router.get("/report/period", summary="Total a pagar por mês/ano")
def period_report(
    month: int = Query(..., ge=1, le=12),
    year: int = Query(..., ge=2000, le=2100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return seamstress_service.get_period_total(db, current_user.company_id, month, year)
