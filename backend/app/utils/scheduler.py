"""
Jobs periódicos do sistema — roda via APScheduler no startup do FastAPI.
"""
from datetime import date, timedelta
from loguru import logger


def check_expiring_licenses():
    """Verifica licenças que vencem em até 10 dias e envia e-mail de aviso."""
    from app.db.database import SessionLocal
    from app.models.license import License
    from app.models.user import User, UserRole
    from app.utils.email import send_license_warning

    db = SessionLocal()
    try:
        today     = date.today()
        deadline  = today + timedelta(days=10)

        expiring = (
            db.query(License)
            .filter(
                License.is_active == True,
                License.valid_until >= today,
                License.valid_until <= deadline,
            )
            .all()
        )

        if not expiring:
            logger.info("Scheduler: nenhuma licença vencendo nos próximos 10 dias")
            return

        for lic in expiring:
            days_left = (lic.valid_until - today).days

            # Busca admins da empresa com e-mail de recuperação cadastrado
            admins = (
                db.query(User)
                .filter(
                    User.company_id == lic.company_id,
                    User.role == UserRole.ADMIN,
                    User.is_active == True,
                    User.recovery_email != None,
                )
                .all()
            )

            for admin in admins:
                sent = send_license_warning(
                    to=admin.recovery_email,
                    name=admin.name,
                    valid_until=lic.valid_until,
                    days_left=days_left,
                )
                if sent:
                    logger.info(
                        f"Aviso de licença enviado para {admin.recovery_email} "
                        f"— vence em {days_left} dia(s) ({lic.valid_until})"
                    )
    except Exception as e:
        logger.error(f"Erro no job check_expiring_licenses: {e}")
    finally:
        db.close()


def check_expiring_vacations():
    """Toda segunda-feira às 08:00: envia e-mail com lista de férias vencidas para admins e RH."""
    from app.db.database import SessionLocal
    from app.models.company import Company
    from app.models.user import User, UserRole
    from app.services.vacation import get_company_overview
    from app.utils.email import send_vacation_warning

    db = SessionLocal()
    try:
        companies = db.query(Company).filter(Company.id > 0).all()
        for company in companies:
            overview = get_company_overview(db, company.id)
            today = date.today()

            overdue_employees = []
            for item in overview:
                if item["vacation_status"] not in ("vencida", "disponivel"):
                    continue
                acq_end = item.get("acquisition_end_date")
                if not acq_end:
                    continue
                days_overdue = (today - acq_end).days
                if days_overdue < 0:
                    continue
                overdue_employees.append({
                    "name": item["employee_name"],
                    "acquisition_end": acq_end,
                    "days_overdue": days_overdue,
                })

            if not overdue_employees:
                logger.info(f"Scheduler: empresa {company.id} sem férias vencidas")
                continue

            overdue_employees.sort(key=lambda x: x["days_overdue"], reverse=True)

            recipients = (
                db.query(User)
                .filter(
                    User.company_id == company.id,
                    User.role.in_([UserRole.ADMIN, UserRole.RH]),
                    User.is_active == True,
                    User.recovery_email != None,
                )
                .all()
            )

            for user in recipients:
                sent = send_vacation_warning(
                    to=user.recovery_email,
                    recipient_name=user.name,
                    employees=overdue_employees,
                )
                if sent:
                    logger.info(
                        f"Aviso de férias vencidas enviado para {user.recovery_email} "
                        f"— {len(overdue_employees)} funcionário(s)"
                    )
    except Exception as e:
        logger.error(f"Erro no job check_expiring_vacations: {e}")
    finally:
        db.close()


def send_monthly_report_job():
    """Todo dia 4 de cada mês às 08:00: envia relatório mensal de RH para admins e RH."""
    from app.db.database import SessionLocal
    from app.models.company import Company
    from app.models.employee import Employee, EmployeeStatus
    from app.models.user import User, UserRole
    from app.models.payroll import Payroll, PayrollStatus
    from app.models.seamstress import SeamstressPayment
    from app.models.vacation import Vacation, VacationStatus
    from app.services.vacation import get_company_overview, _auto_advance_status
    from app.utils.email import send_monthly_report
    from decimal import Decimal

    db = SessionLocal()
    try:
        today = date.today()
        # Mês de referência = mês anterior
        if today.month == 1:
            ref_month, ref_year = 12, today.year - 1
        else:
            ref_month, ref_year = today.month - 1, today.year

        month_names = ["Janeiro","Fevereiro","Março","Abril","Maio","Junho",
                       "Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"]
        month_name = month_names[ref_month - 1]

        companies = db.query(Company).filter(Company.id > 0).all()
        for company in companies:
            # Funcionários
            active_emps = (
                db.query(Employee)
                .filter(Employee.company_id == company.id, Employee.status == EmployeeStatus.ACTIVE)
                .all()
            )
            total_employees = len(active_emps)

            # Folha funcionários (fechados no mês ref)
            payrolls = (
                db.query(Payroll)
                .join(Employee)
                .filter(
                    Employee.company_id == company.id,
                    Payroll.competence_month == ref_month,
                    Payroll.competence_year == ref_year,
                    Payroll.status == PayrollStatus.CLOSED,
                )
                .all()
            )
            total_net_payroll = sum(Decimal(str(p.net_salary or 0)) for p in payrolls)

            # Costureiras (pagamentos do mês ref)
            seam_payments = (
                db.query(SeamstressPayment)
                .join(SeamstressPayment.seamstress)
                .filter(
                    SeamstressPayment.competence_month == ref_month,
                    SeamstressPayment.competence_year == ref_year,
                    SeamstressPayment.status == "pago",
                )
                .all()
            )
            total_seamstress = sum(Decimal(str(p.amount or 0)) for p in seam_payments)
            total_paid = total_net_payroll + total_seamstress

            # Férias no mês de referência
            from datetime import date as _date
            ref_start = _date(ref_year, ref_month, 1)
            import calendar as _cal
            last_day = _cal.monthrange(ref_year, ref_month)[1]
            ref_end = _date(ref_year, ref_month, last_day)

            all_vacs = (
                db.query(Vacation)
                .join(Employee)
                .filter(Employee.company_id == company.id)
                .all()
            )
            all_vacs = [_auto_advance_status(db, v) for v in all_vacs]

            on_vacation = []
            for v in all_vacs:
                if v.status not in (VacationStatus.ACTIVE, VacationStatus.COMPLETED, VacationStatus.SCHEDULED):
                    continue
                if not v.enjoyment_start or v.sell_all_days:
                    continue
                enj_end = v.enjoyment_start + timedelta(days=max((v.enjoyment_days or 0) - 1, 0))
                if v.enjoyment_start <= ref_end and enj_end >= ref_start:
                    emp = db.get(Employee, v.employee_id)
                    if emp:
                        on_vacation.append({"name": emp.name})

            # Férias vencidas (atual)
            overview = get_company_overview(db, company.id)
            overdue_vacation = []
            scheduled_vacation = []
            for item in overview:
                status = item["vacation_status"]
                if status in ("vencida", "disponivel"):
                    acq_end = item.get("acquisition_end_date")
                    if acq_end:
                        days_overdue = (today - acq_end).days
                        if days_overdue >= 0:
                            overdue_vacation.append({"name": item["employee_name"], "days_overdue": days_overdue})
                elif status == "agendada" and item.get("scheduled_start"):
                    start_fmt = item["scheduled_start"].strftime("%d/%m/%Y")
                    scheduled_vacation.append({
                        "name": item["employee_name"],
                        "start": start_fmt,
                        "days": item.get("scheduled_days", 0),
                    })

            overdue_vacation.sort(key=lambda x: x["days_overdue"], reverse=True)

            # Aniversariantes do mês atual (mês do envio)
            birthdays = []
            for emp in active_emps:
                if emp.date_of_birth and emp.date_of_birth.month == today.month:
                    birthdays.append({
                        "name": emp.name,
                        "date_str": emp.date_of_birth.strftime("%d/%m"),
                    })
            birthdays.sort(key=lambda x: x["date_str"])

            data = {
                "month_name": month_name,
                "year": ref_year,
                "total_employees": total_employees,
                "total_net_payroll": float(total_net_payroll),
                "total_seamstress": float(total_seamstress),
                "total_paid": float(total_paid),
                "on_vacation": on_vacation,
                "overdue_vacation": overdue_vacation,
                "scheduled_vacation": scheduled_vacation,
                "birthdays": birthdays,
            }

            recipients = (
                db.query(User)
                .filter(
                    User.company_id == company.id,
                    User.role.in_([UserRole.ADMIN, UserRole.RH]),
                    User.is_active == True,
                    User.recovery_email != None,
                )
                .all()
            )

            for user in recipients:
                sent = send_monthly_report(
                    to=user.recovery_email,
                    recipient_name=user.name,
                    data=data,
                )
                if sent:
                    logger.info(f"Relatório mensal enviado para {user.recovery_email} — {month_name}/{ref_year}")
    except Exception as e:
        logger.error(f"Erro no job send_monthly_report_job: {e}")
    finally:
        db.close()


def start_scheduler():
    """Inicia o APScheduler com os jobs configurados."""
    from apscheduler.schedulers.background import BackgroundScheduler

    scheduler = BackgroundScheduler(timezone="America/Sao_Paulo")

    # Roda todo dia às 08:00 (horário de Brasília)
    scheduler.add_job(
        check_expiring_licenses,
        trigger="cron",
        hour=8,
        minute=0,
        id="check_expiring_licenses",
        replace_existing=True,
    )

    # Roda toda segunda-feira às 08:00
    scheduler.add_job(
        check_expiring_vacations,
        trigger="cron",
        day_of_week="mon",
        hour=8,
        minute=0,
        id="check_expiring_vacations",
        replace_existing=True,
    )

    # Roda todo dia 4 de cada mês às 08:00
    scheduler.add_job(
        send_monthly_report_job,
        trigger="cron",
        day=4,
        hour=8,
        minute=0,
        id="send_monthly_report",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("Scheduler iniciado — licença (diário) + férias vencidas (seg) + relatório mensal (dia 4)")
    return scheduler
