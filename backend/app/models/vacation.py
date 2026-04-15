"""
Férias — suporta gozo integral, fracionado e alertas de vencimento.
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
    enjoyment_days = Column(Integer, default=30)     # dias de gozo (pode ser fracionado)

    # Fracionamento
    is_fractioned = Column(Boolean, default=False)
    paid_days_in_payroll = Column(Integer, default=0)  # dias pagos em folha (sem gozo)

    # Valores calculados (gravados para imutabilidade)
    base_salary = Column(Numeric(10, 2), nullable=True)
    one_third_bonus = Column(Numeric(10, 2), nullable=True)   # 1/3 constitucional
    inss_discount = Column(Numeric(10, 2), nullable=True)
    net_vacation_pay = Column(Numeric(10, 2), nullable=True)

    status = Column(Enum(VacationStatus), default=VacationStatus.SCHEDULED, nullable=False)
    notes = Column(Text, nullable=True)
    pdf_path = Column(String(500), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    employee = relationship("Employee", back_populates="vacations")
    created_by = relationship("User")
