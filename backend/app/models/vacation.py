"""
Férias — suporta gozo integral, fracionado, venda total e itens manuais.
"""
import enum
from sqlalchemy import (
    Column, Integer, String, Date, DateTime, Numeric,
    Boolean, ForeignKey, Enum, Text, func
)
from sqlalchemy.orm import relationship
from app.db.database import Base


class VacationStatus(str, enum.Enum):
    SCHEDULED = "agendada"
    ACTIVE = "em_gozo"
    COMPLETED = "concluida"
    CANCELLED = "cancelada"


class VacationItemType(str, enum.Enum):
    CREDIT = "credito"
    DEBIT = "debito"


class Vacation(Base):
    """Registro de período de férias de um funcionário."""
    __tablename__ = "vacations"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Período aquisitivo
    acquisition_start = Column(Date, nullable=False)
    acquisition_end = Column(Date, nullable=False)

    # Período de gozo
    enjoyment_start = Column(Date, nullable=True)
    enjoyment_days = Column(Integer, default=30)

    # Venda total (funcionário recebe todos os dias em dinheiro, sem gozar)
    sell_all_days = Column(Boolean, default=False, nullable=True)

    # Abono pecuniário: dias convertidos em dinheiro (funcionário goza enjoyment_days e vende abono_days)
    abono_days = Column(Integer, default=0, nullable=True)

    # Fracionamento
    is_fractioned = Column(Boolean, default=False)
    paid_days_in_payroll = Column(Integer, default=0)

    # Valores calculados (editáveis manualmente)
    base_salary = Column(Numeric(10, 2), nullable=True)
    one_third_bonus = Column(Numeric(10, 2), nullable=True)
    inss_discount = Column(Numeric(10, 2), nullable=True)
    net_vacation_pay = Column(Numeric(10, 2), nullable=True)

    status = Column(Enum(VacationStatus), default=VacationStatus.SCHEDULED, nullable=False)
    notes = Column(Text, nullable=True)
    pdf_path = Column(String(500), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    employee = relationship("Employee", back_populates="vacations")
    created_by = relationship("User")
    items = relationship(
        "VacationItem", back_populates="vacation",
        cascade="all, delete-orphan", order_by="VacationItem.id"
    )


class VacationItem(Base):
    """Itens adicionais de férias (créditos e débitos manuais)."""
    __tablename__ = "vacation_items"

    id = Column(Integer, primary_key=True, index=True)
    vacation_id = Column(Integer, ForeignKey("vacations.id", ondelete="CASCADE"), nullable=False)
    item_type = Column(Enum(VacationItemType), nullable=False)
    description = Column(String(200), nullable=False)
    value = Column(Numeric(10, 2), nullable=False, default=0)

    vacation = relationship("Vacation", back_populates="items")
