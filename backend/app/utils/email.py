"""
Envio de emails via smtplib (built-in do Python).
Falha silenciosa em dev quando credenciais não estão configuradas.
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from loguru import logger
from app.core.config import settings


def _send(to: str, subject: str, body_html: str) -> bool:
    """Envia email. Retorna True se enviado, False se falhou."""
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        logger.warning("Email nao enviado: SMTP_USER ou SMTP_PASSWORD nao configurados")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.EMAIL_FROM
    msg["To"] = to
    msg.attach(MIMEText(body_html, "html", "utf-8"))

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.EMAIL_FROM, to, msg.as_string())
        logger.info(f"Email enviado para {to}: {subject}")
        return True
    except Exception as e:
        logger.error(f"Erro ao enviar email para {to}: {e}")
        return False


def send_password_reset(to: str, reset_link: str) -> bool:
    subject = "Redefinição de senha — Sistema RH"
    body = f"""
    <html><body>
    <p>Olá,</p>
    <p>Recebemos uma solicitação para redefinir sua senha no Sistema de RH.</p>
    <p>Clique no link abaixo para criar uma nova senha (válido por 15 minutos):</p>
    <p><a href="{reset_link}">{reset_link}</a></p>
    <p>Se você não solicitou isso, ignore este email.</p>
    </body></html>
    """
    return _send(to, subject, body)
