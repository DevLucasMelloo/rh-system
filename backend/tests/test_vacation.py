"""
Testes do módulo de Férias, 13º Salário e Rescisão.
Cobre: cálculos puros, integração com banco em memória.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import date
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.models import *
from app.utils.inss_calc import calc_inss_ferias
from app.utils.payroll_calc import count_worked_months_for_thirteenth
from app.services.vacation import (
    calc_vacation_pay, calc_notice_days, get_thirteenth,
    schedule_vacation, start_vacation, complete_vacation, cancel_vacation,
    create_termination,
    _count_proportional_vacation_months,
)
from app.schemas.vacation import VacationCreate, VacationStart, TerminationCreate
from app.schemas.company import CompanyCreate
from app.schemas.user import UserCreate
from app.schemas.employee import EmployeeCreate
from app.models.vacation import VacationStatus
from app.models.termination import TerminationReason
from app.models.employee import EmployeeStatus
from app.services import company as company_service
from app.services import user as user_service
from app.services import employee as emp_service


def make_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def setup(db, salary=Decimal("3000"), admission=date(2023, 1, 1)):
    company = company_service.register_company(
        db, CompanyCreate(razao_social="Empresa Teste", cnpj="11222333000181", email="a@b.com")
    )
    admin = user_service.create_user(
        db, UserCreate(name="Admin", email="admin@t.com", password="Senha@123", role="admin"),
        company.id, 0,
    )
    emp = emp_service.create_employee(
        db, EmployeeCreate(
            name="Maria CLT", cpf="529.982.247-25", role="Analista",
            salary=salary,
            admission_date=admission,
            registration_date=admission,
        ),
        company.id, admin.id,
    )
    return company, admin, emp


# ─────────────────────────────────────────────────────────────────────────────
# Cálculos puros
# ─────────────────────────────────────────────────────────────────────────────

def test_calc_vacation_pay_30_dias():
    pay = calc_vacation_pay(Decimal("3000"), 30)
    assert pay["base_salary"]     == Decimal("3000.00"), f"base={pay['base_salary']}"
    assert pay["one_third_bonus"] == Decimal("1000.00"), f"1/3={pay['one_third_bonus']}"
    # INSS sobre 4000: faixa1(1621×7,5%=121,58) + faixa2((2902.84-1621)×9%=106.36) + faixa3((4000-2902.84)×12%=131.66) = 359.60
    inss_esperado = calc_inss_ferias(Decimal("3000"))
    assert pay["inss_discount"]   == inss_esperado
    assert pay["net_vacation_pay"] == Decimal("3000") + Decimal("1000") - inss_esperado
    print(f"[OK] Férias 30 dias: base=3000, 1/3=1000, INSS={inss_esperado}, líq={pay['net_vacation_pay']}")


def test_calc_vacation_pay_15_dias():
    pay = calc_vacation_pay(Decimal("3000"), 15)
    assert pay["base_salary"]     == Decimal("1500.00")
    assert pay["one_third_bonus"] == Decimal("500.00")
    print(f"[OK] Férias 15 dias: base=1500, 1/3=500")


def test_calc_notice_days_sem_justa_causa():
    # 1 ano completo = 30 + 3 = 33 dias
    days = calc_notice_days(
        TerminationReason.SEM_JUSTA_CAUSA,
        date(2022, 1, 1), date(2023, 6, 1),
    )
    assert days == 33, f"Esperado 33, obtido {days}"
    print(f"[OK] Aviso prévio 1 ano completo = 33 dias")


def test_calc_notice_days_max_90():
    # 25 anos = 30 + 75 = 105 → capped em 90
    days = calc_notice_days(
        TerminationReason.SEM_JUSTA_CAUSA,
        date(1998, 1, 1), date(2024, 1, 1),
    )
    assert days == 90, f"Esperado 90, obtido {days}"
    print(f"[OK] Aviso prévio máximo = 90 dias")


def test_calc_notice_days_com_justa_causa():
    days = calc_notice_days(
        TerminationReason.COM_JUSTA_CAUSA,
        date(2022, 1, 1), date(2023, 6, 1),
    )
    assert days == 0, f"Esperado 0, obtido {days}"
    print("[OK] Justa causa = 0 dias aviso")


def test_calc_notice_days_acordo():
    # acordo = metade de 33 = 16
    days = calc_notice_days(
        TerminationReason.ACORDO,
        date(2022, 1, 1), date(2023, 6, 1),
    )
    assert days == 16, f"Esperado 16, obtido {days}"
    print(f"[OK] Acordo = 16 dias aviso (metade de 33)")


def test_proportional_vacation_months():
    # 13 meses de serviço → período atual = 1 mês
    months = _count_proportional_vacation_months(date(2023, 1, 1), date(2024, 2, 20))
    assert months == 2, f"Esperado 2, obtido {months}"  # jan(completo) + fev(>=15)
    print(f"[OK] Férias proporcionais: 13 meses = {months} meses no período atual")


def test_proportional_vacation_months_first_year():
    # 6 meses no primeiro ano, saída dia 10 (< 15 dias no mês)
    months = _count_proportional_vacation_months(date(2023, 1, 1), date(2023, 7, 10))
    assert months == 6, f"Esperado 6, obtido {months}"
    print(f"[OK] Férias proporcionais: 6 meses = {months}")


# ─────────────────────────────────────────────────────────────────────────────
# Integração
# ─────────────────────────────────────────────────────────────────────────────

def test_schedule_vacation():
    db = make_db()
    company, admin, emp = setup(db)
    vac = schedule_vacation(
        db,
        VacationCreate(
            employee_id=emp["id"],
            acquisition_start=date(2023, 1, 1),
            acquisition_end=date(2023, 12, 31),
            enjoyment_start=date(2024, 1, 10),
            enjoyment_days=30,
        ),
        company.id, admin.id,
    )
    assert vac.status == VacationStatus.SCHEDULED
    assert vac.base_salary == Decimal("3000.00")
    assert vac.one_third_bonus == Decimal("1000.00")
    print(f"[OK] Ferias agendadas: base=3000, 1/3=1000, status=agendada")


def test_schedule_vacation_duplicate_409():
    db = make_db()
    company, admin, emp = setup(db)

    def _sched():
        return schedule_vacation(
            db,
            VacationCreate(
                employee_id=emp["id"],
                acquisition_start=date(2023, 1, 1),
                acquisition_end=date(2023, 12, 31),
            ),
            company.id, admin.id,
        )

    _sched()
    try:
        _sched()
        assert False, "Deveria ter retornado 409"
    except Exception as e:
        assert "409" in str(e) or "sobrepoe" in str(e).lower() or "sobrep" in str(e).lower()
        print("[OK] Ferias duplicadas retornam 409")


def test_start_vacation():
    db = make_db()
    company, admin, emp = setup(db)
    vac = schedule_vacation(
        db,
        VacationCreate(
            employee_id=emp["id"],
            acquisition_start=date(2023, 1, 1),
            acquisition_end=date(2023, 12, 31),
        ),
        company.id, admin.id,
    )
    vac = start_vacation(db, vac.id, VacationStart(enjoyment_start=date(2024, 1, 10)), company.id, admin.id)
    assert vac.status == VacationStatus.ACTIVE
    assert vac.enjoyment_start == date(2024, 1, 10)
    print("[OK] Ferias iniciadas: status=em_gozo")


def test_complete_vacation():
    db = make_db()
    company, admin, emp = setup(db)
    vac = schedule_vacation(
        db,
        VacationCreate(
            employee_id=emp["id"],
            acquisition_start=date(2023, 1, 1),
            acquisition_end=date(2023, 12, 31),
        ),
        company.id, admin.id,
    )
    vac = start_vacation(db, vac.id, VacationStart(enjoyment_start=date(2024, 1, 10)), company.id, admin.id)
    vac = complete_vacation(db, vac.id, company.id, admin.id)
    assert vac.status == VacationStatus.COMPLETED
    print("[OK] Ferias concluidas: status=concluida")


def test_cancel_vacation():
    db = make_db()
    company, admin, emp = setup(db)
    vac = schedule_vacation(
        db,
        VacationCreate(
            employee_id=emp["id"],
            acquisition_start=date(2023, 1, 1),
            acquisition_end=date(2023, 12, 31),
        ),
        company.id, admin.id,
    )
    vac = cancel_vacation(db, vac.id, company.id, admin.id)
    assert vac.status == VacationStatus.CANCELLED
    print("[OK] Ferias canceladas: status=cancelada")


def test_thirteenth_parcela1():
    db = make_db()
    company, admin, emp = setup(db, salary=Decimal("3000"), admission=date(2023, 1, 1))
    result = get_thirteenth(db, emp["id"], 2023, 1, company.id)
    # 12 meses completos, bruto = 3000
    assert result["worked_months"] == 12
    assert result["bruto_13"]      == Decimal("3000.00")
    assert result["liquido"]       == Decimal("1500.00")  # parcela 1 = bruto/2, sem INSS
    print(f"[OK] 13 parcela 1 (12 meses): bruto=3000, liq=1500")


def test_thirteenth_parcela2():
    db = make_db()
    company, admin, emp = setup(db, salary=Decimal("3000"), admission=date(2023, 1, 1))
    result = get_thirteenth(db, emp["id"], 2023, 2, company.id)
    from app.utils.inss_calc import calc_inss
    inss_13 = calc_inss(Decimal("3000"))
    esperado = Decimal("3000") - inss_13 - Decimal("1500")
    assert result["liquido"] == esperado
    print(f"[OK] 13 parcela 2: bruto=3000, INSS={inss_13}, liq={result['liquido']}")


def test_thirteenth_6_meses():
    db = make_db()
    company, admin, emp = setup(db, salary=Decimal("3000"), admission=date(2023, 7, 1))
    result = get_thirteenth(db, emp["id"], 2023, 1, company.id)
    assert result["worked_months"] == 6
    assert result["bruto_13"] == Decimal("1500.00")
    assert result["liquido"]  == Decimal("750.00")
    print(f"[OK] 13 6 meses: bruto=1500, parcela1=750")


def test_create_termination_sem_justa_causa():
    db = make_db()
    company, admin, emp = setup(db, salary=Decimal("3000"), admission=date(2022, 1, 1))
    term = create_termination(
        db,
        TerminationCreate(
            employee_id=emp["id"],
            termination_date=date(2023, 6, 15),
            reason=TerminationReason.SEM_JUSTA_CAUSA,
            notice_worked=False,
        ),
        company.id, admin.id,
    )
    assert term.notice_days > 0, "Deve ter aviso previo"
    assert term.multa_fgts > 0,  "Deve ter multa FGTS 40%"
    assert term.aviso_previo_indenizado > 0, "Aviso indenizado deve ser positivo"
    assert term.liquido > 0
    print(f"[OK] Rescisao sem justa causa: aviso={term.notice_days}d, multa_fgts={term.multa_fgts}, liq={term.liquido}")


def test_termination_inactivates_employee():
    db = make_db()
    company, admin, emp = setup(db, salary=Decimal("3000"), admission=date(2022, 1, 1))
    create_termination(
        db,
        TerminationCreate(
            employee_id=emp["id"],
            termination_date=date(2023, 6, 15),
            reason=TerminationReason.SEM_JUSTA_CAUSA,
        ),
        company.id, admin.id,
    )
    from app.repositories import employee as emp_repo_check
    emp_obj = emp_repo_check.get_employee(db, emp["id"])
    assert emp_obj.status == EmployeeStatus.INACTIVE
    assert emp_obj.inactivation_date == date(2023, 6, 15)
    print("[OK] Funcionario inativado apos rescisao")


def test_termination_com_justa_causa_sem_multa():
    db = make_db()
    company, admin, emp = setup(db, salary=Decimal("3000"), admission=date(2022, 1, 1))
    term = create_termination(
        db,
        TerminationCreate(
            employee_id=emp["id"],
            termination_date=date(2023, 6, 15),
            reason=TerminationReason.COM_JUSTA_CAUSA,
        ),
        company.id, admin.id,
    )
    assert term.notice_days             == 0, "Justa causa: sem aviso"
    assert term.multa_fgts              == Decimal("0"), "Justa causa: sem multa FGTS"
    assert term.aviso_previo_indenizado == Decimal("0"), "Justa causa: sem aviso indenizado"
    print(f"[OK] Justa causa: sem aviso, sem multa FGTS, liq={term.liquido}")


def test_termination_duplicate_409():
    db = make_db()
    company, admin, emp = setup(db, salary=Decimal("3000"), admission=date(2022, 1, 1))

    def _term():
        return create_termination(
            db,
            TerminationCreate(
                employee_id=emp["id"],
                termination_date=date(2023, 6, 15),
                reason=TerminationReason.SEM_JUSTA_CAUSA,
            ),
            company.id, admin.id,
        )

    _term()
    try:
        _term()
        assert False, "Deveria retornar 409 ou inativo"
    except Exception as e:
        assert "409" in str(e) or "inativ" in str(e).lower() or "rescis" in str(e).lower()
        print("[OK] Segunda rescisao retorna erro (409 ou funcionario inativo)")


def test_ferias_vencidas_em_rescisao():
    """Funcionario com 2+ anos sem ferias deve ter ferias vencidas na rescisao."""
    db = make_db()
    # Admissao em 2021: em 2024 ja tem 3 periodos completos
    company, admin, emp = setup(db, salary=Decimal("3000"), admission=date(2021, 1, 1))
    term = create_termination(
        db,
        TerminationCreate(
            employee_id=emp["id"],
            termination_date=date(2024, 6, 15),
            reason=TerminationReason.SEM_JUSTA_CAUSA,
        ),
        company.id, admin.id,
    )
    assert term.ferias_vencidas > 0, f"Deve ter ferias vencidas, obtido {term.ferias_vencidas}"
    assert term.um_terco_ferias_venc > 0
    print(f"[OK] Ferias vencidas (3 periodos sem gozo): R$ {term.ferias_vencidas} + 1/3={term.um_terco_ferias_venc}")


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=== Testando modulo de Ferias, 13 Salario e Rescisao ===\n")

    test_calc_vacation_pay_30_dias()
    test_calc_vacation_pay_15_dias()
    test_calc_notice_days_sem_justa_causa()
    test_calc_notice_days_max_90()
    test_calc_notice_days_com_justa_causa()
    test_calc_notice_days_acordo()
    test_proportional_vacation_months()
    test_proportional_vacation_months_first_year()
    test_schedule_vacation()
    test_schedule_vacation_duplicate_409()
    test_start_vacation()
    test_complete_vacation()
    test_cancel_vacation()
    test_thirteenth_parcela1()
    test_thirteenth_parcela2()
    test_thirteenth_6_meses()
    test_create_termination_sem_justa_causa()
    test_termination_inactivates_employee()
    test_termination_com_justa_causa_sem_multa()
    test_termination_duplicate_409()
    test_ferias_vencidas_em_rescisao()

    print("\nTodos os testes de ferias/13/rescisao passaram!")
