"""
Logs de auditoria — imutáveis, nunca podem ser editados ou excluídos.
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import relationship
from app.db.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    action = Column(String(100), nullable=False)       # ex: "login", "salary_change", "delete"
    entity = Column(String(100), nullable=True)        # ex: "employee", "payroll"
    entity_id = Column(Integer, nullable=True)         # ID do registro afetado
    description = Column(Text, nullable=True)          # ex: "Salário de João alterado de R$2000 para R$2200"
    ip_address = Column(String(45), nullable=True)     # IPv4 ou IPv6

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="audit_logs")
