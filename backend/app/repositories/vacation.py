"""Operações de banco para Férias e Rescisões."""
from sqlalchemy.orm import Session, joinedload

from app.models.vacation import Vacation, VacationStatus
from app.models.termination import Termination


# ── Férias ────────────────────────────────────────────────────────────────────

def get_vacation(db: Session, vacation_id: int) -> Vacation | None:
    return db.get(Vacation, vacation_id)


def list_by_employee(db: Session, employee_id: int) -> list[Vacation]:
    return (
        db.query(Vacation)
        .filter(Vacation.employee_id == employee_id)
        .order_by(Vacation.acquisition_start.desc())
        .all()
    )


def list_active_by_company(db: Session, company_id: int) -> list[Vacation]:
    from app.models.employee import Employee
    return (
        db.query(Vacation)
        .join(Employee)
        .filter(
            Employee.company_id == company_id,
            Vacation.status.in_([VacationStatus.SCHEDULED, VacationStatus.ACTIVE]),
        )
        .order_by(Vacation.acquisition_end)
        .all()
    )


def count_completed_by_employee(db: Session, employee_id: int) -> int:
    return (
        db.query(Vacation)
        .filter(
            Vacation.employee_id == employee_id,
            Vacation.status == VacationStatus.COMPLETED,
        )
        .count()
    )


def has_overlapping_acquisition(
    db: Session,
    employee_id: int,
    acquisition_start,
    acquisition_end,
    exclude_id: int | None = None,
) -> bool:
    q = db.query(Vacation).filter(
        Vacation.employee_id == employee_id,
        Vacation.status != VacationStatus.CANCELLED,
        Vacation.acquisition_start <= acquisition_end,
        Vacation.acquisition_end >= acquisition_start,
    )
    if exclude_id:
        q = q.filter(Vacation.id != exclude_id)
    return q.first() is not None


def create_vacation(db: Session, data: dict) -> Vacation:
    vac = Vacation(**data)
    db.add(vac)
    db.commit()
    db.refresh(vac)
    return vac


def update_vacation(db: Session, vac: Vacation, data: dict) -> Vacation:
    for k, v in data.items():
        setattr(vac, k, v)
    db.commit()
    db.refresh(vac)
    return vac


# ── Rescisão ──────────────────────────────────────────────────────────────────

def get_termination(db: Session, termination_id: int) -> Termination | None:
    return db.get(Termination, termination_id)


def get_termination_by_employee(db: Session, employee_id: int) -> Termination | None:
    return (
        db.query(Termination)
        .filter(Termination.employee_id == employee_id)
        .first()
    )


def create_termination(db: Session, data: dict) -> Termination:
    term = Termination(**data)
    db.add(term)
    db.commit()
    db.refresh(term)
    return term
