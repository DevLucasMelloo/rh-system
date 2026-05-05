"""
Backup e Restauração — exporta/importa todos os dados da empresa em ZIP+JSON.
"""
import io, json, zipfile, enum
from datetime import datetime, date, time
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from sqlalchemy import Date as SADate, DateTime as SADateTime, Time as SATime, Numeric as SANumeric
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.core.dependencies import get_current_user, require_admin
from app.models.user import User

router = APIRouter(prefix="/backup", tags=["Backup"])

_BACKUP_VERSION = "1.0"


# ── Serialização ──────────────────────────────────────────────────────────────

def _to_json_safe(val):
    if val is None:
        return None
    if isinstance(val, (datetime, date, time)):
        return val.isoformat()
    if isinstance(val, Decimal):
        return float(val)
    if isinstance(val, enum.Enum):
        return val.value
    return val


def _row_to_dict(row) -> dict:
    return {col.name: _to_json_safe(getattr(row, col.name))
            for col in row.__table__.columns}


def _parse_date(v) -> Optional[date]:
    if not v:
        return None
    try:
        return date.fromisoformat(str(v)[:10])
    except Exception:
        return None


def _parse_time(v) -> Optional[time]:
    if not v:
        return None
    try:
        return time.fromisoformat(str(v)[:8])
    except Exception:
        return None


def _parse_decimal(v) -> Optional[Decimal]:
    if v is None:
        return None
    try:
        return Decimal(str(v))
    except Exception:
        return None


# ── Inserção genérica ─────────────────────────────────────────────────────────

def _insert(db: Session, model_class, rec: dict, **overrides):
    """
    Insere um registro a partir do dict do backup, convertendo tipos
    automaticamente com base nas colunas do modelo.
    Retorna o objeto ORM com o novo ID gerado.
    """
    data: dict = {}
    for col in model_class.__table__.columns:
        name = col.name
        if name == "id":
            continue
        if name in overrides:
            data[name] = overrides[name]
            continue
        val = rec.get(name)
        if val is None:
            data[name] = None
            continue
        col_type = type(col.type)
        if col_type is SADate:
            data[name] = _parse_date(val)
        elif col_type is SADateTime:
            data[name] = None  # deixa o DB preencher (server_default)
        elif col_type is SATime:
            data[name] = _parse_time(val)
        elif col_type is SANumeric:
            data[name] = _parse_decimal(val)
        else:
            data[name] = val
    obj = model_class(**data)
    db.add(obj)
    db.flush()
    return obj


# ── Coleta de dados ───────────────────────────────────────────────────────────

def _collect_data(db: Session, company_id: int) -> dict:
    from app.models.employee import Employee, EmployeeHistory
    from app.models.seamstress import Seamstress, SeamstressPayment
    from app.models.payroll import Payroll, PayrollItem, Vale, ValeInstallment
    from app.models.timesheet import TimesheetEntry, HourBank
    from app.models.vacation import Vacation, VacationItem
    from app.models.termination import Termination
    from app.models.thirteenth import ThirteenthSalary

    employees = db.query(Employee).filter(Employee.company_id == company_id).all()
    emp_ids = [e.id for e in employees]

    seamstresses = db.query(Seamstress).filter(Seamstress.company_id == company_id).all()
    seam_ids = [s.id for s in seamstresses]

    payrolls = db.query(Payroll).filter(Payroll.employee_id.in_(emp_ids)).all() if emp_ids else []
    pay_ids  = [p.id for p in payrolls]

    vales    = db.query(Vale).filter(Vale.employee_id.in_(emp_ids)).all() if emp_ids else []
    vale_ids = [v.id for v in vales]

    vacations = db.query(Vacation).filter(Vacation.employee_id.in_(emp_ids)).all() if emp_ids else []
    vac_ids   = [v.id for v in vacations]

    return {
        "version":             _BACKUP_VERSION,
        "exported_at":         datetime.utcnow().isoformat(),
        "company_id":          company_id,
        "employees":           [_row_to_dict(r) for r in employees],
        "employee_history":    [_row_to_dict(r) for r in db.query(EmployeeHistory).filter(EmployeeHistory.employee_id.in_(emp_ids)).all()] if emp_ids else [],
        "seamstresses":        [_row_to_dict(r) for r in seamstresses],
        "seamstress_payments": [_row_to_dict(r) for r in db.query(SeamstressPayment).filter(SeamstressPayment.seamstress_id.in_(seam_ids)).all()] if seam_ids else [],
        "payrolls":            [_row_to_dict(r) for r in payrolls],
        "payroll_items":       [_row_to_dict(r) for r in db.query(PayrollItem).filter(PayrollItem.payroll_id.in_(pay_ids)).all()] if pay_ids else [],
        "vales":               [_row_to_dict(r) for r in vales],
        "vale_installments":   [_row_to_dict(r) for r in db.query(ValeInstallment).filter(ValeInstallment.vale_id.in_(vale_ids)).all()] if vale_ids else [],
        "timesheet_entries":   [_row_to_dict(r) for r in db.query(TimesheetEntry).filter(TimesheetEntry.employee_id.in_(emp_ids)).all()] if emp_ids else [],
        "hour_banks":          [_row_to_dict(r) for r in db.query(HourBank).filter(HourBank.employee_id.in_(emp_ids)).all()] if emp_ids else [],
        "vacations":           [_row_to_dict(r) for r in vacations],
        "vacation_items":      [_row_to_dict(r) for r in db.query(VacationItem).filter(VacationItem.vacation_id.in_(vac_ids)).all()] if vac_ids else [],
        "terminations":        [_row_to_dict(r) for r in db.query(Termination).filter(Termination.employee_id.in_(emp_ids)).all()] if emp_ids else [],
        "thirteenth_salary":   [_row_to_dict(r) for r in db.query(ThirteenthSalary).filter(ThirteenthSalary.employee_id.in_(emp_ids)).all()] if emp_ids else [],
    }


# ── Restauração ───────────────────────────────────────────────────────────────

def _restore_data(db: Session, company_id: int, data: dict, mode: str) -> dict:
    """
    mode='replace': apaga tudo da empresa e insere do backup.
    mode='add':     insere apenas funcionários/costureiras que não existem ainda.
    Retorna contagem de registros importados.
    """
    from app.models.employee import Employee, EmployeeHistory
    from app.models.seamstress import Seamstress, SeamstressPayment
    from app.models.payroll import Payroll, PayrollItem, Vale, ValeInstallment
    from app.models.timesheet import TimesheetEntry, HourBank
    from app.models.vacation import Vacation, VacationItem
    from app.models.termination import Termination
    from app.models.thirteenth import ThirteenthSalary

    if mode == "replace":
        existing_emps  = db.query(Employee).filter(Employee.company_id == company_id).all()
        existing_seams = db.query(Seamstress).filter(Seamstress.company_id == company_id).all()
        existing_ids   = [e.id for e in existing_emps]
        existing_s_ids = [s.id for s in existing_seams]

        if existing_ids:
            p_ids = [p.id for p in db.query(Payroll).filter(Payroll.employee_id.in_(existing_ids)).all()]
            v_ids = [v.id for v in db.query(Vale).filter(Vale.employee_id.in_(existing_ids)).all()]
            x_ids = [v.id for v in db.query(Vacation).filter(Vacation.employee_id.in_(existing_ids)).all()]
            if v_ids:
                db.query(ValeInstallment).filter(ValeInstallment.vale_id.in_(v_ids)).delete(synchronize_session=False)
            if p_ids:
                db.query(PayrollItem).filter(PayrollItem.payroll_id.in_(p_ids)).delete(synchronize_session=False)
            if x_ids:
                db.query(VacationItem).filter(VacationItem.vacation_id.in_(x_ids)).delete(synchronize_session=False)
            db.query(Payroll).filter(Payroll.employee_id.in_(existing_ids)).delete(synchronize_session=False)
            db.query(Vale).filter(Vale.employee_id.in_(existing_ids)).delete(synchronize_session=False)
            db.query(Vacation).filter(Vacation.employee_id.in_(existing_ids)).delete(synchronize_session=False)
            db.query(Termination).filter(Termination.employee_id.in_(existing_ids)).delete(synchronize_session=False)
            db.query(ThirteenthSalary).filter(ThirteenthSalary.employee_id.in_(existing_ids)).delete(synchronize_session=False)
            db.query(TimesheetEntry).filter(TimesheetEntry.employee_id.in_(existing_ids)).delete(synchronize_session=False)
            db.query(HourBank).filter(HourBank.employee_id.in_(existing_ids)).delete(synchronize_session=False)
            db.query(EmployeeHistory).filter(EmployeeHistory.employee_id.in_(existing_ids)).delete(synchronize_session=False)
            db.query(Employee).filter(Employee.company_id == company_id).delete(synchronize_session=False)
        if existing_s_ids:
            db.query(SeamstressPayment).filter(SeamstressPayment.seamstress_id.in_(existing_s_ids)).delete(synchronize_session=False)
        db.query(Seamstress).filter(Seamstress.company_id == company_id).delete(synchronize_session=False)
        db.flush()

    # Chaves existentes para modo 'add'
    existing_emp_keys: set[str] = set()
    existing_seam_keys: set[str] = set()
    if mode == "add":
        existing_emp_keys  = {f"{e.name}|{e.admission_date}" for e in db.query(Employee).filter(Employee.company_id == company_id).all()}
        existing_seam_keys = {s.name for s in db.query(Seamstress).filter(Seamstress.company_id == company_id).all()}

    emp_map:  dict[int, int] = {}
    seam_map: dict[int, int] = {}
    pay_map:  dict[int, int] = {}
    vale_map: dict[int, int] = {}
    vac_map:  dict[int, int] = {}
    total_inserted = 0

    # ── Funcionários ──────────────────────────────────────────────────────────
    for rec in data.get("employees", []):
        old_id = rec["id"]
        key = f"{rec.get('name')}|{rec.get('admission_date')}"
        if mode == "add" and key in existing_emp_keys:
            continue
        obj = _insert(db, Employee, rec, company_id=company_id)
        emp_map[old_id] = obj.id
        total_inserted += 1

    for rec in data.get("employee_history", []):
        new_emp_id = emp_map.get(rec.get("employee_id"))
        if not new_emp_id:
            continue
        _insert(db, EmployeeHistory, rec, employee_id=new_emp_id, changed_by_id=None)

    # ── Costureiras ───────────────────────────────────────────────────────────
    for rec in data.get("seamstresses", []):
        old_id = rec["id"]
        if mode == "add" and rec.get("name") in existing_seam_keys:
            continue
        obj = _insert(db, Seamstress, rec, company_id=company_id)
        seam_map[old_id] = obj.id
        total_inserted += 1

    for rec in data.get("seamstress_payments", []):
        new_seam_id = seam_map.get(rec.get("seamstress_id"))
        if not new_seam_id:
            continue
        _insert(db, SeamstressPayment, rec, seamstress_id=new_seam_id)

    # ── Folhas de pagamento ───────────────────────────────────────────────────
    for rec in data.get("payrolls", []):
        old_id = rec["id"]
        new_emp_id = emp_map.get(rec.get("employee_id"))
        if not new_emp_id:
            continue
        obj = _insert(db, Payroll, rec, employee_id=new_emp_id, created_by_id=None)
        pay_map[old_id] = obj.id
        total_inserted += 1

    for rec in data.get("payroll_items", []):
        new_pay_id = pay_map.get(rec.get("payroll_id"))
        if not new_pay_id:
            continue
        _insert(db, PayrollItem, rec, payroll_id=new_pay_id)

    # ── Vales ─────────────────────────────────────────────────────────────────
    for rec in data.get("vales", []):
        old_id = rec["id"]
        new_emp_id = emp_map.get(rec.get("employee_id"))
        if not new_emp_id:
            continue
        obj = _insert(db, Vale, rec, employee_id=new_emp_id, registered_by_id=None)
        vale_map[old_id] = obj.id
        total_inserted += 1

    for rec in data.get("vale_installments", []):
        new_vale_id = vale_map.get(rec.get("vale_id"))
        if not new_vale_id:
            continue
        _insert(db, ValeInstallment, rec, vale_id=new_vale_id, payroll_id=None)

    # ── Ponto ─────────────────────────────────────────────────────────────────
    for rec in data.get("timesheet_entries", []):
        new_emp_id = emp_map.get(rec.get("employee_id"))
        if not new_emp_id:
            continue
        _insert(db, TimesheetEntry, rec, employee_id=new_emp_id, registered_by_id=None)
        total_inserted += 1

    # ── Banco de horas ────────────────────────────────────────────────────────
    for rec in data.get("hour_banks", []):
        new_emp_id = emp_map.get(rec.get("employee_id"))
        if not new_emp_id:
            continue
        _insert(db, HourBank, rec, employee_id=new_emp_id)

    # ── Férias ────────────────────────────────────────────────────────────────
    for rec in data.get("vacations", []):
        old_id = rec["id"]
        new_emp_id = emp_map.get(rec.get("employee_id"))
        if not new_emp_id:
            continue
        obj = _insert(db, Vacation, rec, employee_id=new_emp_id, created_by_id=None)
        vac_map[old_id] = obj.id
        total_inserted += 1

    for rec in data.get("vacation_items", []):
        new_vac_id = vac_map.get(rec.get("vacation_id"))
        if not new_vac_id:
            continue
        _insert(db, VacationItem, rec, vacation_id=new_vac_id)

    # ── Rescisões ─────────────────────────────────────────────────────────────
    for rec in data.get("terminations", []):
        new_emp_id = emp_map.get(rec.get("employee_id"))
        if not new_emp_id:
            continue
        _insert(db, Termination, rec, employee_id=new_emp_id, created_by_id=None)
        total_inserted += 1

    # ── 13º Salário ───────────────────────────────────────────────────────────
    for rec in data.get("thirteenth_salary", []):
        new_emp_id = emp_map.get(rec.get("employee_id"))
        if not new_emp_id:
            continue
        _insert(db, ThirteenthSalary, rec, employee_id=new_emp_id, created_by_id=None)
        total_inserted += 1

    db.commit()
    return {"imported": total_inserted}


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/info")
def backup_info(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.models.employee import Employee
    from app.models.seamstress import Seamstress
    from app.models.payroll import Payroll
    from app.models.timesheet import TimesheetEntry

    company_id = current_user.company_id
    emp_count  = db.query(Employee).filter(Employee.company_id == company_id).count()
    seam_count = db.query(Seamstress).filter(Seamstress.company_id == company_id).count()

    emp_ids_q  = db.query(Employee.id).filter(Employee.company_id == company_id).subquery()
    pay_count  = db.query(Payroll).filter(Payroll.employee_id.in_(emp_ids_q)).count()
    ts_count   = db.query(TimesheetEntry).filter(TimesheetEntry.employee_id.in_(emp_ids_q)).count()

    total      = emp_count + seam_count + pay_count + ts_count
    approx_mb  = max(round(total * 0.0012, 1), 0.1)

    return {
        "total_records":    total,
        "approx_size_mb":   approx_mb,
        "employee_count":   emp_count,
        "seamstress_count": seam_count,
    }


@router.post("/export")
def export_backup(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    company_id = current_user.company_id
    data       = _collect_data(db, company_id)

    json_bytes = json.dumps(data, ensure_ascii=False, indent=2, default=str).encode("utf-8")
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("backup.json", json_bytes)
        total_recs = sum(len(v) for v in data.values() if isinstance(v, list))
        manifest   = (
            f"RH System — Backup\n"
            f"Exportado em: {data['exported_at']}\n"
            f"Empresa ID:   {company_id}\n"
            f"Registros:    {total_recs}\n"
        )
        zf.writestr("LEIAME.txt", manifest)
    zip_buffer.seek(0)

    ts       = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"backup_rh_{ts}.zip"

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/import")
async def import_backup(
    file: UploadFile = File(...),
    mode: str = Form("add"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    if mode not in ("replace", "add"):
        raise HTTPException(status_code=400, detail="mode deve ser 'replace' ou 'add'")

    content = await file.read()
    if len(content) > 100 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Arquivo muito grande (máx 100MB)")

    try:
        fname = (file.filename or "").lower()
        if fname.endswith(".zip"):
            with zipfile.ZipFile(io.BytesIO(content)) as zf:
                json_name = next((n for n in zf.namelist() if n.endswith(".json")), None)
                if not json_name:
                    raise HTTPException(status_code=400, detail="ZIP não contém arquivo JSON de backup")
                data = json.loads(zf.read(json_name).decode("utf-8"))
        else:
            data = json.loads(content.decode("utf-8"))
    except (zipfile.BadZipFile, json.JSONDecodeError) as e:
        raise HTTPException(status_code=400, detail=f"Arquivo inválido: {e}")

    if data.get("version") != _BACKUP_VERSION:
        raise HTTPException(status_code=400, detail="Versão de backup incompatível")

    result = _restore_data(db, current_user.company_id, data, mode)
    return {"message": "Backup importado com sucesso", **result}
