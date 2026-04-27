from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.models.thirteenth import ThirteenthSalary, ThirteenthStatus


def get_by_employee_year_parcela(db: Session, employee_id: int, year: int, parcela: int):
    return (
        db.query(ThirteenthSalary)
        .filter_by(employee_id=employee_id, year=year, parcela=parcela)
        .first()
    )


def create_or_update(db: Session, data: dict) -> ThirteenthSalary:
    existing = get_by_employee_year_parcela(
        db, data["employee_id"], data["year"], data["parcela"]
    )
    if existing:
        for k, v in data.items():
            setattr(existing, k, v)
        db.commit()
        db.refresh(existing)
        return existing
    rec = ThirteenthSalary(**data)
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec


def list_by_company(db: Session, company_id: int, year: int | None = None, parcela: int | None = None):
    from app.models.employee import Employee
    q = (
        db.query(ThirteenthSalary)
        .join(Employee, ThirteenthSalary.employee_id == Employee.id)
        .filter(Employee.company_id == company_id)
    )
    if year:
        q = q.filter(ThirteenthSalary.year == year)
    if parcela:
        q = q.filter(ThirteenthSalary.parcela == parcela)
    return q.order_by(desc(ThirteenthSalary.year), ThirteenthSalary.parcela).all()


def get_by_id(db: Session, rec_id: int) -> ThirteenthSalary | None:
    return db.query(ThirteenthSalary).filter_by(id=rec_id).first()


def delete(db: Session, rec: ThirteenthSalary) -> None:
    db.delete(rec)
    db.commit()


def mark_paid(db: Session, rec: ThirteenthSalary) -> ThirteenthSalary:
    rec.status = ThirteenthStatus.PAGO
    db.commit()
    db.refresh(rec)
    return rec
