"""
Cálculos de folha de pagamento — funções puras, sem acesso ao banco.
"""
import calendar
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP


# ── Dias úteis ────────────────────────────────────────────────────────────────

def working_days_in_month(year: int, month: int) -> int:
    """Conta dias úteis (Seg-Sex) no mês. Sem considerar feriados."""
    first = date(year, month, 1)
    last = date(year, month, calendar.monthrange(year, month)[1])
    count = 0
    day = first
    while day <= last:
        if day.weekday() < 5:
            count += 1
        day += timedelta(days=1)
    return count


def next_month(year: int, month: int) -> tuple[int, int]:
    """Retorna (ano, mês) do mês seguinte."""
    if month == 12:
        return year + 1, 1
    return year, month + 1


# ── Salário proporcional ──────────────────────────────────────────────────────

def calc_proportional_salary(
    base_salary: Decimal,
    worked_days: int,
    total_working_days: int,
) -> Decimal:
    """
    Salário proporcional aos dias trabalhados.
    Atestados médicos não descontam — apenas faltas injustificadas.
    """
    if total_working_days <= 0:
        return base_salary
    result = base_salary * Decimal(worked_days) / Decimal(total_working_days)
    return result.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# ── Hora extra ────────────────────────────────────────────────────────────────

def calc_overtime_value(base_salary: Decimal, overtime_minutes: int) -> Decimal:
    """
    Valor das horas extras do mês.
    Fórmula: Salário ÷ 220 × 1,6 × total_horas_extras
    """
    if overtime_minutes <= 0:
        return Decimal("0")
    overtime_hours = Decimal(overtime_minutes) / Decimal("60")
    valor_hora = base_salary / Decimal("220")
    result = valor_hora * Decimal("1.6") * overtime_hours
    return result.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# ── Vale Transporte ───────────────────────────────────────────────────────────

def calc_vt(
    year: int,
    month: int,
    absences: int,
    medical_certs: int,
    vt_per_day: Decimal = Decimal("10.60"),
) -> Decimal:
    """
    VT calculado com base nos dias úteis do mês SEGUINTE ao da competência,
    descontando faltas e atestados do mês atual.

    Exemplo: competência abril → VT baseado em dias úteis de maio,
             menos faltas de abril.
    """
    next_y, next_m = next_month(year, month)
    dias_uteis_prox = working_days_in_month(next_y, next_m)
    dias_a_pagar = max(0, dias_uteis_prox - absences - medical_certs)
    result = Decimal(dias_a_pagar) * vt_per_day
    return result.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# ── DSR (Descanso Semanal Remunerado) ─────────────────────────────────────────

def calc_dsr_discount(base_salary: Decimal, absences_in_month: int) -> Decimal:
    """Legado — mantido para compatibilidade. Use calc_dsr_by_week."""
    if absences_in_month <= 0:
        return Decimal("0")
    dsr_diario = base_salary / Decimal("30")
    result = dsr_diario * Decimal(absences_in_month)
    return result.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calc_dsr_by_week(base_salary: Decimal, absence_dates: list) -> tuple[Decimal, int]:
    """
    DSR correto: desconta 1 domingo por semana que teve falta.
    2+ faltas na mesma semana = 1 DSR. Semanas diferentes = 1 DSR cada.
    Retorna (valor_total_dsr, numero_semanas_afetadas).
    """
    if not absence_dates:
        return Decimal("0"), 0
    weeks = set()
    for d in absence_dates:
        iso = d.isocalendar()
        weeks.add((iso[0], iso[1]))
    dsr_diario = (base_salary / Decimal("30")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    total = (dsr_diario * Decimal(len(weeks))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return total, len(weeks)


def count_working_days_in_range(start: date, end: date) -> int:
    """Conta dias úteis (Seg-Sex) entre start e end, inclusive."""
    count = 0
    cur = start
    while cur <= end:
        if cur.weekday() < 5:
            count += 1
        cur += timedelta(days=1)
    return count


# ── 13º Salário ───────────────────────────────────────────────────────────────

def calc_thirteenth_salary(
    base_salary: Decimal,
    worked_months: int,
    parcela: int,   # 1 ou 2
) -> Decimal:
    """
    13º proporcional.
    Parcela 1 (novembro): metade do valor bruto proporcional.
    Parcela 2 (dezembro): saldo restante (já com descontos, calculado à parte).
    worked_months: meses com pelo menos 15 dias trabalhados.
    """
    bruto = (base_salary * Decimal(worked_months) / Decimal("12")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    if parcela == 1:
        return (bruto / Decimal("2")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return bruto  # desconto é calculado à parte na folha de dezembro


def count_worked_months_for_thirteenth(
    registration_date: date,
    reference_date: date,
) -> int:
    """
    Conta meses para 13º/férias.
    Regra: mês de admissão conta se trabalhou 16+ dias naquele mês.
    """
    start = registration_date
    months = 0

    # Mês de entrada: conta se trabalhou 16+ dias
    days_in_first_month = (
        date(start.year, start.month, calendar.monthrange(start.year, start.month)[1])
        - start
    ).days + 1

    if days_in_first_month >= 16:
        months += 1

    # Meses completos entre o mês seguinte ao de entrada e o mês de referência
    y, m = start.year, start.month
    if m == 12:
        y += 1
        m = 1
    else:
        m += 1

    ref_y, ref_m = reference_date.year, reference_date.month
    while (y, m) <= (ref_y, ref_m):
        months += 1
        if m == 12:
            y += 1
            m = 1
        else:
            m += 1

    return min(months, 12)
