from datetime import date
from decimal import Decimal
from pydantic import BaseModel, field_validator
from app.models.vacation import VacationStatus
from app.models.termination import TerminationReason


# ── Férias ────────────────────────────────────────────────────────────────────

class VacationCreate(BaseModel):
    employee_id:      int
    acquisition_start: date
    acquisition_end:  date
    enjoyment_start:  date | None = None
    enjoyment_days:   int         = 30
    is_fractioned:    bool        = False
    notes:            str | None  = None

    @field_validator("enjoyment_days")
    @classmethod
    def days_valid(cls, v: int) -> int:
        if not (5 <= v <= 30):
            raise ValueError("Dias de férias deve ser entre 5 e 30")
        return v


class VacationStart(BaseModel):
    enjoyment_start: date


class VacationRead(BaseModel):
    id:               int
    employee_id:      int
    employee_name:    str | None = None
    acquisition_start: date
    acquisition_end:  date
    enjoyment_start:  date | None
    enjoyment_days:   int
    is_fractioned:    bool
    base_salary:      Decimal | None
    one_third_bonus:  Decimal | None
    inss_discount:    Decimal | None
    net_vacation_pay: Decimal | None
    status:           VacationStatus
    notes:            str | None

    model_config = {"from_attributes": True}


# ── 13º Salário ───────────────────────────────────────────────────────────────

class ThirteenthRead(BaseModel):
    employee_id:      int
    employee_name:    str
    year:             int
    parcela:          int        # 1 ou 2
    worked_months:    int
    bruto_13:         Decimal
    inss:             Decimal
    primeira_parcela: Decimal    # valor da 1ª parcela
    liquido:          Decimal    # líquido da parcela solicitada


# ── Rescisão ──────────────────────────────────────────────────────────────────

class TerminationCreate(BaseModel):
    employee_id:      int
    termination_date: date
    reason:           TerminationReason
    notice_worked:    bool       = False  # aviso trabalhado (True) ou indenizado (False)
    notes:            str | None = None


class TerminationRead(BaseModel):
    id:                     int
    employee_id:            int
    employee_name:          str | None = None
    termination_date:       date
    reason:                 TerminationReason
    notice_days:            int
    notice_worked:          bool
    saldo_salario:          Decimal
    ferias_proporcionais:   Decimal
    um_terco_ferias_prop:   Decimal
    ferias_vencidas:        Decimal
    um_terco_ferias_venc:   Decimal
    decimo_terceiro_prop:   Decimal
    aviso_previo_indenizado: Decimal
    aviso_previo_desconto:  Decimal
    multa_fgts:             Decimal
    inss_rescisao:          Decimal
    total_creditos:         Decimal
    total_descontos:        Decimal
    liquido:                Decimal
    notes:                  str | None

    model_config = {"from_attributes": True}
