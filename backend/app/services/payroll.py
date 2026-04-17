"""
Serviço de Folha de Pagamento.
Toda a lógica de cálculo fica aqui — os repositórios apenas acessam o banco.
"""
from datetime import date
from decimal import Decimal
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.repositories import payroll as payroll_repo
from app.repositories import employee as emp_repo
from app.repositories import timesheet as ts_repo
from app.repositories import audit_log as audit_repo
from app.models.payroll import Payroll, PayrollItem, Vale, PayrollItemType, PayrollStatus
from app.models.employee import Employee, EmployeeStatus
from app.schemas.payroll import PayrollCreate, PayrollItemCreate, PayrollItemUpdate, ValeCreate
from app.utils.payroll_calc import (
    working_days_in_month, calc_proportional_salary,
    calc_overtime_value, calc_vt, calc_dsr_discount,
    count_worked_months_for_thirteenth, next_month,
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


# ── Cálculo automático ────────────────────────────────────────────────────────

def _auto_generate_items(
    db: Session,
    payroll: Payroll,
    emp: Employee,
) -> None:
    """
    Apaga todos os itens gerados automaticamente (is_manual=False)
    e recria com base nos dados do ponto e nas regras salariais.
    Manual items are preserved.
    """
    # Remover apenas itens automáticos
    for item in list(payroll.items):
        if not item.is_manual:
            db.delete(item)
    db.flush()
    db.refresh(payroll)

    month = payroll.competence_month
    year = payroll.competence_year

    # ── Dados do ponto ────────────────────────────────────────────────────────
    entries = ts_repo.list_entries_by_month(db, emp.id, month, year)
    absences = sum(1 for e in entries if e.is_absence and not e.is_annulled)
    medical_certs = sum(1 for e in entries if e.is_medical_certificate)
    total_overtime_min = sum(e.overtime_minutes for e in entries)

    # Dias trabalhados = dias úteis do mês - faltas injustificadas
    total_working_days = working_days_in_month(year, month)
    worked_days = max(0, total_working_days - absences)

    # ── Salário proporcional ──────────────────────────────────────────────────
    base_salary = Decimal(str(emp.salary))
    salary_value = calc_proportional_salary(base_salary, worked_days, total_working_days)

    _add_auto_item(db, payroll.id, PayrollItemType.SALARY, "Salário", salary_value, True)

    # ── Hora extra ────────────────────────────────────────────────────────────
    if total_overtime_min > 0:
        overtime_value = calc_overtime_value(base_salary, total_overtime_min)
        _add_auto_item(db, payroll.id, PayrollItemType.OVERTIME, "Horas Extras", overtime_value, True)

    # ── Vale Transporte ───────────────────────────────────────────────────────
    vt_value = calc_vt(year, month, absences, medical_certs)
    if vt_value > 0:
        _add_auto_item(db, payroll.id, PayrollItemType.VT, "Vale Transporte", vt_value, True)

    # ── Desconto DSR ──────────────────────────────────────────────────────────
    if absences > 0:
        dsr = calc_dsr_discount(base_salary, absences)
        _add_auto_item(db, payroll.id, PayrollItemType.DSR, "Desconto DSR", dsr, False)

    # ── Desconto faltas ───────────────────────────────────────────────────────
    if absences > 0:
        absence_discount = (
            base_salary * Decimal(absences) / Decimal(total_working_days)
        ).quantize(Decimal("0.01"))
        _add_auto_item(
            db, payroll.id, PayrollItemType.ABSENCE,
            f"Desconto de Faltas ({absences} dia(s))", absence_discount, False,
        )

    # ── INSS ──────────────────────────────────────────────────────────────────
    gross_for_inss = salary_value + (
        calc_overtime_value(base_salary, total_overtime_min) if total_overtime_min > 0 else Decimal("0")
    )
    inss_value = calc_inss(gross_for_inss)
    _add_auto_item(db, payroll.id, PayrollItemType.INSS, "INSS", inss_value, False)

    # ── Parcelas de vale pendentes ────────────────────────────────────────────
    installments = payroll_repo.list_pending_installments(db, emp.id, month, year)
    for inst in installments:
        _add_auto_item(
            db, payroll.id, PayrollItemType.VALE_DESCONTO,
            f"Vale (parcela {inst.installment_number})", inst.amount, False,
        )

    # ── Atualizar metadados do holerite ───────────────────────────────────────
    payroll_repo.update_payroll(db, payroll, {
        "worked_days": worked_days,
        "total_overtime_hours": Decimal(str(total_overtime_min)) / Decimal("60"),
    })

    db.commit()
    payroll_repo.recalc_totals(db, payroll)


def _add_auto_item(
    db: Session,
    payroll_id: int,
    item_type: PayrollItemType,
    description: str,
    amount: Decimal,
    is_credit: bool,
) -> None:
    from app.models.payroll import PayrollItem
    item = PayrollItem(
        payroll_id=payroll_id,
        item_type=item_type,
        description=description,
        amount=amount,
        is_credit=is_credit,
        is_manual=False,
        show_on_payslip=True,
    )
    db.add(item)


# ── Operações de Holerite ─────────────────────────────────────────────────────

def create_payroll(
    db: Session,
    data: PayrollCreate,
    company_id: int,
    created_by_id: int,
) -> Payroll:
    emp = _get_employee(db, data.employee_id, company_id)

    # Impede duplicata
    existing = payroll_repo.get_payroll_by_period(
        db, data.employee_id, data.competence_month, data.competence_year
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail="Já existe holerite para esse funcionário no período informado",
        )

    payroll = payroll_repo.create_payroll(db, {
        "employee_id": data.employee_id,
        "created_by_id": created_by_id,
        "competence_month": data.competence_month,
        "competence_year": data.competence_year,
    })

    _auto_generate_items(db, payroll, emp)
    db.refresh(payroll)

    audit_repo.create_log(
        db, action="payroll_created", user_id=created_by_id,
        entity="payroll", entity_id=payroll.id,
        description=f"Holerite {data.competence_month}/{data.competence_year} criado para funcionário ID {emp.id}",
    )
    return payroll


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


def get_payroll(db: Session, payroll_id: int, company_id: int) -> Payroll:
    return _get_payroll_or_404(db, payroll_id, company_id)


def list_by_employee(db: Session, employee_id: int, company_id: int) -> list[Payroll]:
    emp = emp_repo.get_employee(db, employee_id)
    if not emp or emp.company_id != company_id:
        raise HTTPException(status_code=404, detail="Funcionário não encontrado")
    return payroll_repo.list_payrolls_by_employee(db, employee_id)


def list_by_period(
    db: Session, month: int, year: int, company_id: int
) -> list[Payroll]:
    return payroll_repo.list_payrolls_by_period(db, company_id, month, year)


def add_manual_item(
    db: Session,
    payroll_id: int,
    data: PayrollItemCreate,
    company_id: int,
    user_id: int,
) -> PayrollItem:
    payroll = _get_payroll_or_404(db, payroll_id, company_id)
    _require_draft(payroll)
    item = payroll_repo.add_item(db, payroll_id, {
        **data.model_dump(),
        "is_manual": True,
    })
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

    # Marcar parcelas de vale como pagas
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


# ── Vale ──────────────────────────────────────────────────────────────────────

def create_vale(
    db: Session,
    employee_id: int,
    data: ValeCreate,
    company_id: int,
    registered_by_id: int,
) -> Vale:
    emp = _get_employee(db, employee_id, company_id)

    # Gerar parcelas: distribuição igual com arredondamento na última
    from app.utils.payroll_calc import next_month
    inst_amount = (data.total_amount / Decimal(data.installments)).quantize(Decimal("0.01"))
    # Ajuste de arredondamento na última parcela
    last_amount = data.total_amount - inst_amount * (data.installments - 1)

    installments_data = []
    y, m = data.issued_date.year, data.issued_date.month
    # Primeira parcela no mês seguinte à emissão
    y, m = next_month(y, m)
    for i in range(1, data.installments + 1):
        installments_data.append({
            "installment_number": i,
            "amount": last_amount if i == data.installments else inst_amount,
            "due_month": m,
            "due_year": y,
            "is_paid": False,
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
        description=f"Vale R$ {data.total_amount} em {data.installments}x para funcionário ID {employee_id}",
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


def list_vales_by_employee(db: Session, employee_id: int, company_id: int) -> list[Vale]:
    emp = _get_employee(db, employee_id, company_id)
    return payroll_repo.list_vales_by_employee(db, emp.id)
