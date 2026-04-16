"""
Serviço de Costureiras.
O cálculo do valor é feito externamente — o sistema apenas registra o valor final.
Regra: só pode haver um lançamento por costureira por mês/ano.
"""
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.repositories import seamstress as seamstress_repo
from app.repositories import audit_log as audit_repo
from app.schemas.seamstress import (
    SeamstressCreate, SeamstressUpdate,
    SeamstressPaymentCreate, SeamstressPaymentUpdate,
)
from app.models.seamstress import Seamstress, SeamstressPayment


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_seamstress_or_404(db: Session, seamstress_id: int, company_id: int) -> Seamstress:
    s = seamstress_repo.get_seamstress(db, seamstress_id)
    if not s or s.company_id != company_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Costureira não encontrada")
    return s


def _get_payment_or_404(
    db: Session, payment_id: int, company_id: int
) -> SeamstressPayment:
    p = seamstress_repo.get_payment(db, payment_id)
    if not p:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lançamento não encontrado")
    # Valida que pertence à empresa
    _get_seamstress_or_404(db, p.seamstress_id, company_id)
    return p


def _to_payment_read(p: SeamstressPayment) -> dict:
    return {
        "id": p.id,
        "seamstress_id": p.seamstress_id,
        "seamstress_name": p.seamstress.name if p.seamstress else None,
        "competence_month": p.competence_month,
        "competence_year": p.competence_year,
        "amount": p.amount,
        "notes": p.notes,
    }


# ── Costureira CRUD ───────────────────────────────────────────────────────────

def create_seamstress(
    db: Session, data: SeamstressCreate, company_id: int, created_by_id: int
) -> Seamstress:
    s = seamstress_repo.create_seamstress(db, {
        "company_id": company_id,
        "name": data.name,
        "phone": data.phone,
        "address": data.address,
    })
    audit_repo.create_log(
        db, action="seamstress_created", user_id=created_by_id,
        entity="seamstress", entity_id=s.id,
        description=f"Costureira '{s.name}' cadastrada",
    )
    return s


def list_seamstresses(db: Session, company_id: int, active_only: bool = True) -> list[Seamstress]:
    return seamstress_repo.list_seamstresses(db, company_id, active_only)


def get_seamstress(db: Session, seamstress_id: int, company_id: int) -> Seamstress:
    return _get_seamstress_or_404(db, seamstress_id, company_id)


def update_seamstress(
    db: Session, seamstress_id: int, data: SeamstressUpdate,
    company_id: int, updated_by_id: int
) -> Seamstress:
    s = _get_seamstress_or_404(db, seamstress_id, company_id)
    fields = data.model_dump(exclude_none=True)
    if not fields:
        return s
    updated = seamstress_repo.update_seamstress(db, s, fields)
    audit_repo.create_log(
        db, action="seamstress_updated", user_id=updated_by_id,
        entity="seamstress", entity_id=s.id,
        description=f"Costureira '{s.name}' atualizada",
    )
    return updated


# ── Pagamentos ────────────────────────────────────────────────────────────────

def add_payment(
    db: Session, seamstress_id: int, data: SeamstressPaymentCreate,
    company_id: int, created_by_id: int
) -> dict:
    s = _get_seamstress_or_404(db, seamstress_id, company_id)

    if not s.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Costureira inativa — reative antes de lançar pagamento",
        )

    # Regra: apenas um lançamento por costureira por mês/ano
    existing = seamstress_repo.get_payment_by_period(
        db, seamstress_id, data.competence_month, data.competence_year
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Já existe lançamento para {data.competence_month:02d}/{data.competence_year}. Use PATCH para editar.",
        )

    payment = seamstress_repo.create_payment(db, {
        "seamstress_id": seamstress_id,
        "registered_by_id": created_by_id,
        "competence_month": data.competence_month,
        "competence_year": data.competence_year,
        "amount": data.amount,
        "notes": data.notes,
    })

    audit_repo.create_log(
        db, action="seamstress_payment_created", user_id=created_by_id,
        entity="seamstress_payment", entity_id=payment.id,
        description=f"Lançamento R${data.amount:.2f} para '{s.name}' em {data.competence_month:02d}/{data.competence_year}",
    )

    # Carrega relacionamento para retornar nome
    payment.seamstress = s
    return _to_payment_read(payment)


def update_payment(
    db: Session, payment_id: int, data: SeamstressPaymentUpdate,
    company_id: int, updated_by_id: int
) -> dict:
    p = _get_payment_or_404(db, payment_id, company_id)
    fields = data.model_dump(exclude_none=True)
    if not fields:
        p.seamstress  # força carregamento do relacionamento
        return _to_payment_read(p)

    updated = seamstress_repo.update_payment(db, p, fields)
    audit_repo.create_log(
        db, action="seamstress_payment_updated", user_id=updated_by_id,
        entity="seamstress_payment", entity_id=payment_id,
        description=f"Lançamento #{payment_id} atualizado",
    )
    updated.seamstress  # força carregamento
    return _to_payment_read(updated)


def delete_payment(
    db: Session, payment_id: int, company_id: int, deleted_by_id: int
) -> None:
    p = _get_payment_or_404(db, payment_id, company_id)
    seamstress_name = p.seamstress.name
    seamstress_repo.delete_payment(db, p)
    audit_repo.create_log(
        db, action="seamstress_payment_deleted", user_id=deleted_by_id,
        entity="seamstress_payment", entity_id=payment_id,
        description=f"Lançamento #{payment_id} de '{seamstress_name}' removido",
    )


def list_payments_by_seamstress(
    db: Session, seamstress_id: int, company_id: int
) -> list[dict]:
    _get_seamstress_or_404(db, seamstress_id, company_id)
    payments = seamstress_repo.list_payments_by_seamstress(db, seamstress_id)
    for p in payments:
        p.seamstress  # força carregamento
    return [_to_payment_read(p) for p in payments]


def list_payments_by_period(
    db: Session, company_id: int, month: int, year: int
) -> list[dict]:
    payments = seamstress_repo.list_payments_by_period(db, company_id, month, year)
    return [_to_payment_read(p) for p in payments]


def get_period_total(db: Session, company_id: int, month: int, year: int) -> dict:
    """Total a pagar para todas as costureiras em um mês."""
    payments = seamstress_repo.list_payments_by_period(db, company_id, month, year)
    total = sum(p.amount for p in payments)
    return {
        "month": month,
        "year": year,
        "total": total,
        "count": len(payments),
        "payments": [_to_payment_read(p) for p in payments],
    }
