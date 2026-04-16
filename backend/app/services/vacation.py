"""
Serviço de Férias, 13º Salário e Rescisão.
Toda a lógica de negócio fica aqui.
"""
import calendar
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.repositories import vacation as vac_repo
from app.repositories import employee as emp_repo
from app.repositories import audit_log as audit_repo
from app.models.employee import Employee, EmployeeStatus
from app.models.vacation import Vacation, VacationStatus
from app.models.termination import Termination, TerminationReason
from app.schemas.vacation import VacationCreate, VacationStart, TerminationCreate
from app.utils.inss_calc import calc_inss, calc_inss_ferias
from app.utils.payroll_calc import count_worked_months_for_thirteenth, calc_thirteenth_salary


# ── Helpers internos ──────────────────────────────────────────────────────────

def _q2(v: Decimal) -> Decimal:
    return v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


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


def _get_vacation_or_404(db: Session, vacation_id: int, company_id: int) -> Vacation:
    vac = vac_repo.get_vacation(db, vacation_id)
    if not vac:
        raise HTTPException(status_code=404, detail="Férias não encontrada")
    emp = emp_repo.get_employee(db, vac.employee_id)
    if not emp or emp.company_id != company_id:
        raise HTTPException(status_code=404, detail="Férias não encontrada")
    return vac


# ── Cálculos puros ────────────────────────────────────────────────────────────

def calc_vacation_pay(salary: Decimal, days: int) -> dict:
    """
    Cálculo de remuneração de férias.
    base = salário × dias/30
    1/3  = base / 3
    INSS = progressivo sobre (base + 1/3)
    líquido = base + 1/3 - INSS
    """
    base      = _q2(salary * Decimal(days) / Decimal("30"))
    one_third = _q2(base / Decimal("3"))
    inss      = calc_inss_ferias(base)
    net       = _q2(base + one_third - inss)
    return {
        "base_salary":      base,
        "one_third_bonus":  one_third,
        "inss_discount":    inss,
        "net_vacation_pay": net,
    }


def calc_notice_days(
    reason: TerminationReason,
    admission_date: date,
    termination_date: date,
) -> int:
    """
    Aviso prévio proporcional (CLT, art. 487):
    30 dias + 3 dias por ano completo trabalhado, máx. 90 dias.
    Com justa causa e aposentadoria: 0 dias.
    """
    if reason in (TerminationReason.COM_JUSTA_CAUSA, TerminationReason.APOSENTADORIA):
        return 0
    years_worked = (termination_date - admission_date).days // 365
    days = min(30 + years_worked * 3, 90)
    if reason == TerminationReason.ACORDO:
        days = days // 2  # acordo = 50% do aviso
    return days


def _count_proportional_vacation_months(
    registration_date: date,
    termination_date: date,
) -> int:
    """
    Meses no período aquisitivo atual (incompleto).
    Regra: mês conta se trabalhou >= 15 dias.
    """
    total_months = (
        (termination_date.year - registration_date.year) * 12
        + (termination_date.month - registration_date.month)
    )
    months_in_current = total_months % 12
    # O mês de saída conta se foram >= 15 dias
    if termination_date.day >= 15:
        months_in_current = min(months_in_current + 1, 12)
    return max(months_in_current, 0)


def _count_unpaid_vacation_periods(
    db: Session,
    employee_id: int,
    registration_date: date,
    termination_date: date,
) -> int:
    """Conta períodos aquisitivos completos sem férias gozadas (COMPLETED)."""
    total_months = (
        (termination_date.year - registration_date.year) * 12
        + (termination_date.month - registration_date.month)
    )
    full_periods = total_months // 12
    if full_periods == 0:
        return 0
    completed = vac_repo.count_completed_by_employee(db, employee_id)
    return max(0, full_periods - completed)


# ── Férias ────────────────────────────────────────────────────────────────────

def schedule_vacation(
    db: Session,
    data: VacationCreate,
    company_id: int,
    user_id: int,
) -> Vacation:
    emp = _get_active_employee(db, data.employee_id, company_id)

    if vac_repo.has_overlapping_acquisition(
        db, data.employee_id, data.acquisition_start, data.acquisition_end
    ):
        raise HTTPException(
            status_code=409,
            detail="Já existe um período aquisitivo que se sobrepõe ao informado",
        )

    pay = calc_vacation_pay(Decimal(str(emp.salary)), data.enjoyment_days)

    vac = vac_repo.create_vacation(db, {
        "employee_id":       data.employee_id,
        "created_by_id":     user_id,
        "acquisition_start": data.acquisition_start,
        "acquisition_end":   data.acquisition_end,
        "enjoyment_start":   data.enjoyment_start,
        "enjoyment_days":    data.enjoyment_days,
        "is_fractioned":     data.is_fractioned,
        "notes":             data.notes,
        "status":            VacationStatus.SCHEDULED,
        **pay,
    })

    audit_repo.create_log(
        db, action="vacation_scheduled", user_id=user_id,
        entity="vacation", entity_id=vac.id,
        description=f"Férias agendadas para funcionário ID {emp.id}: "
                    f"{data.acquisition_start} – {data.acquisition_end}",
    )
    return vac


def start_vacation(
    db: Session,
    vacation_id: int,
    body: VacationStart,
    company_id: int,
    user_id: int,
) -> Vacation:
    vac = _get_vacation_or_404(db, vacation_id, company_id)
    if vac.status != VacationStatus.SCHEDULED:
        raise HTTPException(
            status_code=400,
            detail=f"Férias não podem ser iniciadas no status '{vac.status.value}'",
        )
    return vac_repo.update_vacation(db, vac, {
        "status":        VacationStatus.ACTIVE,
        "enjoyment_start": body.enjoyment_start,
    })


def complete_vacation(
    db: Session,
    vacation_id: int,
    company_id: int,
    user_id: int,
) -> Vacation:
    vac = _get_vacation_or_404(db, vacation_id, company_id)
    if vac.status != VacationStatus.ACTIVE:
        raise HTTPException(
            status_code=400,
            detail=f"Férias não podem ser concluídas no status '{vac.status.value}'",
        )
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
        raise HTTPException(
            status_code=400,
            detail=f"Férias com status '{vac.status.value}' não podem ser canceladas",
        )
    return vac_repo.update_vacation(db, vac, {"status": VacationStatus.CANCELLED})


def get_vacation(db: Session, vacation_id: int, company_id: int) -> Vacation:
    return _get_vacation_or_404(db, vacation_id, company_id)


def list_by_employee(db: Session, employee_id: int, company_id: int) -> list[Vacation]:
    emp = _get_employee_any_status(db, employee_id, company_id)
    return vac_repo.list_by_employee(db, emp.id)


def list_active(db: Session, company_id: int) -> list[Vacation]:
    return vac_repo.list_active_by_company(db, company_id)


# ── 13º Salário ───────────────────────────────────────────────────────────────

def get_thirteenth(
    db: Session,
    employee_id: int,
    year: int,
    parcela: int,
    company_id: int,
) -> dict:
    """
    Calcula 13º salário para um funcionário no ano informado.
    parcela=1 → adiantamento (novembro), sem INSS
    parcela=2 → saldo (dezembro): bruto - INSS - 1ª parcela
    """
    emp = _get_employee_any_status(db, employee_id, company_id)

    ref_date     = date(year, 12, 31)
    worked_months = count_worked_months_for_thirteenth(emp.registration_date, ref_date)
    salary        = Decimal(str(emp.salary))

    bruto_13         = _q2(salary * Decimal(worked_months) / Decimal("12"))
    inss_on_bruto    = calc_inss(bruto_13)
    primeira_parcela = _q2(bruto_13 / Decimal("2"))

    if parcela == 1:
        liquido = primeira_parcela
    else:
        liquido = _q2(bruto_13 - inss_on_bruto - primeira_parcela)

    return {
        "employee_id":      emp.id,
        "employee_name":    emp.name,
        "year":             year,
        "parcela":          parcela,
        "worked_months":    worked_months,
        "bruto_13":         bruto_13,
        "inss":             inss_on_bruto,
        "primeira_parcela": primeira_parcela,
        "liquido":          liquido,
    }


# ── Rescisão ──────────────────────────────────────────────────────────────────

def create_termination(
    db: Session,
    data: TerminationCreate,
    company_id: int,
    user_id: int,
) -> Termination:
    emp = _get_active_employee(db, data.employee_id, company_id)

    if vac_repo.get_termination_by_employee(db, emp.id):
        raise HTTPException(
            status_code=409,
            detail="Já existe rescisão registrada para este funcionário",
        )

    salary           = Decimal(str(emp.salary))
    admission_date   = emp.admission_date
    registration_date = emp.registration_date
    term_date        = data.termination_date

    # ── Aviso prévio ──────────────────────────────────────────────────────────
    notice_days = calc_notice_days(data.reason, admission_date, term_date)

    aviso_previo_indenizado = Decimal("0")
    aviso_previo_desconto   = Decimal("0")

    if data.reason == TerminationReason.SEM_JUSTA_CAUSA and not data.notice_worked:
        aviso_previo_indenizado = _q2(salary / Decimal("30") * Decimal(notice_days))
    elif data.reason == TerminationReason.ACORDO:
        aviso_previo_indenizado = _q2(salary / Decimal("30") * Decimal(notice_days))
    elif data.reason == TerminationReason.PEDIDO_DEMISSAO and not data.notice_worked:
        # Funcionário não cumpre aviso → empregador desconta
        aviso_previo_desconto = _q2(salary / Decimal("30") * Decimal(notice_days))

    # ── Saldo de salário ──────────────────────────────────────────────────────
    # Dias trabalhados no mês de rescisão (CLT usa divisor 30)
    saldo_salario = _q2(salary / Decimal("30") * Decimal(term_date.day))

    # ── Férias proporcionais ──────────────────────────────────────────────────
    vac_months        = _count_proportional_vacation_months(registration_date, term_date)
    ferias_prop       = _q2(salary * Decimal(vac_months) / Decimal("12"))
    um_terco_ferias_prop = _q2(ferias_prop / Decimal("3"))

    # ── Férias vencidas ───────────────────────────────────────────────────────
    unpaid_periods   = _count_unpaid_vacation_periods(db, emp.id, registration_date, term_date)
    ferias_vencidas  = _q2(salary * Decimal(unpaid_periods))
    um_terco_ferias_venc = _q2(ferias_vencidas / Decimal("3"))

    # ── 13º proporcional ─────────────────────────────────────────────────────
    worked_months_13    = count_worked_months_for_thirteenth(registration_date, term_date)
    decimo_terceiro_prop = _q2(salary * Decimal(worked_months_13) / Decimal("12"))

    # ── Multa FGTS ────────────────────────────────────────────────────────────
    months_total = (
        (term_date.year - admission_date.year) * 12
        + term_date.month - admission_date.month
        + 1
    )
    fgts_balance = _q2(salary * Decimal("0.08") * Decimal(months_total))

    if data.reason == TerminationReason.SEM_JUSTA_CAUSA:
        multa_fgts = _q2(fgts_balance * Decimal("0.40"))
    elif data.reason == TerminationReason.ACORDO:
        multa_fgts = _q2(fgts_balance * Decimal("0.20"))
    else:
        multa_fgts = Decimal("0")

    # ── INSS rescisório ───────────────────────────────────────────────────────
    # Base: saldo_salario + aviso_previo + 13º + férias (todas com 1/3)
    inss_base = (
        saldo_salario + aviso_previo_indenizado + decimo_terceiro_prop
        + ferias_prop + um_terco_ferias_prop
        + ferias_vencidas + um_terco_ferias_venc
    )
    inss_rescisao = calc_inss(inss_base)

    # ── Totais ────────────────────────────────────────────────────────────────
    total_creditos = (
        saldo_salario + aviso_previo_indenizado
        + ferias_prop + um_terco_ferias_prop
        + ferias_vencidas + um_terco_ferias_venc
        + decimo_terceiro_prop + multa_fgts
    )
    total_descontos = inss_rescisao + aviso_previo_desconto
    liquido         = _q2(total_creditos - total_descontos)

    term = vac_repo.create_termination(db, {
        "employee_id":            emp.id,
        "created_by_id":          user_id,
        "termination_date":       term_date,
        "reason":                 data.reason,
        "notice_days":            notice_days,
        "notice_worked":          data.notice_worked,
        "saldo_salario":          saldo_salario,
        "ferias_proporcionais":   ferias_prop,
        "um_terco_ferias_prop":   um_terco_ferias_prop,
        "ferias_vencidas":        ferias_vencidas,
        "um_terco_ferias_venc":   um_terco_ferias_venc,
        "decimo_terceiro_prop":   decimo_terceiro_prop,
        "aviso_previo_indenizado": aviso_previo_indenizado,
        "aviso_previo_desconto":  aviso_previo_desconto,
        "multa_fgts":             multa_fgts,
        "inss_rescisao":          inss_rescisao,
        "total_creditos":         total_creditos,
        "total_descontos":        total_descontos,
        "liquido":                liquido,
        "notes":                  data.notes,
    })

    # Inativar funcionário
    from app.repositories import employee as emp_repo_mod
    emp_repo_mod.update_employee(db, emp, {
        "status":             EmployeeStatus.INACTIVE,
        "inactivation_date":  term_date,
        "inactivation_reason": data.reason.value,
    })

    audit_repo.create_log(
        db, action="termination_created", user_id=user_id,
        entity="termination", entity_id=term.id,
        description=(
            f"Rescisão de {emp.name} em {term_date} "
            f"({data.reason.value}) — líquido R$ {liquido}"
        ),
    )
    return term


def get_termination(
    db: Session,
    termination_id: int,
    company_id: int,
) -> Termination:
    term = vac_repo.get_termination(db, termination_id)
    if not term:
        raise HTTPException(status_code=404, detail="Rescisão não encontrada")
    emp = emp_repo.get_employee(db, term.employee_id)
    if not emp or emp.company_id != company_id:
        raise HTTPException(status_code=404, detail="Rescisão não encontrada")
    return term
