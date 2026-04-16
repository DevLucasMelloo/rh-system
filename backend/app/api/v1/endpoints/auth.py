from fastapi import APIRouter, Depends, Request, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.core.dependencies import get_current_user
from app.schemas.auth import (
    LoginRequest, TokenResponse, RefreshRequest,
    PasswordResetRequest, PasswordResetConfirm,
)
from app.schemas.user import UserCreate
from app.services import auth as auth_service
from app.services import user as user_service
from app.repositories import user as user_repo
from app.repositories import company as company_repo
from app.models.user import User, UserRole

router = APIRouter(prefix="/auth", tags=["Autenticação"])


@router.post("/setup", status_code=201, summary="Cria o primeiro admin (só funciona sem usuários cadastrados)")
def setup_first_admin(data: UserCreate, db: Session = Depends(get_db)):
    """
    Endpoint de configuração inicial.
    Só funciona quando não existe nenhum usuário no sistema.
    Após o primeiro admin criado, este endpoint retorna 403 permanentemente.
    """
    company = company_repo.get_first_company(db)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cadastre a empresa antes de criar o primeiro usuário",
        )

    existing = user_repo.list_users(db, company.id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Setup já realizado. Use o endpoint de login.",
        )

    # Força perfil admin no primeiro usuário
    data.role = UserRole.ADMIN
    return user_service.create_user(db, data, company.id, created_by_id=0)


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
    auth_service.request_password_reset(db, data.email)
    return {"message": "Se o email existir, você receberá um link de redefinição"}


@router.post("/reset-password", status_code=204)
def reset_password(data: PasswordResetConfirm, db: Session = Depends(get_db)):
    auth_service.confirm_password_reset(db, data)
