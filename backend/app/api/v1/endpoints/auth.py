from fastapi import APIRouter, Depends, Request, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.core.dependencies import get_current_user
from app.schemas.auth import (
    LoginRequest, TokenResponse, RefreshRequest,
    PasswordResetRequest, PasswordResetConfirm,
)
from app.schemas.user import UserCreate, UserRead
from app.schemas.company import CompanyCreate
from app.services import auth as auth_service
from app.services import user as user_service
from app.repositories import user as user_repo
from app.repositories import company as company_repo
from app.models.user import User, UserRole

router = APIRouter(prefix="/auth", tags=["Autenticação"])


class SetupRequest(BaseModel):
    """Dados para criação do primeiro admin + empresa."""
    name: str
    username: str
    password: str
    razao_social: str
    cnpj: str
    company_email: str


@router.get("/setup-status", summary="Verifica se o sistema já foi configurado")
def setup_status(db: Session = Depends(get_db)):
    """Retorna se o setup inicial já foi realizado."""
    company = company_repo.get_first_company(db)
    if not company:
        return {"needs_setup": True}
    existing = user_repo.list_users(db, company.id)
    return {"needs_setup": len(existing) == 0}


@router.post("/setup", status_code=201, summary="Cria empresa e primeiro admin")
def setup_first_admin(data: SetupRequest, db: Session = Depends(get_db)):
    """
    Configuração inicial: cria a empresa e o primeiro usuário admin.
    Só funciona quando não existe nenhuma empresa/usuário cadastrado.
    """
    # Verifica se já foi configurado
    company = company_repo.get_first_company(db)
    if company:
        existing = user_repo.list_users(db, company.id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Setup já realizado. Use o endpoint de login.",
            )

    # Cria empresa se não existir
    if not company:
        company_data = CompanyCreate(
            razao_social=data.razao_social,
            cnpj=data.cnpj,
            email=data.company_email,
        )
        company = company_repo.create_company(db, company_data)

    # Cria admin
    user_data = UserCreate(name=data.name, username=data.username, password=data.password)
    user_data.role = UserRole.ADMIN
    user = user_service.create_user(db, user_data, company.id, created_by_id=0)

    # Retorna token direto para logar automaticamente
    login_data = LoginRequest(username=data.username, password=data.password)
    return auth_service.login(db, login_data, ip=None)


@router.get("/me", response_model=UserRead)
def get_me(current_user: User = Depends(get_current_user)):
    """Retorna os dados do usuário autenticado."""
    return current_user


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, request: Request, db: Session = Depends(get_db)):
    ip = request.client.host if request.client else None
    return auth_service.login(db, data, ip)


@router.post("/refresh", response_model=TokenResponse)
def refresh(data: RefreshRequest, db: Session = Depends(get_db)):
    return auth_service.refresh_access_token(db, data.refresh_token)


@router.post("/logout", status_code=204)
def logout(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    auth_service.logout(db, current_user.id)


@router.post("/forgot-password", status_code=202)
def forgot_password(data: PasswordResetRequest, db: Session = Depends(get_db)):
    auth_service.request_password_reset(db, data.username)
    return {"message": "Se o email existir, você receberá um link de redefinição"}


@router.post("/reset-password", status_code=204)
def reset_password(data: PasswordResetConfirm, db: Session = Depends(get_db)):
    auth_service.confirm_password_reset(db, data)
