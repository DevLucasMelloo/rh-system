from fastapi import APIRouter, Depends, Query, Body
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.core.dependencies import get_current_user, require_rh_or_admin
from app.schemas.timesheet import (
    TimesheetEntryCreate, TimesheetEntryUpdate,
    TimesheetEntryRead, HourBankRead, MonthlyReport,
)
from app.services import timesheet as ts_service
from app.models.user import User

router = APIRouter(prefix="/timesheet", tags=["Controle de Ponto"])


@router.post("/{employee_id}", response_model=TimesheetEntryRead, status_code=201)
def register_entry(
    employee_id: int,
    data: TimesheetEntryCreate,
    current_user: User = Depends(require_rh_or_admin),
    db: Session = Depends(get_db),
):
    return ts_service.register_entry(db, employee_id, data, current_user.company_id, current_user.id)


@router.patch("/entry/{entry_id}", response_model=TimesheetEntryRead)
def update_entry(
    entry_id: int,
    data: TimesheetEntryUpdate,
    current_user: User = Depends(require_rh_or_admin),
    db: Session = Depends(get_db),
):
    return ts_service.update_entry(db, entry_id, data, current_user.company_id, current_user.id)


@router.post("/entry/{entry_id}/annul", response_model=TimesheetEntryRead)
def annul_entry(
    entry_id: int,
    justification: str = Body(..., embed=True),
    current_user: User = Depends(require_rh_or_admin),
    db: Session = Depends(get_db),
):
    return ts_service.annul_entry(db, entry_id, justification, current_user.company_id, current_user.id)


@router.get("/entry/{entry_id}", response_model=TimesheetEntryRead)
def get_entry(
    entry_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ts_service.get_entry(db, entry_id, current_user.company_id)


@router.get("/{employee_id}/report", response_model=MonthlyReport)
def monthly_report(
    employee_id: int,
    month: int = Query(..., ge=1, le=12),
    year: int = Query(..., ge=2000, le=2100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ts_service.get_monthly_report(db, employee_id, month, year, current_user.company_id)


@router.get("/{employee_id}/hour-bank", response_model=HourBankRead)
def hour_bank(
    employee_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ts_service.get_hour_bank(db, employee_id, current_user.company_id)
