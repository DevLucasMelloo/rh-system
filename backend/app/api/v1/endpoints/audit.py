from datetime import date
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import io, pandas as pd

from app.db.database import get_db
from app.core.dependencies import require_rh_or_admin
from app.models.user import User
from app.repositories import audit_log as audit_repo

router = APIRouter(prefix="/audit", tags=["Auditoria"])


def _serialize(log) -> dict:
    return {
        "id":          log.id,
        "action":      log.action,
        "entity":      log.entity,
        "entity_id":   log.entity_id,
        "description": log.description,
        "created_at":  log.created_at.isoformat() if log.created_at else None,
        "user_name":   log.user.name if log.user else "Sistema",
        "user_id":     log.user_id,
    }


@router.get("/logs")
def list_logs(
    user_id:    int | None  = Query(None),
    action:     str | None  = Query(None),
    search:     str | None  = Query(None),
    date_start: date | None = Query(None),
    date_end:   date | None = Query(None),
    limit:  int = Query(200, le=500),
    offset: int = Query(0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rh_or_admin),
):
    logs = audit_repo.list_logs(
        db, current_user.company_id,
        user_id=user_id, action=action, search=search,
        date_start=date_start, date_end=date_end,
        limit=limit, offset=offset,
    )
    return [_serialize(l) for l in logs]


@router.get("/stats")
def get_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rh_or_admin),
):
    return audit_repo.get_stats(db, current_user.company_id)


@router.get("/users")
def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rh_or_admin),
):
    return audit_repo.list_users_with_logs(db, current_user.company_id)


@router.get("/actions")
def list_actions(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rh_or_admin),
):
    return audit_repo.list_actions(db, current_user.company_id)


@router.get("/export")
def export_logs(
    user_id:    int | None  = Query(None),
    action:     str | None  = Query(None),
    search:     str | None  = Query(None),
    date_start: date | None = Query(None),
    date_end:   date | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rh_or_admin),
):
    logs = audit_repo.list_logs(
        db, current_user.company_id,
        user_id=user_id, action=action, search=search,
        date_start=date_start, date_end=date_end,
        limit=5000, offset=0,
    )
    rows = [
        {
            "Data/Hora":   l.created_at.strftime("%d/%m/%Y %H:%M") if l.created_at else "",
            "Usuário":     l.user.name if l.user else "Sistema",
            "Ação":        l.action or "",
            "Módulo":      l.entity or "",
            "Descrição":   l.description or "",
        }
        for l in logs
    ]
    df = pd.DataFrame(rows) if rows else pd.DataFrame(columns=["Data/Hora","Usuário","Ação","Módulo","Descrição"])
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df.to_excel(w, sheet_name="Auditoria", index=False)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=auditoria.xlsx"},
    )
