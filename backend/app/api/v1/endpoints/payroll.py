"""
Endpoints de Folha de Pagamento (Holerite) e Vale.
"""
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.core.dependencies import get_current_user, require_rh_or_admin
from app.models.user import User
from app.schemas.payroll import (
    PayrollCreate, PayrollRead, PayrollItemCreate, PayrollItemUpdate,
    PayrollItemRead, ValeCreate, ValeRead,
)
from app.services import payroll as payroll_service
from app.utils.pdf_generator import generate_payslip_pdf

router = APIRouter(prefix="/payroll", tags=["Folha de Pagamento"])


# ── Holerite ──────────────────────────────────────────────────────────────────

@router.post("", response_model=PayrollRead, status_code=201)
def create_payroll(
    data: PayrollCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rh_or_admin),
):
    """Cria um novo holerite e calcula itens automaticamente a partir do ponto."""
    payroll = payroll_service.create_payroll(
        db, data, current_user.company_id, current_user.id
    )
    return _enrich(payroll)


@router.get("/period", response_model=list[PayrollRead])
def list_by_period(
    month: int = Query(..., ge=1, le=12),
    year: int = Query(..., ge=2000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lista todos os holerites da empresa para um mês/ano."""
    payrolls = payroll_service.list_by_period(db, month, year, current_user.company_id)
    return [_enrich(p) for p in payrolls]


@router.get("/employee/{employee_id}", response_model=list[PayrollRead])
def list_by_employee(
    employee_id: int = Path(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Histórico de holerites de um funcionário."""
    payrolls = payroll_service.list_by_employee(db, employee_id, current_user.company_id)
    return [_enrich(p) for p in payrolls]


@router.get("/{payroll_id}", response_model=PayrollRead)
def get_payroll(
    payroll_id: int = Path(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    payroll = payroll_service.get_payroll(db, payroll_id, current_user.company_id)
    return _enrich(payroll)


@router.post("/{payroll_id}/recalculate", response_model=PayrollRead)
def recalculate(
    payroll_id: int = Path(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rh_or_admin),
):
    """Recalcula todos os itens automáticos mantendo os manuais."""
    payroll = payroll_service.recalculate_payroll(
        db, payroll_id, current_user.company_id, current_user.id
    )
    return _enrich(payroll)


@router.post("/{payroll_id}/close", response_model=PayrollRead)
def close_payroll(
    payroll_id: int = Path(...),
    payment_date: date | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rh_or_admin),
):
    """
    Fecha o holerite (status → fechado).
    Marca parcelas de vale como pagas e bloqueia edições futuras.
    """
    payroll = payroll_service.close_payroll(
        db, payroll_id, payment_date, current_user.company_id, current_user.id
    )
    return _enrich(payroll)


@router.get("/{payroll_id}/pdf")
def download_pdf(
    payroll_id: int = Path(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Gera ou resereve o PDF do holerite."""
    from app.repositories import employee as emp_repo
    payroll = payroll_service.get_payroll(db, payroll_id, current_user.company_id)
    employee = emp_repo.get_employee(db, payroll.employee_id)

    pdf_path = generate_payslip_pdf(payroll, employee, output_dir="pdfs")

    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=f"holerite_{payroll.competence_month:02d}_{payroll.competence_year}.pdf",
    )


# ── Itens do holerite ─────────────────────────────────────────────────────────

@router.post("/{payroll_id}/items", response_model=PayrollItemRead, status_code=201)
def add_item(
    payroll_id: int = Path(...),
    data: PayrollItemCreate = ...,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rh_or_admin),
):
    """Adiciona um item manual ao holerite."""
    item = payroll_service.add_manual_item(
        db, payroll_id, data, current_user.company_id, current_user.id
    )
    return item


@router.patch("/{payroll_id}/items/{item_id}", response_model=PayrollItemRead)
def update_item(
    payroll_id: int = Path(...),
    item_id: int = Path(...),
    data: PayrollItemUpdate = ...,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rh_or_admin),
):
    """Edita valores ou descrição de um item do holerite."""
    item = payroll_service.update_item(
        db, payroll_id, item_id, data, current_user.company_id, current_user.id
    )
    return item


@router.delete("/{payroll_id}/items/{item_id}", status_code=204)
def delete_item(
    payroll_id: int = Path(...),
    item_id: int = Path(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rh_or_admin),
):
    """Remove um item do holerite."""
    payroll_service.delete_item(
        db, payroll_id, item_id, current_user.company_id, current_user.id
    )


# ── Vale ──────────────────────────────────────────────────────────────────────

@router.get("/employees/{employee_id}/vales", response_model=list[ValeRead])
def list_vales(
    employee_id: int = Path(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lista todos os vales de um funcionário."""
    return payroll_service.list_vales_by_employee(db, employee_id, current_user.company_id)


@router.post("/employees/{employee_id}/vales", response_model=ValeRead, status_code=201)
def create_vale(
    employee_id: int = Path(...),
    data: ValeCreate = ...,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rh_or_admin),
):
    """Registra um vale para o funcionário (com parcelamento automático)."""
    vale = payroll_service.create_vale(
        db, employee_id, data, current_user.company_id, current_user.id
    )
    return vale


@router.get("/vales/{vale_id}", response_model=ValeRead)
def get_vale(
    vale_id: int = Path(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    vale = payroll_service.get_vale(db, vale_id, current_user.company_id)
    return vale


# ── Helper ────────────────────────────────────────────────────────────────────

def _enrich(payroll) -> dict:
    """Adiciona employee_name ao holerite para o schema."""
    d = {c.key: getattr(payroll, c.key) for c in payroll.__table__.columns}
    d["items"] = payroll.items
    d["employee_name"] = payroll.employee.name if payroll.employee else None
    d["status"] = payroll.status.value if hasattr(payroll.status, "value") else payroll.status
    return d
