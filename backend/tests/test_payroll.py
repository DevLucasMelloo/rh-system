"""
Testes do módulo de folha de pagamento.
Cobre: INSS progressivo, cálculo de VT, proporcional, hora extra,
       criação de holerite, vale parcelado, fechamento.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import date
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.models import *
from app.utils.inss_calc import calc_inss, DEFAULT_INSS_TABLE
from app.utils.payroll_calc import (
    working_days_in_month, calc_proportional_salary,
    calc_overtime_value, calc_vt, calc_dsr_discount,
    count_worked_months_for_thirteenth, calc_thirteenth_salary,
)
from app.schemas.company import CompanyCreate
from app.schemas.user import UserCreate
from app.schemas.employee import EmployeeCreate
from app.schemas.payroll import PayrollCreate, ValeCreate, PayrollItemCreate
from app.models.payroll import PayrollItemType, PayrollStatus
from app.services import company as company_service
from app.services import user as user_service
from app.services import employee as emp_service
from app.services import payroll as payroll_service
from app.services import timesheet as ts_service
from app.schemas.timesheet import TimesheetEntryCreate

from datetime import time


def make_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def setup(db):
    company = company_service.register_company(
        db, CompanyCreate(razao_social="Empresa Teste", cnpj="11222333000181", email="a@b.com")
    )
    admin = user_service.create_user(
        db, UserCreate(name="Admin", email="admin@t.com", password="Senha@123", role="admin"),
        company.id, 0,
    )
    emp = emp_service.create_employee(
        db, EmployeeCreate(
            name="Carlos CLT", cpf="529.982.247-25", role="Analista",
            salary=Decimal("3000"), admission_date=date(2023, 1, 1),
            registration_date=date(2023, 1, 1),
        ),
        company.id, admin.id,
    )
    return company, admin, emp


# ─────────────────────────────────────────────────────────────────────────────
# Testes de cálculo puro
# ─────────────────────────────────────────────────────────────────────────────

def test_inss_faixa1():
    # R$ 1.000,00 → só faixa 1 (7,5%)
    result = calc_inss(Decimal("1000.00"))
    assert result == Decimal("75.00"), f"Esperado 75.00, obtido {result}"
    print("[OK] INSS faixa 1: R$ 1.000 × 7,5% = R$ 75,00")


def test_inss_duas_faixas():
    # R$ 2.500,00
    # Faixa 1: 1621,00 × 7,5% = 121,58
    # Faixa 2: (2500 - 1621) × 9% = 879 × 9% = 79,11
    # Total: 200,69
    result = calc_inss(Decimal("2500.00"))
    assert result == Decimal("200.69"), f"Esperado 200.69, obtido {result}"
    print("[OK] INSS duas faixas: R$ 2.500 = R$ 200,69")


def test_inss_teto():
    # R$ 8.475,55 (teto)
    # Faixa 1: 1621 × 7,5% = 121,575 → 121,58
    # Faixa 2: (2902.84-1621) × 9% = 1281.84 × 9% = 115,37
    # Faixa 3: (4354.27-2902.84) × 12% = 1451.43 × 12% = 174,17
    # Faixa 4: (8475.55-4354.27) × 14% = 4121.28 × 14% = 576,98
    # Total: 987,10 (approximated, check exact)
    result = calc_inss(Decimal("8475.55"))
    assert result > Decimal("900"), f"INSS sobre teto deveria ser > 900, obtido {result}"
    print(f"[OK] INSS teto: R$ 8.475,55 = R$ {result}")


def test_inss_acima_teto():
    # Salário > teto → mesmo INSS do teto
    result_teto = calc_inss(Decimal("8475.55"))
    result_acima = calc_inss(Decimal("15000.00"))
    assert result_teto == result_acima, "INSS acima do teto deve ser igual ao do teto"
    print(f"[OK] INSS acima do teto: R$ 15.000 = R$ {result_acima} (mesmo que o teto)")


def test_working_days_abril_2025():
    # Abril/2025: 22 dias úteis (Seg-Sex, sem fins de semana, sem feriados)
    days = working_days_in_month(2025, 4)
    assert days == 22, f"Esperado 22, obtido {days}"
    print("[OK] Dias úteis abril/2025 = 22")


def test_proportional_salary():
    # 20 dias de 22 → proporcional
    result = calc_proportional_salary(Decimal("3000"), 20, 22)
    expected = (Decimal("3000") * 20 / 22).quantize(Decimal("0.01"))
    assert result == expected
    print(f"[OK] Proporcional: 20/22 dias de R$ 3.000 = R$ {result}")


def test_overtime_value():
    # Salário 3000, 60 min de hora extra
    # 3000 / 220 * 1.6 * 1 hora = 21,818... → 21,82
    result = calc_overtime_value(Decimal("3000"), 60)
    assert result == Decimal("21.82"), f"Esperado 21.82, obtido {result}"
    print(f"[OK] Hora extra: 60 min com R$ 3.000 = R$ {result}")


def test_vt_calculo():
    # Competência abril/2025: próximo mês = maio (22 dias úteis) - 0 faltas
    result = calc_vt(2025, 4, 0, 0, vt_per_day=Decimal("10.60"))
    days_maio = working_days_in_month(2025, 5)
    expected = Decimal(days_maio) * Decimal("10.60")
    assert result == expected.quantize(Decimal("0.01"))
    print(f"[OK] VT abril/2025 (base maio={days_maio} dias): R$ {result}")


def test_vt_com_faltas():
    # Com 2 faltas e 1 atestado no mês
    result_sem = calc_vt(2025, 4, 0, 0, vt_per_day=Decimal("10.60"))
    result_com = calc_vt(2025, 4, 2, 1, vt_per_day=Decimal("10.60"))
    assert result_com == result_sem - (3 * Decimal("10.60"))
    print(f"[OK] VT com 3 dias ausência: R$ {result_com} (menos 3 × R$ 10,60)")


def test_dsr_desconto():
    # 2 faltas → 2 × (3000/30) = 2 × 100 = 200
    result = calc_dsr_discount(Decimal("3000"), 2)
    assert result == Decimal("200.00"), f"Esperado 200.00, obtido {result}"
    print(f"[OK] DSR 2 faltas: R$ {result}")


def test_decimo_terceiro_proporcional():
    # 6 meses → 50% do salário (parcela 2)
    result = calc_thirteenth_salary(Decimal("3000"), 6, 2)
    assert result == Decimal("1500.00"), f"Esperado 1500.00, obtido {result}"
    print(f"[OK] 13º 6 meses (parcela 2): R$ {result}")


def test_count_worked_months():
    # Admitido em 01/01/2023, referência 01/12/2023 → 12 meses
    months = count_worked_months_for_thirteenth(date(2023, 1, 1), date(2023, 12, 1))
    assert months == 12, f"Esperado 12, obtido {months}"
    # Admitido em 20/01/2023 (apenas 12 dias no primeiro mês) → não conta janeiro
    months2 = count_worked_months_for_thirteenth(date(2023, 1, 20), date(2023, 12, 1))
    assert months2 == 11, f"Esperado 11, obtido {months2}"
    print(f"[OK] Meses 13º: admissão 01/01 = 12, admissão 20/01 = {months2}")


# ─────────────────────────────────────────────────────────────────────────────
# Testes de integração
# ─────────────────────────────────────────────────────────────────────────────

def test_criar_holerite_sem_ponto():
    """Holerite criado sem registros de ponto → salário cheio, sem extra, sem VT zero."""
    db = make_db()
    company, admin, emp = setup(db)

    payroll = payroll_service.create_payroll(
        db,
        PayrollCreate(employee_id=emp["id"], competence_month=4, competence_year=2025),
        company.id, admin.id,
    )

    assert payroll.status == PayrollStatus.DRAFT
    # Com 0 faltas, salário deve ser o cheio
    salary_item = next(i for i in payroll.items if i.item_type.value == "salario")
    assert salary_item.amount == Decimal("3000.00")
    # VT calculado (próximo mês)
    vt_item = next((i for i in payroll.items if i.item_type.value == "vale_transporte"), None)
    assert vt_item is not None
    assert vt_item.amount > 0
    # INSS calculado
    inss_item = next(i for i in payroll.items if i.item_type.value == "inss")
    assert inss_item.amount > 0
    print(f"[OK] Holerite criado: salário={salary_item.amount}, INSS={inss_item.amount}, VT={vt_item.amount}")


def test_holerite_duplicado():
    from fastapi import HTTPException
    db = make_db()
    company, admin, emp = setup(db)

    payroll_service.create_payroll(
        db,
        PayrollCreate(employee_id=emp["id"], competence_month=4, competence_year=2025),
        company.id, admin.id,
    )
    try:
        payroll_service.create_payroll(
            db,
            PayrollCreate(employee_id=emp["id"], competence_month=4, competence_year=2025),
            company.id, admin.id,
        )
        assert False, "Deveria ter lançado HTTPException"
    except HTTPException as e:
        assert e.status_code == 409
    print("[OK] Holerite duplicado retorna 409")


def test_holerite_com_falta():
    """Falta injustificada → salário proporcional + DSR + desconto falta."""
    db = make_db()
    company, admin, emp = setup(db)

    # Registrar 1 falta
    ts_service.register_entry(
        db, emp["id"],
        TimesheetEntryCreate(work_date=date(2025, 4, 14), is_absence=True),
        company.id, admin.id,
    )

    payroll = payroll_service.create_payroll(
        db,
        PayrollCreate(employee_id=emp["id"], competence_month=4, competence_year=2025),
        company.id, admin.id,
    )

    salary_item = next(i for i in payroll.items if i.item_type.value == "salario")
    dsr_item = next((i for i in payroll.items if i.item_type.value == "dsr"), None)
    absence_item = next((i for i in payroll.items if i.item_type.value == "falta"), None)

    # Salário proporcional (21/22 dias)
    expected_salary = calc_proportional_salary(Decimal("3000"), 21, 22)
    assert salary_item.amount == expected_salary
    assert dsr_item is not None and dsr_item.amount > 0
    assert absence_item is not None and absence_item.amount > 0
    print(f"[OK] Holerite com falta: salário={salary_item.amount}, DSR={dsr_item.amount}, descFalta={absence_item.amount}")


def test_holerite_com_hora_extra():
    """Hora extra registrada no ponto → item hora_extra no holerite."""
    db = make_db()
    company, admin, emp = setup(db)

    # Segunda com 30 min extra (acima do limiar de 10)
    ts_service.register_entry(
        db, emp["id"],
        TimesheetEntryCreate(
            work_date=date(2025, 4, 14),  # Segunda
            entry_time=time(8, 0),
            lunch_out_time=time(12, 0),
            lunch_in_time=time(13, 0),
            exit_time=time(19, 0),  # 9h trabalho → 30 min extra
        ),
        company.id, admin.id,
    )

    payroll = payroll_service.create_payroll(
        db,
        PayrollCreate(employee_id=emp["id"], competence_month=4, competence_year=2025),
        company.id, admin.id,
    )

    extra_item = next((i for i in payroll.items if i.item_type.value == "hora_extra"), None)
    assert extra_item is not None, "Item hora_extra não encontrado"
    assert extra_item.amount > 0
    print(f"[OK] Holerite com hora extra: R$ {extra_item.amount}")


def test_item_manual():
    """Adicionar item manual ao holerite recalcula totais."""
    db = make_db()
    company, admin, emp = setup(db)

    from app.schemas.payroll import PayrollItemCreate

    payroll = payroll_service.create_payroll(
        db,
        PayrollCreate(employee_id=emp["id"], competence_month=4, competence_year=2025),
        company.id, admin.id,
    )
    net_antes = payroll.net_salary

    payroll_service.add_manual_item(
        db, payroll.id,
        PayrollItemCreate(
            item_type=PayrollItemType.AUXILIO,
            description="Auxílio Home Office",
            amount=Decimal("200.00"),
            is_credit=True,
        ),
        company.id, admin.id,
    )

    from app.repositories import payroll as payroll_repo
    payroll = payroll_repo.get_payroll(db, payroll.id)
    assert payroll.net_salary > net_antes
    assert any(i.is_manual for i in payroll.items)
    print(f"[OK] Item manual adicionado: net antes={net_antes}, depois={payroll.net_salary}")


def test_fechar_holerite():
    """Fechar holerite muda status para CLOSED e impede edições."""
    from fastapi import HTTPException
    db = make_db()
    company, admin, emp = setup(db)

    payroll = payroll_service.create_payroll(
        db,
        PayrollCreate(employee_id=emp["id"], competence_month=4, competence_year=2025),
        company.id, admin.id,
    )

    closed = payroll_service.close_payroll(
        db, payroll.id, date(2025, 4, 30), company.id, admin.id
    )
    assert closed.status == PayrollStatus.CLOSED
    assert closed.closed_at is not None

    # Tentar fechar de novo → erro
    try:
        payroll_service.close_payroll(db, payroll.id, None, company.id, admin.id)
        assert False, "Deveria lançar HTTPException"
    except HTTPException as e:
        assert e.status_code == 400
    print("[OK] Holerite fechado, segunda tentativa retorna 400")


def test_vale_parcelado():
    """Vale em 3 parcelas gera 3 installments com meses corretos."""
    db = make_db()
    company, admin, emp = setup(db)

    vale = payroll_service.create_vale(
        db, emp["id"],
        ValeCreate(
            total_amount=Decimal("300.00"),
            installments=3,
            notes="Compra de ferramentas",
            issued_date=date(2025, 4, 1),
        ),
        company.id, admin.id,
    )

    assert len(vale.installment_items) == 3
    # Parcela 1 → maio/2025
    assert vale.installment_items[0].due_month == 5
    assert vale.installment_items[0].due_year == 2025
    # Parcela 2 → junho/2025
    assert vale.installment_items[1].due_month == 6
    # Parcela 3 → julho/2025
    assert vale.installment_items[2].due_month == 7
    # Soma das parcelas = total
    total = sum(i.amount for i in vale.installment_items)
    assert total == Decimal("300.00"), f"Soma das parcelas {total} != 300.00"
    print("[OK] Vale R$ 300 em 3x: maio/jun/jul 2025, total correto")


def test_vale_desconta_no_holerite():
    """Parcela de vale do mês aparece como desconto no holerite."""
    db = make_db()
    company, admin, emp = setup(db)

    # Vale emitido em março → 1ª parcela em abril
    payroll_service.create_vale(
        db, emp["id"],
        ValeCreate(
            total_amount=Decimal("100.00"),
            installments=1,
            notes="Adiantamento",
            issued_date=date(2025, 3, 1),
        ),
        company.id, admin.id,
    )

    payroll = payroll_service.create_payroll(
        db,
        PayrollCreate(employee_id=emp["id"], competence_month=4, competence_year=2025),
        company.id, admin.id,
    )

    vale_item = next((i for i in payroll.items if i.item_type.value == "vale_desconto"), None)
    assert vale_item is not None, "Desconto de vale não encontrado no holerite"
    assert vale_item.amount == Decimal("100.00")
    assert not vale_item.is_credit
    print("[OK] Parcela de vale descontada no holerite de abril/2025")


def test_vale_marcado_pago_ao_fechar():
    """Ao fechar o holerite, a parcela de vale deve ser marcada como paga."""
    db = make_db()
    company, admin, emp = setup(db)

    payroll_service.create_vale(
        db, emp["id"],
        ValeCreate(
            total_amount=Decimal("50.00"),
            installments=1,
            issued_date=date(2025, 3, 1),
        ),
        company.id, admin.id,
    )

    payroll = payroll_service.create_payroll(
        db,
        PayrollCreate(employee_id=emp["id"], competence_month=4, competence_year=2025),
        company.id, admin.id,
    )

    payroll_service.close_payroll(db, payroll.id, None, company.id, admin.id)

    from app.repositories import payroll as payroll_repo
    pendentes = payroll_repo.list_pending_installments(db, emp["id"], 4, 2025)
    assert len(pendentes) == 0, "Parcela deveria estar marcada como paga"
    print("[OK] Parcela de vale marcada como paga ao fechar holerite")


def test_recalcular_mantem_itens_manuais():
    """Recalcular não remove itens marcados como manuais."""
    db = make_db()
    company, admin, emp = setup(db)
    from app.schemas.payroll import PayrollItemCreate

    payroll = payroll_service.create_payroll(
        db,
        PayrollCreate(employee_id=emp["id"], competence_month=4, competence_year=2025),
        company.id, admin.id,
    )

    payroll_service.add_manual_item(
        db, payroll.id,
        PayrollItemCreate(
            item_type=PayrollItemType.BONUS,
            description="Bônus de Desempenho",
            amount=Decimal("500.00"),
            is_credit=True,
        ),
        company.id, admin.id,
    )

    payroll_service.recalculate_payroll(db, payroll.id, company.id, admin.id)

    from app.repositories import payroll as payroll_repo
    payroll = payroll_repo.get_payroll(db, payroll.id)
    bonus = next((i for i in payroll.items if i.description == "Bônus de Desempenho"), None)
    assert bonus is not None, "Item manual removido pelo recalculo"
    assert bonus.is_manual
    print("[OK] Recalculo preserva itens manuais")


if __name__ == "__main__":
    print("=== Testando módulo de Folha de Pagamento ===\n")

    # Cálculos puros
    test_inss_faixa1()
    test_inss_duas_faixas()
    test_inss_teto()
    test_inss_acima_teto()
    test_working_days_abril_2025()
    test_proportional_salary()
    test_overtime_value()
    test_vt_calculo()
    test_vt_com_faltas()
    test_dsr_desconto()
    test_decimo_terceiro_proporcional()
    test_count_worked_months()

    # Integração
    test_criar_holerite_sem_ponto()
    test_holerite_duplicado()
    test_holerite_com_falta()
    test_holerite_com_hora_extra()
    test_item_manual()
    test_fechar_holerite()
    test_vale_parcelado()
    test_vale_desconta_no_holerite()
    test_vale_marcado_pago_ao_fechar()
    test_recalcular_mantem_itens_manuais()

    print("\nTodos os testes de folha passaram!")
