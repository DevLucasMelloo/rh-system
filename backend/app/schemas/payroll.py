from datetime import date
from decimal import Decimal
from pydantic import BaseModel, field_validator
from app.models.payroll import PayrollItemType, PayrollStatus


class ValeCreate(BaseModel):
    total_amount: Decimal
    installments: int = 1
    notes: str | None = None
    issued_date: date

    @field_validator("total_amount")
    @classmethod
    def amount_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Valor deve ser maior que zero")
        return v

    @field_validator("installments")
    @classmethod
    def installments_valid(cls, v: int) -> int:
        if not (1 <= v <= 24):
            raise ValueError("Parcelamento entre 1 e 24 vezes")
        return v


class ValeInstallmentRead(BaseModel):
    id: int
    installment_number: int
    amount: Decimal
    due_month: int
    due_year: int
    is_paid: bool

    model_config = {"from_attributes": True}


class ValeRead(BaseModel):
    id: int
    employee_id: int
    total_amount: Decimal
    installments: int
    notes: str | None
    issued_date: date
    installment_items: list[ValeInstallmentRead]

    model_config = {"from_attributes": True}


class PayrollItemCreate(BaseModel):
    item_type: PayrollItemType
    description: str
    amount: Decimal
    is_credit: bool
    notes: str | None = None
    show_on_payslip: bool = True

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, v: Decimal) -> Decimal:
        if v < 0:
            raise ValueError("Valor não pode ser negativo")
        return v


class PayrollItemUpdate(BaseModel):
    amount: Decimal | None = None
    description: str | None = None
    notes: str | None = None
    show_on_payslip: bool | None = None


class PayrollCreate(BaseModel):
    employee_id: int
    competence_month: int
    competence_year: int

    @field_validator("competence_month")
    @classmethod
    def month_valid(cls, v: int) -> int:
        if not (1 <= v <= 12):
            raise ValueError("Mês deve estar entre 1 e 12")
        return v


class PayrollItemRead(BaseModel):
    id: int
    item_type: str
    description: str
    amount: Decimal
    is_credit: bool
    is_manual: bool
    notes: str | None
    show_on_payslip: bool

    model_config = {"from_attributes": True}


class PayrollRead(BaseModel):
    id: int
    employee_id: int
    employee_name: str | None = None
    competence_month: int
    competence_year: int
    payment_date: date | None
    gross_salary: Decimal
    total_benefits: Decimal
    total_discounts: Decimal
    net_salary: Decimal
    worked_days: int
    total_overtime_hours: Decimal
    status: str
    pdf_path: str | None
    items: list[PayrollItemRead]

    model_config = {"from_attributes": True}
