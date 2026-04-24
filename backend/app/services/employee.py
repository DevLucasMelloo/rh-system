"""
Serviço de Funcionários.
Toda regra de negócio fica aqui — nunca nos endpoints ou no banco.
Criptografia Fernet aplicada a CPF, RG, conta bancária e pix antes de persistir.
"""
from decimal import Decimal, InvalidOperation
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.core.security import encrypt_field, decrypt_field
from app.repositories import employee as emp_repo
from app.repositories import audit_log as audit_repo
from app.schemas.employee import EmployeeCreate, EmployeeUpdate, SalaryUpdate, InactivateEmployee
from app.models.employee import Employee, EmployeeStatus


# ── Helpers de criptografia ───────────────────────────────────────────────────

def _vals_equal(old, new) -> bool:
    """Compara valores ignorando diferenças de precisão em Decimais e booleans."""
    if old == new:
        return True
    if old is None or new is None:
        return False
    try:
        return Decimal(str(old)).normalize() == Decimal(str(new)).normalize()
    except Exception:
        return str(old) == str(new)


def _fmt_val(v) -> str:
    if v is None:
        return '—'
    if isinstance(v, Decimal):
        return f'{v:.2f}'
    return str(v)


def _encrypt_sensitive(data: dict) -> dict:
    """Criptografa os campos sensíveis antes de salvar."""
    for field in ("cpf_encrypted", "rg_encrypted", "bank_account_encrypted", "pix_encrypted"):
        if data.get(field):
            data[field] = encrypt_field(data[field])
    return data


def _decrypt_employee(emp: Employee) -> dict:
    """Retorna dict com campos sensíveis descriptografados para a resposta."""
    return {
        "id": emp.id,
        "name": emp.name,
        "cpf": decrypt_field(emp.cpf_encrypted) if emp.cpf_encrypted else None,
        "rg": decrypt_field(emp.rg_encrypted) if emp.rg_encrypted else None,
        "date_of_birth": emp.date_of_birth,
        "phone": emp.phone,
        "father_name": emp.father_name,
        "mother_name": emp.mother_name,
        "address": emp.address,
        "cep": emp.cep,
        "city": emp.city,
        "state": emp.state,
        "role": emp.role,
        "salary": emp.salary,
        "admission_date": emp.admission_date,
        "registration_date": emp.registration_date,
        "status": emp.status.value,
        "is_intern": emp.is_intern,
        "weekly_hours": emp.weekly_hours,
        "bank_account": decrypt_field(emp.bank_account_encrypted) if emp.bank_account_encrypted else None,
        "pix": decrypt_field(emp.pix_encrypted) if emp.pix_encrypted else None,
        "bank_name": emp.bank_name,
        "auxilio": emp.auxilio,
        "needs_transport": emp.needs_transport or False,
        "vt_daily": emp.vt_daily,
        "inactivation_date": emp.inactivation_date,
        "inactivation_reason": emp.inactivation_reason,
    }


def _get_or_404(db: Session, employee_id: int, company_id: int) -> Employee:
    emp = emp_repo.get_employee(db, employee_id)
    if not emp or emp.company_id != company_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Funcionário não encontrado")
    return emp


# ── CPF: unicidade por empresa ────────────────────────────────────────────────

def _cpf_already_exists(db: Session, company_id: int, cpf: str, exclude_id: int | None = None) -> bool:
    """
    Fernet não é determinístico — não dá para buscar CPF diretamente.
    Verificamos unicidade descriptografando todos os registros da empresa.
    Para empresas pequenas (< 500 func.) isso é aceitável.
    """
    employees = emp_repo.list_all(db, company_id)
    for emp in employees:
        if exclude_id and emp.id == exclude_id:
            continue
        if decrypt_field(emp.cpf_encrypted) == cpf:
            return True
    return False


# ── CRUD ──────────────────────────────────────────────────────────────────────

def create_employee(db: Session, data: EmployeeCreate, company_id: int, created_by_id: int) -> dict:
    if _cpf_already_exists(db, company_id, data.cpf):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="CPF já cadastrado")

    fields = _encrypt_sensitive({
        "company_id": company_id,
        "name": data.name,
        "cpf_encrypted": data.cpf,
        "rg_encrypted": data.rg or "",
        "date_of_birth": data.date_of_birth,
        "phone": data.phone,
        "father_name": data.father_name,
        "mother_name": data.mother_name,
        "address": data.address,
        "cep": data.cep,
        "city": data.city,
        "state": data.state,
        "role": data.role,
        "salary": data.salary,
        "admission_date": data.admission_date,
        "registration_date": data.registration_date,
        "is_intern": data.is_intern,
        "weekly_hours": data.weekly_hours,
        "auxilio": data.auxilio,
        "needs_transport": data.needs_transport,
        "vt_daily": data.vt_daily,
        "bank_account_encrypted": data.bank_account or "",
        "pix_encrypted": data.pix or "",
        "bank_name": data.bank_name,
    })

    emp = emp_repo.create_employee(db, fields)

    emp_repo.add_history(
        db, emp.id, created_by_id,
        field_changed="criacao",
        old_value=None,
        new_value=f"Funcionário {emp.name} cadastrado",
    )
    audit_repo.create_log(
        db, action="employee_created", user_id=created_by_id,
        entity="employee", entity_id=emp.id,
        description=f"Funcionário '{emp.name}' cadastrado",
    )
    return _decrypt_employee(emp)


def get_employee(db: Session, employee_id: int, company_id: int) -> dict:
    emp = _get_or_404(db, employee_id, company_id)
    return _decrypt_employee(emp)


def list_employees(db: Session, company_id: int, active_only: bool = True) -> list[dict]:
    if active_only:
        employees = emp_repo.list_active(db, company_id)
    else:
        employees = emp_repo.list_inactive(db, company_id)
    return [_decrypt_employee(e) for e in employees]


def update_employee(
    db: Session,
    employee_id: int,
    data: EmployeeUpdate,
    company_id: int,
    updated_by_id: int,
) -> dict:
    emp = _get_or_404(db, employee_id, company_id)

    changes: dict = {}
    history_entries = []

    # Campos que aceitam null explícito (o usuário pode "zerar" o valor)
    nullable_fields = {"auxilio", "vt_daily", "phone", "date_of_birth", "address",
                       "cep", "city", "state", "bank_name", "father_name", "mother_name", "is_intern"}

    plain_fields = {
        "name": data.name, "phone": data.phone, "date_of_birth": data.date_of_birth,
        "father_name": data.father_name, "mother_name": data.mother_name,
        "address": data.address, "cep": data.cep, "city": data.city, "state": data.state,
        "role": data.role, "salary": data.salary, "weekly_hours": data.weekly_hours,
        "admission_date": data.admission_date, "registration_date": data.registration_date,
        "bank_name": data.bank_name, "is_intern": data.is_intern,
        "auxilio": data.auxilio, "needs_transport": data.needs_transport, "vt_daily": data.vt_daily,
    }

    # RG — campo criptografado tratado como plain aqui (re-criptografa no save)
    if data.rg is not None:
        changes["rg_encrypted"] = encrypt_field(data.rg)
        old_rg = decrypt_field(emp.rg_encrypted) if emp.rg_encrypted else None
        if old_rg != data.rg:
            history_entries.append(("rg", "***", "***atualizado***"))

    sent_fields = data.model_fields_set  # campos explicitamente enviados no PATCH

    for field, new_val in plain_fields.items():
        if field not in sent_fields:
            continue  # campo não foi enviado — não alterar
        if new_val is None and field not in nullable_fields:
            continue  # campo obrigatório enviado como null — ignorar
        old_val = getattr(emp, field)
        if not _vals_equal(old_val, new_val):
            history_entries.append((field, _fmt_val(old_val), _fmt_val(new_val)))
            changes[field] = new_val

    # Campos criptografados
    if data.bank_account is not None:
        changes["bank_account_encrypted"] = encrypt_field(data.bank_account)
        history_entries.append(("bank_account", "***", "***atualizado***"))

    if data.pix is not None:
        changes["pix_encrypted"] = encrypt_field(data.pix)
        history_entries.append(("pix", "***", "***atualizado***"))

    if not changes:
        return _decrypt_employee(emp)

    emp_repo.update_employee(db, emp, changes)

    for field, old_v, new_v in history_entries:
        emp_repo.add_history(db, emp.id, updated_by_id, field, old_v, new_v)

    audit_repo.create_log(
        db, action="employee_updated", user_id=updated_by_id,
        entity="employee", entity_id=emp.id,
        description=f"Dados de '{emp.name}' atualizados: {', '.join(f for f, _, _ in history_entries)}",
    )
    return _decrypt_employee(emp)


def update_salary(
    db: Session,
    employee_id: int,
    data: SalaryUpdate,
    company_id: int,
    updated_by_id: int,
) -> dict:
    emp = _get_or_404(db, employee_id, company_id)

    if emp.status == EmployeeStatus.INACTIVE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Funcionário inativo")

    old_salary = f"{emp.salary:.2f}"
    emp_repo.update_employee(db, emp, {"salary": data.new_salary})

    emp_repo.add_history(
        db, emp.id, updated_by_id,
        field_changed="salary",
        old_value=old_salary,
        new_value=f"{data.new_salary:.2f}",
        reason=data.reason,
    )
    audit_repo.create_log(
        db, action="salary_change", user_id=updated_by_id,
        entity="employee", entity_id=emp.id,
        description=f"Salário de '{emp.name}' alterado de R${old_salary} para R${data.new_salary}. Motivo: {data.reason}",
    )
    return _decrypt_employee(emp)


def inactivate_employee(
    db: Session,
    employee_id: int,
    data: InactivateEmployee,
    company_id: int,
    updated_by_id: int,
) -> dict:
    emp = _get_or_404(db, employee_id, company_id)

    if emp.status == EmployeeStatus.INACTIVE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Funcionário já está inativo")

    emp_repo.inactivate(db, emp, data.reason)
    emp_repo.add_history(
        db, emp.id, updated_by_id,
        field_changed="status",
        old_value="ativo",
        new_value="inativo",
        reason=data.reason,
    )
    audit_repo.create_log(
        db, action="employee_inactivated", user_id=updated_by_id,
        entity="employee", entity_id=emp.id,
        description=f"Funcionário '{emp.name}' inativado. Motivo: {data.reason}",
    )
    return _decrypt_employee(emp)


def reactivate_employee(
    db: Session,
    employee_id: int,
    company_id: int,
    updated_by_id: int,
) -> dict:
    emp = _get_or_404(db, employee_id, company_id)

    if emp.status == EmployeeStatus.ACTIVE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Funcionário já está ativo")

    emp_repo.reactivate(db, emp)
    emp_repo.add_history(
        db, emp.id, updated_by_id,
        field_changed="status",
        old_value="inativo",
        new_value="ativo",
    )
    audit_repo.create_log(
        db, action="employee_reactivated", user_id=updated_by_id,
        entity="employee", entity_id=emp.id,
        description=f"Funcionário '{emp.name}' reativado",
    )
    return _decrypt_employee(emp)


def get_history(db: Session, employee_id: int, company_id: int) -> list:
    _get_or_404(db, employee_id, company_id)
    entries = emp_repo.get_history(db, employee_id)
    return [
        {
            "id": e.id,
            "field_changed": e.field_changed,
            "old_value": e.old_value,
            "new_value": e.new_value,
            "reason": e.reason,
            "changed_at": e.changed_at.isoformat(),
            "changed_by_name": e.changed_by.name if e.changed_by else "Sistema",
        }
        for e in entries
    ]
