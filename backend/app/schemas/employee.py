"""
Schemas de Funcionário.
CPF, RG e conta bancária chegam em texto puro aqui — a criptografia
acontece na camada de serviço antes de salvar no banco.
"""
from datetime import date
from decimal import Decimal
from pydantic import BaseModel, field_validator
import re


def _only_digits(v: str) -> str:
    return re.sub(r"\D", "", v)


def _validate_cpf(cpf: str) -> str:
    digits = _only_digits(cpf)
    if len(digits) != 11:
        raise ValueError("CPF deve ter 11 dígitos")
    if len(set(digits)) == 1:
        raise ValueError("CPF inválido")

    # Validação dos dígitos verificadores
    def _check(d: str, n: int) -> bool:
        total = sum(int(d[i]) * (n - i) for i in range(n - 1))
        rest = (total * 10) % 11
        return rest == 10 or rest == int(d[n - 1])

    if not (_check(digits, 10) and _check(digits, 11)):
        raise ValueError("CPF inválido")

    return f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"


class EmployeeCreate(BaseModel):
    name: str
    cpf: str
    rg: str | None = None
    date_of_birth: date | None = None
    phone: str | None = None
    father_name: str | None = None
    mother_name: str | None = None

    # Endereço
    address: str | None = None
    cep: str | None = None
    city: str | None = None
    state: str | None = None

    # Dados profissionais
    role: str
    salary: Decimal
    admission_date: date
    registration_date: date
    is_intern: bool = False
    weekly_hours: int = 44

    # Dados bancários (texto puro — criptografados no service)
    bank_account: str | None = None
    pix: str | None = None
    bank_name: str | None = None

    @field_validator("cpf")
    @classmethod
    def cpf_valid(cls, v: str) -> str:
        return _validate_cpf(v)

    @field_validator("salary")
    @classmethod
    def salary_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Salário deve ser maior que zero")
        return v

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Nome não pode ser vazio")
        return v.strip()

    @field_validator("weekly_hours")
    @classmethod
    def hours_valid(cls, v: int) -> int:
        if not (1 <= v <= 44):
            raise ValueError("Carga horária semanal deve estar entre 1 e 44 horas")
        return v

    @field_validator("state")
    @classmethod
    def state_uf(cls, v: str | None) -> str | None:
        if v and len(v) != 2:
            raise ValueError("Estado deve ser a sigla UF com 2 letras")
        return v.upper() if v else v


class EmployeeUpdate(BaseModel):
    name: str | None = None
    phone: str | None = None
    date_of_birth: date | None = None
    father_name: str | None = None
    mother_name: str | None = None
    address: str | None = None
    cep: str | None = None
    city: str | None = None
    state: str | None = None
    role: str | None = None
    weekly_hours: int | None = None
    bank_account: str | None = None
    pix: str | None = None
    bank_name: str | None = None
    is_intern: bool | None = None


class SalaryUpdate(BaseModel):
    new_salary: Decimal
    reason: str

    @field_validator("new_salary")
    @classmethod
    def salary_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Salário deve ser maior que zero")
        return v

    @field_validator("reason")
    @classmethod
    def reason_required(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Motivo do reajuste é obrigatório")
        return v.strip()


class InactivateEmployee(BaseModel):
    reason: str

    @field_validator("reason")
    @classmethod
    def reason_required(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Motivo da inativação é obrigatório")
        return v.strip()


class EmployeeHistoryRead(BaseModel):
    id: int
    field_changed: str
    old_value: str | None
    new_value: str | None
    reason: str | None
    changed_at: str
    changed_by_name: str | None = None

    model_config = {"from_attributes": True}


class EmployeeRead(BaseModel):
    id: int
    name: str
    cpf: str           # descriptografado
    rg: str | None
    date_of_birth: date | None
    phone: str | None
    father_name: str | None
    mother_name: str | None
    address: str | None
    cep: str | None
    city: str | None
    state: str | None
    role: str
    salary: Decimal
    admission_date: date
    registration_date: date
    status: str
    is_intern: bool
    weekly_hours: int
    bank_account: str | None  # descriptografado
    pix: str | None           # descriptografado
    bank_name: str | None
    inactivation_date: date | None
    inactivation_reason: str | None

    model_config = {"from_attributes": True}


class EmployeeListItem(BaseModel):
    """Versão resumida para listagem — sem dados sensíveis."""
    id: int
    name: str
    role: str
    salary: Decimal
    admission_date: date
    status: str
    is_intern: bool

    model_config = {"from_attributes": True}
