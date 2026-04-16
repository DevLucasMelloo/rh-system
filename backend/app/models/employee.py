"""
Model de Funcionário.
Campos sensíveis (CPF, RG, conta bancária, pix) são armazenados
criptografados com Fernet — nunca em texto puro.
"""
import enum
from sqlalchemy import (
    Column, Integer, String, Boolean, Date, DateTime,
    Numeric, ForeignKey, Enum, Text, func
)
from sqlalchemy.orm import relationship
from app.db.database import Base


class EmployeeStatus(str, enum.Enum):
    ACTIVE = "ativo"
    INACTIVE = "inativo"


class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)

    # Dados pessoais
    name = Column(String(200), nullable=False, index=True)
    cpf_encrypted = Column(String(500), nullable=False)       # Fernet
    rg_encrypted = Column(String(500), nullable=True)          # Fernet
    date_of_birth = Column(Date, nullable=True)
    phone = Column(String(20), nullable=True)
    father_name = Column(String(200), nullable=True)
    mother_name = Column(String(200), nullable=True)

    # Endereço
    address = Column(String(300), nullable=True)
    cep = Column(String(10), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(2), nullable=True)

    # Dados profissionais
    role = Column(String(100), nullable=False)           # cargo
    salary = Column(Numeric(10, 2), nullable=False)
    admission_date = Column(Date, nullable=False)        # data de admissão
    registration_date = Column(Date, nullable=False)     # data de registro (para férias e 13º)
    status = Column(Enum(EmployeeStatus), default=EmployeeStatus.ACTIVE, nullable=False)
    inactivation_date = Column(Date, nullable=True)
    inactivation_reason = Column(Text, nullable=True)

    # Tipo de contrato
    is_intern = Column(Boolean, default=False)           # estagiário tem carga horária diferente
    weekly_hours = Column(Integer, default=44)           # carga horária semanal

    # Dados bancários — criptografados com Fernet
    bank_account_encrypted = Column(String(500), nullable=True)  # Fernet
    pix_encrypted = Column(String(500), nullable=True)           # Fernet
    bank_name = Column(String(100), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relacionamentos
    company = relationship("Company", back_populates="employees")
    history = relationship("EmployeeHistory", back_populates="employee", cascade="all, delete-orphan")
    timesheet_entries = relationship("TimesheetEntry", back_populates="employee", cascade="all, delete-orphan")
    hour_bank = relationship("HourBank", back_populates="employee", uselist=False, cascade="all, delete-orphan")
    payrolls = relationship("Payroll", back_populates="employee", cascade="all, delete-orphan")
    vacations    = relationship("Vacation",     back_populates="employee", cascade="all, delete-orphan")
    vales        = relationship("Vale",         back_populates="employee", cascade="all, delete-orphan")
    terminations = relationship("Termination",  back_populates="employee", cascade="all, delete-orphan")


class EmployeeHistory(Base):
    """
    Registro imutável de todas as alterações de um funcionário.
    Garante rastreabilidade de reajustes, mudanças de cargo etc.
    """
    __tablename__ = "employee_history"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    changed_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    field_changed = Column(String(100), nullable=False)   # ex: "salary", "role"
    old_value = Column(String(500), nullable=True)
    new_value = Column(String(500), nullable=True)
    reason = Column(Text, nullable=True)                  # justificativa da mudança

    changed_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relacionamentos
    employee = relationship("Employee", back_populates="history")
    changed_by = relationship("User")
