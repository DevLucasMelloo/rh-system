from pydantic import BaseModel, EmailStr, field_validator
import re


def _validate_cnpj(cnpj: str) -> str:
    digits = re.sub(r"\D", "", cnpj)
    if len(digits) != 14:
        raise ValueError("CNPJ deve ter 14 dígitos")
    return f"{digits[:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:]}"


class CompanyCreate(BaseModel):
    razao_social: str
    cnpj: str
    email: EmailStr
    telefone: str | None = None
    endereco: str | None = None
    cidade: str | None = None
    estado: str | None = None
    cep: str | None = None

    @field_validator("cnpj")
    @classmethod
    def cnpj_format(cls, v: str) -> str:
        return _validate_cnpj(v)

    @field_validator("estado")
    @classmethod
    def estado_uf(cls, v: str | None) -> str | None:
        if v and len(v) != 2:
            raise ValueError("Estado deve ser a sigla UF com 2 letras")
        return v.upper() if v else v


class CompanyUpdate(BaseModel):
    razao_social: str | None = None
    email: EmailStr | None = None
    telefone: str | None = None
    endereco: str | None = None
    cidade: str | None = None
    estado: str | None = None
    cep: str | None = None
    vt_valor_diario: str | None = None
    dia_pagamento: int | None = None

    @field_validator("dia_pagamento")
    @classmethod
    def dia_valido(cls, v: int | None) -> int | None:
        if v is not None and not (1 <= v <= 28):
            raise ValueError("Dia de pagamento deve estar entre 1 e 28")
        return v


class CompanyRead(BaseModel):
    id: int
    razao_social: str
    cnpj: str
    email: str
    telefone: str | None
    endereco: str | None
    cidade: str | None
    estado: str | None
    cep: str | None
    vt_valor_diario: str
    dia_pagamento: int

    model_config = {"from_attributes": True}
