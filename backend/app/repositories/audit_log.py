from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.models.audit_log import AuditLog


def create_log(
    db: Session,
    action: str,
    user_id: int | None = None,
    entity: str | None = None,
    entity_id: int | None = None,
    description: str | None = None,
    ip_address: str | None = None,
) -> AuditLog:
    log = AuditLog(
        user_id=user_id,
        action=action,
        entity=entity,
        entity_id=entity_id,
        description=description,
        ip_address=ip_address,
    )
    db.add(log)
    db.commit()
    return log


def list_logs(
    db: Session,
    company_id: int,
    user_id: int | None = None,
    action: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[AuditLog]:
    from app.models.user import User
    query = (
        db.query(AuditLog)
        .join(User, AuditLog.user_id == User.id, isouter=True)
        .filter((User.company_id == company_id) | (AuditLog.user_id == None))
    )
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    if action:
        query = query.filter(AuditLog.action == action)
    return query.order_by(desc(AuditLog.created_at)).offset(offset).limit(limit).all()
