import enum
from sqlalchemy import Column, Integer, String, Date, DateTime, Numeric, ForeignKey, Enum, func
from sqlalchemy.orm import relationship
from app.db.database import Base


class ThirteenthStatus(str, enum.Enum):
    PENDENTE = "pendente"
    PAGO     = "pago"


class ThirteenthSalary(Base):
    __tablename__ = "thirteenth_salary"

    id               = Column(Integer, primary_key=True, index=True)
    employee_id      = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    created_by_id    = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    year             = Column(Integer, nullable=False)
    parcela          = Column(Integer, nullable=False)   # 1 ou 2
    worked_months    = Column(Integer, nullable=False)
    bruto_13         = Column(Numeric(10, 2), nullable=False)
    inss             = Column(Numeric(10, 2), nullable=False)
    primeira_parcela = Column(Numeric(10, 2), nullable=False)
    liquido          = Column(Numeric(10, 2), nullable=False)
    payment_date     = Column(Date, nullable=True)
    status           = Column(Enum(ThirteenthStatus), default=ThirteenthStatus.PENDENTE, nullable=False)
    notes            = Column(String(500), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    employee   = relationship("Employee")
    created_by = relationship("User")
