from decimal import Decimal
from pydantic import BaseModel, field_validator


class SeamstressCreate(BaseModel):
    name: str
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
    phone: str | None = None
    address: str | None = None
    is_active: bool | None = None


class SeamstressRead(BaseModel):
    id: int
    name: str
    phone: str | None
    address: str | None
    is_active: bool

    model_config = {"from_attributes": True}


class SeamstressPaymentCreate(BaseModel):
    competence_month: int
    competence_year: int
    amount: Decimal
    notes: str | None = None

    @field_validator("competence_month")
    @classmethod
    def month_valid(cls, v: int) -> int:
        if not (1 <= v <= 12):
            raise ValueError("Mês deve estar entre 1 e 12")
        return v

    @field_validator("competence_year")
    @classmethod
    def year_valid(cls, v: int) -> int:
        if not (2000 <= v <= 2100):
            raise ValueError("Ano inválido")
        return v

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Valor deve ser maior que zero")
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
    competence_month: int
    competence_year: int
    amount: Decimal
    notes: str | None

    model_config = {"from_attributes": True}
