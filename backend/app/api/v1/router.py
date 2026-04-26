from fastapi import APIRouter
from app.api.v1.endpoints import auth, company, users, employees, seamstresses, timesheet, payroll, vacation, reports, audit

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(company.router)
api_router.include_router(users.router)
api_router.include_router(employees.router)
api_router.include_router(seamstresses.router)
api_router.include_router(timesheet.router)
api_router.include_router(payroll.router)
api_router.include_router(vacation.router)
api_router.include_router(reports.router)
api_router.include_router(audit.router)
