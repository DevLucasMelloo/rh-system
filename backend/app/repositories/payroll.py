from datetime import date
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_

from app.models.payroll import Payroll, PayrollItem, Vale, ValeInstallment, PayrollStatus


# ── Payroll ───────────────────────────────────────────────────────────────────

def get_payroll(db: Session, payroll_id: int) -> Payroll | None:
    return (
        db.query(Payroll)
        .options(joinedload(Payroll.items), joinedload(Payroll.employee))
        .filter(Payroll.id == payroll_id)
        .first()
    )


def get_payroll_by_period(
    db: Session, employee_id: int, month: int, year: int
) -> Payroll | None:
    return (
        db.query(Payroll)
        .filter(and_(
            Payroll.employee_id == employee_id,
            Payroll.competence_month == month,
            Payroll.competence_year == year,
        ))
        .first()
    )


def list_payrolls_by_employee(db: Session, employee_id: int) -> list[Payroll]:
    return (
        db.query(Payroll)
        .options(joinedload(Payroll.items))
        .filter(Payroll.employee_id == employee_id)
        .order_by(Payroll.competence_year.desc(), Payroll.competence_month.desc())
        .all()
    )


def list_payrolls_by_period(
    db: Session, company_id: int, month: int, year: int
) -> list[Payroll]:
    from app.models.employee import Employee
    return (
        db.query(Payroll)
        .join(Employee)
        .options(joinedload(Payroll.items), joinedload(Payroll.employee))
        .filter(and_(
            Employee.company_id == company_id,
            Payroll.competence_month == month,
            Payroll.competence_year == year,
        ))
        .order_by(Employee.name)
        .all()
    )


def create_payroll(db: Session, fields: dict) -> Payroll:
    p = Payroll(**fields)
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def update_payroll(db: Session, payroll: Payroll, fields: dict) -> Payroll:
    for k, v in fields.items():
        setattr(payroll, k, v)
    db.commit()
    db.refresh(payroll)
    return payroll


def close_payroll(db: Session, payroll: Payroll, pdf_path: str | None) -> Payroll:
    from datetime import datetime, timezone
    payroll.status = PayrollStatus.CLOSED
    payroll.closed_at = datetime.now(timezone.utc)
    if pdf_path:
        payroll.pdf_path = pdf_path
    db.commit()
    db.refresh(payroll)
    return payroll


# ── PayrollItem ───────────────────────────────────────────────────────────────

def add_item(db: Session, payroll_id: int, fields: dict) -> PayrollItem:
    item = PayrollItem(payroll_id=payroll_id, **fields)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update_item(db: Session, item: PayrollItem, fields: dict) -> PayrollItem:
    for k, v in fields.items():
        setattr(item, k, v)
    db.commit()
    db.refresh(item)
    return item


def get_item(db: Session, item_id: int) -> PayrollItem | None:
    return db.get(PayrollItem, item_id)


def delete_item(db: Session, item: PayrollItem) -> None:
    db.delete(item)
    db.commit()


def recalc_totals(db: Session, payroll: Payroll) -> Payroll:
    """Recalcula gross/benefits/discounts/net a partir dos itens."""
    db.refresh(payroll)
    credits = sum(i.amount for i in payroll.items if i.is_credit)
    debits = sum(i.amount for i in payroll.items if not i.is_credit)
    payroll.total_benefits = credits
    payroll.total_discounts = debits
    payroll.net_salary = credits - debits
    # gross = soma dos créditos de natureza salarial
    salary_types = {"salario", "hora_extra", "adicional", "bonificacao"}
    payroll.gross_salary = sum(
        i.amount for i in payroll.items
        if i.is_credit and i.item_type.value in salary_types
    )
    db.commit()
    db.refresh(payroll)
    return payroll


# ── Vale ──────────────────────────────────────────────────────────────────────

def create_vale(db: Session, fields: dict, installments: list[dict]) -> Vale:
    vale = Vale(**fields)
    db.add(vale)
    db.flush()  # obtém o ID sem commitar
    for inst in installments:
        db.add(ValeInstallment(vale_id=vale.id, **inst))
    db.commit()
    db.refresh(vale)
    return vale


def get_vale(db: Session, vale_id: int) -> Vale | None:
    return (
        db.query(Vale)
        .options(joinedload(Vale.installment_items))
        .filter(Vale.id == vale_id)
        .first()
    )


def list_vales_by_employee(db: Session, employee_id: int) -> list[Vale]:
    return (
        db.query(Vale)
        .options(joinedload(Vale.installment_items))
        .filter(Vale.employee_id == employee_id)
        .order_by(Vale.competence_year.desc(), Vale.competence_month.desc())
        .all()
    )


def list_pending_installments(
    db: Session, employee_id: int, month: int, year: int
) -> list[ValeInstallment]:
    """Parcelas de vale pendentes para descontar no holerite do mês/ano."""
    return (
        db.query(ValeInstallment)
        .join(Vale)
        .filter(and_(
            Vale.employee_id == employee_id,
            ValeInstallment.due_month == month,
            ValeInstallment.due_year == year,
            ValeInstallment.is_paid == False,
        ))
        .all()
    )


def mark_installment_paid(
    db: Session, installment: ValeInstallment, payroll_id: int
) -> None:
    installment.is_paid = True
    installment.payroll_id = payroll_id
    db.commit()
