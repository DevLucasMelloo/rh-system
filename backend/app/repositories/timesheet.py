from datetime import date, datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, extract

from app.models.timesheet import TimesheetEntry, HourBank, TimesheetPeriod


# ── Entradas de ponto ─────────────────────────────────────────────────────────

def get_entry(db: Session, entry_id: int) -> TimesheetEntry | None:
    return db.get(TimesheetEntry, entry_id)


def get_entry_by_date(db: Session, employee_id: int, work_date: date) -> TimesheetEntry | None:
    return (
        db.query(TimesheetEntry)
        .filter(
            and_(
                TimesheetEntry.employee_id == employee_id,
                TimesheetEntry.work_date == work_date,
            )
        )
        .first()
    )


def list_entries_by_month(
    db: Session, employee_id: int, month: int, year: int
) -> list[TimesheetEntry]:
    return (
        db.query(TimesheetEntry)
        .filter(
            and_(
                TimesheetEntry.employee_id == employee_id,
                extract("month", TimesheetEntry.work_date) == month,
                extract("year", TimesheetEntry.work_date) == year,
            )
        )
        .order_by(TimesheetEntry.work_date)
        .all()
    )


def create_entry(db: Session, fields: dict) -> TimesheetEntry:
    entry = TimesheetEntry(**fields)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def update_entry(db: Session, entry: TimesheetEntry, fields: dict) -> TimesheetEntry:
    for k, v in fields.items():
        setattr(entry, k, v)
    db.commit()
    db.refresh(entry)
    return entry


def delete_entry(db: Session, entry: TimesheetEntry) -> None:
    db.delete(entry)
    db.commit()


# ── Banco de horas ────────────────────────────────────────────────────────────

def get_hour_bank(db: Session, employee_id: int) -> HourBank | None:
    return (
        db.query(HourBank)
        .filter(HourBank.employee_id == employee_id)
        .first()
    )


def upsert_hour_bank(db: Session, employee_id: int, delta: int) -> HourBank:
    """Cria ou atualiza o banco de horas somando o delta."""
    bank = get_hour_bank(db, employee_id)
    if bank:
        bank.balance_minutes += delta
        db.commit()
        db.refresh(bank)
    else:
        bank = HourBank(employee_id=employee_id, balance_minutes=delta)
        db.add(bank)
        db.commit()
        db.refresh(bank)
    return bank


def get_all_entries(db: Session, employee_id: int) -> list[TimesheetEntry]:
    return (
        db.query(TimesheetEntry)
        .filter(TimesheetEntry.employee_id == employee_id)
        .order_by(TimesheetEntry.work_date)
        .all()
    )


def get_entries_range(
    db: Session, employee_id: int, start: date, end: date
) -> list[TimesheetEntry]:
    return (
        db.query(TimesheetEntry)
        .filter(
            TimesheetEntry.employee_id == employee_id,
            TimesheetEntry.work_date >= start,
            TimesheetEntry.work_date <= end,
        )
        .order_by(TimesheetEntry.work_date)
        .all()
    )


# ── Períodos ──────────────────────────────────────────────────────────────────

def get_period(
    db: Session, company_id: int, month: int, year: int
) -> TimesheetPeriod | None:
    return (
        db.query(TimesheetPeriod)
        .filter(
            TimesheetPeriod.company_id == company_id,
            TimesheetPeriod.competence_month == month,
            TimesheetPeriod.competence_year == year,
        )
        .first()
    )


def create_period(db: Session, fields: dict) -> TimesheetPeriod:
    p = TimesheetPeriod(**fields)
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def close_period(
    db: Session, period: TimesheetPeriod, closed_by_id: int
) -> TimesheetPeriod:
    period.status = "closed"
    period.closed_at = datetime.utcnow()
    period.closed_by_id = closed_by_id
    db.commit()
    db.refresh(period)
    return period


def set_hour_bank(db: Session, employee_id: int, balance: int) -> HourBank:
    """Define o saldo absoluto do banco (usado ao recalcular um dia já registrado)."""
    bank = get_hour_bank(db, employee_id)
    if bank:
        bank.balance_minutes = balance
        db.commit()
        db.refresh(bank)
    else:
        bank = HourBank(employee_id=employee_id, balance_minutes=balance)
        db.add(bank)
        db.commit()
        db.refresh(bank)
    return bank
