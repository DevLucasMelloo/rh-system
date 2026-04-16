"""
Serviço de autenticação.
Todas as regras de login, token e reset de senha ficam aqui — nunca nos endpoints.
"""
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.core.security import (
    verify_password, hash_password,
    create_access_token, create_refresh_token,
    create_password_reset_token, decode_token,
)
from app.repositories import user as user_repo
from app.repositories import audit_log as audit_repo
from app.schemas.auth import LoginRequest, TokenResponse, PasswordResetConfirm
from app.utils.email import send_password_reset


def login(db: Session, data: LoginRequest, ip: str | None = None) -> TokenResponse:
    user = user_repo.get_by_email(db, data.email)

    # Mensagem genérica — não revelar se o email existe ou não
    invalid = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Email ou senha incorretos",
    )

    if not user or not user.is_active:
        raise invalid

    if not verify_password(data.password, user.hashed_password):
        audit_repo.create_log(
            db, action="login_failed", user_id=user.id,
            description=f"Tentativa de login falhou para {data.email}",
            ip_address=ip,
        )
        raise invalid

    access = create_access_token(user.id, user.role.value)
    refresh = create_refresh_token(user.id)

    user_repo.update_refresh_token(db, user, refresh)
    audit_repo.create_log(
        db, action="login", user_id=user.id,
        description=f"Login realizado por {user.email}",
        ip_address=ip,
    )

    return TokenResponse(access_token=access, refresh_token=refresh)


def refresh_access_token(db: Session, refresh_token: str) -> TokenResponse:
    payload = decode_token(refresh_token, expected_type="refresh")
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token inválido")

    user = user_repo.get_user(db, int(payload["sub"]))
    if not user or not user.is_active or user.refresh_token != refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token inválido")

    new_access = create_access_token(user.id, user.role.value)
    new_refresh = create_refresh_token(user.id)
    user_repo.update_refresh_token(db, user, new_refresh)

    return TokenResponse(access_token=new_access, refresh_token=new_refresh)


def logout(db: Session, user_id: int) -> None:
    user = user_repo.get_user(db, user_id)
    if user:
        user_repo.update_refresh_token(db, user, None)


def request_password_reset(db: Session, email: str) -> None:
    """
    Envia link de reset de senha.
    Sempre retorna sucesso mesmo se o email não existir (evita enumeração de usuários).
    """
    user = user_repo.get_by_email(db, email)
    if not user or not user.is_active:
        return  # Silencioso

    token = create_password_reset_token(email)
    reset_link = f"http://localhost/reset-password?token={token}"
    send_password_reset(email, reset_link)


def confirm_password_reset(db: Session, data: PasswordResetConfirm) -> None:
    payload = decode_token(data.token, expected_type="password_reset")
    if not payload:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token inválido ou expirado")

    user = user_repo.get_by_email(db, payload["sub"])
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token inválido ou expirado")

    if len(data.new_password) < 8:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Senha deve ter pelo menos 8 caracteres")

    user_repo.update_password(db, user, hash_password(data.new_password))
    user_repo.update_refresh_token(db, user, None)  # invalida sessões abertas
    audit_repo.create_log(
        db, action="password_reset", user_id=user.id,
        description=f"Senha redefinida para {user.email}",
    )
