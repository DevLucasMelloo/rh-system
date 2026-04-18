from pydantic import BaseModel, field_validator
from app.models.user import UserRole


class UserCreate(BaseModel):
    name: str
    username: str
    password: str
    role: UserRole = UserRole.RH

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 4:
            raise ValueError("Senha deve ter pelo menos 4 caracteres")
        return v

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Nome não pode ser vazio")
        return v.strip()

    @field_validator("username")
    @classmethod
    def username_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Usuário não pode ser vazio")
        return v.strip()


class UserUpdate(BaseModel):
    name: str | None = None
    username: str | None = None
    role: UserRole | None = None
    is_active: bool | None = None
    allowed_modules: str | None = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 4:
            raise ValueError("Senha deve ter pelo menos 4 caracteres")
        return v


class AdminPasswordReset(BaseModel):
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 4:
            raise ValueError("Senha deve ter pelo menos 4 caracteres")
        return v


class UserRead(BaseModel):
    id: int
    name: str
    username: str
    role: UserRole
    is_active: bool
    allowed_modules: str | None

    model_config = {"from_attributes": True}
