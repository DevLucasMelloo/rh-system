"""
Serviço de Relatórios e Dashboard.
Gera estatísticas agregadas e exportações em Excel (BytesIO).
"""
import io
import calendar
from datetime import date, timedelta
from decimal import Decimal

import pandas as pd
from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from app.models.employee import Employee, EmployeeStatus
from app.models.payroll import Payroll, PayrollStatus
from app.models.timesheet import TimesheetEntry
from app.models.vacation import Vacation, VacationStatus
from app.models.termination import Termination
from app.schemas.reports import DashboardRead, BirthdayRead, VacationExpiringRead
from app.repositories import seamstress as seamstress_repo


# ── Dashboard ─────────────────────────────────────────────────────────────────

def get_dashboard(db: Session, company_id: int) -> DashboardRead:
    today = date.today()
    month, year = today.month, today.year

    # ── Funcionários ──────────────────────────────────────────────────────────
    all_emps = (
        db.query(Employee)
        .filter(Employee.company_id == company_id)
        .all()
    )
    active   = [e for e in all_emps if e.status == EmployeeStatus.ACTIVE]
    inactive = [e for e in all_emps if e.status == EmployeeStatus.INACTIVE]
    new_hires = [
        e for e in active
        if e.admission_date and e.admission_date >= today - timedelta(days=30)
    ]

    # ── Folha do mês ──────────────────────────────────────────────────────────
    payrolls = (
        db.query(Payroll)
        .join(Employee)
        .filter(
            Employee.company_id == company_id,
            Payroll.competence_month == month,
            Payroll.competence_year  == year,
        )
        .all()
    )
    payrolls_draft  = sum(1 for p in payrolls if p.status == PayrollStatus.DRAFT)
    payrolls_closed = sum(1 for p in payrolls if p.status == PayrollStatus.CLOSED)
    total_net = sum(
        Decimal(str(p.net_salary)) for p in payrolls if p.status == PayrollStatus.CLOSED
    )

    # ── Ponto do mês ──────────────────────────────────────────────────────────
    first_day = date(year, month, 1)
    last_day  = date(year, month, calendar.monthrange(year, month)[1])
    entries   = (
        db.query(TimesheetEntry)
        .join(Employee)
        .filter(
            Employee.company_id == company_id,
            TimesheetEntry.work_date >= first_day,
            TimesheetEntry.work_date <= last_day,
            TimesheetEntry.is_annulled == False,
        )
        .all()
    )
    total_absences  = sum(1 for e in entries if e.is_absence and not e.is_medical_certificate)
    total_ot_min    = sum(e.overtime_minutes for e in entries)
    total_ot_hours  = Decimal(str(total_ot_min)) / Decimal("60")

    # ── Férias ────────────────────────────────────────────────────────────────
    vacs = (
        db.query(Vacation)
        .join(Employee)
        .filter(Employee.company_id == company_id)
        .all()
    )
    vacs_active     = sum(1 for v in vacs if v.status == VacationStatus.ACTIVE)
    vacs_scheduled  = sum(1 for v in vacs if v.status == VacationStatus.SCHEDULED)
    cutoff_60d      = today + timedelta(days=60)
    vacs_expiring   = [
        v for v in vacs
        if v.status in (VacationStatus.SCHEDULED, VacationStatus.ACTIVE)
        and v.acquisition_end <= cutoff_60d
    ]

    # ── Aniversários nos próximos 30 dias ─────────────────────────────────────
    birthdays: list[BirthdayRead] = []
    for emp in active:
        if not emp.date_of_birth:
            continue
        dob = emp.date_of_birth
        try:
            next_bday = date(today.year, dob.month, dob.day)
        except ValueError:
            # 29-fev em ano não bissexto
            next_bday = date(today.year, 3, 1)
        if next_bday < today:
            try:
                next_bday = date(today.year + 1, dob.month, dob.day)
            except ValueError:
                next_bday = date(today.year + 1, 3, 1)
        days_until = (next_bday - today).days
        if days_until <= 30:
            birthdays.append(BirthdayRead(
                employee_id=emp.id,
                name=emp.name,
                date_of_birth=dob,
                days_until=days_until,
            ))
    birthdays.sort(key=lambda b: b.days_until)

    # ── Férias expirando (detalhado) ──────────────────────────────────────────
    expiring: list[VacationExpiringRead] = []
    for v in vacs_expiring:
        emp = db.get(Employee, v.employee_id)
        days_left = (v.acquisition_end - today).days
        expiring.append(VacationExpiringRead(
            employee_id=v.employee_id,
            employee_name=emp.name if emp else "—",
            acquisition_end=v.acquisition_end,
            days_until_expiry=days_left,
            status=v.status.value,
        ))
    expiring.sort(key=lambda x: x.days_until_expiry)

    # ── Costureiras ───────────────────────────────────────────────────────────
    seamstress_pending, seamstress_paid, seamstress_entrega = seamstress_repo.month_totals(
        db, company_id, month, year
    )

    return DashboardRead(
        total_employees=len(all_emps),
        active_employees=len(active),
        inactive_employees=len(inactive),
        new_hires_30_days=len(new_hires),
        current_month=month,
        current_year=year,
        payrolls_draft=payrolls_draft,
        payrolls_closed=payrolls_closed,
        total_net_salary=total_net,
        total_absences_month=total_absences,
        total_overtime_hours_month=total_ot_hours.quantize(Decimal("0.01")),
        vacations_active=vacs_active,
        vacations_scheduled=vacs_scheduled,
        vacations_expiring_60d=len(vacs_expiring),
        birthdays_next_30_days=birthdays,
        expiring_vacations=expiring,
        seamstress_pending_month=Decimal(str(seamstress_pending)) if seamstress_pending else Decimal(0),
        seamstress_paid_month=Decimal(str(seamstress_paid)) if seamstress_paid else Decimal(0),
        seamstress_entrega_month=Decimal(str(seamstress_entrega)) if seamstress_entrega else Decimal(0),
        seamstress_total_month=(
            Decimal(str(seamstress_pending or 0)) +
            Decimal(str(seamstress_paid or 0)) +
            Decimal(str(seamstress_entrega or 0))
        ),
    )


# ── Helpers Excel ─────────────────────────────────────────────────────────────

def _df_to_bytes(df: pd.DataFrame, sheet_name: str) -> bytes:
    """Converte DataFrame para bytes de .xlsx em memória."""
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name=sheet_name, index=False)
    buf.seek(0)
    return buf.read()


def _mask_cpf(cpf: str | None) -> str:
    """Mascara CPF: 529.982.247-25 → ***.***.247-**"""
    if not cpf:
        return ""
    digits = "".join(c for c in cpf if c.isdigit())
    if len(digits) == 11:
        return f"***.***. {digits[6:9]}-**"
    return "***"


# ── Relatório: Folha do Mês ───────────────────────────────────────────────────

def report_payroll(db: Session, company_id: int, month: int, year: int) -> bytes:
    """
    Planilha: resumo da folha de pagamento do mês.
    Uma linha por funcionário.
    """
    payrolls = (
        db.query(Payroll)
        .join(Employee)
        .filter(
            Employee.company_id == company_id,
            Payroll.competence_month == month,
            Payroll.competence_year  == year,
        )
        .order_by(Employee.name)
        .all()
    )

    rows = []
    for p in payrolls:
        emp = db.get(Employee, p.employee_id)
        rows.append({
            "Funcionário":        emp.name if emp else "",
            "Cargo":              emp.role if emp else "",
            "Competência":        f"{month:02d}/{year}",
            "Dias Trabalhados":   p.worked_days,
            "Horas Extras (h)":   float(p.total_overtime_hours),
            "Salário Bruto":      float(p.gross_salary),
            "Total Benefícios":   float(p.total_benefits),
            "Total Descontos":    float(p.total_discounts),
            "Salário Líquido":    float(p.net_salary),
            "Status":             p.status.value,
            "Data Pagamento":     str(p.payment_date) if p.payment_date else "",
        })

    df = pd.DataFrame(rows) if rows else pd.DataFrame(
        columns=["Funcionário", "Cargo", "Competência", "Dias Trabalhados",
                 "Horas Extras (h)", "Salário Bruto", "Total Benefícios",
                 "Total Descontos", "Salário Líquido", "Status", "Data Pagamento"]
    )
    return _df_to_bytes(df, f"Folha {month:02d}-{year}")


# ── Relatório: Espelho de Ponto ───────────────────────────────────────────────

def report_timesheet(
    db: Session,
    company_id: int,
    month: int,
    year: int,
    employee_id: int | None = None,
) -> bytes:
    """
    Planilha: espelho de ponto do mês.
    Filtro opcional por funcionário.
    """
    first_day = date(year, month, 1)
    last_day  = date(year, month, calendar.monthrange(year, month)[1])

    q = (
        db.query(TimesheetEntry)
        .join(Employee)
        .filter(
            Employee.company_id == company_id,
            TimesheetEntry.work_date >= first_day,
            TimesheetEntry.work_date <= last_day,
        )
    )
    if employee_id:
        q = q.filter(TimesheetEntry.employee_id == employee_id)

    entries = q.order_by(Employee.name, TimesheetEntry.work_date).all()

    rows = []
    for e in entries:
        emp = db.get(Employee, e.employee_id)
        rows.append({
            "Funcionário":         emp.name if emp else "",
            "Data":                str(e.work_date),
            "Entrada":             str(e.entry_time)    if e.entry_time    else "",
            "Saída Almoço":        str(e.lunch_out_time) if e.lunch_out_time else "",
            "Retorno Almoço":      str(e.lunch_in_time) if e.lunch_in_time else "",
            "Saída":               str(e.exit_time)     if e.exit_time     else "",
            "Trabalhado (min)":    e.worked_minutes,
            "Hora Extra (min)":    e.overtime_minutes,
            "Atraso (min)":        e.late_minutes,
            "Falta":               "Sim" if e.is_absence and not e.is_annulled else "",
            "Atestado":            "Sim" if e.is_medical_certificate else "",
            "Anulado":             "Sim" if e.is_annulled else "",
        })

    df = pd.DataFrame(rows) if rows else pd.DataFrame(
        columns=["Funcionário", "Data", "Entrada", "Saída Almoço", "Retorno Almoço",
                 "Saída", "Trabalhado (min)", "Hora Extra (min)", "Atraso (min)",
                 "Falta", "Atestado", "Anulado"]
    )
    return _df_to_bytes(df, f"Ponto {month:02d}-{year}")


# ── Relatório: Funcionários ───────────────────────────────────────────────────

def report_employees(db: Session, company_id: int, include_inactive: bool = False) -> bytes:
    """
    Planilha: cadastro de funcionários.
    CPF é mascarado por segurança.
    """
    from app.core.security import decrypt_field

    q = db.query(Employee).filter(Employee.company_id == company_id)
    if not include_inactive:
        q = q.filter(Employee.status == EmployeeStatus.ACTIVE)

    employees = q.order_by(Employee.name).all()

    rows = []
    for emp in employees:
        cpf_plain = ""
        try:
            cpf_plain = decrypt_field(emp.cpf_encrypted) if emp.cpf_encrypted else ""
        except Exception:
            cpf_plain = "***"
        rows.append({
            "Nome":              emp.name,
            "CPF":               _mask_cpf(cpf_plain),
            "Cargo":             emp.role,
            "Salário":           float(emp.salary),
            "Data Admissão":     str(emp.admission_date),
            "Data Registro":     str(emp.registration_date),
            "Status":            emp.status.value,
            "Data Inativação":   str(emp.inactivation_date) if emp.inactivation_date else "",
            "Motivo Inativação": emp.inactivation_reason or "",
            "Cidade":            emp.city or "",
            "Estado":            emp.state or "",
        })

    df = pd.DataFrame(rows) if rows else pd.DataFrame(
        columns=["Nome", "CPF", "Cargo", "Salário", "Data Admissão",
                 "Data Registro", "Status", "Data Inativação", "Motivo Inativação",
                 "Cidade", "Estado"]
    )
    return _df_to_bytes(df, "Funcionários")


# ── Relatório: Férias ─────────────────────────────────────────────────────────

def report_vacations(db: Session, company_id: int) -> bytes:
    """
    Planilha: férias de todos os funcionários.
    """
    vacs = (
        db.query(Vacation)
        .join(Employee)
        .filter(Employee.company_id == company_id)
        .order_by(Employee.name, Vacation.acquisition_start)
        .all()
    )

    rows = []
    for v in vacs:
        emp = db.get(Employee, v.employee_id)
        rows.append({
            "Funcionário":        emp.name if emp else "",
            "Período Aquisitivo Início": str(v.acquisition_start),
            "Período Aquisitivo Fim":    str(v.acquisition_end),
            "Início Gozo":        str(v.enjoyment_start) if v.enjoyment_start else "",
            "Dias de Gozo":       v.enjoyment_days,
            "Fracionado":         "Sim" if v.is_fractioned else "Não",
            "Remuneração Base":   float(v.base_salary)      if v.base_salary      else "",
            "1/3 Constitucional": float(v.one_third_bonus)  if v.one_third_bonus  else "",
            "INSS":               float(v.inss_discount)    if v.inss_discount    else "",
            "Líquido":            float(v.net_vacation_pay) if v.net_vacation_pay else "",
            "Status":             v.status.value,
        })

    df = pd.DataFrame(rows) if rows else pd.DataFrame(
        columns=["Funcionário", "Período Aquisitivo Início", "Período Aquisitivo Fim",
                 "Início Gozo", "Dias de Gozo", "Fracionado", "Remuneração Base",
                 "1/3 Constitucional", "INSS", "Líquido", "Status"]
    )
    return _df_to_bytes(df, "Férias")


# ── Relatório: Rescisões ──────────────────────────────────────────────────────

def report_terminations(db: Session, company_id: int) -> bytes:
    """
    Planilha: rescisões da empresa.
    """
    terms = (
        db.query(Termination)
        .join(Employee)
        .filter(Employee.company_id == company_id)
        .order_by(Termination.termination_date.desc())
        .all()
    )

    rows = []
    for t in terms:
        emp = db.get(Employee, t.employee_id)
        rows.append({
            "Funcionário":          emp.name if emp else "",
            "Data Rescisão":        str(t.termination_date),
            "Motivo":               t.reason.value,
            "Aviso (dias)":         t.notice_days,
            "Aviso Trabalhado":     "Sim" if t.notice_worked else "Não",
            "Saldo Salário":        float(t.saldo_salario),
            "Férias Proporcionais": float(t.ferias_proporcionais),
            "1/3 Férias Prop.":     float(t.um_terco_ferias_prop),
            "Férias Vencidas":      float(t.ferias_vencidas),
            "1/3 Férias Venc.":     float(t.um_terco_ferias_venc),
            "13º Proporcional":     float(t.decimo_terceiro_prop),
            "Aviso Indenizado":     float(t.aviso_previo_indenizado),
            "Multa FGTS":           float(t.multa_fgts),
            "INSS Rescisão":        float(t.inss_rescisao),
            "Total Créditos":       float(t.total_creditos),
            "Total Descontos":      float(t.total_descontos),
            "Líquido":              float(t.liquido),
        })

    df = pd.DataFrame(rows) if rows else pd.DataFrame(
        columns=["Funcionário", "Data Rescisão", "Motivo", "Aviso (dias)",
                 "Aviso Trabalhado", "Saldo Salário", "Férias Proporcionais",
                 "1/3 Férias Prop.", "Férias Vencidas", "1/3 Férias Venc.",
                 "13º Proporcional", "Aviso Indenizado", "Multa FGTS",
                 "INSS Rescisão", "Total Créditos", "Total Descontos", "Líquido"]
    )
    return _df_to_bytes(df, "Rescisões")


# ── Relatório: Banco de Horas ─────────────────────────────────────────────────

def report_hour_bank(db: Session, company_id: int) -> bytes:
    """Planilha: saldo de banco de horas de todos os funcionários ativos."""
    from app.models.timesheet import HourBank

    rows = (
        db.query(Employee, HourBank)
        .outerjoin(HourBank, HourBank.employee_id == Employee.id)
        .filter(
            Employee.company_id == company_id,
            Employee.status == EmployeeStatus.ACTIVE,
        )
        .order_by(Employee.name)
        .all()
    )

    data = []
    for emp, hb in rows:
        balance_min = hb.balance_minutes if hb else 0
        signal = "+" if balance_min >= 0 else "-"
        abs_min = abs(balance_min)
        h, m = divmod(abs_min, 60)
        data.append({
            "Funcionário":       emp.name,
            "Cargo":             emp.role,
            "Saldo (min)":       balance_min,
            "Saldo Formatado":   f"{signal}{h:02d}:{m:02d}",
        })

    df = pd.DataFrame(data) if data else pd.DataFrame(
        columns=["Funcionário", "Cargo", "Saldo (min)", "Saldo Formatado"]
    )
    return _df_to_bytes(df, "Banco de Horas")
