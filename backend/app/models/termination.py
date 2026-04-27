"""
Rescisão de contrato de trabalho.
Armazena as verbas rescisórias calculadas para referência e geração de PDF.
"""
import enum
from sqlalchemy import (
    Column, Integer, String, Date, DateTime, Numeric,
    Boolean, ForeignKey, Enum, Text, func,
)
from sqlalchemy.orm import relationship
from app.db.database import Base


class TerminationReason(str, enum.Enum):
    SEM_JUSTA_CAUSA = "sem_justa_causa"    # Demissão pelo empregador
    COM_JUSTA_CAUSA = "com_justa_causa"    # Justa causa pelo empregador
    PEDIDO_DEMISSAO = "pedido_demissao"    # Funcionário pede demissão
    ACORDO          = "acordo"             # Acordo mútuo (art. 484-A CLT)
    APOSENTADORIA   = "aposentadoria"      # Aposentadoria


class Termination(Base):
    """Verbas rescisórias de um funcionário."""
    __tablename__ = "terminations"

    id             = Column(Integer, primary_key=True, index=True)
    employee_id    = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    created_by_id  = Column(Integer, ForeignKey("users.id",     ondelete="SET NULL"), nullable=True)

    termination_date = Column(Date, nullable=False)
    reason           = Column(Enum(TerminationReason), nullable=False)
    notice_days       = Column(Integer,  default=0)     # dias de aviso prévio calculados
    notice_worked     = Column(Boolean,  default=False)  # aviso trabalhado (True) ou indenizado (False)
    notice_start_date = Column(Date, nullable=True)     # início do aviso prévio (quando trabalhado)
    notice_reduction  = Column(String(20), nullable=True) # "2h_dia" | "7_dias" (sem justa causa trabalhado)

    # ── Verbas (gravadas para imutabilidade) ───────────────────────────────────
    saldo_salario           = Column(Numeric(10, 2), default=0)  # dias trabalhados no mês
    ferias_proporcionais    = Column(Numeric(10, 2), default=0)  # férias proporcionais brutas
    um_terco_ferias_prop    = Column(Numeric(10, 2), default=0)  # 1/3 sobre férias proporcionais
    ferias_vencidas         = Column(Numeric(10, 2), default=0)  # férias vencidas não gozadas
    um_terco_ferias_venc    = Column(Numeric(10, 2), default=0)  # 1/3 sobre férias vencidas
    decimo_terceiro_prop    = Column(Numeric(10, 2), default=0)  # 13º proporcional (bruto)
    aviso_previo_indenizado = Column(Numeric(10, 2), default=0)  # aviso prévio não trabalhado
    multa_fgts              = Column(Numeric(10, 2), default=0)  # multa 40% ou 20% FGTS

    # ── Descontos ─────────────────────────────────────────────────────────────
    inss_rescisao           = Column(Numeric(10, 2), default=0)
    aviso_previo_desconto   = Column(Numeric(10, 2), default=0)  # desconto pedido demissão

    # ── Totais ────────────────────────────────────────────────────────────────
    total_creditos  = Column(Numeric(10, 2), default=0)
    total_descontos = Column(Numeric(10, 2), default=0)
    liquido         = Column(Numeric(10, 2), default=0)

    # ── Metadados de referência ───────────────────────────────────────────────
    saldo_dias        = Column(Integer,      default=0)
    ferias_meses_prop = Column(Integer,      default=0)  # meses proporcionais
    ferias_meses_venc = Column(Integer,      default=0)  # períodos vencidos não gozados
    decimo_meses      = Column(Integer,      default=0)  # meses trabalhados para 13º
    decimo_ja_pago    = Column(Numeric(10,2), default=0) # 13º já pago no ano

    status   = Column(String(20),  default="pendente")  # pendente | concluida
    notes    = Column(Text,        nullable=True)
    pdf_path = Column(String(500), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    employee   = relationship("Employee", back_populates="terminations")
    created_by = relationship("User")
