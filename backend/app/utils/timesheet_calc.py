"""
Cálculos de ponto — isolados em utilitário puro (sem acesso ao banco).
Facilita testes unitários e reutilização.

Regras do sistema:
- CLT: Seg-Qui = 9h (540 min), Sex = 8h (480 min)
- Interns: weekly_hours / 5 dias
- Tolerância de atraso: 5 minutos (não gera desconto)
- Limiar de hora extra: 10 minutos (trabalhar até 10 min a mais não gera hora extra)
- Atestado médico: dia não conta como falta nem desconta banco de horas
- Dia anulado: sem cálculo algum
"""
from datetime import date, time

# Minutos esperados por dia para CLT (weekday: 0=Seg, 4=Sex)
CLT_EXPECTED = {0: 540, 1: 540, 2: 540, 3: 540, 4: 480}

OVERTIME_THRESHOLD_MIN = 10   # trabalhar até 10 min a mais não gera hora extra
LATE_TOLERANCE_MIN = 5        # chegar até 5 min atrasado não conta como atraso


def _to_min(t: time) -> int:
    return t.hour * 60 + t.minute


def expected_minutes(work_date: date, is_intern: bool, weekly_hours: int) -> int:
    """Retorna os minutos esperados de trabalho no dia."""
    weekday = work_date.weekday()
    if weekday >= 5:  # Sábado ou domingo
        return 0
    if is_intern:
        return (weekly_hours * 60) // 5
    return CLT_EXPECTED.get(weekday, 480)


def calc_worked_minutes(
    entry: time | None,
    lunch_out: time | None,
    lunch_in: time | None,
    exit_t: time | None,
) -> int:
    """Minutos efetivamente trabalhados (desconta intervalo de almoço)."""
    if not all([entry, lunch_out, lunch_in, exit_t]):
        return 0
    total = _to_min(exit_t) - _to_min(entry)
    lunch = _to_min(lunch_in) - _to_min(lunch_out)
    return max(0, total - max(0, lunch))


def calc_overtime_minutes(worked: int, expected: int) -> int:
    """
    Horas extras no dia.
    Só conta como extra o que ultrapassar o limiar de 10 minutos.
    """
    diff = worked - expected
    if diff > OVERTIME_THRESHOLD_MIN:
        return diff
    return 0


def calc_late_minutes(worked: int, expected: int) -> int:
    """
    Minutos em falta no dia (atraso ou saída antecipada).
    Diferença de até 5 min não é considerada atraso.
    """
    deficit = expected - worked
    if deficit > LATE_TOLERANCE_MIN:
        return deficit
    return 0


def calc_bank_delta(
    worked: int,
    expected: int,
    is_absence: bool,
    is_medical_certificate: bool,
    is_annulled: bool,
) -> int:
    """
    Variação do banco de horas para o dia.
    - Atestado médico e dia anulado: sem variação (0)
    - Falta: desconta o dia completo
    - Trabalhado: diferença entre trabalhado e esperado
    """
    if is_annulled or is_medical_certificate:
        return 0
    if is_absence:
        return -expected
    return worked - expected


def format_minutes(minutes: int) -> str:
    """Formata minutos como "+2h30" ou "-1h15"."""
    sign = "+" if minutes >= 0 else "-"
    abs_min = abs(minutes)
    h = abs_min // 60
    m = abs_min % 60
    return f"{sign}{h}h{m:02d}"
