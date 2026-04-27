const PageBankHours = (() => {
  const MONTHS = ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez'];
  let curYear = currentYear();

  async function render(container) {
    container.innerHTML = `
      <div class="page-header">
        <div><h1>Banco de Horas</h1><p>Saldo mensal acumulado por funcionário</p></div>
        <div style="display:flex;gap:8px;align-items:center">
          <select class="form-control" id="bank-year-sel" onchange="PageBankHours.onYearChange()" style="width:110px">
            ${_yearOptions()}
          </select>
          <button class="btn btn-secondary" id="btn-recalc-all" onclick="PageBankHours.recalcAll()" title="Recalcular banco de todos os funcionários">
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
      if (btn) { btn.disabled = false; btn.textContent = '↻ Recalcular Todos'; }
    }
  }

  return { render, onYearChange, recalc, recalcAll };
})();
