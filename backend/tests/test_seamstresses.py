"""
Testes do módulo de costureiras.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.models import *
from app.schemas.company import CompanyCreate
from app.schemas.user import UserCreate
from app.schemas.seamstress import (
    SeamstressCreate, SeamstressUpdate,
    SeamstressPaymentCreate, SeamstressPaymentUpdate,
)
from app.services import company as company_service
from app.services import user as user_service
from app.services import seamstress as seamstress_service


def make_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def setup(db):
    company = company_service.register_company(
        db, CompanyCreate(razao_social="Teste", cnpj="11222333000181", email="a@b.com")
    )
    admin = user_service.create_user(
        db, UserCreate(name="Admin", email="admin@t.com", password="Senha@123", role="admin"),
        company.id, 0,
    )
    return company, admin


def make_seamstress(db, company_id, admin_id, name="Ana Costureira"):
    return seamstress_service.create_seamstress(
        db, SeamstressCreate(name=name, phone="(11) 91234-5678"),
        company_id=company_id, created_by_id=admin_id,
    )


# ── Testes ────────────────────────────────────────────────────────────────────

def test_criar_costureira():
    db = make_db()
    company, admin = setup(db)
    s = make_seamstress(db, company.id, admin.id)

    assert s.id is not None
    assert s.name == "Ana Costureira"
    assert s.is_active is True
    print("[OK] Criar costureira")


def test_lancar_pagamento():
    db = make_db()
    company, admin = setup(db)
    s = make_seamstress(db, company.id, admin.id)

    p = seamstress_service.add_payment(
        db, s.id,
        SeamstressPaymentCreate(competence_month=4, competence_year=2025, amount=Decimal("850.00"), notes="Lote abril"),
        company_id=company.id, created_by_id=admin.id,
    )
    assert p["amount"] == Decimal("850.00")
    assert p["competence_month"] == 4
    assert p["seamstress_name"] == "Ana Costureira"
    print("[OK] Lancamento de pagamento mensal")


def test_pagamento_duplicado_no_mesmo_mes():
    from fastapi import HTTPException
    db = make_db()
    company, admin = setup(db)
    s = make_seamstress(db, company.id, admin.id)

    seamstress_service.add_payment(
        db, s.id,
        SeamstressPaymentCreate(competence_month=4, competence_year=2025, amount=Decimal("850.00")),
        company.id, admin.id,
    )
    try:
        seamstress_service.add_payment(
            db, s.id,
            SeamstressPaymentCreate(competence_month=4, competence_year=2025, amount=Decimal("900.00")),
            company.id, admin.id,
        )
        assert False
    except HTTPException as e:
        assert e.status_code == 409
    print("[OK] Pagamento duplicado no mesmo mes retorna 409")


def test_meses_sem_demanda_nao_entram_na_lista():
    db = make_db()
    company, admin = setup(db)
    s = make_seamstress(db, company.id, admin.id)

    # Lança só em março e maio
    seamstress_service.add_payment(db, s.id, SeamstressPaymentCreate(competence_month=3, competence_year=2025, amount=Decimal("700.00")), company.id, admin.id)
    seamstress_service.add_payment(db, s.id, SeamstressPaymentCreate(competence_month=5, competence_year=2025, amount=Decimal("920.00")), company.id, admin.id)

    # Abril não tem lançamento
    abril = seamstress_service.get_period_total(db, company.id, month=4, year=2025)
    assert abril["count"] == 0
    assert abril["total"] == 0

    # Março tem
    marco = seamstress_service.get_period_total(db, company.id, month=3, year=2025)
    assert marco["count"] == 1
    print("[OK] Meses sem demanda nao aparecem no relatorio")


def test_editar_pagamento():
    db = make_db()
    company, admin = setup(db)
    s = make_seamstress(db, company.id, admin.id)

    p = seamstress_service.add_payment(
        db, s.id,
        SeamstressPaymentCreate(competence_month=4, competence_year=2025, amount=Decimal("800.00")),
        company.id, admin.id,
    )
    updated = seamstress_service.update_payment(
        db, p["id"],
        SeamstressPaymentUpdate(amount=Decimal("950.00"), notes="Ajuste"),
        company.id, admin.id,
    )
    assert updated["amount"] == Decimal("950.00")
    assert updated["notes"] == "Ajuste"
    print("[OK] Editar valor de pagamento")


def test_excluir_pagamento():
    from fastapi import HTTPException
    db = make_db()
    company, admin = setup(db)
    s = make_seamstress(db, company.id, admin.id)

    p = seamstress_service.add_payment(
        db, s.id,
        SeamstressPaymentCreate(competence_month=4, competence_year=2025, amount=Decimal("800.00")),
        company.id, admin.id,
    )
    seamstress_service.delete_payment(db, p["id"], company.id, admin.id)

    # Após exclusão, o mês fica vazio
    result = seamstress_service.get_period_total(db, company.id, month=4, year=2025)
    assert result["count"] == 0
    print("[OK] Excluir pagamento")


def test_total_mensal_multiplas_costureiras():
    db = make_db()
    company, admin = setup(db)
    s1 = make_seamstress(db, company.id, admin.id, name="Ana")
    s2 = make_seamstress(db, company.id, admin.id, name="Beatriz")
    s3 = make_seamstress(db, company.id, admin.id, name="Carla")

    seamstress_service.add_payment(db, s1.id, SeamstressPaymentCreate(competence_month=6, competence_year=2025, amount=Decimal("800.00")), company.id, admin.id)
    seamstress_service.add_payment(db, s2.id, SeamstressPaymentCreate(competence_month=6, competence_year=2025, amount=Decimal("1200.00")), company.id, admin.id)
    # s3 nao trabalhou em junho

    result = seamstress_service.get_period_total(db, company.id, month=6, year=2025)
    assert result["count"] == 2
    assert result["total"] == Decimal("2000.00")
    print("[OK] Total mensal com multiplas costureiras (s3 nao entra por nao ter lancamento)")


def test_costureira_inativa_nao_aceita_pagamento():
    from fastapi import HTTPException
    db = make_db()
    company, admin = setup(db)
    s = make_seamstress(db, company.id, admin.id)

    seamstress_service.update_seamstress(
        db, s.id, SeamstressUpdate(is_active=False), company.id, admin.id
    )
    try:
        seamstress_service.add_payment(
            db, s.id,
            SeamstressPaymentCreate(competence_month=4, competence_year=2025, amount=Decimal("800.00")),
            company.id, admin.id,
        )
        assert False
    except HTTPException as e:
        assert e.status_code == 400
    print("[OK] Costureira inativa nao aceita novo lancamento")


def test_isolamento_entre_empresas():
    from fastapi import HTTPException
    db = make_db()
    company1, admin1 = setup(db)
    company2 = company_service.register_company(
        db, CompanyCreate(razao_social="Empresa 2", cnpj="12345678000195", email="b@c.com")
    )
    s = make_seamstress(db, company1.id, admin1.id)

    try:
        seamstress_service.get_seamstress(db, s.id, company_id=company2.id)
        assert False
    except HTTPException as e:
        assert e.status_code == 404
    print("[OK] Costureira de outra empresa retorna 404")


if __name__ == "__main__":
    print("=== Testando modulo de costureiras ===\n")
    test_criar_costureira()
    test_lancar_pagamento()
    test_pagamento_duplicado_no_mesmo_mes()
    test_meses_sem_demanda_nao_entram_na_lista()
    test_editar_pagamento()
    test_excluir_pagamento()
    test_total_mensal_multiplas_costureiras()
    test_costureira_inativa_nao_aceita_pagamento()
    test_isolamento_entre_empresas()
    print("\nTodos os testes passaram!")
