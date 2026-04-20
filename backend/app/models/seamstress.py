from sqlalchemy import Column, Integer, String, Date, DateTime, Numeric, Boolean, ForeignKey, Text, func
from sqlalchemy.orm import relationship
from app.db.database import Base


class Seamstress(Base):
    __tablename__ = "seamstresses"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)

    name = Column(String(200), nullable=False, index=True)
    cpf = Column(String(20), nullable=True)
    phone = Column(String(20), nullable=True)
    address = Column(String(300), nullable=True)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    company = relationship("Company", back_populates="seamstresses")
    payments = relationship("SeamstressPayment", back_populates="seamstress", cascade="all, delete-orphan")


class SeamstressPayment(Base):
    """
    Lançamento de valor para costureira.

    payment_type='mensal': competência mensal, status inicia como 'pendente',
        payment_date preenchido no fechamento do mês.
    payment_type='entrega': pago na entrega, payment_date obrigatório,
        status sempre 'pago'. Não entra no fechamento mensal.
    """
    __tablename__ = "seamstress_payments"

    id = Column(Integer, primary_key=True, index=True)
    seamstress_id = Column(Integer, ForeignKey("seamstresses.id", ondelete="CASCADE"), nullable=False)
    registered_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    payment_type = Column(String(10), nullable=False, default='mensal')   # 'mensal' | 'entrega'
    status = Column(String(10), nullable=False, default='pendente')        # 'pendente' | 'pago'
    competence_month = Column(Integer, nullable=True)
    competence_year = Column(Integer, nullable=True)
    payment_date = Column(Date, nullable=True)   # null enquanto pendente; preenchido ao fechar ou na entrega
    amount = Column(Numeric(10, 2), nullable=False)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    seamstress = relationship("Seamstress", back_populates="payments")
    registered_by = relationship("User")
