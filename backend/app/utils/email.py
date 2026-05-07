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
            "from": settings.EMAIL_FROM or "RH System <onboarding@resend.dev>",
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


def send_license_warning(to: str, name: str, valid_until, days_left: int) -> bool:
    from datetime import date
    data_fmt = valid_until.strftime("%d/%m/%Y") if hasattr(valid_until, "strftime") else str(valid_until)
    urgency_color = "#dc2626" if days_left <= 3 else "#d97706" if days_left <= 7 else "#2563eb"
    subject = f"⚠️ Licença vence em {days_left} dia{'s' if days_left != 1 else ''} — Sistema RH"
    body = f"""
    <html><body style="font-family:sans-serif;color:#1e293b;max-width:480px;margin:0 auto;padding:32px">
      <h2 style="color:{urgency_color};margin-bottom:8px">⚠️ Aviso de Licença</h2>
      <p>Olá, <strong>{name}</strong>!</p>
      <p>A licença do <strong>Sistema de RH</strong> está prestes a vencer.</p>
      <div style="background:#fef9ec;border:1px solid #fbbf24;border-radius:10px;padding:16px;margin:20px 0">
        <p style="margin:0 0 6px;font-size:15px">
          <strong>Vencimento:</strong>
          <span style="color:{urgency_color};font-weight:700"> {data_fmt}</span>
        </p>
        <p style="margin:0;font-size:15px">
          <strong>Dias restantes:</strong>
          <span style="color:{urgency_color};font-weight:700"> {days_left} dia{'s' if days_left != 1 else ''}</span>
        </p>
      </div>
      <p>Entre em contato para renovar o acesso antes do vencimento e evitar a interrupção do sistema.</p>
      <div style="background:#f1f5f9;border-radius:10px;padding:16px;margin:20px 0">
        <p style="margin:0 0 8px;font-weight:600">Contato para renovação:</p>
        <p style="margin:0 0 4px">📱 <a href="tel:+5511937209330" style="color:#2563eb;text-decoration:none">(11) 93720-9330</a></p>
        <p style="margin:0">📧 <a href="mailto:lucassmello29@gmail.com" style="color:#2563eb;text-decoration:none">lucassmello29@gmail.com</a></p>
      </div>
      <hr style="border:none;border-top:1px solid #e2e8f0;margin:24px 0">
      <p style="color:#94a3b8;font-size:12px">Sistema de RH — aviso automático enviado diariamente quando restam até 10 dias</p>
    </body></html>
    """
    return _send(to, subject, body)


def send_monthly_report(to: str, recipient_name: str, data: dict) -> bool:
    """
    Relatório mensal de RH enviado todo dia 4 às 08:00.
    data: {
      month_name, year,
      total_employees,
      total_net_payroll, total_seamstress,
      total_paid (funcionarios + costureiras),
      on_vacation: [{name}],
      overdue_vacation: [{name, days_overdue}],
      scheduled_vacation: [{name, start, days}],
      birthdays: [{name, date_str}],
    }
    """
    month_name = data["month_name"]
    year = data["year"]
    subject = f"Relatório de RH — {month_name}/{year}"

    def _row(label, value, color="#1e293b"):
        return f'<tr><td style="padding:8px 12px;color:#64748b;font-size:13px">{label}</td><td style="padding:8px 12px;font-weight:600;color:{color};font-size:14px">{value}</td></tr>'

    def _fmt_brl(val):
        return f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    def _emp_list(items, empty="Nenhum"):
        if not items:
            return f'<p style="color:#94a3b8;font-size:13px;margin:4px 0">{empty}</p>'
        return "".join(f'<p style="margin:3px 0;font-size:13px">• {i}</p>' for i in items)

    overdue_list   = _emp_list([
        f"{e['name']} <span style='color:#dc2626;font-size:12px'>({e['days_overdue']}d vencido)</span>"
        for e in data.get("overdue_vacation", [])
    ])
    scheduled_list = _emp_list([
        f"{e['name']} — {e['start']} ({e['days']} dias)"
        for e in data.get("scheduled_vacation", [])
    ])
    birthday_list  = _emp_list([f"{e['name']} — {e['date_str']}" for e in data.get("birthdays", [])])

    body = f"""
    <html><body style="font-family:sans-serif;color:#1e293b;max-width:560px;margin:0 auto;padding:32px">
      <h2 style="color:#2563eb;margin-bottom:4px">📊 Relatório de RH</h2>
      <p style="color:#64748b;margin-top:0;margin-bottom:24px">{month_name} de {year}</p>
      <p>Olá, <strong>{recipient_name}</strong>! Segue o resumo do mês anterior.</p>

      <!-- Funcionários -->
      <div style="background:#f8fafc;border-radius:10px;padding:4px 0;margin:20px 0;border:1px solid #e2e8f0">
        <p style="margin:10px 12px 6px;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:#64748b">Funcionários</p>
        <table style="width:100%;border-collapse:collapse">
          {_row("Total de funcionários ativos", data["total_employees"])}
        </table>
      </div>

      <!-- Folha -->
      <div style="background:#f8fafc;border-radius:10px;padding:4px 0;margin:20px 0;border:1px solid #e2e8f0">
        <p style="margin:10px 12px 6px;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:#64748b">Folha de Pagamento</p>
        <table style="width:100%;border-collapse:collapse">
          {_row("Total líquido funcionários", _fmt_brl(data["total_net_payroll"]), "#16a34a")}
          {_row("Total pago costureiras", _fmt_brl(data["total_seamstress"]), "#16a34a")}
          {_row("Total geral pago", _fmt_brl(data["total_paid"]), "#2563eb")}
        </table>
      </div>

      <!-- Férias -->
      <div style="background:#f8fafc;border-radius:10px;padding:12px 16px;margin:20px 0;border:1px solid #e2e8f0">
        <p style="margin:0 0 8px;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:#64748b">Férias Vencidas</p>
        {overdue_list}
        <p style="margin:14px 0 8px;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:#64748b">Férias Agendadas</p>
        {scheduled_list}
      </div>

      <!-- Aniversariantes -->
      <div style="background:#f8fafc;border-radius:10px;padding:12px 16px;margin:20px 0;border:1px solid #e2e8f0">
        <p style="margin:0 0 8px;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:#64748b">Aniversariantes do Mês</p>
        {birthday_list}
      </div>

      <hr style="border:none;border-top:1px solid #e2e8f0;margin:24px 0">
      <p style="color:#94a3b8;font-size:12px">Sistema de RH — relatório automático enviado todo dia 4 de cada mês</p>
    </body></html>
    """
    return _send(to, subject, body)


def send_vacation_warning(to: str, recipient_name: str, employees: list[dict]) -> bool:
    """
    employees: lista de dicts com keys: name, days_overdue, acquisition_end (date)
    days_overdue: positivo = dias que já passou do fim do período aquisitivo
    """
    from datetime import date as _date
    today = _date.today()
    count = len(employees)
    subject = f"⚠️ {count} funcionário{'s' if count != 1 else ''} com férias vencidas — Sistema RH"

    rows = ""
    for emp in employees:
        days = emp["days_overdue"]
        acq_end = emp["acquisition_end"]
        date_fmt = acq_end.strftime("%d/%m/%Y") if hasattr(acq_end, "strftime") else str(acq_end)
        if days <= 0:
            tempo = "Venceu hoje"
        elif days <= 30:
            urgency = "#dc2626"
            tempo = f"Venceu há <strong style='color:{urgency}'>{days} dia{'s' if days != 1 else ''}</strong>"
        elif days <= 90:
            urgency = "#d97706"
            tempo = f"Venceu há <strong style='color:{urgency}'>{days} dias</strong>"
        else:
            urgency = "#64748b"
            tempo = f"Venceu há <strong style='color:{urgency}'>{days} dias</strong>"
        rows += f"""
        <tr>
          <td style="padding:10px 12px;border-bottom:1px solid #e2e8f0;font-weight:600">{emp['name']}</td>
          <td style="padding:10px 12px;border-bottom:1px solid #e2e8f0;color:#64748b;font-size:13px">{date_fmt}</td>
          <td style="padding:10px 12px;border-bottom:1px solid #e2e8f0;font-size:13px">{tempo}</td>
        </tr>"""

    body = f"""
    <html><body style="font-family:sans-serif;color:#1e293b;max-width:560px;margin:0 auto;padding:32px">
      <h2 style="color:#dc2626;margin-bottom:8px">⚠️ Férias Vencidas</h2>
      <p>Olá, <strong>{recipient_name}</strong>!</p>
      <p>
        {count} funcionário{'s estão' if count != 1 else ' está'} com férias vencidas
        e ainda não agendaram o período de gozo.
      </p>
      <table style="width:100%;border-collapse:collapse;margin:20px 0;font-size:14px">
        <thead>
          <tr style="background:#f1f5f9">
            <th style="padding:10px 12px;text-align:left;font-size:12px;text-transform:uppercase;letter-spacing:.5px;color:#64748b">Funcionário</th>
            <th style="padding:10px 12px;text-align:left;font-size:12px;text-transform:uppercase;letter-spacing:.5px;color:#64748b">Fim Aquisitivo</th>
            <th style="padding:10px 12px;text-align:left;font-size:12px;text-transform:uppercase;letter-spacing:.5px;color:#64748b">Situação</th>
          </tr>
        </thead>
        <tbody>{rows}</tbody>
      </table>
      <p style="color:#64748b;font-size:13px">
        Acesse o sistema para agendar as férias dos funcionários listados acima.
      </p>
      <hr style="border:none;border-top:1px solid #e2e8f0;margin:24px 0">
      <p style="color:#94a3b8;font-size:12px">Sistema de RH — aviso automático enviado às segundas-feiras</p>
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
