"""
Serviço de Controle de Ponto.
Todas as regras de cálculo ficam aqui e em timesheet_calc.py.
"""
from datetime import date
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.repositories import timesheet as ts_repo
from app.repositories import employee as emp_repo
from app.repositories import audit_log as audit_repo
from app.schemas.timesheet import TimesheetEntryCreate, TimesheetEntryUpdate
from app.models.employee import Employee, EmployeeStatus
from app.models.timesheet import TimesheetEntry
from app.utils.timesheet_calc import (
    expected_minutes, calc_worked_minutes,
    calc_overtime_minutes, calc_late_minutes,
    calc_bank_delta, format_minutes,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_employee(db: Session, employee_id: int, company_id: int) -> Employee:
    emp = emp_repo.get_employee(db, employee_id)
    if not emp or emp.company_id != company_id:
        raise HTTPException(status_code=404, detail="Funcionário não encontrado")
    if emp.status == EmployeeStatus.INACTIVE:
        raise HTTPException(status_code=400, detail="Funcionário inativo")
    return emp


def _get_entry_or_404(
    db: Session, entry_id: int, company_id: int
) -> tuple[TimesheetEntry, Employee]:
    entry = ts_repo.get_entry(db, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Registro de ponto não encontrado")
    emp = emp_repo.get_employee(db, entry.employee_id)
    if not emp or emp.company_id != company_id:
        raise HTTPException(status_code=404, detail="Registro de ponto não encontrado")
    return entry, emp


def _compute_fields(
    data_create_or_update,
    work_date: date,
    emp: Employee,
    old_bank_delta: int = 0,
) -> dict:
    """Calcula todos os campos derivados de uma entrada de ponto."""
    is_abs = getattr(data_create_or_update, "is_absence", False) or False
    is_med = getattr(data_create_or_update, "is_medical_certificate", False) or False
    is_ann = getattr(data_create_or_update, "is_annulled", False) or False

    worked = calc_worked_minutes(
        getattr(data_create_or_update, "entry_time", None),
        getattr(data_create_or_update, "lunch_out_time", None),
        getattr(data_create_or_update, "lunch_in_time", None),
        getattr(data_create_or_update, "exit_time", None),
    )
    expected = expected_minutes(work_date, emp.is_intern, emp.weekly_hours)
    overtime = calc_overtime_minutes(worked, expected) if not (is_abs or is_med or is_ann) else 0
    late = calc_late_minutes(worked, expected) if not (is_abs or is_med or is_ann) else 0

    return {
        "worked_minutes": worked,
        "overtime_minutes": overtime,
        "late_minutes": late,
    }


# ── Operações ─────────────────────────────────────────────────────────────────

def register_entry(
    db: Session,
    employee_id: int,
    data: TimesheetEntryCreate,
    company_id: int,
    registered_by_id: int,
) -> TimesheetEntry:
    emp = _get_employee(db, employee_id, company_id)

    # Impede duplicata no mesmo dia
    existing = ts_repo.get_entry_by_date(db, employee_id, data.work_date)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Já existe registro para {data.work_date}. Use PATCH para editar.",
        )

    computed = _compute_fields(data, data.work_date, emp)

    entry = ts_repo.create_entry(db, {
        "employee_id": employee_id,
        "registered_by_id": registered_by_id,
        "work_date": data.work_date,
        "entry_time": data.entry_time,
        "lunch_out_time": data.lunch_out_time,
        "lunch_in_time": data.lunch_in_time,
        "exit_time": data.exit_time,
        "is_absence": data.is_absence,
        "is_medical_certificate": data.is_medical_certificate,
        "justification": data.justification,
        "is_annulled": False,
        **computed,
    })

    # Atualiza banco de horas
    expected = expected_minutes(data.work_date, emp.is_intern, emp.weekly_hours)
    delta = calc_bank_delta(
        computed["worked_minutes"], expected,
        data.is_absence, data.is_medical_certificate, False,
    )
    ts_repo.upsert_hour_bank(db, employee_id, delta)

    return entry


def update_entry(
    db: Session,
    entry_id: int,
    data: TimesheetEntryUpdate,
    company_id: int,
    updated_by_id: int,
) -> TimesheetEntry:
    entry, emp = _get_entry_or_404(db, entry_id, company_id)

    # Reverter o delta antigo do banco de horas antes de recalcular
    old_expected = expected_minutes(entry.work_date, emp.is_intern, emp.weekly_hours)
    old_delta = calc_bank_delta(
        entry.worked_minutes, old_expected,
        entry.is_absence, entry.is_medical_certificate, entry.is_annulled,
    )

    # Mesclar dados existentes com os novos (PATCH parcial)
    merged = TimesheetEntryUpdate(
        entry_time=data.entry_time if data.entry_time is not None else entry.entry_time,
        lunch_out_time=data.lunch_out_time if data.lunch_out_time is not None else entry.lunch_out_time,
        lunch_in_time=data.lunch_in_time if data.lunch_in_time is not None else entry.lunch_in_time,
        exit_time=data.exit_time if data.exit_time is not None else entry.exit_time,
        is_absence=data.is_absence if data.is_absence is not None else entry.is_absence,
        is_medical_certificate=data.is_medical_certificate if data.is_medical_certificate is not None else entry.is_medical_certificate,
        justification=data.justification if data.justification is not None else entry.justification,
        is_annulled=data.is_annulled if data.is_annulled is not None else entry.is_annulled,
    )

    computed = _compute_fields(merged, entry.work_date, emp)

    fields = data.model_dump(exclude_none=True)
    fields.update(computed)

    updated = ts_repo.update_entry(db, entry, fields)

    # Recalcular banco: reverter o antigo e aplicar o novo
    new_delta = calc_bank_delta(
        computed["worked_minutes"], old_expected,
        merged.is_absence, merged.is_medical_certificate, merged.is_annulled,
    )
    bank = ts_repo.get_hour_bank(db, entry.employee_id)
    current_balance = bank.balance_minutes if bank else 0
    ts_repo.set_hour_bank(db, entry.employee_id, current_balance - old_delta + new_delta)

    audit_repo.create_log(
        db, action="timesheet_updated", user_id=updated_by_id,
        entity="timesheet", entity_id=entry_id,
        description=f"Ponto {entry.work_date} do funcionário ID {entry.employee_id} atualizado",
    )
    return updated


def annul_entry(
    db: Session,
    entry_id: int,
    justification: str,
    company_id: int,
    updated_by_id: int,
) -> TimesheetEntry:
    """Anula um dia de ponto (atestado médico aprovado etc.) — sem impacto no banco."""
    if not justification or not justification.strip():
        raise HTTPException(status_code=400, detail="Justificativa obrigatória para anulação")

    entry, emp = _get_entry_or_404(db, entry_id, company_id)

    if entry.is_annulled:
        raise HTTPException(status_code=400, detail="Dia já está anulado")

    # Reverter impacto no banco de horas
    old_expected = expected_minutes(entry.work_date, emp.is_intern, emp.weekly_hours)
    old_delta = calc_bank_delta(
        entry.worked_minutes, old_expected,
        entry.is_absence, entry.is_medical_certificate, False,
    )
    bank = ts_repo.get_hour_bank(db, entry.employee_id)
    current = bank.balance_minutes if bank else 0
    ts_repo.set_hour_bank(db, entry.employee_id, current - old_delta)  # anulado = 0 delta

    updated = ts_repo.update_entry(db, entry, {
        "is_annulled": True,
        "justification": justification,
        "overtime_minutes": 0,
        "late_minutes": 0,
    })

    audit_repo.create_log(
        db, action="timesheet_annulled", user_id=updated_by_id,
        entity="timesheet", entity_id=entry_id,
        description=f"Ponto {entry.work_date} anulado: {justification}",
    )
    return updated


def get_entry(db: Session, entry_id: int, company_id: int) -> TimesheetEntry:
    entry, _ = _get_entry_or_404(db, entry_id, company_id)
    return entry


def get_monthly_report(
    db: Session, employee_id: int, month: int, year: int, company_id: int
) -> dict:
    emp = emp_repo.get_employee(db, employee_id)
    if not emp or emp.company_id != company_id:
        raise HTTPException(status_code=404, detail="Funcionário não encontrado")

    entries = ts_repo.list_entries_by_month(db, employee_id, month, year)
    bank = ts_repo.get_hour_bank(db, employee_id)

    total_worked = sum(e.worked_minutes for e in entries if not e.is_annulled)
    total_overtime = sum(e.overtime_minutes for e in entries)
    total_late = sum(e.late_minutes for e in entries)
    total_absences = sum(1 for e in entries if e.is_absence and not e.is_annulled)
    total_med = sum(1 for e in entries if e.is_medical_certificate)

    return {
        "employee_id": employee_id,
        "employee_name": emp.name,
        "month": month,
        "year": year,
        "total_worked_minutes": total_worked,
        "total_overtime_minutes": total_overtime,
        "total_late_minutes": total_late,
        "total_absences": total_absences,
        "total_medical_certificates": total_med,
        "hour_bank_balance_minutes": bank.balance_minutes if bank else 0,
        "entries": [
            {
                "work_date": e.work_date,
                "worked_minutes": e.worked_minutes,
                "overtime_minutes": e.overtime_minutes,
                "late_minutes": e.late_minutes,
                "is_absence": e.is_absence,
                "is_medical_certificate": e.is_medical_certificate,
                "is_annulled": e.is_annulled,
            }
            for e in entries
        ],
    }


def get_hour_bank(db: Session, employee_id: int, company_id: int) -> dict:
    emp = emp_repo.get_employee(db, employee_id)
    if not emp or emp.company_id != company_id:
        raise HTTPException(status_code=404, detail="Funcionário não encontrado")

    bank = ts_repo.get_hour_bank(db, employee_id)
    balance = bank.balance_minutes if bank else 0
    return {
        "employee_id": employee_id,
        "balance_minutes": balance,
        "balance_hours": format_minutes(balance),
    }
