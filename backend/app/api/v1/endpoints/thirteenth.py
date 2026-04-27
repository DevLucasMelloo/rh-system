from datetime import date
from fastapi import APIRouter, Depends, Path, Query, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
import io, pandas as pd

from app.db.database import get_db
from app.core.dependencies import get_current_user, require_rh_or_admin
from app.models.user import User
from app.models.employee import EmployeeStatus
from app.repositories import thirteenth as repo
from app.repositories import employee as emp_repo
from app.repositories import audit_log as audit_repo
from app.services.vacation import get_thirteenth as calc_thirteenth

router = APIRouter(prefix="/thirteenth", tags=["13º Salário"])


# ── Schemas ──────────────────────────────────────────────────────────────────

class GenerateRequest(BaseModel):
    employee_id: int
    year:        int
    parcela:     int  # 1 ou 2
    notes:       str | None = None


class GenerateBatchRequest(BaseModel):
    year:    int
    parcela: int  # 1 ou 2


class ThirteenthRead(BaseModel):
    id:               int
    employee_id:      int
    employee_name:    str | None = None
    year:             int
    parcela:          int
    worked_months:    int
    bruto_13:         float
    inss:             float
    primeira_parcela: float
    liquido:          float
    payment_date:     date | None
    status:           str
    notes:            str | None
    created_at:       str | None

    model_config = {"from_attributes": True}


def _serialize(rec) -> dict:
    emp_name = rec.employee.name if rec.employee else None
    return {
        "id":               rec.id,
        "employee_id":      rec.employee_id,
        "employee_name":    emp_name,
        "year":             rec.year,
        "parcela":          rec.parcela,
        "worked_months":    rec.worked_months,
        "bruto_13":         float(rec.bruto_13),
        "inss":             float(rec.inss),
        "primeira_parcela": float(rec.primeira_parcela),
        "liquido":          float(rec.liquido),
        "payment_date":     rec.payment_date.isoformat() if rec.payment_date else None,
        "status":           rec.status.value if hasattr(rec.status, "value") else rec.status,
        "notes":            rec.notes,
        "created_at":       rec.created_at.isoformat() if rec.created_at else None,
    }


def _payment_date(year: int, parcela: int) -> date:
    return date(year, 11, 20) if parcela == 1 else date(year, 12, 20)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/generate", status_code=201)
def generate_one(
    body: GenerateRequest,
    db: Session   = Depends(get_db),
    current_user: User = Depends(require_rh_or_admin),
):
    calc = calc_thirteenth(db, body.employee_id, body.year, body.parcela, current_user.company_id)
    rec  = repo.create_or_update(db, {
        "employee_id":      body.employee_id,
        "created_by_id":    current_user.id,
        "year":             body.year,
        "parcela":          body.parcela,
        "worked_months":    calc["worked_months"],
        "bruto_13":         calc["bruto_13"],
        "inss":             calc["inss"],
        "primeira_parcela": calc["primeira_parcela"],
        "liquido":          calc["liquido"],
        "payment_date":     _payment_date(body.year, body.parcela),
        "notes":            body.notes,
    })
    audit_repo.create_log(
        db, action="thirteenth_generated", user_id=current_user.id,
        entity="thirteenth_salary", entity_id=rec.id,
        description=f"13º {body.parcela}ª parcela {body.year} gerado para {calc['employee_name']} — líquido R$ {calc['liquido']}",
    )
    return _serialize(rec)


@router.post("/generate-batch", status_code=201)
def generate_batch(
    body: GenerateBatchRequest,
    db: Session   = Depends(get_db),
    current_user: User = Depends(require_rh_or_admin),
):
    employees = emp_repo.list_all(db, current_user.company_id)
    results = []
    for emp in employees:
        if emp.status == EmployeeStatus.INACTIVE or not emp.registration_date:
            continue
        try:
            calc = calc_thirteenth(db, emp.id, body.year, body.parcela, current_user.company_id)
            rec  = repo.create_or_update(db, {
                "employee_id":      emp.id,
                "created_by_id":    current_user.id,
                "year":             body.year,
                "parcela":          body.parcela,
                "worked_months":    calc["worked_months"],
                "bruto_13":         calc["bruto_13"],
                "inss":             calc["inss"],
                "primeira_parcela": calc["primeira_parcela"],
                "liquido":          calc["liquido"],
                "payment_date":     _payment_date(body.year, body.parcela),
                "notes":            body.notes if hasattr(body, "notes") else None,
            })
            results.append(_serialize(rec))
        except Exception:
            pass
    audit_repo.create_log(
        db, action="thirteenth_batch_generated", user_id=current_user.id,
        entity="thirteenth_salary", entity_id=None,
        description=f"13º {body.parcela}ª parcela {body.year} gerado em lote — {len(results)} funcionário(s)",
    )
    return results


@router.get("")
def list_thirteenth(
    year:    int | None = Query(None),
    parcela: int | None = Query(None),
    db: Session   = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    recs = repo.list_by_company(db, current_user.company_id, year=year, parcela=parcela)
    return [_serialize(r) for r in recs]


class UpdateRequest(BaseModel):
    valor_parcela: float        # bruto desta parcela
    inss:          float = 0.0  # INSS (apenas 2ª parcela)


@router.patch("/{rec_id}")
def update_thirteenth(
    rec_id: int = Path(...),
    body: UpdateRequest = ...,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rh_or_admin),
):
    rec = repo.get_by_id(db, rec_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Registro não encontrado")
    rec.inss    = body.inss
    rec.liquido = round(body.valor_parcela - body.inss, 2)
    db.commit()
    db.refresh(rec)
    audit_repo.create_log(
        db, action="thirteenth_updated", user_id=current_user.id,
        entity="thirteenth_salary", entity_id=rec_id,
        description=f"13º {rec.parcela}ª parcela {rec.year} editado — {rec.employee.name if rec.employee else ''} — líquido R$ {rec.liquido}",
    )
    return _serialize(rec)


@router.patch("/{rec_id}/mark-paid")
def mark_paid(
    rec_id: int = Path(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rh_or_admin),
):
    rec = repo.get_by_id(db, rec_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Registro não encontrado")
    updated = repo.mark_paid(db, rec)
    audit_repo.create_log(
        db, action="thirteenth_paid", user_id=current_user.id,
        entity="thirteenth_salary", entity_id=rec_id,
        description=f"13º {rec.parcela}ª parcela {rec.year} marcado como pago — {rec.employee.name if rec.employee else ''}",
    )
    return _serialize(updated)


@router.delete("/{rec_id}", status_code=204)
def delete_thirteenth(
    rec_id: int = Path(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rh_or_admin),
):
    rec = repo.get_by_id(db, rec_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Registro não encontrado")
    audit_repo.create_log(
        db, action="thirteenth_deleted", user_id=current_user.id,
        entity="thirteenth_salary", entity_id=rec_id,
        description=f"13º {rec.parcela}ª parcela {rec.year} excluído — {rec.employee.name if rec.employee else ''}",
    )
    repo.delete(db, rec)


@router.get("/export")
def export_thirteenth(
    year:    int | None = Query(None),
    parcela: int | None = Query(None),
    db: Session   = Depends(get_db),
    current_user: User = Depends(require_rh_or_admin),
):
    recs = repo.list_by_company(db, current_user.company_id, year=year, parcela=parcela)
    rows = [
        {
            "Funcionário":   r.employee.name if r.employee else "",
            "Ano":           r.year,
            "Parcela":       r.parcela,
            "Meses":         r.worked_months,
            "Bruto":         float(r.bruto_13),
            "INSS":          float(r.inss),
            "1ª Parcela":    float(r.primeira_parcela),
            "Líquido":       float(r.liquido),
            "Pgto":          r.payment_date.strftime("%d/%m/%Y") if r.payment_date else "",
            "Status":        r.status.value if hasattr(r.status, "value") else r.status,
        }
        for r in recs
    ]
    df  = pd.DataFrame(rows) if rows else pd.DataFrame(columns=["Funcionário","Ano","Parcela","Meses","Bruto","INSS","1ª Parcela","Líquido","Pgto","Status"])
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df.to_excel(w, sheet_name="13º Salário", index=False)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=13_salario.xlsx"},
    )
