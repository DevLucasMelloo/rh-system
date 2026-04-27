"""
Folha de Pagamento — holerite mensal.
Benefícios e descontos podem ser ajustados manualmente mesmo com cálculo automático ativo.
"""
import enum
from sqlalchemy import (
    Column, Integer, String, Date, DateTime, Numeric,
    Boolean, ForeignKey, Enum, Text, func
)
from sqlalchemy.orm import relationship
from app.db.database import Base


class PayrollStatus(str, enum.Enum):
    DRAFT = "rascunho"
    CLOSED = "fechado"       # fechamento realizado — imutável


class PayrollItemType(str, enum.Enum):
    # Benefícios (créditos)
    SALARY = "salario"
    VT = "vale_transporte"
    AUXILIO = "auxilio"
    AUXILIO_FAMILIA = "auxilio_familia"
    BONUS = "bonificacao"
    OVERTIME = "hora_extra"
    ADDITIONAL = "adicional"
    THIRTEENTH_FIRST = "decimo_terceiro_primeira"
    THIRTEENTH_SECOND = "decimo_terceiro_segunda"
    VACATION_PAY = "ferias"
    # Descontos (débitos)
    INSS = "inss"
    VALE_DESCONTO = "vale_desconto"
    ABSENCE = "falta"
    DSR = "dsr"
    IR = "imposto_renda"
    OTHER_DISCOUNT = "outros_desconto"
    OTHER_CREDIT = "outros_credito"
    BANK_DEDUCT = "banco_desconto"   # desconto de horas negativas do banco
    BANK_PAY = "banco_credito"       # pagamento de horas positivas do banco


class Payroll(Base):
    """Holerite mensal de um funcionário."""
    __tablename__ = "payrolls"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    competence_month = Column(Integer, nullable=False)   # 1-12
    competence_year = Column(Integer, nullable=False)
    payment_date = Column(Date, nullable=True)           # data efetiva de pagamento

    # Totalizadores (calculados pelo service e gravados para imutabilidade histórica)
    gross_salary = Column(Numeric(10, 2), default=0)     # salário bruto
    total_benefits = Column(Numeric(10, 2), default=0)   # total de benefícios
    total_discounts = Column(Numeric(10, 2), default=0)  # total de descontos
    net_salary = Column(Numeric(10, 2), default=0)       # salário líquido

    worked_days = Column(Integer, default=0)
    total_overtime_hours = Column(Numeric(5, 2), default=0)

    # Flags de cálculo
    pay_overtime = Column(Boolean, default=False)                    # pagar HE em dinheiro
    use_hour_bank_for_absences = Column(Boolean, default=False)      # usar banco de horas para cobrir faltas

    notes = Column(Text, nullable=True)                              # observação por funcionário

    status = Column(Enum(PayrollStatus), default=PayrollStatus.DRAFT, nullable=False)
    pdf_path = Column(String(500), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    closed_at = Column(DateTime(timezone=True), nullable=True)

    employee = relationship("Employee", back_populates="payrolls")
    created_by = relationship("User")
    items = relationship("PayrollItem", back_populates="payroll", cascade="all, delete-orphan")


class PayrollItem(Base):
    """
    Linha individual do holerite (benefício ou desconto).
    Permite edição manual de qualquer item antes do fechamento.
    """
    __tablename__ = "payroll_items"

    id = Column(Integer, primary_key=True, index=True)
    payroll_id = Column(Integer, ForeignKey("payrolls.id", ondelete="CASCADE"), nullable=False)

    item_type = Column(Enum(PayrollItemType), nullable=False)
    description = Column(String(200), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    is_credit = Column(Boolean, nullable=False)          # True = benefício, False = desconto
    is_manual = Column(Boolean, default=False)           # True = editado manualmente
    notes = Column(Text, nullable=True)                  # campo "Outros" — comentário livre
    show_on_payslip = Column(Boolean, default=True)      # exibir ou ocultar no PDF

    payroll = relationship("Payroll", back_populates="items")


class Vale(Base):
    """
    Vale concedido ao funcionário.
    Suporta parcelamento e comentário descritivo.
    """
    __tablename__ = "vales"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    registered_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    total_amount = Column(Numeric(10, 2), nullable=False)   # valor total do vale
    installments = Column(Integer, default=1)               # número de parcelas
    notes = Column(Text, nullable=True)                     # ex: "Compra de Botina"

    # Controle de parcelas — cada desconto mensal referencia este vale
    issued_date = Column(Date, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    employee = relationship("Employee", back_populates="vales")
    registered_by = relationship("User")
    installment_items = relationship("ValeInstallment", back_populates="vale", cascade="all, delete-orphan")


class ValeInstallment(Base):
    """Parcela individual de um vale."""
    __tablename__ = "vale_installments"

    id = Column(Integer, primary_key=True, index=True)
    vale_id = Column(Integer, ForeignKey("vales.id", ondelete="CASCADE"), nullable=False)
    payroll_id = Column(Integer, ForeignKey("payrolls.id", ondelete="SET NULL"), nullable=True)

    installment_number = Column(Integer, nullable=False)   # 1, 2, 3...
    amount = Column(Numeric(10, 2), nullable=False)
    due_month = Column(Integer, nullable=False)            # mês de desconto (1-12)
    due_year = Column(Integer, nullable=False)
    is_paid = Column(Boolean, default=False)

    vale = relationship("Vale", back_populates="installment_items")
