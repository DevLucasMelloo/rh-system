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

    scheduler.start()
    logger.info("Scheduler iniciado — job de licença configurado para 08:00 diário")
    return scheduler
