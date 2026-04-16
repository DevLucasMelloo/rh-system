"""
Endpoints de Férias, 13º Salário e Rescisão.
"""
from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.core.dependencies import get_current_user, require_rh_or_admin
from app.models.user import User
from app.schemas.vacation import (
    VacationCreate, VacationStart, VacationRead,
    ThirteenthRead,
    TerminationCreate, TerminationRead,
)
from app.services import vacation as vac_service

router = APIRouter(prefix="/vacation", tags=["Férias / 13º / Rescisão"])


# ── Férias ────────────────────────────────────────────────────────────────────

@router.post("", response_model=VacationRead, status_code=201)
def schedule_vacation(
    data: VacationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rh_or_admin),
):
    """Agenda um período de férias para um funcionário."""
    vac = vac_service.schedule_vacation(db, data, current_user.company_id, current_user.id)
    return _enrich_vacation(vac, db)


@router.get("/employee/{employee_id}", response_model=list[VacationRead])
def list_by_employee(
    employee_id: int = Path(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lista o histórico de férias de um funcionário."""
    vacs = vac_service.list_by_employee(db, employee_id, current_user.company_id)
    return [_enrich_vacation(v, db) for v in vacs]


@router.get("/active", response_model=list[VacationRead])
def list_active(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lista férias agendadas ou em gozo de toda a empresa."""
    vacs = vac_service.list_active(db, current_user.company_id)
    return [_enrich_vacation(v, db) for v in vacs]


@router.get("/{vacation_id}", response_model=VacationRead)
def get_vacation(
    vacation_id: int = Path(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    vac = vac_service.get_vacation(db, vacation_id, current_user.company_id)
    return _enrich_vacation(vac, db)


@router.post("/{vacation_id}/start", response_model=VacationRead)
def start_vacation(
    body: VacationStart,
    vacation_id: int = Path(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rh_or_admin),
):
    """Inicia o gozo das férias (muda status para em_gozo)."""
    vac = vac_service.start_vacation(db, vacation_id, body, current_user.company_id, current_user.id)
    return _enrich_vacation(vac, db)


@router.post("/{vacation_id}/complete", response_model=VacationRead)
def complete_vacation(
    vacation_id: int = Path(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rh_or_admin),
):
    """Conclui as férias (muda status para concluida)."""
    vac = vac_service.complete_vacation(db, vacation_id, current_user.company_id, current_user.id)
    return _enrich_vacation(vac, db)


@router.post("/{vacation_id}/cancel", response_model=VacationRead)
def cancel_vacation(
    vacation_id: int = Path(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rh_or_admin),
):
    """Cancela férias agendadas ou em gozo."""
    vac = vac_service.cancel_vacation(db, vacation_id, current_user.company_id, current_user.id)
    return _enrich_vacation(vac, db)


# ── 13º Salário ───────────────────────────────────────────────────────────────

@router.get("/thirteenth/{employee_id}", response_model=ThirteenthRead)
def get_thirteenth(
    employee_id: int = Path(...),
    year: int   = Query(..., ge=2000),
    parcela: int = Query(2, ge=1, le=2),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Calcula 13º salário de um funcionário.
    parcela=1 → adiantamento (novembro)
    parcela=2 → saldo líquido (dezembro)
    """
    return vac_service.get_thirteenth(
        db, employee_id, year, parcela, current_user.company_id
    )


# ── Rescisão ──────────────────────────────────────────────────────────────────

@router.post("/termination", response_model=TerminationRead, status_code=201)
def create_termination(
    data: TerminationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rh_or_admin),
):
    """
    Registra a rescisão de um funcionário.
    Calcula todas as verbas rescisórias e marca o funcionário como inativo.
    """
    term = vac_service.create_termination(db, data, current_user.company_id, current_user.id)
    return _enrich_termination(term, db)


@router.get("/termination/{termination_id}", response_model=TerminationRead)
def get_termination(
    termination_id: int = Path(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    term = vac_service.get_termination(db, termination_id, current_user.company_id)
    return _enrich_termination(term, db)


# ── Helpers de resposta ───────────────────────────────────────────────────────

def _enrich_vacation(vac: object, db: Session) -> dict:
    from app.repositories import employee as emp_repo
    d = {c.name: getattr(vac, c.name) for c in vac.__table__.columns}
    emp = emp_repo.get_employee(db, vac.employee_id)
    d["employee_name"] = emp.name if emp else None
    return d


def _enrich_termination(term: object, db: Session) -> dict:
    from app.repositories import employee as emp_repo
    d = {c.name: getattr(term, c.name) for c in term.__table__.columns}
    emp = emp_repo.get_employee(db, term.employee_id)
    d["employee_name"] = emp.name if emp else None
    return d
