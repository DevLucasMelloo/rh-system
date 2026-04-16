from fastapi import APIRouter
from app.api.v1.endpoints import auth, company, users, employees, seamstresses, timesheet, payroll

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(company.router)
api_router.include_router(users.router)
api_router.include_router(employees.router)
api_router.include_router(seamstresses.router)
api_router.include_router(timesheet.router)
api_router.include_router(payroll.router)
