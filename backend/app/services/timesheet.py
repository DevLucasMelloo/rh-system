"""
Serviço de Controle de Ponto.
Todas as regras de cálculo ficam aqui e em timesheet_calc.py.
"""
import calendar
from datetime import date, time as dtime, timedelta
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.repositories import timesheet as ts_repo
from app.repositories import employee as emp_repo
from app.repositories import audit_log as audit_repo
from app.schemas.timesheet import (
    TimesheetEntryCreate, TimesheetEntryUpdate,
    BulkSaveRequest, BatchDayRequest, PeriodCreate, PeriodRead, PeriodEmployeeInfo, DayRead,
)
from app.models.employee import Employee, EmployeeStatus
from app.models.timesheet import TimesheetEntry
from app.utils.timesheet_calc import (
    expected_minutes, expected_minutes_for_compensar,
    calc_worked_minutes,
    calc_overtime_minutes, calc_late_minutes,
    calc_bank_delta, format_minutes,
)

WEEKDAY_PT = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]


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
    is_abs  = getattr(data_create_or_update, "is_absence", False) or False
    is_med  = getattr(data_create_or_update, "is_medical_certificate", False) or False
    is_ann  = getattr(data_create_or_update, "is_annulled", False) or False
    is_hol  = getattr(data_create_or_update, "is_holiday", False) or False
    is_rec  = getattr(data_create_or_update, "is_recess", False) or False
    is_comp = getattr(data_create_or_update, "is_compensar", False) or False
    is_dsr  = getattr(data_create_or_update, "is_dsr_deducted", False) or False

    worked = calc_worked_minutes(
        getattr(data_create_or_update, "entry_time", None),
        getattr(data_create_or_update, "lunch_out_time", None),
        getattr(data_create_or_update, "lunch_in_time", None),
        getattr(data_create_or_update, "exit_time", None),
    )

    no_calc = is_abs or is_med or is_ann or is_hol or is_rec or is_comp or is_dsr
    if no_calc:
        worked = 0

    expected = expected_minutes(work_date, emp.is_intern, emp.weekly_hours)
    overtime = calc_overtime_minutes(worked, expected) if not no_calc else 0
    late     = calc_late_minutes(worked, expected) if not no_calc else 0

    return {
        "worked_minutes":   worked,
        "overtime_minutes": overtime,
        "late_minutes":     late,
    }


# ── Auto-DSR rules ────────────────────────────────────────────────────────────

def _ensure_special_entry(
    db: Session,
    employee_id: int,
    work_date: date,
    user_id: int,
    **flags,
) -> None:
    """Cria ou atualiza Sáb/Dom com flags de desconto automático DSR."""
    existing = ts_repo.get_entry_by_date(db, employee_id, work_date)
    base = {
        "employee_id":            employee_id,
        "registered_by_id":       user_id,
        "work_date":              work_date,
        "is_absence":             False,
        "is_holiday":             False,
        "is_medical_certificate": False,
        "is_recess":              False,
        "is_compensar":           False,
        "is_dsr_deducted":        False,
        "is_annulled":            False,
        "worked_minutes":         0,
        "overtime_minutes":       0,
        "late_minutes":           0,
    }
    base.update(flags)

    if existing:
        # Nunca sobrescreve um feriado explícito com DSR automático
        if existing.is_holiday and not flags.get("is_holiday"):
            return
        update_fields = {k: v for k, v in base.items()
                         if k not in ("employee_id", "work_date")}
        ts_repo.update_entry(db, existing, update_fields)
    else:
        ts_repo.create_entry(db, base)


def _apply_weekly_dsr_rules(
    db: Session,
    employee_id: int,
    emp: Employee,
    affected_dates: list[date],
    user_id: int,
) -> None:
    """
    Aplica regras de DSR para as semanas que contêm as datas afetadas.

    Regras:
    1. Seg-Sex todos recesso → Sáb (is_recess) e Dom (is_dsr_deducted).
       Feriado dentro do recesso permanece pago.
    2. Seg-Sex todos com falta (5 consecutivas) → Sáb e Dom (is_dsr_deducted).
    3. Qualquer falta na semana + feriado na semana → feriado descontado + Dom descontado.
    """
    if not affected_dates:
        return

    mondays: set[date] = set()
    for d in affected_dates:
        mondays.add(d - timedelta(days=d.weekday()))

    all_start = min(mondays) - timedelta(days=1)
    all_end   = max(mondays) + timedelta(days=13)
    entries_map: dict[date, TimesheetEntry] = {
        e.work_date: e
        for e in ts_repo.get_entries_range(db, employee_id, all_start, all_end)
    }

    for monday in sorted(mondays):
        weekdays   = [monday + timedelta(days=i) for i in range(5)]
        saturday   = monday + timedelta(days=5)
        sunday     = monday + timedelta(days=6)

        day_entries = [entries_map.get(d) for d in weekdays]

        adm = emp.admission_date
        if adm and sunday < adm:
            continue

        has_any = any(e is not None for e in day_entries)
        if not has_any:
            for auto_date in (saturday, sunday):
                e = entries_map.get(auto_date)
                if e and (getattr(e, "is_dsr_deducted", False) or
                          (getattr(e, "is_recess", False) and not e.is_holiday)):
                    ts_repo.delete_entry(db, e)
            continue

        all_recess = all(
            e and getattr(e, "is_recess", False) and not e.is_holiday
            for e in day_entries
        )
        all_absent = all(
            e and e.is_absence and not e.is_medical_certificate and not e.is_annulled
            for e in day_entries
        )
        any_absent = any(
            e and e.is_absence and not e.is_medical_certificate and not e.is_annulled
            for e in day_entries
        )
        any_holiday = any(e and e.is_holiday for e in day_entries)

        if all_recess:
            _ensure_special_entry(db, employee_id, saturday, user_id, is_recess=True)
            _ensure_special_entry(db, employee_id, sunday,   user_id, is_dsr_deducted=True)
            entries_map[saturday] = ts_repo.get_entry_by_date(db, employee_id, saturday)
            entries_map[sunday]   = ts_repo.get_entry_by_date(db, employee_id, sunday)

        elif all_absent:
            _ensure_special_entry(db, employee_id, saturday, user_id, is_dsr_deducted=True)
            _ensure_special_entry(db, employee_id, sunday,   user_id, is_dsr_deducted=True)
            entries_map[saturday] = ts_repo.get_entry_by_date(db, employee_id, saturday)
            entries_map[sunday]   = ts_repo.get_entry_by_date(db, employee_id, sunday)

        elif any_absent and any_holiday:
            # Falta + feriado na mesma semana: desconta feriado e DSR
            for d, e in zip(weekdays, day_entries):
                if e and e.is_holiday and not getattr(e, "is_dsr_deducted", False):
                    ts_repo.update_entry(db, e, {"is_dsr_deducted": True})
                    entries_map[d] = ts_repo.get_entry_by_date(db, employee_id, d)
            _ensure_special_entry(db, employee_id, sunday, user_id, is_dsr_deducted=True)
            entries_map[sunday] = ts_repo.get_entry_by_date(db, employee_id, sunday)

        else:
            # Nenhuma regra ativa: remove automáticos se existirem
            for auto_date in (saturday, sunday):
                e = entries_map.get(auto_date)
                if e and (getattr(e, "is_dsr_deducted", False) or
                          (getattr(e, "is_recess", False) and not e.is_holiday)):
                    ts_repo.delete_entry(db, e)
                    entries_map.pop(auto_date, None)
            if not any_absent:
                for d, e in zip(weekdays, day_entries):
                    if e and e.is_holiday and getattr(e, "is_dsr_deducted", False):
                        ts_repo.update_entry(db, e, {"is_dsr_deducted": False})


# ── Operações ─────────────────────────────────────────────────────────────────

def register_entry(
    db: Session,
    employee_id: int,
    data: TimesheetEntryCreate,
    company_id: int,
    registered_by_id: int,
) -> TimesheetEntry:
    emp = _get_employee(db, employee_id, company_id)

    existing = ts_repo.get_entry_by_date(db, employee_id, data.work_date)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Já existe registro para {data.work_date}. Use PATCH para editar.",
        )

    computed = _compute_fields(data, data.work_date, emp)

    entry = ts_repo.create_entry(db, {
        "employee_id":            employee_id,
        "registered_by_id":       registered_by_id,
        "work_date":              data.work_date,
        "entry_time":             data.entry_time,
        "lunch_out_time":         data.lunch_out_time,
        "lunch_in_time":          data.lunch_in_time,
        "exit_time":              data.exit_time,
        "is_absence":             data.is_absence,
        "is_medical_certificate": data.is_medical_certificate,
        "justification":          data.justification,
        "is_annulled":            False,
        **computed,
    })

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

    old_expected = expected_minutes(entry.work_date, emp.is_intern, emp.weekly_hours)
    old_delta = calc_bank_delta(
        entry.worked_minutes, old_expected,
        entry.is_absence, entry.is_medical_certificate, entry.is_annulled,
        getattr(entry, "is_recess", False),
        getattr(entry, "is_compensar", False),
        getattr(entry, "is_dsr_deducted", False),
    )

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
    if not justification or not justification.strip():
        raise HTTPException(status_code=400, detail="Justificativa obrigatória para anulação")

    entry, emp = _get_entry_or_404(db, entry_id, company_id)

    if entry.is_annulled:
        raise HTTPException(status_code=400, detail="Dia já está anulado")

    old_expected = expected_minutes(entry.work_date, emp.is_intern, emp.weekly_hours)
    old_delta = calc_bank_delta(
        entry.worked_minutes, old_expected,
        entry.is_absence, entry.is_medical_certificate, False,
        getattr(entry, "is_recess", False),
        getattr(entry, "is_compensar", False),
        getattr(entry, "is_dsr_deducted", False),
    )
    bank = ts_repo.get_hour_bank(db, entry.employee_id)
    current = bank.balance_minutes if bank else 0
    ts_repo.set_hour_bank(db, entry.employee_id, current - old_delta)

    updated = ts_repo.update_entry(db, entry, {
        "is_annulled":      True,
        "justification":    justification,
        "overtime_minutes": 0,
        "late_minutes":     0,
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

    entries   = ts_repo.list_entries_by_month(db, employee_id, month, year)
    bank      = ts_repo.get_hour_bank(db, employee_id)
    total_worked   = sum(e.worked_minutes for e in entries if not e.is_annulled)
    total_overtime = sum(e.overtime_minutes for e in entries)
    total_late     = sum(e.late_minutes for e in entries)
    total_absences = sum(1 for e in entries if e.is_absence and not e.is_annulled)
    total_med      = sum(1 for e in entries if e.is_medical_certificate)

    return {
        "employee_id":                employee_id,
        "employee_name":              emp.name,
        "month":                      month,
        "year":                       year,
        "total_worked_minutes":       total_worked,
        "total_overtime_minutes":     total_overtime,
        "total_late_minutes":         total_late,
        "total_absences":             total_absences,
        "total_medical_certificates": total_med,
        "hour_bank_balance_minutes":  bank.balance_minutes if bank else 0,
        "entries": [
            {
                "work_date":              e.work_date,
                "worked_minutes":         e.worked_minutes,
                "overtime_minutes":       e.overtime_minutes,
                "late_minutes":           e.late_minutes,
                "is_absence":             e.is_absence,
                "is_medical_certificate": e.is_medical_certificate,
                "is_annulled":            e.is_annulled,
            }
            for e in entries
        ],
    }


# ── Períodos de Ponto ─────────────────────────────────────────────────────────

def _eligible_employees(db: Session, company_id: int, month: int, year: int) -> list:
    last_day = date(year, month, calendar.monthrange(year, month)[1])
    emps = emp_repo.list_active(db, company_id)
    return [e for e in emps if e.admission_date is None or e.admission_date <= last_day]


def _period_employee_info(emp: Employee, month: int, year: int, entries: list) -> PeriodEmployeeInfo:
    first = date(year, month, 1)
    last  = date(year, month, calendar.monthrange(year, month)[1])
    adm   = emp.admission_date
    start = max(first, adm) if adm else first

    total_days = (last - start).days + 1
    total_workdays = sum(
        1 for d in (date(year, month, day) for day in range(start.day, last.day + 1))
        if d.weekday() < 5
    )
    entry_dates = {e.work_date for e in entries}
    filled_workdays = sum(
        1 for d in (date(year, month, day) for day in range(start.day, last.day + 1))
        if d.weekday() < 5 and d in entry_dates
    )

    balance_minutes = 0
    for e in entries:
        if getattr(e, "is_holiday", False) and not getattr(e, "is_dsr_deducted", False):
            continue
        exp = expected_minutes(e.work_date, emp.is_intern, emp.weekly_hours)
        is_comp = getattr(e, "is_compensar", False)
        if is_comp:
            exp = expected_minutes_for_compensar(e.work_date, emp.is_intern, emp.weekly_hours)
        balance_minutes += calc_bank_delta(
            e.worked_minutes, exp,
            e.is_absence, e.is_medical_certificate, e.is_annulled,
            getattr(e, "is_recess", False), is_comp,
            getattr(e, "is_dsr_deducted", False),
        )

    return PeriodEmployeeInfo(
        employee_id=emp.id,
        name=emp.name,
        admission_date=adm,
        start_date=start,
        end_date=last,
        total_days=total_days,
        filled_workdays=filled_workdays,
        total_workdays=total_workdays,
        balance_minutes=balance_minutes,
    )


def open_period(db: Session, data: PeriodCreate, company_id: int, user_id: int) -> PeriodRead:
    existing = ts_repo.get_period(db, company_id, data.competence_month, data.competence_year)
    if existing:
        raise HTTPException(status_code=409, detail="Período já foi aberto.")

    period = ts_repo.create_period(db, {
        "company_id":       company_id,
        "competence_month": data.competence_month,
        "competence_year":  data.competence_year,
        "status":           "open",
    })
    audit_repo.create_log(
        db, action="timesheet_period_opened", user_id=user_id,
        entity="timesheet_period", entity_id=period.id,
        description=f"Período de ponto {data.competence_month:02d}/{data.competence_year} aberto",
    )
    return get_period_info(db, data.competence_month, data.competence_year, company_id)


def close_period(db: Session, month: int, year: int, company_id: int, user_id: int) -> dict:
    period = ts_repo.get_period(db, company_id, month, year)
    if not period:
        raise HTTPException(status_code=404, detail="Período não encontrado.")
    if period.status == "closed":
        raise HTTPException(status_code=400, detail="Período já está fechado.")

    ts_repo.close_period(db, period, user_id)
    audit_repo.create_log(
        db, action="timesheet_period_closed", user_id=user_id,
        entity="timesheet_period", entity_id=period.id,
        description=f"Período de ponto {month:02d}/{year} fechado",
    )
    return {"status": "closed", "month": month, "year": year}


def get_period_info(db: Session, month: int, year: int, company_id: int) -> PeriodRead:
    period = ts_repo.get_period(db, company_id, month, year)
    emps   = _eligible_employees(db, company_id, month, year)

    employees_info = []
    for emp in emps:
        first = date(year, month, 1)
        last  = date(year, month, calendar.monthrange(year, month)[1])
        adm   = emp.admission_date
        start = max(first, adm) if adm else first
        entries = ts_repo.get_entries_range(db, emp.id, start, last)
        employees_info.append(_period_employee_info(emp, month, year, entries))

    return PeriodRead(
        id=period.id if period else None,
        competence_month=month,
        competence_year=year,
        status=period.status if period else "not_opened",
        employees=employees_info,
    )


def get_employee_days(
    db: Session, employee_id: int, month: int, year: int, company_id: int
) -> list[DayRead]:
    emp = emp_repo.get_employee(db, employee_id)
    if not emp or emp.company_id != company_id:
        raise HTTPException(status_code=404, detail="Funcionário não encontrado")

    first = date(year, month, 1)
    last  = date(year, month, calendar.monthrange(year, month)[1])
    adm   = emp.admission_date
    start = max(first, adm) if adm else first

    entries_map: dict[date, TimesheetEntry] = {
        e.work_date: e
        for e in ts_repo.get_entries_range(db, employee_id, start, last)
    }

    vacation_dates: set[date] = set()
    try:
        from app.models.vacation import Vacation, VacationStatus
        vacations = (
            db.query(Vacation)
            .filter(
                Vacation.employee_id == employee_id,
                Vacation.status.in_([VacationStatus.SCHEDULED, VacationStatus.ACTIVE, VacationStatus.COMPLETED]),
                Vacation.sell_all_days.isnot(True),
                Vacation.enjoyment_start.isnot(None),
            )
            .all()
        )
        for v in vacations:
            if v.enjoyment_start and v.enjoyment_days:
                vac_end = v.enjoyment_start + timedelta(days=v.enjoyment_days - 1)
                d = v.enjoyment_start
                while d <= vac_end:
                    if first <= d <= last:
                        vacation_dates.add(d)
                    d += timedelta(days=1)
    except Exception:
        pass

    days = []
    cur = start
    while cur <= last:
        wd    = cur.weekday()
        entry = entries_map.get(cur)
        is_vac = cur in vacation_dates
        days.append(DayRead(
            work_date=cur,
            weekday=wd,
            weekday_name=WEEKDAY_PT[wd],
            is_weekend=wd >= 5,
            entry_id=entry.id if entry else None,
            entry_time=str(entry.entry_time)[:5] if entry and entry.entry_time else None,
            lunch_out_time=str(entry.lunch_out_time)[:5] if entry and entry.lunch_out_time else None,
            lunch_in_time=str(entry.lunch_in_time)[:5] if entry and entry.lunch_in_time else None,
            exit_time=str(entry.exit_time)[:5] if entry and entry.exit_time else None,
            worked_minutes=entry.worked_minutes if entry else 0,
            overtime_minutes=entry.overtime_minutes if entry else 0,
            is_absence=entry.is_absence if entry else False,
            is_medical_certificate=entry.is_medical_certificate if entry else False,
            certificate_hours=float(entry.certificate_hours) if entry and entry.certificate_hours else None,
            is_holiday=entry.is_holiday if entry else False,
            is_recess=getattr(entry, "is_recess", False) if entry else False,
            is_compensar=getattr(entry, "is_compensar", False) if entry else False,
            is_dsr_deducted=getattr(entry, "is_dsr_deducted", False) if entry else False,
            justification=entry.justification if entry else None,
            is_annulled=entry.is_annulled if entry else False,
            is_vacation=is_vac,
        ))
        cur += timedelta(days=1)
    return days


def bulk_save_entries(
    db: Session, employee_id: int, month: int, year: int,
    data: BulkSaveRequest, company_id: int, user_id: int,
) -> dict:
    emp = emp_repo.get_employee(db, employee_id)
    if not emp or emp.company_id != company_id:
        raise HTTPException(status_code=404, detail="Funcionário não encontrado")

    def parse_t(s: str | None) -> dtime | None:
        if not s:
            return None
        try:
            h, m = s.strip().split(":")
            return dtime(int(h), int(m))
        except Exception:
            return None

    saved = 0
    affected_dates: list[date] = []

    for item in data.entries:
        entry_t   = parse_t(item.entry_time)
        lunch_out = parse_t(item.lunch_out_time)
        lunch_in  = parse_t(item.lunch_in_time)
        exit_t    = parse_t(item.exit_time)

        is_special = (item.is_absence or item.is_medical_certificate or item.is_holiday
                      or item.is_recess or item.is_compensar)
        has_data = entry_t is not None or is_special

        existing = ts_repo.get_entry_by_date(db, employee_id, item.work_date)

        if not has_data:
            if existing and not existing.is_annulled:
                if getattr(existing, "is_dsr_deducted", False):
                    continue  # Não remove DSR automático manualmente
                old_exp = expected_minutes(item.work_date, emp.is_intern, emp.weekly_hours)
                if getattr(existing, "is_compensar", False):
                    old_exp = expected_minutes_for_compensar(item.work_date, emp.is_intern, emp.weekly_hours)
                old_delta = calc_bank_delta(
                    existing.worked_minutes, old_exp,
                    existing.is_absence, existing.is_medical_certificate, existing.is_annulled,
                    getattr(existing, "is_recess", False),
                    getattr(existing, "is_compensar", False),
                    getattr(existing, "is_dsr_deducted", False),
                )
                bank = ts_repo.get_hour_bank(db, employee_id)
                ts_repo.set_hour_bank(db, employee_id, (bank.balance_minutes if bank else 0) - old_delta)
                ts_repo.delete_entry(db, existing)
                affected_dates.append(item.work_date)
            continue

        class _D:
            pass
        adapter = _D()
        adapter.entry_time            = entry_t
        adapter.lunch_out_time        = lunch_out
        adapter.lunch_in_time         = lunch_in
        adapter.exit_time             = exit_t
        adapter.is_absence            = item.is_absence
        adapter.is_medical_certificate = item.is_medical_certificate
        adapter.is_holiday            = item.is_holiday
        adapter.is_recess             = item.is_recess
        adapter.is_compensar          = item.is_compensar
        adapter.is_dsr_deducted       = False
        adapter.is_annulled           = False

        computed = _compute_fields(adapter, item.work_date, emp)

        expected_mins = expected_minutes(item.work_date, emp.is_intern, emp.weekly_hours)
        if item.is_compensar:
            expected_mins = expected_minutes_for_compensar(item.work_date, emp.is_intern, emp.weekly_hours)

        fields = {
            "employee_id":            employee_id,
            "registered_by_id":       user_id,
            "work_date":              item.work_date,
            "entry_time":             entry_t,
            "lunch_out_time":         lunch_out,
            "lunch_in_time":          lunch_in,
            "exit_time":              exit_t,
            "is_absence":             item.is_absence,
            "is_medical_certificate": item.is_medical_certificate,
            "certificate_hours":      item.certificate_hours,
            "is_holiday":             item.is_holiday,
            "is_recess":              item.is_recess,
            "is_compensar":           item.is_compensar,
            "is_dsr_deducted":        False,
            "justification":          item.justification,
            "is_annulled":            False,
            **computed,
        }

        new_delta = 0 if item.is_holiday else calc_bank_delta(
            computed["worked_minutes"], expected_mins,
            item.is_absence, item.is_medical_certificate, False,
            item.is_recess, item.is_compensar, False,
        )

        if existing:
            old_exp = expected_minutes(item.work_date, emp.is_intern, emp.weekly_hours)
            if getattr(existing, "is_compensar", False):
                old_exp = expected_minutes_for_compensar(item.work_date, emp.is_intern, emp.weekly_hours)
            old_delta = calc_bank_delta(
                existing.worked_minutes, old_exp,
                existing.is_absence, existing.is_medical_certificate, existing.is_annulled,
                getattr(existing, "is_recess", False),
                getattr(existing, "is_compensar", False),
                getattr(existing, "is_dsr_deducted", False),
            )
            del fields["employee_id"]
            del fields["work_date"]
            ts_repo.update_entry(db, existing, fields)
            bank = ts_repo.get_hour_bank(db, employee_id)
            ts_repo.set_hour_bank(db, employee_id, (bank.balance_minutes if bank else 0) - old_delta + new_delta)
        else:
            ts_repo.create_entry(db, fields)
            ts_repo.upsert_hour_bank(db, employee_id, new_delta)

        affected_dates.append(item.work_date)
        saved += 1

    if affected_dates:
        _apply_weekly_dsr_rules(db, employee_id, emp, affected_dates, user_id)

    return {"saved": saved}


# ── Lançamento em lote ────────────────────────────────────────────────────────

def batch_day_launch(
    db: Session,
    data: BatchDayRequest,
    company_id: int,
    user_id: int,
) -> dict:
    """Lança Feriado, Recesso ou Compensar para múltiplos funcionários de uma vez."""
    if data.type not in ("feriado", "recesso", "compensar"):
        raise HTTPException(status_code=400, detail="Tipo inválido. Use: feriado, recesso ou compensar")

    if data.type == "recesso":
        if not data.start_date or not data.end_date:
            raise HTTPException(status_code=400, detail="start_date e end_date são obrigatórios para recesso")
        dates: list[date] = []
        cur = data.start_date
        while cur <= data.end_date:
            dates.append(cur)
            cur += timedelta(days=1)
    else:
        if not data.launch_date:
            raise HTTPException(status_code=400, detail="launch_date é obrigatório para feriado e compensar")
        dates = [data.launch_date]

    total_created = 0

    for emp_id in data.employee_ids:
        emp = emp_repo.get_employee(db, emp_id)
        if not emp or emp.company_id != company_id:
            continue
        if emp.status == EmployeeStatus.INACTIVE:
            continue

        affected: list[date] = []

        for work_date in dates:
            # Fins de semana no recesso: serão criados pela regra DSR automática
            if data.type == "recesso" and work_date.weekday() >= 5:
                continue

            existing = ts_repo.get_entry_by_date(db, emp_id, work_date)

            is_holiday   = data.type == "feriado"
            is_recess    = data.type == "recesso"
            is_compensar = data.type == "compensar"

            expected_mins = expected_minutes(work_date, emp.is_intern, emp.weekly_hours)
            if is_compensar:
                expected_mins = expected_minutes_for_compensar(work_date, emp.is_intern, emp.weekly_hours)

            new_delta = -expected_mins if is_compensar else 0

            fields = {
                "employee_id":            emp_id,
                "registered_by_id":       user_id,
                "work_date":              work_date,
                "entry_time":             None,
                "lunch_out_time":         None,
                "lunch_in_time":          None,
                "exit_time":              None,
                "is_absence":             False,
                "is_medical_certificate": False,
                "certificate_hours":      None,
                "is_holiday":             is_holiday,
                "is_recess":              is_recess,
                "is_compensar":           is_compensar,
                "is_dsr_deducted":        False,
                "justification":          None,
                "is_annulled":            False,
                "worked_minutes":         0,
                "overtime_minutes":       0,
                "late_minutes":           0,
            }

            if existing:
                old_exp = expected_minutes(work_date, emp.is_intern, emp.weekly_hours)
                if getattr(existing, "is_compensar", False):
                    old_exp = expected_minutes_for_compensar(work_date, emp.is_intern, emp.weekly_hours)
                old_delta = calc_bank_delta(
                    existing.worked_minutes, old_exp,
                    existing.is_absence, existing.is_medical_certificate, existing.is_annulled,
                    getattr(existing, "is_recess", False),
                    getattr(existing, "is_compensar", False),
                    getattr(existing, "is_dsr_deducted", False),
                )
                update_f = {k: v for k, v in fields.items() if k not in ("employee_id", "work_date")}
                ts_repo.update_entry(db, existing, update_f)
                bank = ts_repo.get_hour_bank(db, emp_id)
                ts_repo.set_hour_bank(db, emp_id, (bank.balance_minutes if bank else 0) - old_delta + new_delta)
            else:
                ts_repo.create_entry(db, fields)
                ts_repo.upsert_hour_bank(db, emp_id, new_delta)

            affected.append(work_date)
            total_created += 1

        if affected and data.type == "recesso":
            _apply_weekly_dsr_rules(db, emp_id, emp, affected, user_id)

    type_label = {"feriado": "Feriado", "recesso": "Recesso", "compensar": "Compensar"}[data.type]
    audit_repo.create_log(
        db, action="timesheet_batch_launch", user_id=user_id,
        entity="timesheet", entity_id=None,
        description=f"Lançamento em lote: {type_label} para {len(data.employee_ids)} funcionário(s) — {total_created} entrada(s)",
    )

    return {"created": total_created, "employees": len(data.employee_ids)}


# ── Banco de horas ────────────────────────────────────────────────────────────

def _month_absence_minutes(entries, year: int, month: int, emp) -> int:
    total = 0
    for e in entries:
        if (e.is_absence
                and not getattr(e, "is_holiday", False)
                and e.work_date.year == year
                and e.work_date.month == month):
            total += expected_minutes(e.work_date, emp.is_intern, emp.weekly_hours)
    return total


def get_bank_summary(db: Session, year: int, company_id: int) -> list[dict]:
    from app.repositories import payroll as payroll_repo
    from app.models.payroll import PayrollStatus

    employees = emp_repo.list_active(db, company_id)
    result = []

    for emp in employees:
        months_data = {}
        for month in range(1, 13):
            entries = ts_repo.list_entries_by_month(db, emp.id, month, year)
            monthly_delta = 0
            for e in entries:
                if getattr(e, "is_holiday", False) and not getattr(e, "is_dsr_deducted", False):
                    continue
                if e.is_annulled or e.is_medical_certificate:
                    continue
                if getattr(e, "is_recess", False) or getattr(e, "is_dsr_deducted", False):
                    continue
                if e.is_absence:
                    continue  # falta: desconto direto no salário, não entra no banco
                if getattr(e, "is_compensar", False):
                    exp_c = expected_minutes_for_compensar(e.work_date, emp.is_intern, emp.weekly_hours)
                    monthly_delta -= exp_c
                else:
                    exp = expected_minutes(e.work_date, emp.is_intern, emp.weekly_hours)
                    monthly_delta += (e.worked_minutes or 0) - exp

            # Operações de banco no holerite fechado deste mês
            paid_minutes     = 0  # HE paga (banco_credito ou pay_overtime legado)
            deducted_minutes = 0  # banco negativo descontado (banco_desconto)
            payroll = payroll_repo.get_payroll_by_period(db, emp.id, month, year)
            if payroll and payroll.status == PayrollStatus.CLOSED:
                sal = float(payroll.gross_salary or 0)
                for item in (payroll.items or []):
                    if item.item_type == "banco_credito":
                        rate = (sal / 220 * 1.6) if sal else 0
                        if rate > 0:
                            paid_minutes += int(float(item.amount) / rate * 60)
                    elif item.item_type == "banco_desconto":
                        rate = sal / 220 if sal else 0
                        if rate > 0:
                            deducted_minutes += int(float(item.amount) / rate * 60)
                # Compatibilidade com holerites antigos que usavam flag pay_overtime
                if paid_minutes == 0 and payroll.pay_overtime and payroll.total_overtime_hours:
                    paid_minutes = int(float(payroll.total_overtime_hours) * 60)

            months_data[month] = {
                "balance_minutes":   monthly_delta,
                "paid_minutes":      paid_minutes,
                "deducted_minutes":  deducted_minutes,
            }

        bank = ts_repo.get_hour_bank(db, emp.id)
        result.append({
            "employee_id":           emp.id,
            "name":                  emp.name,
            "months":                months_data,
            "total_balance_minutes": bank.balance_minutes if bank else 0,
        })

    return result


def sync_hour_bank(db: Session, employee_id: int) -> int:
    """
    Recalcula e persiste o banco de horas do zero.
    - Dias normais: delta trabalhado vs esperado
    - Compensar: horas negativas (-expected_minutes)
    - Faltas, recesso, DSR: neutros para o banco
    - HE pagas: debitam o banco
    """
    from app.repositories import payroll as payroll_repo
    from app.models.payroll import PayrollStatus

    emp = emp_repo.get_employee(db, employee_id)
    if not emp:
        return 0

    all_entries = ts_repo.get_all_entries(db, employee_id)
    balance = 0

    for e in all_entries:
        if getattr(e, "is_holiday", False) and not getattr(e, "is_dsr_deducted", False):
            continue
        if e.is_annulled or e.is_medical_certificate:
            continue
        if getattr(e, "is_recess", False) or getattr(e, "is_dsr_deducted", False):
            continue
        if e.is_absence:
            continue

        if getattr(e, "is_compensar", False):
            exp = expected_minutes_for_compensar(e.work_date, emp.is_intern, emp.weekly_hours)
            balance -= exp
        else:
            exp = expected_minutes(e.work_date, emp.is_intern, emp.weekly_hours)
            balance += (e.worked_minutes or 0) - exp

    for p in payroll_repo.list_payrolls_by_employee(db, employee_id):
        if p.status != PayrollStatus.CLOSED:
            continue
        if p.use_hour_bank_for_absences:
            balance -= _month_absence_minutes(all_entries, p.competence_year, p.competence_month, emp)
        # Operações manuais de banco (novos tipos banco_desconto / banco_credito)
        has_banco_item = False
        for item in (p.items or []):
            if item.item_type == "banco_desconto":
                sal = float(p.gross_salary or 0)
                rate = sal / 220 if sal else 0
                if rate > 0:
                    balance += int(float(item.amount) / rate * 60)
                    has_banco_item = True
            elif item.item_type == "banco_credito":
                sal = float(p.gross_salary or 0)
                rate = (sal / 220 * 1.6) if sal else 0
                if rate > 0:
                    balance -= int(float(item.amount) / rate * 60)
                    has_banco_item = True
        # Compatibilidade com holerites antigos que usavam flag pay_overtime
        if not has_banco_item and p.pay_overtime and p.total_overtime_hours:
            balance -= int(float(p.total_overtime_hours) * 60)

    ts_repo.set_hour_bank(db, employee_id, balance)
    return balance


def recalculate_hour_bank(db: Session, employee_id: int, company_id: int) -> dict:
    emp = emp_repo.get_employee(db, employee_id)
    if not emp or emp.company_id != company_id:
        raise HTTPException(status_code=404, detail="Funcionário não encontrado")
    balance = sync_hour_bank(db, employee_id)
    return {
        "employee_id":     employee_id,
        "balance_minutes": balance,
        "balance_hours":   format_minutes(balance),
    }


def recalculate_all_banks(db: Session, company_id: int) -> dict:
    employees = emp_repo.list_active(db, company_id)
    count = 0
    for emp in employees:
        sync_hour_bank(db, emp.id)
        count += 1
    return {"recalculated": count}


def get_hour_bank(db: Session, employee_id: int, company_id: int) -> dict:
    emp = emp_repo.get_employee(db, employee_id)
    if not emp or emp.company_id != company_id:
        raise HTTPException(status_code=404, detail="Funcionário não encontrado")

    bank = ts_repo.get_hour_bank(db, employee_id)
    balance = bank.balance_minutes if bank else 0
    return {
        "employee_id":     employee_id,
        "balance_minutes": balance,
        "balance_hours":   format_minutes(balance),
    }
