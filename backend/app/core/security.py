"""
Módulo central de segurança:
- Hashing de senhas com bcrypt
- Criação e validação de tokens JWT (access + refresh)
- Criptografia/descriptografia Fernet para dados sensíveis
"""
from datetime import datetime, timedelta, timezone
from typing import Optional
import secrets

import bcrypt
from cryptography.fernet import Fernet, InvalidToken
from jose import JWTError, jwt

from app.core.config import settings

# ---------------------------------------------------------------------------
# Fernet — criptografia de campos sensíveis (CPF, RG, conta bancária)
# ---------------------------------------------------------------------------
_fernet = Fernet(settings.FERNET_KEY.encode())


def encrypt_field(value: str) -> str:
    """Criptografa um campo sensível antes de salvar no banco."""
    if not value:
        return value
    return _fernet.encrypt(value.encode()).decode()


def decrypt_field(value: str) -> str:
    """Descriptografa um campo sensível recuperado do banco."""
    if not value:
        return value
    try:
        return _fernet.decrypt(value.encode()).decode()
    except InvalidToken:
        # Retorna vazio em vez de explodir — log de auditoria pode registrar
        return ""


# ---------------------------------------------------------------------------
# Senhas
# ---------------------------------------------------------------------------
def hash_password(plain_password: str) -> str:
    """Gera hash bcrypt da senha. Nunca armazenar em texto puro."""
    return bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Compara senha fornecida com hash armazenado."""
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


# ---------------------------------------------------------------------------
# JWT — Access Token e Refresh Token
# ---------------------------------------------------------------------------
def _create_token(
    data: dict,
    expires_delta: timedelta,
    token_type: str,
) -> str:
    payload = data.copy()
    now = datetime.now(timezone.utc)
    payload.update({
        "iat": now,
        "exp": now + expires_delta,
        "type": token_type,
        "jti": secrets.token_hex(16),  # ID único por token — garante unicidade mesmo no mesmo segundo
    })
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_access_token(user_id: int, role: str) -> str:
    """Cria access token com validade curta."""
    return _create_token(
        data={"sub": str(user_id), "role": role},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        token_type="access",
    )


def create_refresh_token(user_id: int) -> str:
    """Cria refresh token com validade longa."""
    return _create_token(
        data={"sub": str(user_id)},
        expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        token_type="refresh",
    )


def create_password_reset_token(email: str) -> str:
    """Cria token temporário para reset de senha (15 min)."""
    return _create_token(
        data={"sub": email},
        expires_delta=timedelta(minutes=15),
        token_type="password_reset",
    )


def decode_token(token: str, expected_type: str) -> Optional[dict]:
    """
    Decodifica e valida um JWT.
    Retorna o payload ou None se inválido/expirado/tipo errado.
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        if payload.get("type") != expected_type:
            return None
        return payload
    except JWTError:
        return None
