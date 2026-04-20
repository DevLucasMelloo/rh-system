from decimal import Decimal
from datetime import date
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.repositories import seamstress as seamstress_repo
from app.repositories import audit_log as audit_repo
from app.schemas.seamstress import (
    SeamstressCreate, SeamstressUpdate,
    SeamstressPaymentCreate, SeamstressPaymentUpdate,
    CloseMonthRequest, MonthReportRead, SeamstressMonthSummary,
)
from app.models.seamstress import Seamstress, SeamstressPayment


def _get_seamstress_or_404(db: Session, seamstress_id: int, company_id: int) -> Seamstress:
    s = seamstress_repo.get_seamstress(db, seamstress_id)
    if not s or s.company_id != company_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Costureira não encontrada")
    return s


def _get_payment_or_404(db: Session, payment_id: int, company_id: int) -> SeamstressPayment:
    p = seamstress_repo.get_payment(db, payment_id)
    if not p:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lançamento não encontrado")
    _get_seamstress_or_404(db, p.seamstress_id, company_id)
    return p


def _to_payment_read(p: SeamstressPayment) -> dict:
    return {
        "id": p.id,
        "seamstress_id": p.seamstress_id,
        "seamstress_name": p.seamstress.name if p.seamstress else None,
        "payment_type": p.payment_type,
        "status": p.status,
        "competence_month": p.competence_month,
        "competence_year": p.competence_year,
        "payment_date": p.payment_date,
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
        "cpf": data.cpf,
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

    if data.payment_type == "mensal":
        if not data.competence_month or not data.competence_year:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Pagamento mensal requer competence_month e competence_year",
            )
        fields = {
            "seamstress_id": seamstress_id,
            "registered_by_id": created_by_id,
            "payment_type": "mensal",
            "status": "pendente",
            "competence_month": data.competence_month,
            "competence_year": data.competence_year,
            "payment_date": None,
            "amount": data.amount,
            "notes": data.notes,
        }
        desc = f"Lançamento mensal R${data.amount:.2f} para '{s.name}' — competência {data.competence_month:02d}/{data.competence_year}"

    else:  # entrega
        if not data.payment_date:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Pagamento na entrega requer payment_date",
            )
        fields = {
            "seamstress_id": seamstress_id,
            "registered_by_id": created_by_id,
            "payment_type": "entrega",
            "status": "pago",
            "competence_month": data.payment_date.month,
            "competence_year": data.payment_date.year,
            "payment_date": data.payment_date,
            "amount": data.amount,
            "notes": data.notes,
        }
        desc = f"Pagamento entrega R${data.amount:.2f} para '{s.name}' em {data.payment_date}"

    payment = seamstress_repo.create_payment(db, fields)
    audit_repo.create_log(
        db, action="seamstress_payment_created", user_id=created_by_id,
        entity="seamstress_payment", entity_id=payment.id,
        description=desc,
    )
    payment.seamstress = s
    return _to_payment_read(payment)


def list_payments_by_seamstress(
    db: Session, seamstress_id: int, company_id: int
) -> list[dict]:
    _get_seamstress_or_404(db, seamstress_id, company_id)
    payments = seamstress_repo.list_payments_by_seamstress(db, seamstress_id)
    for p in payments:
        p.seamstress
    return [_to_payment_read(p) for p in payments]


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


# ── Relatório / Fechamento Mensal ─────────────────────────────────────────────

def get_month_report(
    db: Session, company_id: int, month: int, year: int
) -> MonthReportRead:
    mensais = seamstress_repo.list_mensal_by_competence(db, company_id, month, year)
    entregas = seamstress_repo.list_entrega_by_month(db, company_id, month, year)

    # Agrupa mensais por costureira
    mensal_map: dict[int, list] = {}
    for p in mensais:
        mensal_map.setdefault(p.seamstress_id, []).append(p)

    # Agrupa entregas por costureira
    entrega_map: dict[int, Decimal] = {}
    for p in entregas:
        entrega_map[p.seamstress_id] = entrega_map.get(p.seamstress_id, Decimal(0)) + Decimal(str(p.amount))

    all_ids = set(mensal_map) | set(entrega_map)

    summaries: list[SeamstressMonthSummary] = []
    total_mensal_pendente = Decimal(0)
    total_mensal_pago = Decimal(0)
    total_entrega = Decimal(0)

    for sid in sorted(all_ids):
        payments = mensal_map.get(sid, [])
        mensal_amount = sum(Decimal(str(p.amount)) for p in payments)
        ent_amount = entrega_map.get(sid, Decimal(0))

        # Status do mês: pendente se houver qualquer mensal pendente
        st = "pago"
        pay_date = None
        for p in payments:
            if p.status == "pendente":
                st = "pendente"
                break
            else:
                pay_date = p.payment_date

        seamstress_name = payments[0].seamstress.name if payments else (
            # busca pelo entrega
            next((p.seamstress.name for p in entregas if p.seamstress_id == sid), str(sid))
        )

        if st == "pendente":
            total_mensal_pendente += mensal_amount
        else:
            total_mensal_pago += mensal_amount
        total_entrega += ent_amount

        if mensal_amount or ent_amount:
            summaries.append(SeamstressMonthSummary(
                seamstress_id=sid,
                seamstress_name=seamstress_name,
                mensal_amount=mensal_amount,
                entrega_amount=ent_amount,
                status=st,
                payment_date=pay_date,
            ))

    # Força carregamento dos relacionamentos
    for p in mensais + entregas:
        _ = p.seamstress

    return MonthReportRead(
        competence_month=month,
        competence_year=year,
        seamstresses=summaries,
        total_mensal_pendente=total_mensal_pendente,
        total_mensal_pago=total_mensal_pago,
        total_entrega=total_entrega,
        total_geral=total_mensal_pendente + total_mensal_pago + total_entrega,
    )


def close_month(
    db: Session, company_id: int, data: CloseMonthRequest, closed_by_id: int
) -> dict:
    count = seamstress_repo.close_month(
        db, company_id, data.competence_month, data.competence_year, data.payment_date
    )
    if count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nenhum lançamento mensal pendente encontrado para essa competência",
        )
    audit_repo.create_log(
        db, action="seamstress_month_closed", user_id=closed_by_id,
        entity="seamstress_payment", entity_id=0,
        description=f"Fechamento {data.competence_month:02d}/{data.competence_year} — {count} costureira(s) pagas em {data.payment_date}",
    )
    return {"closed": count, "payment_date": data.payment_date}


