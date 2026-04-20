from datetime import date
from decimal import Decimal
from pydantic import BaseModel


# ── Dashboard ─────────────────────────────────────────────────────────────────

class BirthdayRead(BaseModel):
    employee_id: int
    name: str
    date_of_birth: date
    days_until: int     # dias até o aniversário (0 = hoje)


class VacationExpiringRead(BaseModel):
    employee_id: int
    employee_name: str
    acquisition_end: date
    days_until_expiry: int
    status: str


class DashboardRead(BaseModel):
    # Funcionários
    total_employees:    int
    active_employees:   int
    inactive_employees: int
    new_hires_30_days:  int

    # Folha do mês atual
    current_month:      int
    current_year:       int
    payrolls_draft:     int
    payrolls_closed:    int
    total_net_salary:   Decimal   # soma dos salários líquidos fechados no mês

    # Ponto do mês atual
    total_absences_month:      int
    total_overtime_hours_month: Decimal

    # Férias
    vacations_active:       int   # em_gozo
    vacations_scheduled:    int   # agendadas
    vacations_expiring_60d: int   # período aquisitivo vence em até 60 dias

    # Costureiras
    seamstress_pending_month: Decimal   # mensal pendente competência atual
    seamstress_paid_month:    Decimal   # mensal pago competência atual
    seamstress_entrega_month: Decimal   # entregas pagas no mês
    seamstress_total_month:   Decimal   # total geral (pendente + pago + entrega)

    # Listas detalhadas
    birthdays_next_30_days:  list[BirthdayRead]
    expiring_vacations:      list[VacationExpiringRead]
