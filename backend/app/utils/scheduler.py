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

    scheduler.start()
    logger.info("Scheduler iniciado — licença (diário 08:00) + férias vencidas (seg 08:00)")
    return scheduler
