from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.core.dependencies import get_current_user
from app.schemas.auth import (
    LoginRequest, TokenResponse, RefreshRequest,
    PasswordResetRequest, PasswordResetConfirm,
)
from app.services import auth as auth_service
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["Autenticação"])


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
