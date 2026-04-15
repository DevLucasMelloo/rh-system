"""
Configuração do banco de dados com SQLAlchemy.
SQLite para desenvolvimento — basta trocar DATABASE_URL no .env para PostgreSQL em produção.
"""
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session
from typing import Generator

from app.core.config import settings


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    # SQLite exige check_same_thread=False para uso com FastAPI (multi-thread)
    connect_args["check_same_thread"] = False

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    # Pool de conexões — para SQLite usa StaticPool automaticamente
    echo=settings.is_development,  # Loga queries SQL apenas em dev
)


# Ativa WAL no SQLite para melhor concorrência de leitura
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if settings.DATABASE_URL.startswith("sqlite"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")  # Garante integridade referencial
        cursor.close()


# ---------------------------------------------------------------------------
# Session Factory
# ---------------------------------------------------------------------------
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


# ---------------------------------------------------------------------------
# Base para os Models
# ---------------------------------------------------------------------------
class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Dependency — injetada nos endpoints via FastAPI Depends
# ---------------------------------------------------------------------------
def get_db() -> Generator[Session, None, None]:
    """
    Fornece uma sessão de banco por request.
    A sessão é sempre fechada após o request, mesmo com erro.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
