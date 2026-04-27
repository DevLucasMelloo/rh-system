"""
Endpoints de Férias, 13º Salário e Rescisão.
"""
from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.core.dependencies import get_current_user, require_rh_or_admin
from app.models.user import User
from app.schemas.vacation import (
    VacationCreate, VacationUpdate, VacationStart, VacationRead,
    VacationPreviewRequest, VacationPreviewRead, VacationEligibilityRead,
    VacationItemCreate, VacationItemUpdate,
    VacationOverviewEmployee,
    ThirteenthRead,
    TerminationCreate, TerminationRead,
)
from app.services import vacation as vac_service

router = APIRouter(prefix="/vacation", tags=["Férias / 13º / Rescisão"])


# ── Literais primeiro (evitar conflito com /{vacation_id}) ───────────────────

@router.get("/company-overview", response_model=list[VacationOverviewEmployee])
def company_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return vac_service.get_company_overview(db, current_user.company_id)


@router.get("/active", response_model=list[VacationRead])
def list_active(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    vacs = vac_service.list_active(db, current_user.company_id)
    return [_enrich_vacation(v, db) for v in vacs]


@router.post("/preview", response_model=VacationPreviewRead)
def preview_vacation(
    body: VacationPreviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return vac_service.preview_vacation_calc(
        db, body.employee_id, body.enjoyment_days, body.sell_all_days, current_user.company_id,
        abono_days=body.abono_days,
    )


@router.get("/employee/{employee_id}/eligibility", response_model=VacationEligibilityRead)
def get_eligibility(
    employee_id: int = Path(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return vac_service.get_eligibility(db, employee_id, current_user.company_id)


@router.get("/employee/{employee_id}", response_model=list[VacationRead])
def list_by_employee(
    employee_id: int = Path(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    vacs = vac_service.list_by_employee(db, employee_id, current_user.company_id)
    return [_enrich_vacation(v, db) for v in vacs]


@router.get("/thirteenth/{employee_id}", response_model=ThirteenthRead)
def get_thirteenth(
    employee_id: int = Path(...),
    year: int    = Query(..., ge=2000),
    parcela: int = Query(2, ge=1, le=2),
    db: Session  = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return vac_service.get_thirteenth(db, employee_id, year, parcela, current_user.company_id)


@router.get("/thirteenth-batch", response_model=list[ThirteenthRead])
def get_thirteenth_batch(
    year:    int = Query(..., ge=2000),
    parcela: int = Query(2, ge=1, le=2),
    db: Session  = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.repositories import employee as emp_repo
    from app.models.employee import EmployeeStatus
    employees = emp_repo.list_all(db, current_user.company_id)
    result = []
    for emp in employees:
        if emp.status == EmployeeStatus.INACTIVE:
            continue
        if not emp.registration_date:
            continue
        try:
            result.append(vac_service.get_thirteenth(db, emp.id, year, parcela, current_user.company_id))
        except Exception:
            pass
    return result


# ── Rescisão (literais antes de /{id}) ───────────────────────────────────────

@router.get("/terminations", response_model=list[TerminationRead])
def list_terminations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    terms = vac_service.list_terminations(db, current_user.company_id)
    return [_enrich_termination(t, db) for t in terms]


@router.post("/termination", response_model=TerminationRead, status_code=201)
def create_termination(
    data: TerminationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rh_or_admin),
):
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


# ── CRUD Férias ───────────────────────────────────────────────────────────────

@router.post("", response_model=VacationRead, status_code=201)
def schedule_vacation(
    data: VacationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rh_or_admin),
):
    vac = vac_service.schedule_vacation(db, data, current_user.company_id, current_user.id)
    return _enrich_vacation(vac, db)


@router.get("/{vacation_id}", response_model=VacationRead)
def get_vacation(
    vacation_id: int = Path(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    vac = vac_service.get_vacation(db, vacation_id, current_user.company_id)
    return _enrich_vacation(vac, db)


@router.patch("/{vacation_id}", response_model=VacationRead)
def update_vacation(
    data: VacationUpdate,
    vacation_id: int = Path(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rh_or_admin),
):
    vac = vac_service.update_vacation_service(db, vacation_id, data, current_user.company_id, current_user.id)
    return _enrich_vacation(vac, db)


@router.delete("/{vacation_id}", status_code=204)
def delete_vacation(
    vacation_id: int = Path(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rh_or_admin),
):
    vac_service.delete_vacation_service(db, vacation_id, current_user.company_id, current_user.id)


# ── Ciclo de vida ─────────────────────────────────────────────────────────────

@router.post("/{vacation_id}/start", response_model=VacationRead)
def start_vacation(
    body: VacationStart,
    vacation_id: int = Path(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rh_or_admin),
):
    vac = vac_service.start_vacation(db, vacation_id, body, current_user.company_id, current_user.id)
    return _enrich_vacation(vac, db)


@router.post("/{vacation_id}/complete", response_model=VacationRead)
def complete_vacation(
    vacation_id: int = Path(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rh_or_admin),
):
    vac = vac_service.complete_vacation(db, vacation_id, current_user.company_id, current_user.id)
    return _enrich_vacation(vac, db)


@router.post("/{vacation_id}/cancel", response_model=VacationRead)
def cancel_vacation(
    vacation_id: int = Path(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rh_or_admin),
):
    vac = vac_service.cancel_vacation(db, vacation_id, current_user.company_id, current_user.id)
    return _enrich_vacation(vac, db)


# ── Itens de Férias ───────────────────────────────────────────────────────────

@router.post("/{vacation_id}/items", response_model=VacationRead, status_code=201)
def add_vacation_item(
    data: VacationItemCreate,
    vacation_id: int = Path(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rh_or_admin),
):
    vac = vac_service.add_vacation_item(db, vacation_id, data, current_user.company_id)
    return _enrich_vacation(vac, db)


@router.patch("/{vacation_id}/items/{item_id}", response_model=VacationRead)
def update_vacation_item(
    data: VacationItemUpdate,
    vacation_id: int = Path(...),
    item_id: int     = Path(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rh_or_admin),
):
    vac = vac_service.update_vacation_item_service(db, vacation_id, item_id, data, current_user.company_id)
    return _enrich_vacation(vac, db)


@router.delete("/{vacation_id}/items/{item_id}", response_model=VacationRead)
def delete_vacation_item(
    vacation_id: int = Path(...),
    item_id: int     = Path(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rh_or_admin),
):
    vac = vac_service.delete_vacation_item_service(db, vacation_id, item_id, current_user.company_id)
    return _enrich_vacation(vac, db)


# ── Helpers de resposta ───────────────────────────────────────────────────────

def _enrich_vacation(vac: object, db: Session) -> dict:
    from app.repositories import employee as emp_repo
    d = {c.name: getattr(vac, c.name) for c in vac.__table__.columns}
    emp = emp_repo.get_employee(db, vac.employee_id)
    d["employee_name"]      = emp.name              if emp else None
    d["registration_date"]  = emp.registration_date if emp else None
    d["items"] = [
        {"id": i.id, "vacation_id": i.vacation_id, "item_type": i.item_type,
         "description": i.description, "value": i.value}
        for i in (vac.items or [])
    ]
    return d


def _enrich_termination(term: object, db: Session) -> dict:
    from app.repositories import employee as emp_repo
    d = {c.name: getattr(term, c.name) for c in term.__table__.columns}
    emp = emp_repo.get_employee(db, term.employee_id)
    d["employee_name"] = emp.name if emp else None
    return d
