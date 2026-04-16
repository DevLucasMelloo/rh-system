from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_

from app.models.seamstress import Seamstress, SeamstressPayment


# ── Costureira ────────────────────────────────────────────────────────────────

def get_seamstress(db: Session, seamstress_id: int) -> Seamstress | None:
    return db.get(Seamstress, seamstress_id)


def list_seamstresses(db: Session, company_id: int, active_only: bool = True) -> list[Seamstress]:
    query = db.query(Seamstress).filter(Seamstress.company_id == company_id)
    if active_only:
        query = query.filter(Seamstress.is_active == True)
    return query.order_by(Seamstress.name).all()


def create_seamstress(db: Session, fields: dict) -> Seamstress:
    obj = Seamstress(**fields)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def update_seamstress(db: Session, seamstress: Seamstress, fields: dict) -> Seamstress:
    for k, v in fields.items():
        setattr(seamstress, k, v)
    db.commit()
    db.refresh(seamstress)
    return seamstress


# ── Pagamentos ────────────────────────────────────────────────────────────────

def get_payment(db: Session, payment_id: int) -> SeamstressPayment | None:
    return db.get(SeamstressPayment, payment_id)


def get_payment_by_period(
    db: Session, seamstress_id: int, month: int, year: int
) -> SeamstressPayment | None:
    return (
        db.query(SeamstressPayment)
        .filter(
            and_(
                SeamstressPayment.seamstress_id == seamstress_id,
                SeamstressPayment.competence_month == month,
                SeamstressPayment.competence_year == year,
            )
        )
        .first()
    )


def list_payments_by_seamstress(
    db: Session, seamstress_id: int
) -> list[SeamstressPayment]:
    return (
        db.query(SeamstressPayment)
        .filter(SeamstressPayment.seamstress_id == seamstress_id)
        .order_by(SeamstressPayment.competence_year.desc(), SeamstressPayment.competence_month.desc())
        .all()
    )


def list_payments_by_period(
    db: Session, company_id: int, month: int, year: int
) -> list[SeamstressPayment]:
    """Todos os pagamentos de um mês/ano para a empresa — usado no fechamento mensal."""
    return (
        db.query(SeamstressPayment)
        .join(Seamstress)
        .filter(
            and_(
                Seamstress.company_id == company_id,
                SeamstressPayment.competence_month == month,
                SeamstressPayment.competence_year == year,
            )
        )
        .options(joinedload(SeamstressPayment.seamstress))
        .order_by(Seamstress.name)
        .all()
    )


def create_payment(db: Session, fields: dict) -> SeamstressPayment:
    obj = SeamstressPayment(**fields)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def update_payment(db: Session, payment: SeamstressPayment, fields: dict) -> SeamstressPayment:
    for k, v in fields.items():
        setattr(payment, k, v)
    db.commit()
    db.refresh(payment)
    return payment


def delete_payment(db: Session, payment: SeamstressPayment) -> None:
    db.delete(payment)
    db.commit()
