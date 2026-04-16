from datetime import date
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_

from app.models.employee import Employee, EmployeeStatus, EmployeeHistory


# ── Funcionário ───────────────────────────────────────────────────────────────

def get_employee(db: Session, employee_id: int) -> Employee | None:
    return db.get(Employee, employee_id)


def get_by_cpf_encrypted(db: Session, company_id: int, cpf_encrypted: str) -> Employee | None:
    """Busca por CPF já criptografado (Fernet é não-determinístico — use apenas para unicidade)."""
    # Fernet não é determinístico: mesmo valor gera tokens diferentes.
    # Unicidade de CPF é verificada no service via descriptografia.
    return None  # placeholder — validação feita no service


def list_active(db: Session, company_id: int) -> list[Employee]:
    return (
        db.query(Employee)
        .filter(and_(Employee.company_id == company_id, Employee.status == EmployeeStatus.ACTIVE))
        .order_by(Employee.name)
        .all()
    )


def list_inactive(db: Session, company_id: int) -> list[Employee]:
    return (
        db.query(Employee)
        .filter(and_(Employee.company_id == company_id, Employee.status == EmployeeStatus.INACTIVE))
        .order_by(Employee.name)
        .all()
    )


def list_all(db: Session, company_id: int) -> list[Employee]:
    return (
        db.query(Employee)
        .filter(Employee.company_id == company_id)
        .order_by(Employee.name)
        .all()
    )


def create_employee(db: Session, fields: dict) -> Employee:
    employee = Employee(**fields)
    db.add(employee)
    db.commit()
    db.refresh(employee)
    return employee


def update_employee(db: Session, employee: Employee, fields: dict) -> Employee:
    for key, value in fields.items():
        setattr(employee, key, value)
    db.commit()
    db.refresh(employee)
    return employee


def inactivate(db: Session, employee: Employee, reason: str) -> Employee:
    employee.status = EmployeeStatus.INACTIVE
    employee.inactivation_date = date.today()
    employee.inactivation_reason = reason
    db.commit()
    db.refresh(employee)
    return employee


def reactivate(db: Session, employee: Employee) -> Employee:
    employee.status = EmployeeStatus.ACTIVE
    employee.inactivation_date = None
    employee.inactivation_reason = None
    db.commit()
    db.refresh(employee)
    return employee


# ── Histórico ─────────────────────────────────────────────────────────────────

def add_history(
    db: Session,
    employee_id: int,
    changed_by_id: int | None,
    field_changed: str,
    old_value: str | None,
    new_value: str | None,
    reason: str | None = None,
) -> EmployeeHistory:
    entry = EmployeeHistory(
        employee_id=employee_id,
        changed_by_id=changed_by_id,
        field_changed=field_changed,
        old_value=old_value,
        new_value=new_value,
        reason=reason,
    )
    db.add(entry)
    db.commit()
    return entry


def get_history(db: Session, employee_id: int) -> list[EmployeeHistory]:
    return (
        db.query(EmployeeHistory)
        .options(joinedload(EmployeeHistory.changed_by))
        .filter(EmployeeHistory.employee_id == employee_id)
        .order_by(EmployeeHistory.changed_at.desc())
        .all()
    )
