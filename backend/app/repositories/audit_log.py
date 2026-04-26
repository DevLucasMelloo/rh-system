from datetime import date, datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, distinct
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


def _base_query(db: Session, company_id: int):
    from app.models.user import User
    return (
        db.query(AuditLog)
        .join(User, AuditLog.user_id == User.id, isouter=True)
        .filter((User.company_id == company_id) | (AuditLog.user_id.is_(None)))
    )


def list_logs(
    db: Session,
    company_id: int,
    user_id: int | None = None,
    action: str | None = None,
    search: str | None = None,
    date_start: date | None = None,
    date_end: date | None = None,
    limit: int = 200,
    offset: int = 0,
) -> list[AuditLog]:
    query = _base_query(db, company_id)
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    if action:
        query = query.filter(AuditLog.action == action)
    if search:
        query = query.filter(AuditLog.description.ilike(f"%{search}%"))
    if date_start:
        query = query.filter(AuditLog.created_at >= datetime(date_start.year, date_start.month, date_start.day))
    if date_end:
        query = query.filter(AuditLog.created_at <= datetime(date_end.year, date_end.month, date_end.day, 23, 59, 59))
    return query.order_by(desc(AuditLog.created_at)).offset(offset).limit(limit).all()


def get_stats(db: Session, company_id: int) -> dict:
    today_start = datetime.combine(date.today(), datetime.min.time())
    base = _base_query(db, company_id)
    total        = base.count()
    today_count  = base.filter(AuditLog.created_at >= today_start).count()
    action_types = base.with_entities(func.count(distinct(AuditLog.action))).scalar()
    active_users = base.filter(AuditLog.user_id.isnot(None)).with_entities(func.count(distinct(AuditLog.user_id))).scalar()
    return {"total": total, "today": today_count, "action_types": action_types, "active_users": active_users}


def list_users_with_logs(db: Session, company_id: int) -> list[dict]:
    from app.models.user import User
    users = (
        db.query(User.id, User.name)
        .join(AuditLog, User.id == AuditLog.user_id)
        .filter(User.company_id == company_id)
        .distinct()
        .order_by(User.name)
        .all()
    )
    return [{"id": u.id, "name": u.name} for u in users]


def list_actions(db: Session, company_id: int) -> list[str]:
    rows = _base_query(db, company_id).with_entities(distinct(AuditLog.action)).all()
    return sorted(r[0] for r in rows if r[0])
