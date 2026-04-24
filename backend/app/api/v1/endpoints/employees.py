from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.core.dependencies import get_current_user, require_rh_or_admin
from app.schemas.employee import (
    EmployeeCreate, EmployeeUpdate, EmployeeRead,
    EmployeeListItem, EmployeeHistoryRead, SalaryUpdate, InactivateEmployee, RaiseApply,
)
from app.services import employee as emp_service
from app.models.user import User

router = APIRouter(prefix="/employees", tags=["Funcionários"])


@router.post("", response_model=EmployeeRead, status_code=201)
def create_employee(
    data: EmployeeCreate,
    current_user: User = Depends(require_rh_or_admin),
    db: Session = Depends(get_db),
):
    return emp_service.create_employee(db, data, current_user.company_id, current_user.id)


@router.get("", response_model=list[EmployeeRead])
def list_employees(
    inactive: bool = Query(False, description="True para listar inativos"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return emp_service.list_employees(db, current_user.company_id, active_only=not inactive)


@router.get("/{employee_id}", response_model=EmployeeRead)
def get_employee(
    employee_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return emp_service.get_employee(db, employee_id, current_user.company_id)


@router.patch("/{employee_id}", response_model=EmployeeRead)
def update_employee(
    employee_id: int,
    data: EmployeeUpdate,
    current_user: User = Depends(require_rh_or_admin),
    db: Session = Depends(get_db),
):
    return emp_service.update_employee(db, employee_id, data, current_user.company_id, current_user.id)


@router.patch("/{employee_id}/salary", response_model=EmployeeRead)
def update_salary(
    employee_id: int,
    data: SalaryUpdate,
    current_user: User = Depends(require_rh_or_admin),
    db: Session = Depends(get_db),
):
    return emp_service.update_salary(db, employee_id, data, current_user.company_id, current_user.id)


@router.patch("/{employee_id}/raise", response_model=EmployeeRead)
def apply_raise(
    employee_id: int,
    data: RaiseApply,
    current_user: User = Depends(require_rh_or_admin),
    db: Session = Depends(get_db),
):
    return emp_service.apply_raise(db, employee_id, data, current_user.company_id, current_user.id)


@router.post("/{employee_id}/inactivate", response_model=EmployeeRead)
def inactivate(
    employee_id: int,
    data: InactivateEmployee,
    current_user: User = Depends(require_rh_or_admin),
    db: Session = Depends(get_db),
):
    return emp_service.inactivate_employee(db, employee_id, data, current_user.company_id, current_user.id)


@router.post("/{employee_id}/reactivate", response_model=EmployeeRead)
def reactivate(
    employee_id: int,
    current_user: User = Depends(require_rh_or_admin),
    db: Session = Depends(get_db),
):
    return emp_service.reactivate_employee(db, employee_id, current_user.company_id, current_user.id)


@router.get("/{employee_id}/history", response_model=list[EmployeeHistoryRead])
def get_history(
    employee_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return emp_service.get_history(db, employee_id, current_user.company_id)
