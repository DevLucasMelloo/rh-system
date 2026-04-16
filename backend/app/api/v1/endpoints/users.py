from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.core.dependencies import get_current_user, require_admin
from app.schemas.user import UserCreate, UserRead, UserUpdate, PasswordChange
from app.services import user as user_service
from app.repositories import user as user_repo
from app.models.user import User

router = APIRouter(prefix="/users", tags=["Usuários"])


@router.post("", response_model=UserRead, status_code=201)
def create_user(
    data: UserCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Somente Admin pode criar novos usuários."""
    return user_service.create_user(db, data, current_user.company_id, current_user.id)


@router.get("", response_model=list[UserRead])
def list_users(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return user_repo.list_users(db, current_user.company_id)


@router.get("/me", response_model=UserRead)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/me/password", status_code=204)
def change_my_password(
    data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_service.change_password(db, current_user.id, data)


@router.patch("/{user_id}", response_model=UserRead)
def update_user(
    user_id: int,
    data: UserUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return user_service.update_user(db, user_id, data, current_user.id)
