const PageBankHours = (() => {
  const MONTHS = ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez'];
  let curYear = currentYear();
  let _lastData = [];

  async function render(container) {
    container.innerHTML = `
      <div class="page-header">
        <div><h1>Banco de Horas</h1><p>Saldo mensal acumulado por funcionário</p></div>
        <div style="display:flex;gap:8px;align-items:center">
          <select class="form-control" id="bank-year-sel" onchange="PageBankHours.onYearChange()" style="width:110px">
            ${_yearOptions()}
          </select>
          <button class="btn" style="background:#dc2626;color:#fff" onclick="PageBankHours.exportPdf()" title="Exportar tabela em PDF">
            🖨 Exportar PDF
          </button>
          <button class="btn btn-primary" id="btn-recalc-all" onclick="PageBankHours.recalcAll()" title="Recalcular banco de todos os funcionários">
            ↻ Recalcular Todos
          </button>
        </div>
      </div>
      <div id="bank-content">${loadingRow(14)}</div>`;
    await _load();
  }

  function _yearOptions() {
    let html = '';
    for (let y = curYear + 1; y >= curYear - 3; y--) {
      html += `<option value="${y}" ${y === curYear ? 'selected' : ''}>${y}</option>`;
    }
    return html;
  }

  async function onYearChange() {
    const sel = document.getElementById('bank-year-sel');
    if (sel) curYear = parseInt(sel.value);
    await _load();
  }

  async function _load() {
    const el = document.getElementById('bank-content');
    if (!el) return;
    el.innerHTML = loadingRow(14);
    try {
      const data = await Api.getBankSummary(curYear);
      _lastData = data;
      _render(data);
    } catch (e) {
      el.innerHTML = `<div class="alert alert-error">${e.message}</div>`;
    }
  }

  function _fmtMin(min) {
    if (min === 0) return '—';
    const abs = Math.abs(min);
    const h = Math.floor(abs / 60);
    const m = abs % 60;
    return (min > 0 ? '+' : '-') + h + 'h' + (m > 0 ? String(m).padStart(2,'0') : '');
  }

  function _color(min) {
    if (min > 0) return 'var(--success)';
    if (min < 0) return 'var(--danger)';
    return 'var(--text-muted)';
  }

  function _colorHex(min) {
    if (min > 0) return '#16a34a';
    if (min < 0) return '#dc2626';
    return '#6b7280';
  }

  function _render(data) {
    const el = document.getElementById('bank-content');
    if (!el) return;

    if (!data.length) {
      el.innerHTML = `<div class="alert alert-warning">Nenhum funcionário ativo encontrado.</div>`;
      return;
    }

    const headerCols = MONTHS.map(m =>
      `<th style="text-align:center;min-width:72px;padding:10px 4px">${m}</th>`
    ).join('');

    const rows = data.map(emp => {
      const cells = Array.from({ length: 12 }, (_, i) => {
        const md = emp.months[i + 1] || { balance_minutes: 0, paid_minutes: 0, deducted_minutes: 0 };
        const val = md.balance_minutes;
        const text = _fmtMin(val);
        const color = _color(val);

        let paidBadge = '';
        if (md.paid_minutes > 0) {
          const ph = Math.floor(md.paid_minutes / 60);
          const pm = md.paid_minutes % 60;
          const pStr = ph + 'h' + (pm > 0 ? String(pm).padStart(2,'0') : '');
          paidBadge = `<div style="font-size:10px;color:var(--primary);margin-top:2px;white-space:nowrap"
                            title="HE pagas neste mês: ${pStr}">✓ pago ${pStr}</div>`;
        }

        let deductedBadge = '';
        if (md.deducted_minutes > 0) {
          const dh = Math.floor(md.deducted_minutes / 60);
          const dm = md.deducted_minutes % 60;
          const dStr = dh + 'h' + (dm > 0 ? String(dm).padStart(2,'0') : '');
          deductedBadge = `<div style="font-size:10px;color:var(--warning,#d97706);margin-top:2px;white-space:nowrap"
                                title="Banco negativo descontado neste mês: ${dStr}">✗ desc. ${dStr}</div>`;
        }

        return `<td style="text-align:center;vertical-align:middle;padding:6px 4px">
          <span style="font-weight:600;color:${color};font-size:13px">${text}</span>
          ${paidBadge}${deductedBadge}
        </td>`;
      }).join('');

      const tot = emp.total_balance_minutes;
      return `<tr>
        <td style="white-space:nowrap;font-weight:600;padding:8px 12px">${emp.name}</td>
        ${cells}
        <td style="text-align:center;padding:8px 12px;border-left:2px solid var(--border)">
          <span style="font-weight:700;font-size:14px;color:${_color(tot)}">${_fmtMin(tot)}</span>
        </td>
        <td style="padding:4px 8px">
          <button class="btn btn-sm btn-secondary" title="Recalcular banco de horas"
            onclick="PageBankHours.recalc(${emp.employee_id})">↻</button>
        </td>
      </tr>`;
    }).join('');

    el.innerHTML = `
      <div class="table-wrapper" style="overflow-x:auto">
        <table style="min-width:1000px;border-collapse:collapse">
          <thead>
            <tr>
              <th style="min-width:160px;padding:10px 12px">Funcionário</th>
              ${headerCols}
              <th style="text-align:center;border-left:2px solid var(--border);padding:10px 12px;white-space:nowrap">Total Banco</th>
              <th></th>
            </tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
      <p style="margin-top:12px;font-size:12px;color:var(--text-muted)">
        ✓ pago = H.E. paga naquele mês &nbsp;|&nbsp; ✗ desc. = falta descontada do salário (não afeta o banco) &nbsp;|&nbsp; ↻ recalcula o banco do zero
      </p>`;
  }

  function exportPdf() {
    const data = _lastData;
    if (!data || !data.length) { toast('Nenhum dado para exportar.', 'error'); return; }

    const user = Api.getUser();
    const company = user?.company_name || '';
    const now = new Date().toLocaleDateString('pt-BR');

    const headerCols = MONTHS.map(m =>
      `<th style="text-align:center;padding:7px 4px;background:#1e3a5f;color:#fff;font-size:11px">${m}</th>`
    ).join('');

    const rows = data.map((emp, idx) => {
      const bg = idx % 2 === 0 ? '#f8fafc' : '#ffffff';
      const cells = Array.from({ length: 12 }, (_, i) => {
        const md = emp.months[i + 1] || { balance_minutes: 0, paid_minutes: 0, deducted_minutes: 0 };
        const val = md.balance_minutes;
        const color = _colorHex(val);
        const text = _fmtMin(val);

        let badges = '';
        if (md.paid_minutes > 0) {
          const ph = Math.floor(md.paid_minutes / 60);
          const pm = md.paid_minutes % 60;
          badges += `<div style="font-size:9px;color:#2563eb">${ph}h${pm > 0 ? String(pm).padStart(2,'0') : ''} pago</div>`;
        }
        if (md.deducted_minutes > 0) {
          const dh = Math.floor(md.deducted_minutes / 60);
          const dm = md.deducted_minutes % 60;
          badges += `<div style="font-size:9px;color:#b45309">${dh}h${dm > 0 ? String(dm).padStart(2,'0') : ''} desc.</div>`;
        }

        return `<td style="text-align:center;padding:5px 3px;border-bottom:1px solid #e2e8f0;background:${bg}">
          <span style="font-weight:700;color:${color};font-size:11px">${text}</span>${badges}
        </td>`;
      }).join('');

      const tot = emp.total_balance_minutes;
      const totColor = _colorHex(tot);
      return `<tr>
        <td style="white-space:nowrap;font-weight:600;padding:7px 10px;border-bottom:1px solid #e2e8f0;background:${bg};font-size:12px">${emp.name}</td>
        ${cells}
        <td style="text-align:center;padding:7px 10px;border-bottom:1px solid #e2e8f0;border-left:2px solid #1e3a5f;background:${bg}">
          <span style="font-weight:800;font-size:12px;color:${totColor}">${_fmtMin(tot)}</span>
        </td>
      </tr>`;
    }).join('');

    const html = `<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<title>Banco de Horas ${curYear}</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Segoe UI', Arial, sans-serif; background: #fff; color: #1e293b; }
  @page { size: A4 landscape; margin: 12mm 10mm; }
  @media print { body { -webkit-print-color-adjust: exact; print-color-adjust: exact; } }
</style>
</head>
<body>
<div style="padding:16px 20px 20px">
  <!-- Cabeçalho -->
  <div style="display:flex;justify-content:space-between;align-items:flex-end;margin-bottom:18px;
              border-bottom:3px solid #1e3a5f;padding-bottom:12px">
    <div>
      <div style="font-size:9px;font-weight:600;letter-spacing:2px;text-transform:uppercase;
                  color:#1e3a5f;margin-bottom:4px">Relatório de</div>
      <div style="font-size:24px;font-weight:800;color:#1e3a5f">Banco de Horas</div>
      ${company ? `<div style="font-size:13px;color:#475569;margin-top:3px">${company}</div>` : ''}
    </div>
    <div style="text-align:right">
      <div style="font-size:20px;font-weight:700;color:#1e3a5f">${curYear}</div>
      <div style="font-size:11px;color:#64748b;margin-top:2px">Gerado em ${now}</div>
    </div>
  </div>

  <!-- Legenda -->
  <div style="display:flex;gap:20px;margin-bottom:14px;font-size:11px;color:#475569">
    <span style="color:#16a34a;font-weight:600">● Positivo</span>
    <span style="color:#dc2626;font-weight:600">● Negativo</span>
    <span style="color:#6b7280;font-weight:600">● Sem saldo</span>
    <span style="color:#2563eb">pago = H.E. pagas no mês</span>
    <span style="color:#b45309">desc. = banco descontado no mês</span>
  </div>

  <!-- Tabela -->
  <table style="width:100%;border-collapse:collapse;font-size:11px">
    <thead>
      <tr>
        <th style="text-align:left;padding:8px 10px;background:#1e3a5f;color:#fff;min-width:140px;font-size:12px;border-radius:4px 0 0 0">
          Funcionário
        </th>
        ${headerCols}
        <th style="text-align:center;padding:8px 10px;background:#1e3a5f;color:#fff;border-left:2px solid #4a7ab5;white-space:nowrap;font-size:12px;border-radius:0 4px 0 0">
          Total
        </th>
      </tr>
    </thead>
    <tbody>${rows}</tbody>
  </table>

  <!-- Rodapé -->
  <div style="margin-top:18px;padding-top:10px;border-top:1px solid #e2e8f0;
              display:flex;justify-content:space-between;align-items:center;font-size:10px;color:#94a3b8">
    <span>Sistema RH &mdash; Banco de Horas ${curYear}</span>
    <span>Total de funcionários: ${data.length}</span>
  </div>
</div>
</body>
</html>`;

    const win = window.open('', '_blank');
    win.document.write(html);
    win.document.close();
    win.onload = () => { win.focus(); win.print(); };
  }

  async function recalc(empId) {
    try {
      const r = await Api.recalculateHourBank(empId);
      toast(`Banco recalculado: ${r.balance_hours}`);
      await _load();
    } catch (e) {
      toast(e.message, 'error');
    }
  }

  async function recalcAll() {
    const btn = document.getElementById('btn-recalc-all');
    if (btn) { btn.disabled = true; btn.textContent = 'Recalculando...'; }
    try {
      const r = await Api.recalculateAllBanks();
      toast(`Banco recalculado para ${r.recalculated} funcionário(s)`);
      await _load();
    } catch (e) {
      toast(e.message, 'error');
    } finally {
      if (btn) { btn.disabled = false; btn.innerHTML = '↻ Recalcular Todos'; }
    }
  }

  return { render, onYearChange, recalc, recalcAll, exportPdf };
})();
