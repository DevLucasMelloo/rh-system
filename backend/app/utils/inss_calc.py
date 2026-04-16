"""
Cálculo progressivo de INSS.
Tabela editável — valores armazenados aqui como padrão, substituíveis via parâmetro.

Tabela vigente (2024/2025):
  Até R$ 1.621,00          → 7,5%
  R$ 1.621,01 – R$ 2.902,84 → 9%
  R$ 2.902,85 – R$ 4.354,27 → 12%
  R$ 4.354,28 – R$ 8.475,55 → 14%
"""
from decimal import Decimal, ROUND_HALF_UP

# Tabela padrão: (limite_superior, alíquota)
DEFAULT_INSS_TABLE = [
    (Decimal("1621.00"),  Decimal("0.075")),
    (Decimal("2902.84"),  Decimal("0.09")),
    (Decimal("4354.27"),  Decimal("0.12")),
    (Decimal("8475.55"),  Decimal("0.14")),
]


def calc_inss(salary: Decimal, table: list | None = None) -> Decimal:
    """
    Calcula INSS progressivo sobre o salário.
    Cada faixa é tributada apenas sobre o valor que cai dentro dela.

    Exemplo (salário R$ 2.500,00):
      Faixa 1: R$ 1.621,00 × 7,5%  = R$ 121,58
      Faixa 2: (R$ 2.500,00 – R$ 1.621,00) × 9% = R$ 79,11
      Total: R$ 200,69
    """
    if table is None:
        table = DEFAULT_INSS_TABLE

    total = Decimal("0")
    prev_limit = Decimal("0")

    for limit, rate in table:
        if salary <= prev_limit:
            break
        taxable = min(salary, limit) - prev_limit
        total += taxable * rate
        prev_limit = limit

    return total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calc_inss_ferias(salary: Decimal, table: list | None = None) -> Decimal:
    """
    INSS sobre férias: base = salário + 1/3 constitucional.
    O 1/3 é calculado sobre o salário de férias, não sobre o bruto.
    """
    um_terco = (salary / Decimal("3")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    base = salary + um_terco
    return calc_inss(base, table)
