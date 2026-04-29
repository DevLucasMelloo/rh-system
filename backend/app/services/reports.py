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
from app.services.vacation import _auto_advance_status
from app.models.termination import Termination
from app.schemas.reports import DashboardRead, BirthdayRead, VacationExpiringRead, ScheduledVacationRead, ActiveVacationRead, MonthlyTotalRead, AnnualPayrollRead, AnnualEmployeeRow, AnnualEmployeeMonth
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

    # (ponto removido dos cards do dashboard)

    # ── Férias ────────────────────────────────────────────────────────────────
    vacs = (
        db.query(Vacation)
        .join(Employee)
        .filter(Employee.company_id == company_id)
        .all()
    )
    vacs = [_auto_advance_status(db, v) for v in vacs]
    vacs_active     = sum(1 for v in vacs if v.status == VacationStatus.ACTIVE)
    vacs_scheduled  = sum(1 for v in vacs if v.status == VacationStatus.SCHEDULED)
    cutoff_60d      = today + timedelta(days=60)
    vacs_expiring   = [
        v for v in vacs
        if v.status in (VacationStatus.SCHEDULED, VacationStatus.ACTIVE)
        and v.acquisition_end <= cutoff_60d          # vence nos próximos 60 dias OU já venceu
    ]

    # ── Aniversários do mês atual ─────────────────────────────────────────────
    birthdays: list[BirthdayRead] = []
    for emp in active:
        if not emp.date_of_birth:
            continue
        dob = emp.date_of_birth
        if dob.month != today.month:
            continue
        try:
            bday_this_year = date(today.year, dob.month, dob.day)
        except ValueError:
            bday_this_year = date(today.year, 3, 1)
        days_until = (bday_this_year - today).days
        birthdays.append(BirthdayRead(
            employee_id=emp.id,
            name=emp.name,
            date_of_birth=dob,
            days_until=days_until,
            birth_day=dob.day,
            role=getattr(emp, "role", None),
        ))
    birthdays.sort(key=lambda b: b.birth_day)

    # ── Férias expirando/vencidas (detalhado) ────────────────────────────────
    expiring: list[VacationExpiringRead] = []
    for v in vacs_expiring:
        emp = db.get(Employee, v.employee_id)
        days_left = (v.acquisition_end - today).days
        expiring.append(VacationExpiringRead(
            employee_id=v.employee_id,
            employee_name=emp.name if emp else "—",
            role=getattr(emp, "role", None) if emp else None,
            acquisition_end=v.acquisition_end,
            days_until_expiry=days_left,
            is_expired=days_left < 0,
            status=v.status.value,
        ))
    # Vencidas primeiro (mais urgentes), depois por proximidade
    expiring.sort(key=lambda x: x.days_until_expiry)

    # ── Férias Agendadas ─────────────────────────────────────────────────────
    scheduled_vacations: list[ScheduledVacationRead] = []
    for v in vacs:
        if not v.enjoyment_start or v.enjoyment_start <= today:
            continue
        if v.status not in (VacationStatus.SCHEDULED, VacationStatus.ACTIVE):
            continue
        emp = db.get(Employee, v.employee_id)
        scheduled_vacations.append(ScheduledVacationRead(
            employee_id=v.employee_id,
            employee_name=emp.name if emp else "—",
            enjoyment_start=v.enjoyment_start,
            enjoyment_days=v.enjoyment_days,
        ))
    scheduled_vacations.sort(key=lambda x: x.enjoyment_start)

    # ── Em Férias ────────────────────────────────────────────────────────────
    active_vacations: list[ActiveVacationRead] = []
    for v in vacs:
        if not v.enjoyment_start or v.enjoyment_start > today:
            continue
        if v.status not in (VacationStatus.SCHEDULED, VacationStatus.ACTIVE):
            continue
        enjoyment_end = v.enjoyment_start + timedelta(days=v.enjoyment_days - 1)
        if enjoyment_end < today:
            continue  # já terminou, não mostrar
        emp = db.get(Employee, v.employee_id)
        active_vacations.append(ActiveVacationRead(
            employee_id=v.employee_id,
            employee_name=emp.name if emp else "—",
            enjoyment_start=v.enjoyment_start,
            enjoyment_end=enjoyment_end,
        ))
    active_vacations.sort(key=lambda x: x.enjoyment_start)

    # ── Evolução mensal — últimos 6 meses ────────────────────────────────────
    monthly_totals: list[MonthlyTotalRead] = []
    for i in range(5, -1, -1):
        total_months = year * 12 + month - 1 - i
        m_year  = total_months // 12
        m_month = total_months % 12 + 1
        m_payrolls = (
            db.query(Payroll)
            .join(Employee)
            .filter(
                Employee.company_id == company_id,
                Payroll.competence_month == m_month,
                Payroll.competence_year  == m_year,
                Payroll.status == PayrollStatus.CLOSED,
            )
            .all()
        )
        m_payroll_total = sum(Decimal(str(p.net_salary)) for p in m_payrolls)
        _, m_seam_paid, m_seam_entrega = seamstress_repo.month_totals(db, company_id, m_month, m_year)
        m_seam_total = Decimal(str(m_seam_paid or 0)) + Decimal(str(m_seam_entrega or 0))
        monthly_totals.append(MonthlyTotalRead(
            year=m_year,
            month=m_month,
            payroll=m_payroll_total,
            seamstress=m_seam_total,
            total=m_payroll_total + m_seam_total,
        ))

    # ── Costureiras ───────────────────────────────────────────────────────────
    seamstress_pending, seamstress_paid, seamstress_entrega = seamstress_repo.month_totals(
        db, company_id, month, year
    )
    seamstress_total = (
        Decimal(str(seamstress_pending or 0)) +
        Decimal(str(seamstress_paid or 0)) +
        Decimal(str(seamstress_entrega or 0))
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
        vacations_active=vacs_active,
        vacations_scheduled=vacs_scheduled,
        vacations_expiring_60d=len(vacs_expiring),
        monthly_totals=monthly_totals,
        birthdays_next_30_days=birthdays,
        expiring_vacations=expiring,
        scheduled_vacations=scheduled_vacations,
        active_vacations=active_vacations,
        seamstress_pending_month=Decimal(str(seamstress_pending)) if seamstress_pending else Decimal(0),
        seamstress_paid_month=Decimal(str(seamstress_paid)) if seamstress_paid else Decimal(0),
        seamstress_entrega_month=Decimal(str(seamstress_entrega)) if seamstress_entrega else Decimal(0),
        seamstress_total_month=seamstress_total,
        custo_total_month=total_net + seamstress_total,
    )


# ── Folha Anual por Funcionário ───────────────────────────────────────────────

def get_annual_payroll(db: Session, company_id: int, year: int) -> AnnualPayrollRead:
    """
    Retorna para cada funcionário ativo:
    - Salário contratado em cada mês (reconstruído pelo histórico de alterações)
    - Auxílio fixo cadastrado no funcionário
    Meses com folha fechada mostram o valor; sem folha, mostra —.
    Meses anteriores à admissão ficam em branco.
    """
    import calendar as cal
    from app.models.employee import EmployeeHistory

    year_end = date(year, 12, 31)

    # Todos os funcionários que entraram até o fim do ano (ativos + inativos com folha no ano)
    active_emps = (
        db.query(Employee)
        .filter(
            Employee.company_id == company_id,
            Employee.status == EmployeeStatus.ACTIVE,
            Employee.admission_date <= year_end,
        )
        .order_by(Employee.name)
        .all()
    )

    # Inclui também inativos que tinham folha no ano (saíram durante o ano)
    all_emps: dict[int, Employee] = {e.id: e for e in active_emps}
    inactive_with_payroll = (
        db.query(Employee)
        .join(Payroll)
        .filter(
            Employee.company_id == company_id,
            Employee.status == EmployeeStatus.INACTIVE,
            Payroll.competence_year == year,
        )
        .all()
    )
    for emp in inactive_with_payroll:
        all_emps.setdefault(emp.id, emp)

    # Histórico de salário E auxílio de todos de uma vez (evita N+1)
    all_ids = list(all_emps.keys())
    history_all = (
        db.query(EmployeeHistory)
        .filter(
            EmployeeHistory.employee_id.in_(all_ids),
            EmployeeHistory.field_changed.in_(["salary", "auxilio"]),
        )
        .order_by(EmployeeHistory.employee_id, EmployeeHistory.changed_at.desc())
        .all()
    )
    salary_hist: dict[int, list] = {}
    auxilio_hist: dict[int, list] = {}
    for h in history_all:
        if h.field_changed == "salary":
            salary_hist.setdefault(h.employee_id, []).append(h)
        else:
            auxilio_hist.setdefault(h.employee_id, []).append(h)

    def _value_at_month_end(current, history_list: list, m: int) -> Decimal | None:
        """Reconstrói o valor vigente no último dia do mês percorrendo o histórico."""
        last_day = date(year, m, cal.monthrange(year, m)[1])
        effective = Decimal(str(current)) if current is not None else None
        for h in history_list:
            change_date = h.changed_at.date() if hasattr(h.changed_at, "date") else h.changed_at
            if change_date > last_day:
                try:
                    old = h.old_value
                    effective = Decimal(str(old)) if old not in (None, "—", "") else None
                except Exception:
                    pass
            else:
                break
        return effective

    rows = []
    for emp_id, emp in sorted(all_emps.items(), key=lambda x: x[1].name):
        adm = emp.admission_date or date(year, 1, 1)

        today = date.today()
        month_list = []
        prev_salary = prev_aux = None
        for m in range(1, 13):
            # Meses antes da admissão: em branco
            before_adm = (adm.year == year and m < adm.month) or adm.year > year
            # Meses futuros do ano corrente: em branco
            future = (year == today.year and m > today.month)
            if before_adm or future:
                month_list.append(AnnualEmployeeMonth(month=m))
                continue

            sal = _value_at_month_end(emp.salary,  salary_hist.get(emp_id, []),  m)
            aux = _value_at_month_end(emp.auxilio, auxilio_hist.get(emp_id, []), m)

            is_sal_inc = sal is not None and prev_salary is not None and sal > prev_salary
            is_aux_inc = aux is not None and prev_aux   is not None and aux > prev_aux
            month_list.append(AnnualEmployeeMonth(
                month=m,
                gross_salary=sal,
                auxilio=aux,
                is_salary_increase=is_sal_inc,
                is_auxilio_increase=is_aux_inc,
            ))
            if sal is not None: prev_salary = sal
            if aux is not None: prev_aux    = aux

        rows.append(AnnualEmployeeRow(
            employee_id=emp_id,
            name=emp.name,
            admission_month=adm.month,
            admission_year=adm.year,
            months=month_list,
        ))

    return AnnualPayrollRead(year=year, employees=rows)


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
