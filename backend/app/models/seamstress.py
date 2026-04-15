from sqlalchemy import Column, Integer, String, Date, DateTime, Numeric, Boolean, ForeignKey, Text, func
from sqlalchemy.orm import relationship
from app.db.database import Base


class Seamstress(Base):
    """Costureira — sem salário fixo, valor lançado manualmente por mês."""
    __tablename__ = "seamstresses"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)

    name = Column(String(200), nullable=False, index=True)
    phone = Column(String(20), nullable=True)
    address = Column(String(300), nullable=True)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    company = relationship("Company", back_populates="seamstresses")
    payments = relationship("SeamstressPayment", back_populates="seamstress", cascade="all, delete-orphan")


class SeamstressPayment(Base):
    """
    Lançamento mensal do valor da costureira.
    O cálculo é feito externamente — o sistema registra apenas o valor final.
    """
    __tablename__ = "seamstress_payments"

    id = Column(Integer, primary_key=True, index=True)
    seamstress_id = Column(Integer, ForeignKey("seamstresses.id", ondelete="CASCADE"), nullable=False)
    registered_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    competence_month = Column(Integer, nullable=False)   # 1-12
    competence_year = Column(Integer, nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    seamstress = relationship("Seamstress", back_populates="payments")
    registered_by = relationship("User")
