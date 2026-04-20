from sqlalchemy import (
    Column, Integer, String, Date, DateTime, Time, Boolean,
    Numeric, ForeignKey, Text, UniqueConstraint, func
)
from sqlalchemy.orm import relationship
from app.db.database import Base


class TimesheetEntry(Base):
    """Registro diário de ponto de um funcionário."""
    __tablename__ = "timesheet_entries"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    registered_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    work_date = Column(Date, nullable=False, index=True)

    # 4 batidas do dia
    entry_time = Column(Time, nullable=True)          # entrada
    lunch_out_time = Column(Time, nullable=True)      # saída para almoço
    lunch_in_time = Column(Time, nullable=True)       # retorno do almoço
    exit_time = Column(Time, nullable=True)           # saída final

    # Cálculos (preenchidos pelo service)
    worked_minutes = Column(Integer, default=0)       # minutos trabalhados no dia
    overtime_minutes = Column(Integer, default=0)     # horas extras em minutos
    late_minutes = Column(Integer, default=0)         # minutos de atraso

    # Ausências e justificativas
    is_absence = Column(Boolean, default=False)
    is_medical_certificate = Column(Boolean, default=False)
    certificate_hours = Column(Numeric(4, 1), nullable=True)
    is_holiday = Column(Boolean, default=False)   # feriado — dia abonado, sem impacto no banco
    justification = Column(Text, nullable=True)

    # Dia anulado (atestado aprovado — não conta como falta nem extra)
    is_annulled = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    employee = relationship("Employee", back_populates="timesheet_entries")
    registered_by = relationship("User")


class HourBank(Base):
    """
    Banco de horas acumulado por funcionário.
    Atualizado automaticamente quando um dia de ponto é processado.
    """
    __tablename__ = "hour_banks"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, unique=True)

    balance_minutes = Column(Integer, default=0)  # saldo em minutos (pode ser negativo)

    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    employee = relationship("Employee", back_populates="hour_bank")


class TimesheetPeriod(Base):
    """Controle de abertura/fechamento do período de ponto por empresa."""
    __tablename__ = "timesheet_periods"
    __table_args__ = (UniqueConstraint("company_id", "competence_month", "competence_year"),)

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    competence_month = Column(Integer, nullable=False)
    competence_year = Column(Integer, nullable=False)
    status = Column(String(10), nullable=False, default="open")  # 'open' | 'closed'

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    closed_at = Column(DateTime(timezone=True), nullable=True)
    closed_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
