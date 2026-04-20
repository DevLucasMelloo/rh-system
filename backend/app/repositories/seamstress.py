from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import date

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


def list_payments_by_seamstress(db: Session, seamstress_id: int) -> list[SeamstressPayment]:
    return (
        db.query(SeamstressPayment)
        .filter(SeamstressPayment.seamstress_id == seamstress_id)
        .order_by(SeamstressPayment.created_at.desc())
        .all()
    )


def list_mensal_by_competence(
    db: Session, company_id: int, month: int, year: int
) -> list[SeamstressPayment]:
    """Pagamentos mensais de uma competência (pendentes ou pagos)."""
    return (
        db.query(SeamstressPayment)
        .join(Seamstress)
        .filter(
            Seamstress.company_id == company_id,
            SeamstressPayment.payment_type == "mensal",
            SeamstressPayment.competence_month == month,
            SeamstressPayment.competence_year == year,
        )
        .all()
    )


def list_entrega_by_month(
    db: Session, company_id: int, month: int, year: int
) -> list[SeamstressPayment]:
    """Pagamentos na entrega com payment_date dentro do mês."""
    from sqlalchemy import extract
    return (
        db.query(SeamstressPayment)
        .join(Seamstress)
        .filter(
            Seamstress.company_id == company_id,
            SeamstressPayment.payment_type == "entrega",
            extract("month", SeamstressPayment.payment_date) == month,
            extract("year", SeamstressPayment.payment_date) == year,
        )
        .all()
    )


def close_month(
    db: Session, company_id: int, month: int, year: int, payment_date: date
) -> int:
    """Marca todos os pagamentos mensais pendentes da competência como pagos. Retorna qtd."""
    payments = (
        db.query(SeamstressPayment)
        .join(Seamstress)
        .filter(
            Seamstress.company_id == company_id,
            SeamstressPayment.payment_type == "mensal",
            SeamstressPayment.status == "pendente",
            SeamstressPayment.competence_month == month,
            SeamstressPayment.competence_year == year,
        )
        .all()
    )
    for p in payments:
        p.status = "pago"
        p.payment_date = payment_date
    db.commit()
    return len(payments)


def month_totals(
    db: Session, company_id: int, month: int, year: int
) -> tuple:
    """Retorna (pendente_mensal, pago_mensal, entrega_mes) para o dashboard."""
    from sqlalchemy import extract
    mensais = (
        db.query(SeamstressPayment)
        .join(Seamstress)
        .filter(
            Seamstress.company_id == company_id,
            SeamstressPayment.payment_type == "mensal",
            SeamstressPayment.competence_month == month,
            SeamstressPayment.competence_year == year,
        )
        .all()
    )
    entrega = (
        db.query(SeamstressPayment)
        .join(Seamstress)
        .filter(
            Seamstress.company_id == company_id,
            SeamstressPayment.payment_type == "entrega",
            extract("month", SeamstressPayment.payment_date) == month,
            extract("year", SeamstressPayment.payment_date) == year,
        )
        .all()
    )
    pendente = sum(p.amount for p in mensais if p.status == "pendente")
    pago     = sum(p.amount for p in mensais if p.status == "pago")
    ent      = sum(p.amount for p in entrega)
    return pendente, pago, ent


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
