"""
Serviço de Folha de Pagamento.
"""
import calendar as cal
from datetime import date, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.repositories import payroll as payroll_repo
from app.repositories import employee as emp_repo
from app.repositories import timesheet as ts_repo
from app.repositories import audit_log as audit_repo
from app.models.payroll import Payroll, PayrollItem, Vale, PayrollItemType, PayrollStatus
from app.models.employee import Employee, EmployeeStatus
from app.schemas.payroll import (
    PayrollCreate, PayrollBatchCreate, PayrollFlagsUpdate,
    PayrollItemCreate, PayrollItemUpdate, ValeCreate,
)
from app.utils.payroll_calc import (
    working_days_in_month, count_working_days_in_range,
    calc_proportional_salary, calc_overtime_value,
    calc_dsr_by_week, next_month,
)
from app.utils.inss_calc import calc_inss


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_employee(db: Session, employee_id: int, company_id: int) -> Employee:
    emp = emp_repo.get_employee(db, employee_id)
    if not emp or emp.company_id != company_id:
        raise HTTPException(status_code=404, detail="Funcionário não encontrado")
    if emp.status == EmployeeStatus.INACTIVE:
        raise HTTPException(status_code=400, detail="Funcionário inativo")
    return emp


def _get_payroll_or_404(db: Session, payroll_id: int, company_id: int) -> Payroll:
    p = payroll_repo.get_payroll(db, payroll_id)
    if not p:
        raise HTTPException(status_code=404, detail="Holerite não encontrado")
    emp = emp_repo.get_employee(db, p.employee_id)
    if not emp or emp.company_id != company_id:
        raise HTTPException(status_code=404, detail="Holerite não encontrado")
    return p


def _require_draft(payroll: Payroll) -> None:
    if payroll.status == PayrollStatus.CLOSED:
        raise HTTPException(
            status_code=400,
            detail="Holerite já fechado — não pode ser alterado",
        )


def _eligible_employees(db: Session, company_id: int, month: int, year: int) -> list[Employee]:
    """Funcionários ativos admitidos até o último dia do mês de competência."""
    last_day = date(year, month, cal.monthrange(year, month)[1])
    emps = emp_repo.list_active(db, company_id)
    result = []
    for e in emps:
        if e.admission_date is None or e.admission_date <= last_day:
            result.append(e)
    return result


# ── Cálculo automático ────────────────────────────────────────────────────────

def _auto_generate_items(db: Session, payroll: Payroll, emp: Employee) -> None:
    """
    Remove itens automáticos e recria com as regras atuais.
    Itens manuais (is_manual=True) são preservados.
    Lê as flags pay_overtime e use_hour_bank_for_absences do próprio payroll.
    """
    for item in list(payroll.items):
        if not item.is_manual:
            db.delete(item)
    db.flush()
    db.refresh(payroll)

    month = payroll.competence_month
    year  = payroll.competence_year
    base_salary = Decimal(str(emp.salary))

    first_of_month = date(year, month, 1)
    last_of_month  = date(year, month, cal.monthrange(year, month)[1])
    total_working_days = working_days_in_month(year, month)

    # ── Período proporcional (funcionário novo ou férias parciais) ────────────
    start_date = first_of_month
    if emp.admission_date and emp.admission_date > first_of_month:
        start_date = emp.admission_date

    actual_working_days = count_working_days_in_range(start_date, last_of_month)

    # ── Férias: contar dias de gozo no mês para subtrair do salário ───────────
    vacation_working_days = 0
    try:
        from app.models.vacation import Vacation, VacationStatus
        vacations = (
            db.query(Vacation)
            .filter(
                Vacation.employee_id == emp.id,
                Vacation.status.in_([VacationStatus.ACTIVE, VacationStatus.COMPLETED]),
            )
            .all()
        )
        for v in vacations:
            if v.enjoyment_start and v.enjoyment_days:
                vac_end = v.enjoyment_start + timedelta(days=v.enjoyment_days - 1)
                vac_start_eff = max(v.enjoyment_start, first_of_month)
                vac_end_eff   = min(vac_end, last_of_month)
                if vac_start_eff <= vac_end_eff:
                    vacation_working_days += count_working_days_in_range(vac_start_eff, vac_end_eff)
    except Exception:
        pass

    # ── Dados do ponto ────────────────────────────────────────────────────────
    entries = ts_repo.list_entries_by_month(db, emp.id, month, year)

    absence_entries = [
        e for e in entries
        if e.is_absence and not e.is_annulled and not e.is_medical_certificate
    ]
    absence_dates   = [e.work_date for e in absence_entries]
    absences        = len(absence_dates)
    medical_certs   = sum(1 for e in entries if e.is_medical_certificate)
    total_ot_min    = sum(e.overtime_minutes for e in entries if not e.is_annulled)
    total_late_min  = sum(e.late_minutes     for e in entries if not e.is_annulled)

    # ── Dias elegíveis para salário (período ativo menos dias de férias)
    # Faltas NÃO reduzem o salário aqui — são descontos separados abaixo.
    salary_eligible_days = max(0, actual_working_days - vacation_working_days)

    # ── Dias trabalhados (para exibição) ─────────────────────────────────────
    worked_days = max(0, salary_eligible_days - absences)

    # ── Salário bruto ─────────────────────────────────────────────────────────
    # Proporcional apenas para funcionários novos (admission > início do mês)
    # ou quando há dias de férias descontando o período.
    salary_value = calc_proportional_salary(base_salary, salary_eligible_days, total_working_days)
    _add_auto(db, payroll.id, PayrollItemType.SALARY, "Salário", salary_value, True)

    # ── Hora extra (somente se flag ativa) ────────────────────────────────────
    ot_value = Decimal("0")
    if payroll.pay_overtime and total_ot_min > 0:
        ot_value = calc_overtime_value(base_salary, total_ot_min)
        h, m_ = divmod(total_ot_min, 60)
        _add_auto(db, payroll.id, PayrollItemType.OVERTIME,
                  f"Horas Extras ({h}h{m_:02d}m)", ot_value, True)

    # ── Vale Transporte ───────────────────────────────────────────────────────
    if emp.needs_transport:
        vt_daily = Decimal(str(emp.vt_daily or "10.60"))
        next_y, next_m = next_month(year, month)
        dias_prox = working_days_in_month(next_y, next_m)
        dias_vt   = max(0, dias_prox - absences - medical_certs)
        vt_value  = (vt_daily * Decimal(dias_vt)).quantize(Decimal("0.01"))
        if vt_value > 0:
            _add_auto(db, payroll.id, PayrollItemType.VT, "Vale Transporte", vt_value, True)

    # ── Auxílio ───────────────────────────────────────────────────────────────
    if emp.auxilio and emp.auxilio > 0:
        _add_auto(db, payroll.id, PayrollItemType.AUXILIO,
                  "Auxílio", Decimal(str(emp.auxilio)), True)

    # ── Faltas e DSR ──────────────────────────────────────────────────────────
    if absences > 0:
        if payroll.use_hour_bank_for_absences:
            # Debitar do banco de horas (8h por falta)
            absence_minutes = absences * 480
            ts_repo.upsert_hour_bank(db, emp.id, -absence_minutes)
            h_abs = absences * 8
            _add_auto(db, payroll.id, PayrollItemType.ABSENCE,
                      f"Faltas cobertas por Banco de Horas ({absences}d = {h_abs}h)",
                      Decimal("0"), False)
        else:
            daily = (base_salary / Decimal("30")).quantize(Decimal("0.01"))
            absence_discount = (daily * Decimal(absences)).quantize(Decimal("0.01"))
            _add_auto(db, payroll.id, PayrollItemType.ABSENCE,
                      f"Desconto de Faltas ({absences} dia(s))", absence_discount, False)

            dsr_value, dsr_weeks = calc_dsr_by_week(base_salary, absence_dates)
            if dsr_value > 0:
                _add_auto(db, payroll.id, PayrollItemType.DSR,
                          f"Desconto DSR ({dsr_weeks} semana(s))", dsr_value, False)

    # ── Atrasos ───────────────────────────────────────────────────────────────
    if total_late_min > 0:
        late_value = (
            base_salary / Decimal("220") / Decimal("60") * Decimal(total_late_min)
        ).quantize(Decimal("0.01"))
        h_l, m_l = divmod(total_late_min, 60)
        _add_auto(db, payroll.id, PayrollItemType.ABSENCE,
                  f"Desconto de Atrasos ({h_l}h{m_l:02d}m)", late_value, False)

    # ── INSS ──────────────────────────────────────────────────────────────────
    gross_for_inss = salary_value + ot_value
    inss_value = calc_inss(gross_for_inss)
    _add_auto(db, payroll.id, PayrollItemType.INSS, "INSS", inss_value, False)

    # ── Parcelas de vale ──────────────────────────────────────────────────────
    installments = payroll_repo.list_pending_installments(db, emp.id, month, year)
    for inst in installments:
        _add_auto(db, payroll.id, PayrollItemType.VALE_DESCONTO,
                  f"Vale – parcela {inst.installment_number}", inst.amount, False)

    # ── Atualizar metadados ───────────────────────────────────────────────────
    payroll_repo.update_payroll(db, payroll, {
        "worked_days": worked_days,
        "total_overtime_hours": Decimal(str(total_ot_min)) / Decimal("60"),
    })
    db.commit()
    payroll_repo.recalc_totals(db, payroll)


def _add_auto(
    db: Session,
    payroll_id: int,
    item_type: PayrollItemType,
    description: str,
    amount: Decimal,
    is_credit: bool,
) -> None:
    db.add(PayrollItem(
        payroll_id=payroll_id,
        item_type=item_type,
        description=description,
        amount=amount,
        is_credit=is_credit,
        is_manual=False,
        show_on_payslip=True,
    ))


# ── Operações de Holerite ─────────────────────────────────────────────────────

def list_eligible_employees(db: Session, month: int, year: int, company_id: int) -> list[dict]:
    """Retorna todos os funcionários elegíveis com o holerite do período (se existir)."""
    emps = _eligible_employees(db, company_id, month, year)
    result = []
    for emp in emps:
        payroll = payroll_repo.get_payroll_by_period(db, emp.id, month, year)
        result.append({
            "employee_id": emp.id,
            "name": emp.name,
            "salary": emp.salary,
            "admission_date": emp.admission_date,
            "has_payroll": payroll is not None,
            "payroll": payroll,
        })
    return result


def create_payroll(
    db: Session,
    data: PayrollCreate,
    company_id: int,
    created_by_id: int,
) -> Payroll:
    emp = _get_employee(db, data.employee_id, company_id)

    existing = payroll_repo.get_payroll_by_period(
        db, data.employee_id, data.competence_month, data.competence_year
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail="Já existe holerite para esse funcionário no período informado",
        )

    payroll = payroll_repo.create_payroll(db, {
        "employee_id":              data.employee_id,
        "created_by_id":            created_by_id,
        "competence_month":         data.competence_month,
        "competence_year":          data.competence_year,
        "pay_overtime":             data.pay_overtime,
        "use_hour_bank_for_absences": data.use_hour_bank_for_absences,
    })

    _auto_generate_items(db, payroll, emp)
    db.refresh(payroll)

    audit_repo.create_log(
        db, action="payroll_created", user_id=created_by_id,
        entity="payroll", entity_id=payroll.id,
        description=f"Holerite {data.competence_month}/{data.competence_year} criado para {emp.name}",
    )
    return payroll


def batch_create_payrolls(
    db: Session,
    data: PayrollBatchCreate,
    company_id: int,
    created_by_id: int,
) -> list[Payroll]:
    """Cria holerites para todos os funcionários elegíveis que ainda não têm um."""
    emps = _eligible_employees(db, company_id, data.competence_month, data.competence_year)
    created = []
    for emp in emps:
        existing = payroll_repo.get_payroll_by_period(
            db, emp.id, data.competence_month, data.competence_year
        )
        if existing:
            continue
        payroll = payroll_repo.create_payroll(db, {
            "employee_id":              emp.id,
            "created_by_id":            created_by_id,
            "competence_month":         data.competence_month,
            "competence_year":          data.competence_year,
            "pay_overtime":             data.pay_overtime,
            "use_hour_bank_for_absences": data.use_hour_bank_for_absences,
        })
        _auto_generate_items(db, payroll, emp)
        db.refresh(payroll)
        created.append(payroll)

    audit_repo.create_log(
        db, action="payroll_batch_created", user_id=created_by_id,
        entity="payroll", entity_id=0,
        description=f"Batch de holerites {data.competence_month}/{data.competence_year}: {len(created)} criado(s)",
    )
    return created


def recalculate_payroll(
    db: Session,
    payroll_id: int,
    company_id: int,
    updated_by_id: int,
) -> Payroll:
    payroll = _get_payroll_or_404(db, payroll_id, company_id)
    _require_draft(payroll)
    emp = emp_repo.get_employee(db, payroll.employee_id)
    _auto_generate_items(db, payroll, emp)
    db.refresh(payroll)
    return payroll


def update_payroll_flags(
    db: Session,
    payroll_id: int,
    data: PayrollFlagsUpdate,
    company_id: int,
    user_id: int,
) -> Payroll:
    """Atualiza flags (pay_overtime, use_hour_bank_for_absences, notes) e recalcula."""
    payroll = _get_payroll_or_404(db, payroll_id, company_id)
    _require_draft(payroll)

    fields = data.model_dump(exclude_none=True)
    payroll_repo.update_payroll(db, payroll, fields)
    db.refresh(payroll)

    # Se mudou flag de cálculo, recalcular itens automáticos
    if "pay_overtime" in fields or "use_hour_bank_for_absences" in fields:
        emp = emp_repo.get_employee(db, payroll.employee_id)
        _auto_generate_items(db, payroll, emp)
        db.refresh(payroll)

    return payroll


def get_payroll(db: Session, payroll_id: int, company_id: int) -> Payroll:
    return _get_payroll_or_404(db, payroll_id, company_id)


def list_by_employee(db: Session, employee_id: int, company_id: int) -> list[Payroll]:
    emp = emp_repo.get_employee(db, employee_id)
    if not emp or emp.company_id != company_id:
        raise HTTPException(status_code=404, detail="Funcionário não encontrado")
    return payroll_repo.list_payrolls_by_employee(db, employee_id)


def list_by_period(db: Session, month: int, year: int, company_id: int) -> list[Payroll]:
    return payroll_repo.list_payrolls_by_period(db, company_id, month, year)


def delete_payroll(db: Session, payroll_id: int, company_id: int, user_id: int) -> None:
    payroll = _get_payroll_or_404(db, payroll_id, company_id)

    # Se estava fechado: reverter parcelas de vale
    if payroll.status == PayrollStatus.CLOSED:
        from app.models.payroll import ValeInstallment
        insts = (
            db.query(ValeInstallment)
            .filter(ValeInstallment.payroll_id == payroll_id)
            .all()
        )
        for inst in insts:
            inst.is_paid = False
            inst.payroll_id = None
        db.flush()

    audit_repo.create_log(
        db, action="payroll_deleted", user_id=user_id,
        entity="payroll", entity_id=payroll_id,
        description=f"Holerite ID {payroll_id} excluído para reprocessamento",
    )
    payroll_repo.delete_payroll(db, payroll)


def add_manual_item(
    db: Session,
    payroll_id: int,
    data: PayrollItemCreate,
    company_id: int,
    user_id: int,
) -> PayrollItem:
    payroll = _get_payroll_or_404(db, payroll_id, company_id)
    _require_draft(payroll)
    item = payroll_repo.add_item(db, payroll_id, {**data.model_dump(), "is_manual": True})
    payroll_repo.recalc_totals(db, payroll)
    return item


def update_item(
    db: Session,
    payroll_id: int,
    item_id: int,
    data: PayrollItemUpdate,
    company_id: int,
    user_id: int,
) -> PayrollItem:
    payroll = _get_payroll_or_404(db, payroll_id, company_id)
    _require_draft(payroll)
    item = payroll_repo.get_item(db, item_id)
    if not item or item.payroll_id != payroll_id:
        raise HTTPException(status_code=404, detail="Item não encontrado")
    updated = payroll_repo.update_item(db, item, {
        **data.model_dump(exclude_none=True),
        "is_manual": True,
    })
    payroll_repo.recalc_totals(db, payroll)
    return updated


def delete_item(
    db: Session,
    payroll_id: int,
    item_id: int,
    company_id: int,
    user_id: int,
) -> None:
    payroll = _get_payroll_or_404(db, payroll_id, company_id)
    _require_draft(payroll)
    item = payroll_repo.get_item(db, item_id)
    if not item or item.payroll_id != payroll_id:
        raise HTTPException(status_code=404, detail="Item não encontrado")
    payroll_repo.delete_item(db, item)
    payroll_repo.recalc_totals(db, payroll)


def close_payroll(
    db: Session,
    payroll_id: int,
    payment_date: date | None,
    company_id: int,
    user_id: int,
) -> Payroll:
    payroll = _get_payroll_or_404(db, payroll_id, company_id)
    _require_draft(payroll)

    period = ts_repo.get_period(db, company_id, payroll.competence_month, payroll.competence_year)
    if period and period.status != "closed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"O ponto de {payroll.competence_month:02d}/{payroll.competence_year} ainda está aberto.",
        )

    installments = payroll_repo.list_pending_installments(
        db, payroll.employee_id, payroll.competence_month, payroll.competence_year
    )
    for inst in installments:
        payroll_repo.mark_installment_paid(db, inst, payroll_id)

    if payment_date:
        payroll_repo.update_payroll(db, payroll, {"payment_date": payment_date})

    closed = payroll_repo.close_payroll(db, payroll, None)

    audit_repo.create_log(
        db, action="payroll_closed", user_id=user_id,
        entity="payroll", entity_id=payroll_id,
        description=f"Holerite ID {payroll_id} fechado",
    )
    return closed


def close_all_payrolls(
    db: Session,
    month: int,
    year: int,
    payment_date: date | None,
    company_id: int,
    user_id: int,
) -> list[Payroll]:
    """Fecha todos os holerites em rascunho para o período."""
    period = ts_repo.get_period(db, company_id, month, year)
    if period and period.status != "closed":
        raise HTTPException(
            status_code=400,
            detail=f"O ponto de {month:02d}/{year} ainda está aberto.",
        )

    payrolls = payroll_repo.list_payrolls_by_period(db, company_id, month, year)
    closed = []
    for p in payrolls:
        if p.status == PayrollStatus.CLOSED:
            continue
        insts = payroll_repo.list_pending_installments(db, p.employee_id, month, year)
        for inst in insts:
            payroll_repo.mark_installment_paid(db, inst, p.id)
        if payment_date:
            payroll_repo.update_payroll(db, p, {"payment_date": payment_date})
        payroll_repo.close_payroll(db, p, None)
        closed.append(p)

    audit_repo.create_log(
        db, action="payroll_batch_closed", user_id=user_id,
        entity="payroll", entity_id=0,
        description=f"Fechamento em lote {month}/{year}: {len(closed)} holerite(s)",
    )
    return payrolls


# ── Vale ──────────────────────────────────────────────────────────────────────

def create_vale(
    db: Session,
    employee_id: int,
    data: ValeCreate,
    company_id: int,
    registered_by_id: int,
) -> Vale:
    emp = _get_employee(db, employee_id, company_id)

    inst_amount = (data.total_amount / Decimal(data.installments)).quantize(Decimal("0.01"))
    last_amount = data.total_amount - inst_amount * (data.installments - 1)

    installments_data = []
    y, m = data.issued_date.year, data.issued_date.month
    y, m = next_month(y, m)
    for i in range(1, data.installments + 1):
        installments_data.append({
            "installment_number": i,
            "amount": last_amount if i == data.installments else inst_amount,
            "due_month": m, "due_year": y, "is_paid": False,
        })
        y, m = next_month(y, m)

    vale = payroll_repo.create_vale(db, {
        "employee_id": employee_id,
        "registered_by_id": registered_by_id,
        "total_amount": data.total_amount,
        "installments": data.installments,
        "notes": data.notes,
        "issued_date": data.issued_date,
    }, installments_data)

    audit_repo.create_log(
        db, action="vale_created", user_id=registered_by_id,
        entity="vale", entity_id=vale.id,
        description=f"Vale R$ {data.total_amount} em {data.installments}x para {emp.name}",
    )
    return vale


def get_vale(db: Session, vale_id: int, company_id: int) -> Vale:
    vale = payroll_repo.get_vale(db, vale_id)
    if not vale:
        raise HTTPException(status_code=404, detail="Vale não encontrado")
    emp = emp_repo.get_employee(db, vale.employee_id)
    if not emp or emp.company_id != company_id:
        raise HTTPException(status_code=404, detail="Vale não encontrado")
    return vale


def list_all_vales(db: Session, company_id: int) -> list[Vale]:
    return payroll_repo.list_all_vales_by_company(db, company_id)


def list_vales_by_employee(db: Session, employee_id: int, company_id: int) -> list[Vale]:
    emp = _get_employee(db, employee_id, company_id)
    return payroll_repo.list_vales_by_employee(db, emp.id)
