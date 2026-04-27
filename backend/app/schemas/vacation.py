from datetime import date
from decimal import Decimal
from pydantic import BaseModel, field_validator
from app.models.vacation import VacationStatus, VacationItemType
from app.models.termination import TerminationReason


# ── Itens de Férias ───────────────────────────────────────────────────────────

class VacationItemCreate(BaseModel):
    item_type: VacationItemType
    description: str
    value: Decimal

class VacationItemUpdate(BaseModel):
    item_type: VacationItemType | None = None
    description: str | None = None
    value: Decimal | None = None

class VacationItemRead(BaseModel):
    id: int
    vacation_id: int
    item_type: VacationItemType
    description: str
    value: Decimal
    model_config = {"from_attributes": True}


# ── Férias ────────────────────────────────────────────────────────────────────

class VacationCreate(BaseModel):
    employee_id:       int
    acquisition_start: date
    acquisition_end:   date
    enjoyment_start:   date | None = None
    enjoyment_days:    int         = 30
    sell_all_days:     bool        = False
    abono_days:        int         = 0
    is_fractioned:     bool        = False
    notes:             str | None  = None
    # Valores manuais (sobrepõem o cálculo automático)
    base_salary:       Decimal | None = None
    one_third_bonus:   Decimal | None = None
    inss_discount:     Decimal | None = None

    @field_validator("enjoyment_days")
    @classmethod
    def days_valid(cls, v: int) -> int:
        if v != 0 and not (5 <= v <= 30):
            raise ValueError("Dias de férias deve ser entre 5 e 30 (ou 0 para venda total)")
        return v


class VacationUpdate(BaseModel):
    acquisition_start: date | None = None
    acquisition_end:   date | None = None
    enjoyment_start:   date | None = None
    enjoyment_days:    int | None  = None
    sell_all_days:     bool | None = None
    abono_days:        int | None  = None
    notes:             str | None  = None
    base_salary:       Decimal | None = None
    one_third_bonus:   Decimal | None = None
    inss_discount:     Decimal | None = None


class VacationStart(BaseModel):
    enjoyment_start: date


class VacationPreviewRequest(BaseModel):
    employee_id:   int
    enjoyment_days: int = 30
    sell_all_days:  bool = False
    abono_days:     int  = 0


class VacationPeriodInfo(BaseModel):
    period_number:   int
    acq_start:       date
    acq_end:         date
    concessivo_end:  date
    is_overdue:      bool


class VacationEligibilityRead(BaseModel):
    employee_id:        int
    employee_name:      str
    registration_date:  date
    months_registered:  int
    is_eligible:        bool
    unclaimed_periods:  int
    overdue_periods:    int
    salary:             Decimal
    available_periods:  list[VacationPeriodInfo] = []


class VacationPreviewRead(BaseModel):
    employee_id:     int
    enjoyment_days:  int
    sell_all_days:   bool
    abono_days:      int = 0
    total_paid_days: int = 30
    base_salary:     Decimal
    one_third_bonus: Decimal
    inss_discount:   Decimal
    net_vacation_pay: Decimal


class VacationRead(BaseModel):
    id:               int
    employee_id:      int
    employee_name:    str | None  = None
    registration_date: date | None = None
    acquisition_start: date
    acquisition_end:  date
    enjoyment_start:  date | None
    enjoyment_days:   int
    sell_all_days:    bool = False
    abono_days:       int  = 0
    is_fractioned:    bool
    base_salary:      Decimal | None
    one_third_bonus:  Decimal | None
    inss_discount:    Decimal | None
    net_vacation_pay: Decimal | None
    status:           VacationStatus
    notes:            str | None
    items:            list[VacationItemRead] = []

    model_config = {"from_attributes": True}


# ── Visão geral por empresa ───────────────────────────────────────────────────

class VacationOverviewEmployee(BaseModel):
    employee_id:       int
    employee_name:     str
    registration_date: date
    months_registered: int
    vacation_status:   str   # "vencida" | "agendada" | "disponivel" | "regular" | "inelegivel"
    vencimento:        date | None = None
    scheduled_start:   date | None = None
    scheduled_end:     date | None = None
    scheduled_days:    int  | None = None
    sell_all_days:     bool        = False
    unclaimed_periods: int
    overdue_periods:   int
    is_eligible:       bool


# ── 13º Salário ───────────────────────────────────────────────────────────────

class ThirteenthRead(BaseModel):
    employee_id:      int
    employee_name:    str
    year:             int
    parcela:          int
    worked_months:    int
    bruto_13:         Decimal
    inss:             Decimal
    primeira_parcela: Decimal
    liquido:          Decimal


# ── Rescisão ──────────────────────────────────────────────────────────────────

class TerminationCreate(BaseModel):
    employee_id:       int
    termination_date:  date
    reason:            TerminationReason
    notice_worked:     bool       = False
    notice_start_date: date | None = None   # início do aviso prévio (se trabalhado)
    notice_reduction:  str | None = None    # "2h_dia" | "7_dias" (sem justa causa trabalhado)
    notes:             str | None = None


class TerminationUpdate(BaseModel):
    notice_start_date:       date    | None = None
    notice_worked:           bool    | None = None
    saldo_salario:           Decimal | None = None
    ferias_proporcionais:    Decimal | None = None
    um_terco_ferias_prop:    Decimal | None = None
    ferias_vencidas:         Decimal | None = None
    um_terco_ferias_venc:    Decimal | None = None
    decimo_terceiro_prop:    Decimal | None = None
    aviso_previo_indenizado: Decimal | None = None
    aviso_previo_desconto:   Decimal | None = None
    multa_fgts:              Decimal | None = None
    inss_rescisao:           Decimal | None = None
    notes:                   str     | None = None


class TerminationRead(BaseModel):
    id:                     int
    employee_id:            int
    employee_name:          str | None = None
    termination_date:       date
    reason:                 TerminationReason
    notice_days:            int
    notice_worked:          bool
    notice_start_date:      date | None = None
    notice_end_date:        date | None = None   # computed: notice_start_date + notice_days
    notice_reduction:       str  | None = None   # "2h_dia" | "7_dias"
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
    status:                 str
    notes:                  str | None
    saldo_dias:             int     = 0
    ferias_meses_prop:      int     = 0
    ferias_meses_venc:      int     = 0
    decimo_meses:           int     = 0
    decimo_ja_pago:         Decimal = Decimal("0")

    model_config = {"from_attributes": True}
