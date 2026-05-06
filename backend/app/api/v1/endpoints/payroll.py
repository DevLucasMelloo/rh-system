"""
Endpoints de Folha de Pagamento e Vale.
IMPORTANTE: rotas literais devem vir ANTES de /{payroll_id} para evitar conflito de parsing.
"""
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.core.dependencies import get_current_user, require_rh_or_admin
from app.models.user import User
from app.schemas.payroll import (
    PayrollCreate, PayrollBatchCreate, PayrollFlagsUpdate, PayrollRead,
    PayrollItemCreate, PayrollItemUpdate, PayrollItemRead,
    ValeCreate, ValeUpdate, ValeRead, EligibleEmployeeRead,
)
from app.services import payroll as payroll_service

router = APIRouter(prefix="/payroll", tags=["Folha de Pagamento"])


# ── Holerite — rotas literais (antes de /{payroll_id}) ───────────────────────

@router.post("", response_model=PayrollRead, status_code=201)
def create_payroll(
    data: PayrollCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rh_or_admin),
):
    payroll = payroll_service.create_payroll(db, data, current_user.company_id, current_user.id)
    return _enrich(payroll)


@router.get("/period", response_model=list[PayrollRead])
def list_by_period(
    month: int = Query(..., ge=1, le=12),
    year:  int = Query(..., ge=2000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    payrolls = payroll_service.list_by_period(db, month, year, current_user.company_id)
    return [_enrich(p) for p in payrolls]


@router.get("/eligible", response_model=list[EligibleEmployeeRead])
def list_eligible(
    month: int = Query(..., ge=1, le=12),
    year:  int = Query(..., ge=2000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lista funcionários elegíveis para o período com o holerite atual (se existir)."""
    rows = payroll_service.list_eligible_employees(db, month, year, current_user.company_id)
    result = []
    for r in rows:
        result.append({
            "employee_id":    r["employee_id"],
            "name":           r["name"],
            "salary":         r["salary"],
            "admission_date": r["admission_date"],
            "has_payroll":    r["has_payroll"],
            "payroll":        _enrich(r["payroll"]) if r["payroll"] else None,
        })
    return result


@router.post("/batch", response_model=list[PayrollRead], status_code=201)
def batch_create(
    data: PayrollBatchCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rh_or_admin),
):
    """Cria holerites para todos os funcionários elegíveis sem holerite no período."""
    payrolls = payroll_service.batch_create_payrolls(
        db, data, current_user.company_id, current_user.id
    )
    return [_enrich(p) for p in payrolls]


@router.post("/period/close-all", response_model=list[PayrollRead])
def close_all(
    month: int = Query(..., ge=1, le=12),
    year:  int = Query(..., ge=2000),
    payment_date: date | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rh_or_admin),
):
    """Fecha todos os holerites em rascunho para o período."""
    payrolls = payroll_service.close_all_payrolls(
        db, month, year, payment_date, current_user.company_id, current_user.id
    )
    return [_enrich(p) for p in payrolls]


@router.get("/employee/{employee_id}", response_model=list[PayrollRead])
def list_by_employee(
    employee_id: int = Path(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    payrolls = payroll_service.list_by_employee(db, employee_id, current_user.company_id)
    return [_enrich(p) for p in payrolls]


@router.get("/resumo-anual")
def resumo_anual(
    year: int = Query(..., ge=2000, le=2100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Resumo mensal do ano: funcionários + costureiras por mês."""
    from app.models.employee import Employee
    from app.models.seamstress import Seamstress, SeamstressPayment
    from app.models.payroll import Payroll

    company_id = current_user.company_id
    MONTH_NAMES = ["Janeiro","Fevereiro","Março","Abril","Maio","Junho",
                   "Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"]

    # Coleta todos os holerites do ano para a empresa
    emp_ids_q = db.query(Employee.id).filter(Employee.company_id == company_id).subquery()
    payrolls  = (
        db.query(Payroll)
        .filter(Payroll.employee_id.in_(emp_ids_q), Payroll.competence_year == year)
        .join(Employee, Employee.id == Payroll.employee_id)
        .order_by(Payroll.competence_month, Employee.name)
        .all()
    )

    # Coleta pagamentos de costureiras do ano
    seam_ids_q = db.query(Seamstress.id).filter(Seamstress.company_id == company_id).subquery()
    seam_pays  = (
        db.query(SeamstressPayment)
        .filter(SeamstressPayment.seamstress_id.in_(seam_ids_q),
                SeamstressPayment.competence_year == year)
        .join(Seamstress, Seamstress.id == SeamstressPayment.seamstress_id)
        .order_by(SeamstressPayment.competence_month, Seamstress.name)
        .all()
    )

    # Monta dicionário por mês
    months_with_data: set[int] = set(
        [p.competence_month for p in payrolls] +
        [sp.competence_month for sp in seam_pays if sp.competence_month]
    )

    result = []
    for m in sorted(months_with_data, reverse=True):
        month_payrolls = [p for p in payrolls if p.competence_month == m]

        # Agrupa por funcionário — se houver mais de um holerite no mês
        # (ex.: rascunho + fechado), pega o de maior valor líquido (o mais atualizado)
        from collections import defaultdict
        emp_dict: dict[int, dict] = {}
        for p in month_payrolls:
            eid = p.employee_id
            val = float(p.net_salary or 0)
            if eid not in emp_dict or val > emp_dict[eid]["net_salary"]:
                emp_dict[eid] = {
                    "payroll_id": p.id,
                    "name": p.employee.name,
                    "net_salary": val,
                }
        emp_rows = sorted(emp_dict.values(), key=lambda x: x["name"])

        # Agrupa costureiras por nome + tipo de pagamento, somando os valores
        seam_dict: dict[tuple, dict] = {}
        for sp in seam_pays:
            if sp.competence_month != m:
                continue
            tipo = sp.payment_type or "mensal"   # "mensal" | "entrega"
            key  = (sp.seamstress.name, tipo)
            if key not in seam_dict:
                seam_dict[key] = {"name": sp.seamstress.name, "payment_type": tipo, "amount": 0.0}
            seam_dict[key]["amount"] += float(sp.amount or 0)
        seam_rows = sorted(seam_dict.values(), key=lambda x: (x["name"], x["payment_type"]))

        total_emp  = sum(r["net_salary"] for r in emp_rows)
        total_seam = sum(r["amount"]     for r in seam_rows)
        result.append({
            "month":              m,
            "year":               year,
            "month_name":         MONTH_NAMES[m - 1],
            "employees":          emp_rows,
            "seamstresses":       seam_rows,
            "total_employees":    total_emp,
            "total_seamstresses": total_seam,
            "total":              total_emp + total_seam,
        })

    return result


@router.get("/vales", response_model=list[ValeRead])
def list_all_vales(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    vales = payroll_service.list_all_vales(db, current_user.company_id)
    return [_enrich_vale(v) for v in vales]


# ── Holerite — rotas parametrizadas /{payroll_id} ────────────────────────────

@router.get("/{payroll_id}", response_model=PayrollRead)
def get_payroll(
    payroll_id: int = Path(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _enrich(payroll_service.get_payroll(db, payroll_id, current_user.company_id))


@router.delete("/{payroll_id}", status_code=204)
def delete_payroll(
    payroll_id: int = Path(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rh_or_admin),
):
    """Exclui um holerite (inclusive fechados) para permitir reprocessamento."""
    payroll_service.delete_payroll(db, payroll_id, current_user.company_id, current_user.id)


@router.post("/{payroll_id}/recalculate", response_model=PayrollRead)
def recalculate(
    payroll_id: int = Path(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rh_or_admin),
):
    payroll = payroll_service.recalculate_payroll(
        db, payroll_id, current_user.company_id, current_user.id
    )
    return _enrich(payroll)


@router.patch("/{payroll_id}/flags", response_model=PayrollRead)
def update_flags(
    payroll_id: int = Path(...),
    data: PayrollFlagsUpdate = ...,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rh_or_admin),
):
    """Atualiza flags de cálculo (pay_overtime, use_hour_bank_for_absences, notes) e recalcula."""
    payroll = payroll_service.update_payroll_flags(
        db, payroll_id, data, current_user.company_id, current_user.id
    )
    return _enrich(payroll)


@router.post("/{payroll_id}/close", response_model=PayrollRead)
def close_payroll(
    payroll_id: int = Path(...),
    payment_date: date | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rh_or_admin),
):
    payroll = payroll_service.close_payroll(
        db, payroll_id, payment_date, current_user.company_id, current_user.id
    )
    return _enrich(payroll)


@router.get("/{payroll_id}/pdf")
def download_pdf(
    payroll_id: int = Path(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.repositories import employee as emp_repo
    from app.utils.pdf_generator import generate_payslip_pdf
    payroll = payroll_service.get_payroll(db, payroll_id, current_user.company_id)
    employee = emp_repo.get_employee(db, payroll.employee_id)
    pdf_path = generate_payslip_pdf(payroll, employee, output_dir="pdfs")
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=f"holerite_{payroll.competence_month:02d}_{payroll.competence_year}.pdf",
    )


# ── Itens do holerite ─────────────────────────────────────────────────────────

@router.post("/{payroll_id}/items", response_model=PayrollItemRead, status_code=201)
def add_item(
    payroll_id: int = Path(...),
    data: PayrollItemCreate = ...,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rh_or_admin),
):
    return payroll_service.add_manual_item(
        db, payroll_id, data, current_user.company_id, current_user.id
    )


@router.patch("/{payroll_id}/items/{item_id}", response_model=PayrollItemRead)
def update_item(
    payroll_id: int = Path(...),
    item_id:    int = Path(...),
    data: PayrollItemUpdate = ...,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rh_or_admin),
):
    return payroll_service.update_item(
        db, payroll_id, item_id, data, current_user.company_id, current_user.id
    )


@router.delete("/{payroll_id}/items/{item_id}", status_code=204)
def delete_item(
    payroll_id: int = Path(...),
    item_id:    int = Path(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rh_or_admin),
):
    payroll_service.delete_item(
        db, payroll_id, item_id, current_user.company_id, current_user.id
    )


# ── Vale ──────────────────────────────────────────────────────────────────────

@router.get("/employees/{employee_id}/vales", response_model=list[ValeRead])
def list_vales(
    employee_id: int = Path(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return payroll_service.list_vales_by_employee(db, employee_id, current_user.company_id)


@router.post("/employees/{employee_id}/vales", response_model=ValeRead, status_code=201)
def create_vale(
    employee_id: int = Path(...),
    data: ValeCreate = ...,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rh_or_admin),
):
    vale = payroll_service.create_vale(
        db, employee_id, data, current_user.company_id, current_user.id
    )
    return _enrich_vale(vale)


@router.get("/vales/{vale_id}", response_model=ValeRead)
def get_vale(
    vale_id: int = Path(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _enrich_vale(payroll_service.get_vale(db, vale_id, current_user.company_id))


@router.patch("/vales/{vale_id}", response_model=ValeRead)
def update_vale(
    vale_id: int = Path(...),
    data: ValeUpdate = ...,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rh_or_admin),
):
    vale = payroll_service.update_vale(db, vale_id, data, current_user.company_id, current_user.id)
    return _enrich_vale(vale)


@router.delete("/vales/{vale_id}", status_code=204)
def delete_vale(
    vale_id: int = Path(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rh_or_admin),
):
    payroll_service.delete_vale(db, vale_id, current_user.company_id, current_user.id)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _enrich_vale(vale) -> dict:
    d = {c.key: getattr(vale, c.key) for c in vale.__table__.columns}
    d["installment_items"] = vale.installment_items
    d["employee_name"] = vale.employee.name if vale.employee else None
    return d


def _enrich(payroll) -> dict:
    if payroll is None:
        return None
    d = {c.key: getattr(payroll, c.key) for c in payroll.__table__.columns}
    d["items"] = payroll.items
    d["employee_name"] = payroll.employee.name if payroll.employee else None
    d["status"] = payroll.status.value if hasattr(payroll.status, "value") else payroll.status
    return d
