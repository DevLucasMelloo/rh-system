"""
Serviço de Férias, 13º Salário e Rescisão.
Toda a lógica de negócio fica aqui.
"""
import calendar
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.repositories import vacation as vac_repo
from app.repositories import employee as emp_repo
from app.repositories import audit_log as audit_repo
from app.models.employee import Employee, EmployeeStatus
from app.models.vacation import Vacation, VacationStatus, VacationItem, VacationItemType
from app.models.termination import Termination, TerminationReason
from app.schemas.vacation import (
    VacationCreate, VacationUpdate, VacationStart,
    VacationItemCreate, VacationItemUpdate,
    TerminationCreate, TerminationUpdate,
)
from app.utils.inss_calc import calc_inss, calc_inss_ferias
from app.utils.payroll_calc import count_worked_months_for_thirteenth, calc_thirteenth_salary


# ── Helpers internos ──────────────────────────────────────────────────────────

def _q2(v: Decimal) -> Decimal:
    return v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _add_months(d: date, months: int) -> date:
    total = d.year * 12 + d.month - 1 + months
    year = total // 12
    month = total % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _get_active_employee(db: Session, employee_id: int, company_id: int) -> Employee:
    emp = emp_repo.get_employee(db, employee_id)
    if not emp or emp.company_id != company_id:
        raise HTTPException(status_code=404, detail="Funcionário não encontrado")
    if emp.status == EmployeeStatus.INACTIVE:
        raise HTTPException(status_code=400, detail="Funcionário inativo")
    return emp


def _get_employee_any_status(db: Session, employee_id: int, company_id: int) -> Employee:
    emp = emp_repo.get_employee(db, employee_id)
    if not emp or emp.company_id != company_id:
        raise HTTPException(status_code=404, detail="Funcionário não encontrado")
    return emp


def _auto_advance_status(db: Session, vac: Vacation) -> Vacation:
    """Avança o status automaticamente com base nas datas."""
    today = date.today()
    if vac.status == VacationStatus.SCHEDULED:
        if vac.sell_all_days:
            # Venda total: sem gozo, pode concluir direto
            pass
        elif vac.enjoyment_start and vac.enjoyment_start <= today:
            vac = vac_repo.update_vacation(db, vac, {"status": VacationStatus.ACTIVE})
    if vac.status == VacationStatus.ACTIVE:
        if vac.sell_all_days:
            vac = vac_repo.update_vacation(db, vac, {"status": VacationStatus.COMPLETED})
        elif vac.enjoyment_start and vac.enjoyment_days:
            end_date = vac.enjoyment_start + timedelta(days=vac.enjoyment_days)
            if end_date <= today:
                vac = vac_repo.update_vacation(db, vac, {"status": VacationStatus.COMPLETED})
    return vac


def _get_vacation_or_404(db: Session, vacation_id: int, company_id: int) -> Vacation:
    vac = vac_repo.get_vacation(db, vacation_id)
    if not vac:
        raise HTTPException(status_code=404, detail="Férias não encontrada")
    emp = emp_repo.get_employee(db, vac.employee_id)
    if not emp or emp.company_id != company_id:
        raise HTTPException(status_code=404, detail="Férias não encontrada")
    return _auto_advance_status(db, vac)


def _months_registered(reg_date: date) -> int:
    today = date.today()
    return (today.year - reg_date.year) * 12 + (today.month - reg_date.month)


def _recalc_net(base: Decimal, one_third: Decimal, inss: Decimal, items: list) -> Decimal:
    extra = sum(
        i.value if i.item_type == VacationItemType.CREDIT else -i.value
        for i in items
    )
    return _q2(base + one_third - inss + Decimal(str(extra)))


# ── Cálculos puros ────────────────────────────────────────────────────────────

def calc_vacation_pay(salary: Decimal, days: int) -> dict:
    """
    base = salário × dias/30
    1/3  = base / 3
    INSS = progressivo sobre base (tabela férias)
    líquido = base + 1/3 - INSS
    """
    paid_days = days if days > 0 else 30  # venda total usa 30 dias para cálculo
    base      = _q2(salary * Decimal(paid_days) / Decimal("30"))
    one_third = _q2(base / Decimal("3"))
    inss      = calc_inss_ferias(base)
    net       = _q2(base + one_third - inss)
    return {
        "base_salary":      base,
        "one_third_bonus":  one_third,
        "inss_discount":    inss,
        "net_vacation_pay": net,
    }


# ── Elegibilidade ─────────────────────────────────────────────────────────────

def get_eligibility(db: Session, employee_id: int, company_id: int) -> dict:
    """
    Calcula elegibilidade e períodos disponíveis.

    Regra CLT:
      - Período aquisitivo: 12 meses a partir do registro (meses 0-12, 12-24, ...)
      - Período concessivo: 12 meses após o aquisitivo (meses 12-24, 24-36, ...)
      - Férias vencidas: período cujo concessivo já encerrou sem gozo (> 24 meses sem férias)
      - A contagem usa a data de registro, não a de admissão.
    """
    emp = _get_employee_any_status(db, employee_id, company_id)
    reg_date = emp.registration_date
    today    = date.today()
    months   = _months_registered(reg_date)

    # Quantos períodos aquisitivos completos já encerraram
    periods_with_acq_ended = months // 12

    # Quantos períodos com concessivo também encerrado (overdue window)
    # Período N (0-indexed) tem concessivo encerrando em (N+2)*12 meses de registro
    # Portanto: overdue se (N+2)*12 <= months → N <= months/12 - 2
    periods_with_conc_ended = max(0, months // 12 - 1)

    # Férias não canceladas já registradas
    vacation_count = vac_repo.count_non_cancelled_by_employee(db, emp.id)

    unclaimed = max(0, periods_with_acq_ended - vacation_count)
    overdue   = max(0, periods_with_conc_ended - vacation_count)

    # Monta lista de períodos disponíveis para agendamento
    available_periods = []
    for n in range(vacation_count, periods_with_acq_ended):
        acq_start     = _add_months(reg_date, n * 12)
        acq_end       = _add_months(reg_date, (n + 1) * 12) - timedelta(days=1)
        conc_end      = _add_months(reg_date, (n + 2) * 12)
        is_overdue    = today >= conc_end
        available_periods.append({
            "period_number": n + 1,
            "acq_start":     acq_start,
            "acq_end":       acq_end,
            "concessivo_end": conc_end,
            "is_overdue":    is_overdue,
        })

    return {
        "employee_id":       emp.id,
        "employee_name":     emp.name,
        "registration_date": reg_date,
        "months_registered": months,
        "is_eligible":       unclaimed > 0,
        "unclaimed_periods": unclaimed,
        "overdue_periods":   overdue,
        "salary":            Decimal(str(emp.salary)),
        "available_periods": available_periods,
    }


def preview_vacation_calc(db: Session, employee_id: int, enjoyment_days: int, sell_all_days: bool, company_id: int, abono_days: int = 0) -> dict:
    emp = _get_employee_any_status(db, employee_id, company_id)
    salary = Decimal(str(emp.salary))
    if sell_all_days:
        total_paid_days = 30
    else:
        total_paid_days = min(30, (enjoyment_days or 30) + (abono_days or 0))
    pay = calc_vacation_pay(salary, total_paid_days)
    return {
        "employee_id":     emp.id,
        "enjoyment_days":  enjoyment_days,
        "sell_all_days":   sell_all_days,
        "abono_days":      abono_days,
        "total_paid_days": total_paid_days,
        **pay,
    }


# ── Férias ────────────────────────────────────────────────────────────────────

def schedule_vacation(
    db: Session,
    data: VacationCreate,
    company_id: int,
    user_id: int,
) -> Vacation:
    emp = _get_active_employee(db, data.employee_id, company_id)

    # Verificar elegibilidade: deve ter pelo menos 1 período aquisitivo completo
    months = _months_registered(emp.registration_date)
    periods_elapsed = months // 12
    vacation_count  = vac_repo.count_non_cancelled_by_employee(db, data.employee_id)
    if periods_elapsed == 0 or vacation_count >= periods_elapsed:
        if months < 12:
            raise HTTPException(
                status_code=400,
                detail=f"Funcionário tem apenas {months} mês(es) de registro. São necessários 12 meses.",
            )
        raise HTTPException(status_code=400, detail="Funcionário não possui períodos de férias disponíveis para agendamento.")

    if vac_repo.has_overlapping_acquisition(
        db, data.employee_id, data.acquisition_start, data.acquisition_end
    ):
        raise HTTPException(
            status_code=409,
            detail="Já existe um período aquisitivo que se sobrepõe ao informado",
        )

    sell_all  = data.sell_all_days
    enj_days  = 0 if sell_all else data.enjoyment_days
    abono_d   = 0 if sell_all else (data.abono_days or 0)
    total_paid = 30 if sell_all else min(30, enj_days + abono_d)

    # Cálculo automático (sobreposto por valores manuais se fornecidos)
    auto = calc_vacation_pay(Decimal(str(emp.salary)), total_paid)
    base      = _q2(data.base_salary)      if data.base_salary      is not None else auto["base_salary"]
    one_third = _q2(data.one_third_bonus)  if data.one_third_bonus  is not None else auto["one_third_bonus"]
    inss      = _q2(data.inss_discount)    if data.inss_discount     is not None else auto["inss_discount"]
    net       = _q2(base + one_third - inss)

    vac = vac_repo.create_vacation(db, {
        "employee_id":       data.employee_id,
        "created_by_id":     user_id,
        "acquisition_start": data.acquisition_start,
        "acquisition_end":   data.acquisition_end,
        "enjoyment_start":   data.enjoyment_start,
        "enjoyment_days":    enj_days,
        "sell_all_days":     sell_all,
        "abono_days":        abono_d,
        "is_fractioned":     data.is_fractioned,
        "notes":             data.notes,
        "status":            VacationStatus.SCHEDULED,
        "base_salary":       base,
        "one_third_bonus":   one_third,
        "inss_discount":     inss,
        "net_vacation_pay":  net,
    })

    audit_repo.create_log(
        db, action="vacation_scheduled", user_id=user_id,
        entity="vacation", entity_id=vac.id,
        description=f"Férias agendadas para {emp.name}: {data.acquisition_start} – {data.acquisition_end}",
    )
    return vac


def update_vacation_service(
    db: Session,
    vacation_id: int,
    data: VacationUpdate,
    company_id: int,
    user_id: int,
) -> Vacation:
    vac = _get_vacation_or_404(db, vacation_id, company_id)
    if vac.status != VacationStatus.SCHEDULED:
        raise HTTPException(status_code=400, detail="Apenas férias agendadas podem ser editadas")

    updates: dict = {}

    if data.acquisition_start is not None: updates["acquisition_start"] = data.acquisition_start
    if data.acquisition_end   is not None: updates["acquisition_end"]   = data.acquisition_end
    if data.enjoyment_start   is not None: updates["enjoyment_start"]   = data.enjoyment_start
    if data.notes             is not None: updates["notes"]             = data.notes

    # Sell-all toggle
    sell_all = data.sell_all_days if data.sell_all_days is not None else bool(vac.sell_all_days)
    updates["sell_all_days"] = sell_all
    if data.enjoyment_days is not None:
        updates["enjoyment_days"] = 0 if sell_all else data.enjoyment_days
    elif sell_all:
        updates["enjoyment_days"] = 0

    if data.abono_days is not None:
        updates["abono_days"] = 0 if sell_all else data.abono_days

    # Recalculate if any value field changed
    base      = _q2(data.base_salary)      if data.base_salary      is not None else (vac.base_salary      or Decimal("0"))
    one_third = _q2(data.one_third_bonus)  if data.one_third_bonus  is not None else (vac.one_third_bonus  or Decimal("0"))
    inss      = _q2(data.inss_discount)    if data.inss_discount     is not None else (vac.inss_discount    or Decimal("0"))

    if any(v is not None for v in [data.base_salary, data.one_third_bonus, data.inss_discount]):
        updates.update({"base_salary": base, "one_third_bonus": one_third, "inss_discount": inss})
    else:
        base      = vac.base_salary      or Decimal("0")
        one_third = vac.one_third_bonus  or Decimal("0")
        inss      = vac.inss_discount    or Decimal("0")

    updates["net_vacation_pay"] = _recalc_net(base, one_third, inss, vac.items)

    if data.acquisition_start or data.acquisition_end:
        acq_start = data.acquisition_start or vac.acquisition_start
        acq_end   = data.acquisition_end   or vac.acquisition_end
        if vac_repo.has_overlapping_acquisition(db, vac.employee_id, acq_start, acq_end, exclude_id=vacation_id):
            raise HTTPException(status_code=409, detail="Período aquisitivo se sobrepõe a um existente")

    return vac_repo.update_vacation(db, vac, updates)


def delete_vacation_service(
    db: Session,
    vacation_id: int,
    company_id: int,
    user_id: int,
) -> None:
    vac = _get_vacation_or_404(db, vacation_id, company_id)
    if vac.status not in (VacationStatus.SCHEDULED, VacationStatus.CANCELLED):
        raise HTTPException(status_code=400, detail="Apenas férias agendadas ou canceladas podem ser excluídas")
    vac_repo.delete_vacation(db, vac)
    audit_repo.create_log(
        db, action="vacation_deleted", user_id=user_id,
        entity="vacation", entity_id=vacation_id,
        description=f"Férias ID {vacation_id} excluídas",
    )


# ── Itens de Férias ───────────────────────────────────────────────────────────

def _get_item_and_vac(db: Session, vacation_id: int, item_id: int, company_id: int):
    vac = _get_vacation_or_404(db, vacation_id, company_id)
    item = vac_repo.get_vacation_item(db, item_id)
    if not item or item.vacation_id != vacation_id:
        raise HTTPException(status_code=404, detail="Item não encontrado")
    return vac, item


def add_vacation_item(
    db: Session,
    vacation_id: int,
    data: VacationItemCreate,
    company_id: int,
) -> Vacation:
    vac = _get_vacation_or_404(db, vacation_id, company_id)
    vac_repo.create_vacation_item(db, {
        "vacation_id": vacation_id,
        "item_type":   data.item_type,
        "description": data.description,
        "value":       data.value,
    })
    # Recalculate net
    vac = vac_repo.get_vacation(db, vacation_id)
    base      = vac.base_salary     or Decimal("0")
    one_third = vac.one_third_bonus or Decimal("0")
    inss      = vac.inss_discount   or Decimal("0")
    net = _recalc_net(base, one_third, inss, vac.items)
    return vac_repo.update_vacation(db, vac, {"net_vacation_pay": net})


def update_vacation_item_service(
    db: Session,
    vacation_id: int,
    item_id: int,
    data: VacationItemUpdate,
    company_id: int,
) -> Vacation:
    vac, item = _get_item_and_vac(db, vacation_id, item_id, company_id)
    upd = {k: v for k, v in data.model_dump().items() if v is not None}
    vac_repo.update_vacation_item(db, item, upd)
    vac = vac_repo.get_vacation(db, vacation_id)
    base      = vac.base_salary     or Decimal("0")
    one_third = vac.one_third_bonus or Decimal("0")
    inss      = vac.inss_discount   or Decimal("0")
    net = _recalc_net(base, one_third, inss, vac.items)
    return vac_repo.update_vacation(db, vac, {"net_vacation_pay": net})


def delete_vacation_item_service(
    db: Session,
    vacation_id: int,
    item_id: int,
    company_id: int,
) -> Vacation:
    vac, item = _get_item_and_vac(db, vacation_id, item_id, company_id)
    vac_repo.delete_vacation_item(db, item)
    vac = vac_repo.get_vacation(db, vacation_id)
    base      = vac.base_salary     or Decimal("0")
    one_third = vac.one_third_bonus or Decimal("0")
    inss      = vac.inss_discount   or Decimal("0")
    net = _recalc_net(base, one_third, inss, vac.items)
    return vac_repo.update_vacation(db, vac, {"net_vacation_pay": net})


# ── Ciclo de vida ─────────────────────────────────────────────────────────────

def start_vacation(
    db: Session,
    vacation_id: int,
    body: VacationStart,
    company_id: int,
    user_id: int,
) -> Vacation:
    vac = _get_vacation_or_404(db, vacation_id, company_id)
    if vac.status != VacationStatus.SCHEDULED:
        raise HTTPException(status_code=400, detail=f"Férias não podem ser iniciadas no status '{vac.status.value}'")
    return vac_repo.update_vacation(db, vac, {
        "status":          VacationStatus.ACTIVE,
        "enjoyment_start": body.enjoyment_start,
    })


def complete_vacation(
    db: Session,
    vacation_id: int,
    company_id: int,
    user_id: int,
) -> Vacation:
    vac = _get_vacation_or_404(db, vacation_id, company_id)
    if vac.status not in (VacationStatus.ACTIVE, VacationStatus.SCHEDULED):
        raise HTTPException(status_code=400, detail=f"Férias não podem ser concluídas no status '{vac.status.value}'")
    completed = vac_repo.update_vacation(db, vac, {"status": VacationStatus.COMPLETED})
    audit_repo.create_log(
        db, action="vacation_completed", user_id=user_id,
        entity="vacation", entity_id=vacation_id,
        description=f"Férias ID {vacation_id} concluídas",
    )
    return completed


def cancel_vacation(
    db: Session,
    vacation_id: int,
    company_id: int,
    user_id: int,
) -> Vacation:
    vac = _get_vacation_or_404(db, vacation_id, company_id)
    if vac.status not in (VacationStatus.SCHEDULED, VacationStatus.ACTIVE):
        raise HTTPException(status_code=400, detail=f"Férias com status '{vac.status.value}' não podem ser canceladas")
    return vac_repo.update_vacation(db, vac, {"status": VacationStatus.CANCELLED})


def get_vacation(db: Session, vacation_id: int, company_id: int) -> Vacation:
    return _get_vacation_or_404(db, vacation_id, company_id)


def list_by_employee(db: Session, employee_id: int, company_id: int) -> list[Vacation]:
    emp = _get_employee_any_status(db, employee_id, company_id)
    vacs = vac_repo.list_by_employee(db, emp.id)
    return [_auto_advance_status(db, v) for v in vacs]


def list_active(db: Session, company_id: int) -> list[Vacation]:
    vacs = vac_repo.list_active_by_company(db, company_id)
    return [_auto_advance_status(db, v) for v in vacs]


def get_company_overview(db: Session, company_id: int) -> list[dict]:
    """Situação de férias de todos os funcionários ativos da empresa."""
    from app.repositories import employee as emp_repo_mod
    employees = emp_repo_mod.list_all(db, company_id)
    result = []

    for emp in employees:
        if emp.status == EmployeeStatus.INACTIVE:
            continue
        if not emp.registration_date:
            continue

        reg_date = emp.registration_date
        months   = _months_registered(reg_date)
        periods_with_acq_ended  = months // 12
        periods_with_conc_ended = max(0, months // 12 - 1)
        vacation_count = vac_repo.count_non_cancelled_by_employee(db, emp.id)
        unclaimed = max(0, periods_with_acq_ended - vacation_count)
        overdue   = max(0, periods_with_conc_ended - vacation_count)

        all_vacs      = [_auto_advance_status(db, v) for v in vac_repo.list_by_employee(db, emp.id)]
        scheduled_vac = next(
            (v for v in all_vacs
             if v.status in (VacationStatus.SCHEDULED, VacationStatus.ACTIVE)),
            None,
        )

        if overdue > 0:
            vac_status = "vencida"
        elif scheduled_vac is not None:
            vac_status = "agendada"
        elif unclaimed > 0:
            vac_status = "disponivel"
        elif months < 12:
            vac_status = "inelegivel"
        else:
            vac_status = "regular"

        # Concessivo end of the first unclaimed period
        vencimento = None
        if periods_with_acq_ended > vacation_count:
            n = vacation_count
            vencimento = _add_months(reg_date, (n + 2) * 12)

        sched_start = sched_end = sched_days = None
        sell_all = False
        if scheduled_vac:
            sched_start = scheduled_vac.enjoyment_start
            sched_days  = scheduled_vac.enjoyment_days or 0
            sell_all    = bool(scheduled_vac.sell_all_days)
            if sched_start and sched_days:
                sched_end = sched_start + timedelta(days=sched_days - 1)

        result.append({
            "employee_id":       emp.id,
            "employee_name":     emp.name,
            "registration_date": reg_date,
            "months_registered": months,
            "vacation_status":   vac_status,
            "vencimento":        vencimento,
            "scheduled_start":   sched_start,
            "scheduled_end":     sched_end,
            "scheduled_days":    sched_days,
            "sell_all_days":     sell_all,
            "unclaimed_periods": unclaimed,
            "overdue_periods":   overdue,
            "is_eligible":       unclaimed > 0,
        })

    order = {"vencida": 0, "disponivel": 1, "agendada": 2, "regular": 3, "inelegivel": 4}
    result.sort(key=lambda x: (order.get(x["vacation_status"], 5), x["employee_name"]))
    return result


# ── 13º Salário ───────────────────────────────────────────────────────────────

def get_thirteenth(
    db: Session,
    employee_id: int,
    year: int,
    parcela: int,
    company_id: int,
) -> dict:
    emp = _get_employee_any_status(db, employee_id, company_id)
    ref_date      = date(year, 12, 31)
    worked_months = count_worked_months_for_thirteenth(emp.registration_date, ref_date)
    salary        = Decimal(str(emp.salary))

    bruto_13         = _q2(salary * Decimal(worked_months) / Decimal("12"))
    inss_on_bruto    = calc_inss(bruto_13)
    primeira_parcela = _q2(bruto_13 / Decimal("2"))

    if parcela == 1:
        inss_parcela = Decimal("0")
        liquido      = primeira_parcela
    else:
        inss_parcela = inss_on_bruto
        liquido      = _q2(bruto_13 - inss_on_bruto - primeira_parcela)

    return {
        "employee_id":      emp.id,
        "employee_name":    emp.name,
        "year":             year,
        "parcela":          parcela,
        "worked_months":    worked_months,
        "bruto_13":         bruto_13,
        "inss":             inss_parcela,
        "primeira_parcela": primeira_parcela,
        "liquido":          liquido,
    }


# ── Rescisão ──────────────────────────────────────────────────────────────────

def calc_notice_days(reason: TerminationReason, admission_date: date, termination_date: date) -> int:
    if reason in (TerminationReason.COM_JUSTA_CAUSA, TerminationReason.APOSENTADORIA):
        return 0
    years_worked = (termination_date - admission_date).days // 365
    days = min(30 + years_worked * 3, 90)
    if reason == TerminationReason.ACORDO:
        days = days // 2
    return days


def _count_proportional_vacation_months(registration_date: date, termination_date: date) -> int:
    total_months = (
        (termination_date.year - registration_date.year) * 12
        + (termination_date.month - registration_date.month)
    )
    months_in_current = total_months % 12
    if termination_date.day >= 15:
        months_in_current = min(months_in_current + 1, 12)
    return max(months_in_current, 0)


def _count_unpaid_vacation_periods(
    db: Session, employee_id: int, registration_date: date, termination_date: date
) -> int:
    total_months = (
        (termination_date.year - registration_date.year) * 12
        + (termination_date.month - registration_date.month)
    )
    full_periods = total_months // 12
    if full_periods == 0:
        return 0
    completed = vac_repo.count_completed_by_employee(db, employee_id)
    return max(0, full_periods - completed)


def create_termination(
    db: Session,
    data: TerminationCreate,
    company_id: int,
    user_id: int,
) -> Termination:
    emp = _get_active_employee(db, data.employee_id, company_id)

    if vac_repo.get_termination_by_employee(db, emp.id):
        raise HTTPException(status_code=409, detail="Já existe rescisão registrada para este funcionário")

    salary            = Decimal(str(emp.salary))
    admission_date    = emp.admission_date
    registration_date = emp.registration_date
    term_date         = data.termination_date

    notice_days = calc_notice_days(data.reason, admission_date, term_date)

    aviso_previo_indenizado = Decimal("0")
    aviso_previo_desconto   = Decimal("0")

    if data.reason == TerminationReason.SEM_JUSTA_CAUSA and not data.notice_worked:
        aviso_previo_indenizado = _q2(salary / Decimal("30") * Decimal(notice_days))
    elif data.reason == TerminationReason.ACORDO:
        aviso_previo_indenizado = _q2(salary / Decimal("30") * Decimal(notice_days))
    elif data.reason == TerminationReason.PEDIDO_DEMISSAO and not data.notice_worked:
        aviso_previo_desconto = _q2(salary / Decimal("30") * Decimal(notice_days))

    saldo_salario = _q2(salary / Decimal("30") * Decimal(term_date.day))

    vac_months           = _count_proportional_vacation_months(registration_date, term_date)
    ferias_prop          = _q2(salary * Decimal(vac_months) / Decimal("12"))
    um_terco_ferias_prop = _q2(ferias_prop / Decimal("3"))

    unpaid_periods       = _count_unpaid_vacation_periods(db, emp.id, registration_date, term_date)
    ferias_vencidas      = _q2(salary * Decimal(unpaid_periods))
    um_terco_ferias_venc = _q2(ferias_vencidas / Decimal("3"))

    worked_months_13     = count_worked_months_for_thirteenth(registration_date, term_date)
    decimo_terceiro_prop = _q2(salary * Decimal(worked_months_13) / Decimal("12"))

    months_total = (
        (term_date.year - admission_date.year) * 12
        + term_date.month - admission_date.month + 1
    )
    fgts_balance = _q2(salary * Decimal("0.08") * Decimal(months_total))

    if data.reason == TerminationReason.SEM_JUSTA_CAUSA:
        multa_fgts = _q2(fgts_balance * Decimal("0.40"))
    elif data.reason == TerminationReason.ACORDO:
        multa_fgts = _q2(fgts_balance * Decimal("0.20"))
    else:
        multa_fgts = Decimal("0")

    inss_base = (
        saldo_salario + aviso_previo_indenizado + decimo_terceiro_prop
        + ferias_prop + um_terco_ferias_prop
        + ferias_vencidas + um_terco_ferias_venc
    )
    inss_rescisao = calc_inss(inss_base)

    total_creditos = (
        saldo_salario + aviso_previo_indenizado
        + ferias_prop + um_terco_ferias_prop
        + ferias_vencidas + um_terco_ferias_venc
        + decimo_terceiro_prop + multa_fgts
    )
    total_descontos = inss_rescisao + aviso_previo_desconto
    liquido         = _q2(total_creditos - total_descontos)

    term = vac_repo.create_termination(db, {
        "employee_id":             emp.id,
        "created_by_id":           user_id,
        "termination_date":        term_date,
        "reason":                  data.reason,
        "notice_days":             notice_days,
        "notice_worked":           data.notice_worked,
        "notice_start_date":       data.notice_start_date,
        "saldo_salario":           saldo_salario,
        "ferias_proporcionais":    ferias_prop,
        "um_terco_ferias_prop":    um_terco_ferias_prop,
        "ferias_vencidas":         ferias_vencidas,
        "um_terco_ferias_venc":    um_terco_ferias_venc,
        "decimo_terceiro_prop":    decimo_terceiro_prop,
        "aviso_previo_indenizado": aviso_previo_indenizado,
        "aviso_previo_desconto":   aviso_previo_desconto,
        "multa_fgts":              multa_fgts,
        "inss_rescisao":           inss_rescisao,
        "total_creditos":          total_creditos,
        "total_descontos":         total_descontos,
        "liquido":                 liquido,
        "notes":                   data.notes,
    })

    # Inativa o funcionário somente se a data de rescisão já chegou
    from app.repositories import employee as emp_repo_mod
    if term_date <= date.today():
        emp_repo_mod.update_employee(db, emp, {
            "status":              EmployeeStatus.INACTIVE,
            "inactivation_date":   term_date,
            "inactivation_reason": data.reason.value,
        })

    audit_repo.create_log(
        db, action="termination_created", user_id=user_id,
        entity="termination", entity_id=term.id,
        description=f"Rescisão de {emp.name} em {term_date} ({data.reason.value}) — líquido R$ {liquido}",
    )
    return term


def _check_auto_inactivate(db: Session, term: Termination) -> None:
    """Inativa o funcionário automaticamente quando a data de rescisão chega."""
    from app.repositories import employee as emp_repo_mod
    if term.termination_date > date.today():
        return
    emp = emp_repo.get_employee(db, term.employee_id)
    if emp and emp.status == EmployeeStatus.ACTIVE:
        emp_repo_mod.update_employee(db, emp, {
            "status":              EmployeeStatus.INACTIVE,
            "inactivation_date":   term.termination_date,
            "inactivation_reason": term.reason.value,
        })


def get_termination(db: Session, termination_id: int, company_id: int) -> Termination:
    term = vac_repo.get_termination(db, termination_id)
    if not term:
        raise HTTPException(status_code=404, detail="Rescisão não encontrada")
    emp = emp_repo.get_employee(db, term.employee_id)
    if not emp or emp.company_id != company_id:
        raise HTTPException(status_code=404, detail="Rescisão não encontrada")
    _check_auto_inactivate(db, term)
    return term


def list_terminations(db: Session, company_id: int) -> list[Termination]:
    terms = vac_repo.list_terminations(db, company_id)
    for t in terms:
        _check_auto_inactivate(db, t)
    return terms


def update_termination(
    db: Session,
    termination_id: int,
    data: TerminationUpdate,
    company_id: int,
) -> Termination:
    term = get_termination(db, termination_id, company_id)
    updates = data.model_dump(exclude_unset=True)
    if not updates:
        return term

    # Merge atualização com valores atuais e recalcula totais
    def _cur(field):
        return Decimal(str(getattr(term, field) or 0))

    saldo          = Decimal(str(updates.get("saldo_salario",          _cur("saldo_salario"))))
    fer_prop       = Decimal(str(updates.get("ferias_proporcionais",   _cur("ferias_proporcionais"))))
    terc_prop      = Decimal(str(updates.get("um_terco_ferias_prop",   _cur("um_terco_ferias_prop"))))
    fer_venc       = Decimal(str(updates.get("ferias_vencidas",        _cur("ferias_vencidas"))))
    terc_venc      = Decimal(str(updates.get("um_terco_ferias_venc",   _cur("um_terco_ferias_venc"))))
    dec_prop       = Decimal(str(updates.get("decimo_terceiro_prop",   _cur("decimo_terceiro_prop"))))
    aviso_ind      = Decimal(str(updates.get("aviso_previo_indenizado",_cur("aviso_previo_indenizado"))))
    multa          = Decimal(str(updates.get("multa_fgts",             _cur("multa_fgts"))))
    inss           = Decimal(str(updates.get("inss_rescisao",          _cur("inss_rescisao"))))
    aviso_desc     = Decimal(str(updates.get("aviso_previo_desconto",  _cur("aviso_previo_desconto"))))

    total_cred = _q2(saldo + fer_prop + terc_prop + fer_venc + terc_venc + dec_prop + aviso_ind + multa)
    total_desc = _q2(inss + aviso_desc)

    updates["total_creditos"]  = total_cred
    updates["total_descontos"] = total_desc
    updates["liquido"]         = _q2(total_cred - total_desc)

    vac_repo.update_termination(db, term, updates)
    return term
