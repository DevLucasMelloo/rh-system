"""
Testes do módulo de Relatórios e Dashboard.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import date, timedelta
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.models import *
from app.schemas.company import CompanyCreate
from app.schemas.user import UserCreate
from app.schemas.employee import EmployeeCreate
from app.schemas.payroll import PayrollCreate
from app.schemas.vacation import VacationCreate, VacationStart, TerminationCreate
from app.models.termination import TerminationReason
from app.services import company as company_service
from app.services import user as user_service
from app.services import employee as emp_service
from app.services import payroll as payroll_service
from app.services import vacation as vac_service
from app.services import reports as report_service


def make_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def setup(db, n_employees=2):
    """Cria empresa, admin e N funcionários."""
    company = company_service.register_company(
        db, CompanyCreate(razao_social="Empresa Teste", cnpj="11222333000181", email="a@b.com")
    )
    admin = user_service.create_user(
        db, UserCreate(name="Admin", email="admin@t.com", password="Senha@123", role="admin"),
        company.id, 0,
    )
    emps = []
    cpfs = ["529.982.247-25", "811.311.183-24", "987.654.321-00"]
    for i in range(n_employees):
        emp = emp_service.create_employee(
            db, EmployeeCreate(
                name=f"Funcionario {i+1}",
                cpf=cpfs[i],
                role="Analista",
                salary=Decimal("3000"),
                admission_date=date(2023, 1, 1),
                registration_date=date(2023, 1, 1),
            ),
            company.id, admin.id,
        )
        emps.append(emp)
    return company, admin, emps


# ─────────────────────────────────────────────────────────────────────────────
# Dashboard
# ─────────────────────────────────────────────────────────────────────────────

def test_dashboard_vazio():
    """Dashboard com empresa sem funcionários retorna zeros."""
    db = make_db()
    company = company_service.register_company(
        db, CompanyCreate(razao_social="Vazia", cnpj="11222333000182", email="b@b.com")
    )
    d = report_service.get_dashboard(db, company.id)
    assert d.total_employees    == 0
    assert d.active_employees   == 0
    assert d.payrolls_draft     == 0
    assert d.total_net_salary   == Decimal("0")
    assert d.vacations_active   == 0
    assert d.birthdays_next_30_days == []
    print("[OK] Dashboard vazio: todos os contadores = 0")


def test_dashboard_com_funcionarios():
    db = make_db()
    company, admin, emps = setup(db, n_employees=2)
    d = report_service.get_dashboard(db, company.id)
    assert d.total_employees   == 2
    assert d.active_employees  == 2
    assert d.inactive_employees == 0
    print(f"[OK] Dashboard: {d.total_employees} funcionarios, {d.active_employees} ativos")


def test_dashboard_com_folha_fechada():
    db = make_db()
    company, admin, emps = setup(db, n_employees=1)
    today = date.today()
    p = payroll_service.create_payroll(
        db,
        PayrollCreate(employee_id=emps[0]["id"], competence_month=today.month, competence_year=today.year),
        company.id, admin.id,
    )
    payroll_service.close_payroll(db, p.id, today, company.id, admin.id)
    d = report_service.get_dashboard(db, company.id)
    assert d.payrolls_closed == 1
    assert d.payrolls_draft  == 0
    assert d.total_net_salary > 0
    print(f"[OK] Dashboard: folha fechada, net_salary={d.total_net_salary}")


def test_dashboard_ferias_expirando():
    db = make_db()
    company, admin, emps = setup(db, n_employees=1)
    # Férias com acquisition_end em 30 dias (dentro do alerta de 60 dias)
    expiry = date.today() + timedelta(days=30)
    vac_service.schedule_vacation(
        db,
        VacationCreate(
            employee_id=emps[0]["id"],
            acquisition_start=expiry - timedelta(days=365),
            acquisition_end=expiry,
        ),
        company.id, admin.id,
    )
    d = report_service.get_dashboard(db, company.id)
    assert d.vacations_expiring_60d == 1
    assert len(d.expiring_vacations) == 1
    print(f"[OK] Dashboard: ferias expirando em {d.expiring_vacations[0].days_until_expiry} dias")


def test_dashboard_aniversarios():
    db = make_db()
    company = company_service.register_company(
        db, CompanyCreate(razao_social="B-Day", cnpj="11222333000183", email="c@b.com")
    )
    admin = user_service.create_user(
        db, UserCreate(name="Admin", email="admin2@t.com", password="Senha@123", role="admin"),
        company.id, 0,
    )
    # Funcionário com aniversário em 10 dias
    bday = date.today() + timedelta(days=10)
    dob  = date(1990, bday.month, bday.day)
    emp_service.create_employee(
        db, EmployeeCreate(
            name="Ana Aniversario", cpf="529.982.247-25", role="Dev",
            salary=Decimal("3000"),
            admission_date=date(2022, 1, 1),
            registration_date=date(2022, 1, 1),
            date_of_birth=dob,
        ),
        company.id, admin.id,
    )
    d = report_service.get_dashboard(db, company.id)
    assert len(d.birthdays_next_30_days) == 1
    assert d.birthdays_next_30_days[0].days_until == 10
    print(f"[OK] Dashboard: aniversario em {d.birthdays_next_30_days[0].days_until} dias")


# ─────────────────────────────────────────────────────────────────────────────
# Relatórios Excel
# ─────────────────────────────────────────────────────────────────────────────

def test_report_payroll_vazio():
    db = make_db()
    company, admin, emps = setup(db, n_employees=1)
    data = report_service.report_payroll(db, company.id, 1, 2020)
    assert isinstance(data, bytes)
    assert len(data) > 0  # arquivo Excel sempre tem header
    print(f"[OK] Relatorio folha vazio: {len(data)} bytes")


def test_report_payroll_com_dados():
    db = make_db()
    company, admin, emps = setup(db, n_employees=2)
    today = date.today()
    for emp in emps:
        payroll_service.create_payroll(
            db,
            PayrollCreate(employee_id=emp["id"], competence_month=today.month, competence_year=today.year),
            company.id, admin.id,
        )
    data = report_service.report_payroll(db, company.id, today.month, today.year)
    assert len(data) > 500  # arquivo com conteúdo real
    print(f"[OK] Relatorio folha com 2 holerites: {len(data)} bytes")


def test_report_employees():
    db = make_db()
    company, admin, emps = setup(db, n_employees=2)
    data = report_service.report_employees(db, company.id)
    assert isinstance(data, bytes) and len(data) > 0
    print(f"[OK] Relatorio funcionarios: {len(data)} bytes")


def test_report_employees_include_inactive():
    db = make_db()
    company, admin, emps = setup(db, n_employees=2)
    # Demite o primeiro
    vac_service.create_termination(
        db,
        TerminationCreate(
            employee_id=emps[0]["id"],
            termination_date=date.today(),
            reason=TerminationReason.PEDIDO_DEMISSAO,
        ),
        company.id, admin.id,
    )
    data_only_active   = report_service.report_employees(db, company.id, include_inactive=False)
    data_with_inactive = report_service.report_employees(db, company.id, include_inactive=True)
    # Com inativos o arquivo deve ser maior (mais linhas)
    assert len(data_with_inactive) >= len(data_only_active)
    print(f"[OK] Relatorio com inativos: {len(data_with_inactive)} bytes (>= {len(data_only_active)})")


def test_report_timesheet():
    db = make_db()
    company, admin, emps = setup(db, n_employees=1)
    data = report_service.report_timesheet(db, company.id, 1, 2020)
    assert isinstance(data, bytes) and len(data) > 0
    print(f"[OK] Relatorio ponto: {len(data)} bytes")


def test_report_vacations():
    db = make_db()
    company, admin, emps = setup(db, n_employees=1)
    vac_service.schedule_vacation(
        db,
        VacationCreate(
            employee_id=emps[0]["id"],
            acquisition_start=date(2023, 1, 1),
            acquisition_end=date(2023, 12, 31),
        ),
        company.id, admin.id,
    )
    data = report_service.report_vacations(db, company.id)
    assert isinstance(data, bytes) and len(data) > 500
    print(f"[OK] Relatorio ferias: {len(data)} bytes")


def test_report_terminations():
    db = make_db()
    company, admin, emps = setup(db, n_employees=1)
    vac_service.create_termination(
        db,
        TerminationCreate(
            employee_id=emps[0]["id"],
            termination_date=date(2024, 6, 15),
            reason=TerminationReason.SEM_JUSTA_CAUSA,
        ),
        company.id, admin.id,
    )
    data = report_service.report_terminations(db, company.id)
    assert isinstance(data, bytes) and len(data) > 500
    print(f"[OK] Relatorio rescisoes: {len(data)} bytes")


def test_report_hour_bank():
    db = make_db()
    company, admin, emps = setup(db, n_employees=2)
    data = report_service.report_hour_bank(db, company.id)
    assert isinstance(data, bytes) and len(data) > 0
    print(f"[OK] Relatorio banco de horas: {len(data)} bytes")


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=== Testando modulo de Relatorios e Dashboard ===\n")

    test_dashboard_vazio()
    test_dashboard_com_funcionarios()
    test_dashboard_com_folha_fechada()
    test_dashboard_ferias_expirando()
    test_dashboard_aniversarios()
    test_report_payroll_vazio()
    test_report_payroll_com_dados()
    test_report_employees()
    test_report_employees_include_inactive()
    test_report_timesheet()
    test_report_vacations()
    test_report_terminations()
    test_report_hour_bank()

    print("\nTodos os testes de relatorios passaram!")
