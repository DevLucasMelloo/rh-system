from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.core.security import hash_password, verify_password
from app.repositories import user as user_repo
from app.repositories import audit_log as audit_repo
from app.schemas.user import UserCreate, UserUpdate, PasswordChange, AdminPasswordReset
from app.models.user import User


def get_user_or_404(db: Session, user_id: int) -> User:
    user = user_repo.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado")
    return user


def create_user(db: Session, data: UserCreate, company_id: int, created_by_id: int) -> User:
    if user_repo.get_by_email(db, data.username):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Usuário já cadastrado")

    user = user_repo.create_user(
        db=db,
        data=data,
        company_id=company_id,
        hashed_password=hash_password(data.password),
    )
    audit_repo.create_log(
        db, action="user_created", user_id=created_by_id,
        entity="user", entity_id=user.id,
        description=f"Usuário '{user.name}' ({user.role.value}) criado",
    )
    return user


def update_user(db: Session, user_id: int, data: UserUpdate, updated_by_id: int) -> User:
    user = get_user_or_404(db, user_id)
    updated = user_repo.update_user(db, user, data)
    audit_repo.create_log(
        db, action="user_updated", user_id=updated_by_id,
        entity="user", entity_id=user_id,
        description=f"Dados do usuário '{user.name}' atualizados",
    )
    return updated


def admin_reset_password(db: Session, user_id: int, data: AdminPasswordReset, admin_id: int) -> None:
    user = get_user_or_404(db, user_id)
    user_repo.update_password(db, user, hash_password(data.new_password))
    user_repo.update_refresh_token(db, user, None)
    audit_repo.create_log(
        db, action="password_reset", user_id=admin_id,
        entity="user", entity_id=user_id,
        description=f"Senha do usuário '{user.name}' redefinida pelo administrador",
    )


def change_password(db: Session, user_id: int, data: PasswordChange) -> None:
    user = get_user_or_404(db, user_id)

    if not verify_password(data.current_password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Senha atual incorreta")

    if data.current_password == data.new_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nova senha deve ser diferente da atual")

    user_repo.update_password(db, user, hash_password(data.new_password))
    user_repo.update_refresh_token(db, user, None)  # invalida sessões abertas
    audit_repo.create_log(
        db, action="password_changed", user_id=user_id,
        description=f"Senha alterada pelo próprio usuário",
    )
