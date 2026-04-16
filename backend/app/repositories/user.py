from sqlalchemy.orm import Session
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate


def get_user(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def get_by_email(db: Session, email: str) -> User | None:
    # Busca por email — SQLAlchemy usa parâmetro vinculado (sem SQL injection)
    return db.query(User).filter(User.email == email.lower()).first()


def list_users(db: Session, company_id: int) -> list[User]:
    return db.query(User).filter(User.company_id == company_id).all()


def create_user(db: Session, data: UserCreate, company_id: int, hashed_password: str) -> User:
    user = User(
        company_id=company_id,
        name=data.name,
        email=data.email.lower(),
        hashed_password=hashed_password,
        role=data.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user(db: Session, user: User, data: UserUpdate) -> User:
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user


def update_password(db: Session, user: User, hashed_password: str) -> None:
    user.hashed_password = hashed_password
    db.commit()


def update_refresh_token(db: Session, user: User, token: str | None) -> None:
    user.refresh_token = token
    db.commit()
