"""Operações de banco para Férias e Rescisões."""
from sqlalchemy.orm import Session, joinedload

from app.models.vacation import Vacation, VacationStatus, VacationItem
from app.models.termination import Termination


# ── Férias ────────────────────────────────────────────────────────────────────

def get_vacation(db: Session, vacation_id: int) -> Vacation | None:
    return (
        db.query(Vacation)
        .options(joinedload(Vacation.items))
        .filter(Vacation.id == vacation_id)
        .first()
    )


def list_by_employee(db: Session, employee_id: int) -> list[Vacation]:
    return (
        db.query(Vacation)
        .options(joinedload(Vacation.items))
        .filter(Vacation.employee_id == employee_id)
        .order_by(Vacation.acquisition_start.desc())
        .all()
    )


def list_active_by_company(db: Session, company_id: int) -> list[Vacation]:
    from app.models.employee import Employee
    return (
        db.query(Vacation)
        .join(Employee)
        .options(joinedload(Vacation.items))
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


def count_non_cancelled_by_employee(db: Session, employee_id: int) -> int:
    return (
        db.query(Vacation)
        .filter(
            Vacation.employee_id == employee_id,
            Vacation.status != VacationStatus.CANCELLED,
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
    return get_vacation(db, vac.id)


def update_vacation(db: Session, vac: Vacation, data: dict) -> Vacation:
    for k, v in data.items():
        setattr(vac, k, v)
    db.commit()
    db.refresh(vac)
    return get_vacation(db, vac.id)


def delete_vacation(db: Session, vac: Vacation) -> None:
    db.delete(vac)
    db.commit()


# ── Itens de Férias ───────────────────────────────────────────────────────────

def get_vacation_item(db: Session, item_id: int) -> VacationItem | None:
    return db.get(VacationItem, item_id)


def create_vacation_item(db: Session, data: dict) -> VacationItem:
    item = VacationItem(**data)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update_vacation_item(db: Session, item: VacationItem, data: dict) -> VacationItem:
    for k, v in data.items():
        setattr(item, k, v)
    db.commit()
    db.refresh(item)
    return item


def delete_vacation_item(db: Session, item: VacationItem) -> None:
    db.delete(item)
    db.commit()


# ── Rescisão ──────────────────────────────────────────────────────────────────

def get_termination(db: Session, termination_id: int) -> Termination | None:
    return db.get(Termination, termination_id)


def list_terminations(db: Session, company_id: int) -> list[Termination]:
    from app.models.employee import Employee
    return (
        db.query(Termination)
        .join(Employee, Termination.employee_id == Employee.id)
        .filter(Employee.company_id == company_id)
        .order_by(Termination.termination_date.desc())
        .all()
    )


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


def update_termination(db: Session, term: Termination, data: dict) -> Termination:
    for key, value in data.items():
        setattr(term, key, value)
    db.commit()
    db.refresh(term)
    return term
