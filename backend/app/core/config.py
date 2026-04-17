from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List
import os


class Settings(BaseSettings):
    # Ambiente
    ENVIRONMENT: str = "development"

    # Banco de dados
    DATABASE_URL: str = "sqlite:///./rh_system.db"

    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Criptografia Fernet
    FERNET_KEY: str

    # Email
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_FROM: str = ""

    # Banco — echo de queries SQL (desativar em dev para não poluir terminal)
    DB_ECHO: bool = False

    # Versão
    APP_VERSION: str = "1.0.0"

    # CORS
    ALLOWED_ORIGINS: str = "http://localhost,http://127.0.0.1,http://localhost:3000,http://127.0.0.1:3000,http://localhost:5500,http://127.0.0.1:5500"

    @property
    def allowed_origins_list(self) -> List[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",")]

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"

    @field_validator("SECRET_KEY")
    @classmethod
    def secret_key_must_be_strong(cls, v: str) -> str:
        if v == "troque-esta-chave-por-uma-segura":
            raise ValueError("SECRET_KEY não pode ser o valor padrão de exemplo")
        if len(v) < 32:
            raise ValueError("SECRET_KEY deve ter pelo menos 32 caracteres")
        return v

    @field_validator("FERNET_KEY")
    @classmethod
    def fernet_key_must_be_set(cls, v: str) -> str:
        if v == "troque-esta-chave-por-uma-gerada":
            raise ValueError("FERNET_KEY não pode ser o valor padrão de exemplo")
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
