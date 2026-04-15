"""
Testes da camada de segurança:
- Hashing de senha com bcrypt
- Criptografia Fernet (campos sensíveis)
- Geração e validação de tokens JWT
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.security import (
    hash_password, verify_password,
    encrypt_field, decrypt_field,
    create_access_token, create_refresh_token,
    create_password_reset_token, decode_token,
)


def test_password_hashing():
    password = "MinhaSenh@Segura123"
    hashed = hash_password(password)

    assert hashed != password, "Hash não pode ser igual à senha original"
    assert hashed.startswith("$2b$"), "Deve usar bcrypt"
    assert verify_password(password, hashed), "Verificação deve retornar True para senha correta"
    assert not verify_password("senha_errada", hashed), "Deve retornar False para senha errada"
    print("[OK] bcrypt: hash e verificacao de senha")


def test_fernet_encryption():
    cpf = "123.456.789-00"
    encrypted = encrypt_field(cpf)

    assert encrypted != cpf, "Campo criptografado nao pode ser igual ao original"
    assert len(encrypted) > 50, "Token Fernet deve ser longo"

    decrypted = decrypt_field(encrypted)
    assert decrypted == cpf, "Descriptografia deve retornar valor original"

    # Campo vazio retorna vazio
    assert encrypt_field("") == ""
    assert decrypt_field("") == ""

    # Token invalido retorna string vazia (nao explode)
    assert decrypt_field("token_invalido_xpto") == ""
    print("[OK] Fernet: criptografia e descriptografia de campos sensiveis")


def test_access_token():
    token = create_access_token(user_id=42, role="admin")
    payload = decode_token(token, expected_type="access")

    assert payload is not None, "Token valido deve ser decodificavel"
    assert payload["sub"] == "42"
    assert payload["role"] == "admin"
    assert payload["type"] == "access"

    # Tipo errado deve falhar
    assert decode_token(token, expected_type="refresh") is None
    print("[OK] JWT: access token criado e validado")


def test_refresh_token():
    token = create_refresh_token(user_id=7)
    payload = decode_token(token, expected_type="refresh")

    assert payload is not None
    assert payload["sub"] == "7"
    assert payload["type"] == "refresh"
    print("[OK] JWT: refresh token criado e validado")


def test_password_reset_token():
    email = "usuario@empresa.com"
    token = create_password_reset_token(email)
    payload = decode_token(token, expected_type="password_reset")

    assert payload is not None
    assert payload["sub"] == email
    print("[OK] JWT: token de reset de senha criado e validado")


def test_token_type_isolation():
    """Tokens de tipos diferentes nao devem ser intercambiaveis."""
    access = create_access_token(user_id=1, role="rh")
    refresh = create_refresh_token(user_id=1)
    reset = create_password_reset_token("a@b.com")

    assert decode_token(access, "refresh") is None
    assert decode_token(access, "password_reset") is None
    assert decode_token(refresh, "access") is None
    assert decode_token(reset, "access") is None
    print("[OK] JWT: tokens de tipos diferentes sao isolados")


if __name__ == "__main__":
    print("=== Testando seguranca ===\n")
    test_password_hashing()
    test_fernet_encryption()
    test_access_token()
    test_refresh_token()
    test_password_reset_token()
    test_token_type_isolation()
    print("\nTodos os testes passaram!")
