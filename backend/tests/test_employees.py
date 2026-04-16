"""
Testes do módulo de funcionários.
Banco SQLite em memória — cada teste começa limpo.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import date
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.models import *
from app.schemas.company import CompanyCreate
from app.schemas.user import UserCreate
from app.schemas.employee import EmployeeCreate, EmployeeUpdate, SalaryUpdate, InactivateEmployee
from app.services import company as company_service
from app.services import user as user_service
from app.services import employee as emp_service
from app.core.security import decrypt_field


def make_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def setup(db):
    company = company_service.register_company(
        db, CompanyCreate(razao_social="Teste", cnpj="11222333000181", email="a@b.com")
    )
    admin = user_service.create_user(
        db,
        UserCreate(name="Admin", email="admin@t.com", password="Senha@123", role="admin"),
        company.id, 0,
    )
    return company, admin


def make_employee(db, company_id, admin_id, cpf="529.982.247-25", name="Joao Silva"):
    return emp_service.create_employee(
        db,
        EmployeeCreate(
            name=name,
            cpf=cpf,
            role="Operador",
            salary=Decimal("2500.00"),
            admission_date=date(2023, 1, 10),
            registration_date=date(2023, 1, 10),
        ),
        company_id=company_id,
        created_by_id=admin_id,
    )


# ── Testes ────────────────────────────────────────────────────────────────────

def test_criar_funcionario():
    db = make_db()
    company, admin = setup(db)
    emp = make_employee(db, company.id, admin.id)

    assert emp["id"] is not None
    assert emp["name"] == "Joao Silva"
    assert emp["cpf"] == "529.982.247-25"   # descriptografado corretamente
    assert emp["salary"] == Decimal("2500.00")
    assert emp["status"] == "ativo"
    print("[OK] Criar funcionario — CPF descriptografado na resposta")


def test_cpf_invalido():
    from fastapi import HTTPException
    db = make_db()
    company, admin = setup(db)
    try:
        emp_service.create_employee(
            db,
            EmployeeCreate(
                name="Teste", cpf="000.000.000-00", role="Op",
                salary=Decimal("1500"), admission_date=date.today(), registration_date=date.today(),
            ),
            company.id, admin.id,
        )
        assert False, "Deveria rejeitar CPF inválido"
    except Exception as e:
        assert "CPF" in str(e)
    print("[OK] CPF invalido rejeitado pelo schema")


def test_cpf_duplicado():
    from fastapi import HTTPException
    db = make_db()
    company, admin = setup(db)
    make_employee(db, company.id, admin.id)

    try:
        make_employee(db, company.id, admin.id, cpf="529.982.247-25", name="Outro")
        assert False
    except HTTPException as e:
        assert e.status_code == 409
    print("[OK] CPF duplicado retorna 409")


def test_cpf_criptografado_no_banco():
    from sqlalchemy import create_engine, text
    db = make_db()
    company, admin = setup(db)
    make_employee(db, company.id, admin.id)

    # Acessar diretamente o banco para verificar criptografia
    from app.models.employee import Employee
    raw = db.query(Employee).first()
    assert raw.cpf_encrypted != "529.982.247-25", "CPF nao pode estar em texto puro no banco"
    assert len(raw.cpf_encrypted) > 50, "Deve ser token Fernet longo"
    assert decrypt_field(raw.cpf_encrypted) == "529.982.247-25"
    print("[OK] CPF criptografado no banco, descriptografado corretamente")


def test_listar_ativos_e_inativos():
    db = make_db()
    company, admin = setup(db)
    make_employee(db, company.id, admin.id, cpf="529.982.247-25", name="Ativo 1")
    e2 = make_employee(db, company.id, admin.id, cpf="153.509.460-56", name="Ativo 2")

    ativos = emp_service.list_employees(db, company.id, active_only=True)
    assert len(ativos) == 2

    emp_service.inactivate_employee(
        db, e2["id"], InactivateEmployee(reason="Pediu demissao"), company.id, admin.id
    )

    ativos_depois = emp_service.list_employees(db, company.id, active_only=True)
    inativos = emp_service.list_employees(db, company.id, active_only=False)

    assert len(ativos_depois) == 1
    assert len(inativos) == 1
    assert inativos[0]["status"] == "inativo"
    print("[OK] Listar ativos e inativos separadamente")


def test_reajuste_salarial_com_historico():
    db = make_db()
    company, admin = setup(db)
    emp = make_employee(db, company.id, admin.id)

    atualizado = emp_service.update_salary(
        db, emp["id"],
        SalaryUpdate(new_salary=Decimal("3000.00"), reason="Promoção anual"),
        company.id, admin.id,
    )
    assert atualizado["salary"] == Decimal("3000.00")

    historico = emp_service.get_history(db, emp["id"], company.id)
    reajuste = next(h for h in historico if h["field_changed"] == "salary")
    assert reajuste["old_value"] == "2500.00"
    assert reajuste["new_value"] == "3000.00"
    assert reajuste["reason"] == "Promoção anual"
    print("[OK] Reajuste salarial com historico registrado")


def test_inativar_e_reativar():
    from fastapi import HTTPException
    db = make_db()
    company, admin = setup(db)
    emp = make_employee(db, company.id, admin.id)

    inativado = emp_service.inactivate_employee(
        db, emp["id"], InactivateEmployee(reason="Rescisao"), company.id, admin.id
    )
    assert inativado["status"] == "inativo"
    assert inativado["inactivation_reason"] == "Rescisao"

    # Inativar de novo deve falhar
    try:
        emp_service.inactivate_employee(
            db, emp["id"], InactivateEmployee(reason="De novo"), company.id, admin.id
        )
        assert False
    except HTTPException as e:
        assert e.status_code == 400

    # Reativar
    reativado = emp_service.reactivate_employee(db, emp["id"], company.id, admin.id)
    assert reativado["status"] == "ativo"
    assert reativado["inactivation_date"] is None
    print("[OK] Inativar e reativar funcionario")


def test_atualizar_dados():
    db = make_db()
    company, admin = setup(db)
    emp = make_employee(db, company.id, admin.id)

    atualizado = emp_service.update_employee(
        db, emp["id"],
        EmployeeUpdate(phone="(11) 99999-0000", city="Campinas", role="Supervisor"),
        company.id, admin.id,
    )
    assert atualizado["phone"] == "(11) 99999-0000"
    assert atualizado["city"] == "Campinas"
    assert atualizado["role"] == "Supervisor"

    historico = emp_service.get_history(db, emp["id"], company.id)
    campos = [h["field_changed"] for h in historico]
    assert "phone" in campos
    assert "role" in campos
    print("[OK] Atualizar dados com historico de alteracoes")


def test_acesso_entre_empresas_bloqueado():
    from fastapi import HTTPException
    db = make_db()
    company1, admin1 = setup(db)
    company2 = company_service.register_company(
        db, CompanyCreate(razao_social="Empresa 2", cnpj="12345678000195", email="b@c.com")
    )
    emp = make_employee(db, company1.id, admin1.id)

    # Empresa 2 não deve acessar funcionário da empresa 1
    try:
        emp_service.get_employee(db, emp["id"], company_id=company2.id)
        assert False
    except HTTPException as e:
        assert e.status_code == 404
    print("[OK] Isolamento entre empresas — 404 ao acessar funcionario de outra empresa")


def test_reajuste_funcionario_inativo_bloqueado():
    from fastapi import HTTPException
    db = make_db()
    company, admin = setup(db)
    emp = make_employee(db, company.id, admin.id)
    emp_service.inactivate_employee(
        db, emp["id"], InactivateEmployee(reason="Saiu"), company.id, admin.id
    )

    try:
        emp_service.update_salary(
            db, emp["id"],
            SalaryUpdate(new_salary=Decimal("9999"), reason="Tentativa"),
            company.id, admin.id,
        )
        assert False
    except HTTPException as e:
        assert e.status_code == 400
    print("[OK] Reajuste de funcionario inativo bloqueado")


if __name__ == "__main__":
    print("=== Testando modulo de funcionarios ===\n")
    test_criar_funcionario()
    test_cpf_invalido()
    test_cpf_duplicado()
    test_cpf_criptografado_no_banco()
    test_listar_ativos_e_inativos()
    test_reajuste_salarial_com_historico()
    test_inativar_e_reativar()
    test_atualizar_dados()
    test_acesso_entre_empresas_bloqueado()
    test_reajuste_funcionario_inativo_bloqueado()
    print("\nTodos os testes passaram!")
