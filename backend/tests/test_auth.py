"""
Testes de autenticação usando banco SQLite em memória.
Cada teste começa com banco limpo — sem interferência entre testes.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.models import *  # registra todos os models
from app.schemas.auth import LoginRequest, RefreshRequest, PasswordResetConfirm
from app.schemas.company import CompanyCreate
from app.schemas.user import UserCreate, PasswordChange
from app.services import auth as auth_service
from app.services import company as company_service
from app.services import user as user_service
from app.repositories import user as user_repo


# ── Banco em memória para testes ──────────────────────────────────────────────
def make_test_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


def setup_company_and_admin(db):
    """Cria empresa e usuário admin para uso nos testes."""
    company = company_service.register_company(
        db,
        CompanyCreate(
            razao_social="Empresa Teste LTDA",
            cnpj="11222333000181",
            email="empresa@teste.com",
        ),
    )
    admin = user_service.create_user(
        db,
        UserCreate(name="Admin Teste", email="admin@teste.com", password="Senha@123", role="admin"),
        company_id=company.id,
        created_by_id=0,
    )
    return company, admin


# ── Testes ────────────────────────────────────────────────────────────────────

def test_login_sucesso():
    db = make_test_db()
    _, admin = setup_company_and_admin(db)

    tokens = auth_service.login(db, LoginRequest(email="admin@teste.com", password="Senha@123"))
    assert tokens.access_token
    assert tokens.refresh_token
    assert tokens.token_type == "bearer"
    print("[OK] Login com credenciais corretas")


def test_login_senha_errada():
    from fastapi import HTTPException
    db = make_test_db()
    setup_company_and_admin(db)

    try:
        auth_service.login(db, LoginRequest(email="admin@teste.com", password="errada"))
        assert False, "Deveria ter levantado HTTPException"
    except HTTPException as e:
        assert e.status_code == 401
    print("[OK] Login com senha errada retorna 401")


def test_login_email_inexistente():
    from fastapi import HTTPException
    db = make_test_db()

    try:
        auth_service.login(db, LoginRequest(email="nao@existe.com", password="qualquer"))
        assert False
    except HTTPException as e:
        assert e.status_code == 401
    print("[OK] Login com email inexistente retorna 401 (sem revelar existencia)")


def test_refresh_token():
    db = make_test_db()
    setup_company_and_admin(db)

    tokens = auth_service.login(db, LoginRequest(email="admin@teste.com", password="Senha@123"))
    new_tokens = auth_service.refresh_access_token(db, tokens.refresh_token)

    assert new_tokens.access_token != tokens.access_token
    assert new_tokens.refresh_token
    print("[OK] Refresh token gera novos tokens")


def test_refresh_token_invalido():
    from fastapi import HTTPException
    db = make_test_db()

    try:
        auth_service.refresh_access_token(db, "token.invalido.aqui")
        assert False
    except HTTPException as e:
        assert e.status_code == 401
    print("[OK] Refresh token invalido retorna 401")


def test_logout_invalida_refresh():
    from fastapi import HTTPException
    db = make_test_db()
    _, admin = setup_company_and_admin(db)

    tokens = auth_service.login(db, LoginRequest(email="admin@teste.com", password="Senha@123"))
    auth_service.logout(db, admin.id)

    # Após logout, o refresh token não deve mais funcionar
    try:
        auth_service.refresh_access_token(db, tokens.refresh_token)
        assert False
    except HTTPException as e:
        assert e.status_code == 401
    print("[OK] Logout invalida o refresh token")


def test_criar_usuario_somente_admin():
    db = make_test_db()
    company, admin = setup_company_and_admin(db)

    rh = user_service.create_user(
        db,
        UserCreate(name="Fulano RH", email="rh@teste.com", password="Senha@123", role="rh"),
        company_id=company.id,
        created_by_id=admin.id,
    )
    assert rh.id
    assert rh.role.value == "rh"
    print("[OK] Admin cria usuario com perfil RH")


def test_email_duplicado():
    from fastapi import HTTPException
    db = make_test_db()
    company, admin = setup_company_and_admin(db)

    try:
        user_service.create_user(
            db,
            UserCreate(name="Outro", email="admin@teste.com", password="Senha@123"),
            company_id=company.id,
            created_by_id=admin.id,
        )
        assert False
    except HTTPException as e:
        assert e.status_code == 409
    print("[OK] Email duplicado retorna 409")


def test_trocar_senha():
    from fastapi import HTTPException
    db = make_test_db()
    _, admin = setup_company_and_admin(db)

    user_service.change_password(
        db, admin.id,
        PasswordChange(current_password="Senha@123", new_password="NovaSenha@456"),
    )

    # Senha antiga não deve mais funcionar
    try:
        auth_service.login(db, LoginRequest(email="admin@teste.com", password="Senha@123"))
        assert False
    except HTTPException:
        pass

    # Nova senha deve funcionar
    tokens = auth_service.login(db, LoginRequest(email="admin@teste.com", password="NovaSenha@456"))
    assert tokens.access_token
    print("[OK] Troca de senha funciona e invalida senha antiga")


def test_reset_senha_token_invalido():
    from fastapi import HTTPException
    db = make_test_db()

    try:
        auth_service.confirm_password_reset(
            db, PasswordResetConfirm(token="token.fake.aqui", new_password="Nova@123")
        )
        assert False
    except HTTPException as e:
        assert e.status_code == 400
    print("[OK] Reset com token invalido retorna 400")


if __name__ == "__main__":
    print("=== Testando autenticacao ===\n")
    test_login_sucesso()
    test_login_senha_errada()
    test_login_email_inexistente()
    test_refresh_token()
    test_refresh_token_invalido()
    test_logout_invalida_refresh()
    test_criar_usuario_somente_admin()
    test_email_duplicado()
    test_trocar_senha()
    test_reset_senha_token_invalido()
    print("\nTodos os testes passaram!")
