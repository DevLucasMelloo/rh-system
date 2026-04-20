from datetime import date
from decimal import Decimal
from pydantic import BaseModel, field_validator


class SeamstressCreate(BaseModel):
    name: str
    cpf: str | None = None
    phone: str | None = None
    address: str | None = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Nome não pode ser vazio")
        return v.strip()


class SeamstressUpdate(BaseModel):
    name: str | None = None
    cpf: str | None = None
    phone: str | None = None
    address: str | None = None
    is_active: bool | None = None


class SeamstressRead(BaseModel):
    id: int
    name: str
    cpf: str | None
    phone: str | None
    address: str | None
    is_active: bool

    model_config = {"from_attributes": True}


# ── Pagamentos ────────────────────────────────────────────────────────────────

class SeamstressPaymentCreate(BaseModel):
    payment_type: str = "mensal"           # 'mensal' | 'entrega'
    competence_month: int | None = None    # obrigatório para mensal
    competence_year: int | None = None     # obrigatório para mensal
    payment_date: date | None = None       # obrigatório para entrega
    amount: Decimal
    notes: str | None = None

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Valor deve ser maior que zero")
        return v

    @field_validator("payment_type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v not in ("mensal", "entrega"):
            raise ValueError("Tipo deve ser 'mensal' ou 'entrega'")
        return v


class SeamstressPaymentUpdate(BaseModel):
    amount: Decimal | None = None
    notes: str | None = None

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, v: Decimal | None) -> Decimal | None:
        if v is not None and v <= 0:
            raise ValueError("Valor deve ser maior que zero")
        return v


class SeamstressPaymentRead(BaseModel):
    id: int
    seamstress_id: int
    seamstress_name: str | None = None
    payment_type: str
    status: str
    competence_month: int | None
    competence_year: int | None
    payment_date: date | None
    amount: Decimal
    notes: str | None

    model_config = {"from_attributes": True}


# ── Fechamento mensal ─────────────────────────────────────────────────────────

class CloseMonthRequest(BaseModel):
    competence_month: int
    competence_year: int
    payment_date: date


class SeamstressMonthSummary(BaseModel):
    seamstress_id: int
    seamstress_name: str
    mensal_amount: Decimal     # valor mensal pendente
    entrega_amount: Decimal    # valor entrega pago no mês (informativo)
    status: str                # 'pendente' | 'pago'
    payment_date: date | None


class MonthReportRead(BaseModel):
    competence_month: int
    competence_year: int
    seamstresses: list[SeamstressMonthSummary]
    total_mensal_pendente: Decimal
    total_mensal_pago: Decimal
    total_entrega: Decimal
    total_geral: Decimal
