"""
Envio de emails via Resend API.
Falha silenciosa quando RESEND_API_KEY não está configurada.
"""
from loguru import logger
from app.core.config import settings


def _send(to: str, subject: str, body_html: str) -> bool:
    if not settings.RESEND_API_KEY:
        logger.warning("Email nao enviado: RESEND_API_KEY nao configurada")
        return False

    try:
        import resend
        resend.api_key = settings.RESEND_API_KEY
        resend.Emails.send({
            "from": settings.EMAIL_FROM or "onboarding@resend.dev",
            "to": [to],
            "subject": subject,
            "html": body_html,
        })
        logger.info(f"Email enviado para {to}: {subject}")
        return True
    except Exception as e:
        logger.error(f"Erro ao enviar email para {to}: {e}")
        return False


def send_password_reset(to: str, reset_link: str) -> bool:
    subject = "Redefinição de senha — Sistema RH"
    body = f"""
    <html><body style="font-family:sans-serif;color:#1e293b;max-width:480px;margin:0 auto;padding:32px">
      <h2 style="color:#2563eb;margin-bottom:8px">Sistema de RH</h2>
      <p>Olá,</p>
      <p>Recebemos uma solicitação para redefinir sua senha.</p>
      <p>Clique no botão abaixo para criar uma nova senha. O link é válido por <strong>15 minutos</strong>.</p>
      <p style="margin:28px 0">
        <a href="{reset_link}"
           style="background:#2563eb;color:#fff;padding:12px 28px;border-radius:8px;
                  text-decoration:none;font-weight:600;font-size:15px">
          Redefinir Senha
        </a>
      </p>
      <p style="color:#64748b;font-size:13px">
        Se você não solicitou isso, ignore este e-mail. Sua senha não será alterada.
      </p>
      <hr style="border:none;border-top:1px solid #e2e8f0;margin:24px 0">
      <p style="color:#94a3b8;font-size:12px">Sistema de RH — mensagem automática</p>
    </body></html>
    """
    return _send(to, subject, body)


def send_welcome(to: str, name: str, username: str) -> bool:
    subject = "Bem-vindo ao Sistema RH"
    body = f"""
    <html><body style="font-family:sans-serif;color:#1e293b;max-width:480px;margin:0 auto;padding:32px">
      <h2 style="color:#2563eb;margin-bottom:8px">Sistema de RH</h2>
      <p>Olá, <strong>{name}</strong>!</p>
      <p>Sua conta foi criada com sucesso no Sistema de RH.</p>
      <div style="background:#f8fafc;border-radius:10px;padding:16px;margin:20px 0;border:1px solid #e2e8f0">
        <p style="margin:0 0 6px"><strong>Usuário:</strong> {username}</p>
      </div>
      <p>Acesse o sistema e cadastre um e-mail de recuperação nas <strong>Configurações</strong>
         para poder redefinir sua senha caso esqueça.</p>
      <hr style="border:none;border-top:1px solid #e2e8f0;margin:24px 0">
      <p style="color:#94a3b8;font-size:12px">Sistema de RH — mensagem automática</p>
    </body></html>
    """
    return _send(to, subject, body)
