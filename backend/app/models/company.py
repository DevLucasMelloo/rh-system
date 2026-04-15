from sqlalchemy import Column, Integer, String, DateTime, func
from sqlalchemy.orm import relationship
from app.db.database import Base


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    razao_social = Column(String(200), nullable=False)
    cnpj = Column(String(18), nullable=False, unique=True)  # formato: 00.000.000/0000-00
    email = Column(String(200), nullable=False)
    telefone = Column(String(20), nullable=True)
    endereco = Column(String(300), nullable=True)
    cidade = Column(String(100), nullable=True)
    estado = Column(String(2), nullable=True)
    cep = Column(String(10), nullable=True)

    # Configurações do sistema
    vt_valor_diario = Column(String(20), default="10.60")  # R$ por dia (ida e volta)
    dia_pagamento = Column(Integer, default=5)  # dia do mês (padrão: dia 5)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relacionamentos
    users = relationship("User", back_populates="company", cascade="all, delete-orphan")
    employees = relationship("Employee", back_populates="company", cascade="all, delete-orphan")
    seamstresses = relationship("Seamstress", back_populates="company", cascade="all, delete-orphan")
