"""
Endpoints de Relatórios e Dashboard.
"""
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import io

from app.db.database import get_db
from app.core.dependencies import get_current_user, require_rh_or_admin
from app.models.user import User
from app.schemas.reports import DashboardRead, AnnualPayrollRead
from app.services import reports as report_service

router = APIRouter(prefix="/reports", tags=["Relatórios / Dashboard"])


# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("/dashboard", response_model=DashboardRead)
def get_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Painel geral da empresa: totais de funcionários, folha, ponto,
    férias, aniversários e alertas.
    """
    return report_service.get_dashboard(db, current_user.company_id)


@router.get("/annual-payroll", response_model=AnnualPayrollRead)
def get_annual_payroll(
    year: int = Query(..., ge=2020),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return report_service.get_annual_payroll(db, current_user.company_id, year)


# ── Relatórios Excel ──────────────────────────────────────────────────────────

def _excel_response(data: bytes, filename: str) -> StreamingResponse:
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/payroll")
def export_payroll(
    month: int = Query(..., ge=1, le=12),
    year:  int = Query(..., ge=2000),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rh_or_admin),
):
    """Exporta o resumo da folha de pagamento de um mês em Excel."""
    data = report_service.report_payroll(db, current_user.company_id, month, year)
    return _excel_response(data, f"folha_{month:02d}_{year}.xlsx")


@router.get("/timesheet")
def export_timesheet(
    month:       int      = Query(..., ge=1, le=12),
    year:        int      = Query(..., ge=2000),
    employee_id: int | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rh_or_admin),
):
    """
    Exporta o espelho de ponto do mês em Excel.
    Sem employee_id → todos os funcionários da empresa.
    """
    data = report_service.report_timesheet(
        db, current_user.company_id, month, year, employee_id
    )
    suffix = f"_emp{employee_id}" if employee_id else ""
    return _excel_response(data, f"ponto_{month:02d}_{year}{suffix}.xlsx")


@router.get("/employees")
def export_employees(
    include_inactive: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rh_or_admin),
):
    """
    Exporta o cadastro de funcionários em Excel.
    CPF mascarado por segurança.
    """
    data = report_service.report_employees(db, current_user.company_id, include_inactive)
    return _excel_response(data, "funcionarios.xlsx")


@router.get("/vacations")
def export_vacations(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rh_or_admin),
):
    """Exporta o histórico de férias de todos os funcionários em Excel."""
    data = report_service.report_vacations(db, current_user.company_id)
    return _excel_response(data, "ferias.xlsx")


@router.get("/terminations")
def export_terminations(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rh_or_admin),
):
    """Exporta o relatório de rescisões em Excel."""
    data = report_service.report_terminations(db, current_user.company_id)
    return _excel_response(data, "rescisoes.xlsx")


@router.get("/hour-bank")
def export_hour_bank(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rh_or_admin),
):
    """Exporta o saldo de banco de horas de todos os funcionários ativos em Excel."""
    data = report_service.report_hour_bank(db, current_user.company_id)
    return _excel_response(data, "banco_horas.xlsx")
