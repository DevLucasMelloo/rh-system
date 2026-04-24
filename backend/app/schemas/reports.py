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
    total_net_salary:   Decimal

    # Férias
    vacations_active:       int
    vacations_scheduled:    int
    vacations_expiring_60d: int

    # Costureiras
    seamstress_pending_month: Decimal
    seamstress_paid_month:    Decimal
    seamstress_entrega_month: Decimal
    seamstress_total_month:   Decimal

    # Custo total do mês (folha + costureiras)
    custo_total_month: Decimal

    # Listas detalhadas
    birthdays_next_30_days:  list[BirthdayRead]
    expiring_vacations:      list[VacationExpiringRead]


# ── Folha Anual por Funcionário ───────────────────────────────────────────────

class AnnualEmployeeMonth(BaseModel):
    month: int
    net_salary: Decimal | None = None
    is_salary_increase: bool = False  # salário maior que mês anterior


class AnnualEmployeeRow(BaseModel):
    employee_id: int
    name:        str
    months:      list[AnnualEmployeeMonth]  # 12 items, Jan-Dez


class AnnualPayrollRead(BaseModel):
    year:      int
    employees: list[AnnualEmployeeRow]
