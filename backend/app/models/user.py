import enum
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum, func
from sqlalchemy.orm import relationship
from app.db.database import Base


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    RH = "rh"
    FINANCEIRO = "financeiro"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)

    name = Column(String(150), nullable=False)
    email = Column(String(200), nullable=False, unique=True, index=True)
    hashed_password = Column(String(200), nullable=False)  # bcrypt — nunca texto puro
    role = Column(Enum(UserRole), nullable=False, default=UserRole.RH)
    is_active = Column(Boolean, default=True)

    # Controle de acesso por módulo (JSON string com lista de módulos permitidos)
    # None = acesso total ao perfil; lista = módulos restritos
    allowed_modules = Column(String(500), nullable=True)

    # Refresh token armazenado para invalidação
    refresh_token = Column(String(500), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relacionamentos
    company = relationship("Company", back_populates="users")
    audit_logs = relationship("AuditLog", back_populates="user")
