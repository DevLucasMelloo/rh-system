const PageSummary = (() => {

  function fmtMoney(v) {
    return 'R$ ' + Number(v || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  async function render(container) {
    if (!container) return;
    const year = new Date().getFullYear();

    container.innerHTML = `
      <div class="page-header">
        <div>
          <h1>Resumo de Pagamentos</h1>
          <p>Visão anual consolidada — funcionários e costureiras</p>
        </div>
        <div style="display:flex;gap:10px;align-items:center">
          <select id="sel-year" class="form-control" style="width:110px" onchange="PageSummary.changeYear()">
            ${[year, year-1, year-2].map(y => `<option value="${y}" ${y===year?'selected':''}>${y}</option>`).join('')}
          </select>
        </div>
      </div>
      <div id="summary-body">
        <div style="text-align:center;padding:60px 0">
          <div class="spinner" style="width:32px;height:32px;margin:0 auto 12px"></div>
          <div style="color:var(--text-light);font-size:14px">Carregando resumo...</div>
        </div>
      </div>`;

    loadSummary(year);
  }

  async function changeYear() {
    const sel = document.getElementById('sel-year');
    if (sel) loadSummary(Number(sel.value));
  }

  async function loadSummary(year) {
    const body = document.getElementById('summary-body');
    if (!body) return;

    try {
      const data = await Api.request('GET', `/payroll/resumo-anual?year=${year}`);
      const currentMonth = new Date().getMonth() + 1;
      const currentYear  = new Date().getFullYear();

      if (!data || data.length === 0) {
        body.innerHTML = `
          <div class="card" style="padding:48px;text-align:center;color:var(--text-light)">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="margin:0 auto 16px;display:block;opacity:.4"><rect x="2" y="5" width="20" height="14" rx="2"/><line x1="2" y1="10" x2="22" y2="10"/></svg>
            <div style="font-size:15px;font-weight:600;margin-bottom:6px">Nenhum pagamento em ${year}</div>
            <div style="font-size:13px">Gere folhas de pagamento ou registre pagamentos de costureiras para ver o resumo aqui.</div>
          </div>`;
        return;
      }

      // ── Totais anuais ──────────────────────────────────────────────────────
      const totalAno     = data.reduce((s, m) => s + m.total, 0);
      const totalEmpAno  = data.reduce((s, m) => s + m.total_employees, 0);
      const totalSeamAno = data.reduce((s, m) => s + m.total_seamstresses, 0);

      let html = `
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:14px;margin-bottom:24px">
          ${_statCard('Funcionários ' + year, fmtMoney(totalEmpAno), '#2563eb', '#eff6ff',
            '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/>')}
          ${_statCard('Costureiras ' + year, fmtMoney(totalSeamAno), '#7c3aed', '#f5f3ff',
            '<circle cx="12" cy="12" r="3"/><line x1="12" y1="3" x2="12" y2="9"/><line x1="12" y1="15" x2="12" y2="21"/><line x1="3" y1="12" x2="9" y2="12"/><line x1="15" y1="12" x2="21" y2="12"/>')}
          ${_statCard('Total Geral ' + year, fmtMoney(totalAno), '#16a34a', '#f0fdf4',
            '<line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>')}
        </div>`;

      // ── Card por mês ───────────────────────────────────────────────────────
      for (const m of data) {
        const payIds     = m.employees.map(e => e.payroll_id).filter(Boolean);
        const isCurrent  = m.month === currentMonth && m.year === currentYear;

        const empRows = m.employees.length
          ? m.employees.map(e => `
              <div style="display:flex;justify-content:space-between;align-items:center;
                          padding:9px 16px;border-bottom:1px solid var(--border);
                          border-left:3px solid #2563eb;background:#fff">
                <span style="font-size:13px;color:var(--text)">${e.name}</span>
                <div style="display:flex;align-items:center;gap:10px">
                  <span style="font-size:13px;font-weight:700;color:var(--text)">${fmtMoney(e.net_salary)}</span>
                  ${e.payroll_id ? `
                  <button
                    title="Imprimir holerite de ${e.name}"
                    onclick="PageSummary.printOne(${e.payroll_id}, this)"
                    style="width:28px;height:28px;border-radius:6px;border:1px solid var(--border);
                           background:#fff;cursor:pointer;display:flex;align-items:center;
                           justify-content:center;transition:all .15s;flex-shrink:0;padding:0"
                    onmouseover="this.style.background='#eff6ff';this.style.borderColor='#2563eb'"
                    onmouseout="this.style.background='#fff';this.style.borderColor='var(--border)'">
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="2">
                      <polyline points="6 9 6 2 18 2 18 9"/>
                      <path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/>
                      <rect x="6" y="14" width="12" height="8"/>
                    </svg>
                  </button>` : ''}
                </div>
              </div>`).join('')
          : `<div style="padding:28px 16px;text-align:center;color:var(--text-light);font-size:13px">
               <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="display:block;margin:0 auto 8px;opacity:.4"><rect x="2" y="5" width="20" height="14" rx="2"/><line x1="2" y1="10" x2="22" y2="10"/></svg>
               Sem holerites
             </div>`;

        const seamRows = m.seamstresses.length
          ? m.seamstresses.map(s => {
              const tipoLabel = s.payment_type === 'entrega' ? 'Entrega' : 'Mensal';
              const tipoColor = s.payment_type === 'entrega' ? '#d97706' : '#7c3aed';
              const tipoBg    = s.payment_type === 'entrega' ? '#fffbeb' : '#f5f3ff';
              return `
              <div style="display:flex;justify-content:space-between;align-items:center;
                          padding:10px 16px;border-bottom:1px solid var(--border);
                          border-left:3px solid ${tipoColor};margin-bottom:1px;background:#fff">
                <div style="display:flex;align-items:center;gap:8px">
                  <span style="font-size:13px;color:var(--text)">${s.name}</span>
                  <span style="font-size:10px;font-weight:700;padding:2px 7px;border-radius:20px;
                               background:${tipoBg};color:${tipoColor};text-transform:uppercase;letter-spacing:.4px">${tipoLabel}</span>
                </div>
                <span style="font-size:13px;font-weight:700;color:var(--text)">${fmtMoney(s.amount)}</span>
              </div>`;}).join('')
          : `<div style="padding:28px 16px;text-align:center;color:var(--text-light);font-size:13px">
               <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="display:block;margin:0 auto 8px;opacity:.4"><circle cx="12" cy="12" r="3"/><line x1="12" y1="3" x2="12" y2="9"/><line x1="12" y1="15" x2="12" y2="21"/><line x1="3" y1="12" x2="9" y2="12"/><line x1="15" y1="12" x2="21" y2="12"/></svg>
               Sem pagamentos registrados
             </div>`;

        html += `
          <div class="card" style="margin-bottom:18px;overflow:hidden">

            <!-- Cabeçalho -->
            <div style="display:flex;align-items:center;justify-content:space-between;
                        padding:16px 20px;border-bottom:1px solid var(--border)">
              <div style="display:flex;align-items:center;gap:12px">
                <div>
                  <div style="display:flex;align-items:center;gap:10px">
                    <span style="font-size:17px;font-weight:800;color:var(--text)">${m.month_name} / ${m.year}</span>
                    ${isCurrent ? `<span style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.6px;
                                        background:#ede9fe;color:#7c3aed;padding:3px 8px;border-radius:20px">
                                    Período Atual
                                  </span>` : ''}
                  </div>
                  <div style="font-size:12px;color:var(--text-light);margin-top:2px">
                    ${m.employees.length} funcionário${m.employees.length !== 1?'s':''} · ${m.seamstresses.length} costureira${m.seamstresses.length !== 1?'s':''}
                  </div>
                </div>
              </div>

              <div style="display:flex;align-items:center;gap:14px">
                <div style="text-align:right">
                  <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--text-light)">Mês Total</div>
                  <div style="font-size:20px;font-weight:800;color:var(--text)">${fmtMoney(m.total)}</div>
                </div>
                ${payIds.length > 0 ? `
                <button
                  title="Imprimir todos os holerites de ${m.month_name}"
                  onclick="PageSummary.printMonth(${JSON.stringify(payIds)}, '${m.month_name}', ${m.year})"
                  style="width:36px;height:36px;border-radius:8px;border:1px solid var(--border);
                         background:#fff;cursor:pointer;display:flex;align-items:center;
                         justify-content:center;transition:all .15s;flex-shrink:0"
                  onmouseover="this.style.background='#eff6ff';this.style.borderColor='#2563eb'"
                  onmouseout="this.style.background='#fff';this.style.borderColor='var(--border)'">
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="2">
                    <polyline points="6 9 6 2 18 2 18 9"/>
                    <path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/>
                    <rect x="6" y="14" width="12" height="8"/>
                  </svg>
                </button>` : ''}
              </div>
            </div>

            <!-- Colunas -->
            <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr))">

              <!-- Funcionários -->
              <div style="border-right:1px solid var(--border)">
                <div style="display:flex;align-items:center;justify-content:space-between;padding:12px 16px;border-bottom:1px solid var(--border)">
                  <div style="display:flex;align-items:center;gap:8px">
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="2">
                      <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
                      <circle cx="9" cy="7" r="4"/>
                      <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
                      <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
                    </svg>
                    <span style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.6px;color:#2563eb">Funcionários</span>
                  </div>
                  <span style="font-size:12px;font-weight:800;color:#2563eb">${fmtMoney(m.total_employees)}</span>
                </div>
                ${empRows}
              </div>

              <!-- Costureiras -->
              <div>
                <div style="display:flex;align-items:center;justify-content:space-between;padding:12px 16px;border-bottom:1px solid var(--border)">
                  <div style="display:flex;align-items:center;gap:8px">
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#7c3aed" stroke-width="2">
                      <circle cx="12" cy="12" r="3"/>
                      <line x1="12" y1="3" x2="12" y2="9"/>
                      <line x1="12" y1="15" x2="12" y2="21"/>
                      <line x1="3" y1="12" x2="9" y2="12"/>
                      <line x1="15" y1="12" x2="21" y2="12"/>
                    </svg>
                    <span style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.6px;color:#7c3aed">Costureiras</span>
                  </div>
                  <span style="font-size:12px;font-weight:800;color:#7c3aed">${fmtMoney(m.total_seamstresses)}</span>
                </div>
                ${seamRows}
              </div>

            </div>
          </div>`;
      }

      body.innerHTML = html;

    } catch (err) {
      const b = document.getElementById('summary-body');
      if (b) b.innerHTML = `<div class="alert alert-error">${err.message}</div>`;
    }
  }

  function _statCard(label, value, color, bg, iconPath) {
    return `
      <div class="card" style="padding:18px 22px;display:flex;align-items:center;gap:14px">
        <div style="width:42px;height:42px;border-radius:11px;background:${bg};display:flex;align-items:center;justify-content:center;flex-shrink:0">
          <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="${color}" stroke-width="2">${iconPath}</svg>
        </div>
        <div>
          <div style="font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.5px;color:var(--text-light);margin-bottom:4px">${label}</div>
          <div style="font-size:19px;font-weight:800;color:${color}">${value}</div>
        </div>
      </div>`;
  }

  async function printOne(payrollId, btn) {
    const orig = btn.innerHTML;
    btn.innerHTML = '<div class="spinner" style="width:12px;height:12px;border-width:2px"></div>';
    btn.disabled = true;
    try {
      await Api.openPayrollPdfTab(payrollId);
    } catch (err) {
      toast(err.message, 'error');
    } finally {
      btn.innerHTML = orig;
      btn.disabled = false;
    }
  }

  async function printMonth(payrollIds, monthName, year) {
    if (!payrollIds || payrollIds.length === 0) return;
    const btn = event.currentTarget;

    // Abre todas as janelas em branco sincronamente (antes de qualquer await)
    // para não ser bloqueado pelo popup-blocker do navegador
    const wins = payrollIds.map((_, i) =>
      window.open('about:blank', `_payslip_${monthName}_${year}_${i}`)
    );

    const orig = btn.innerHTML;
    btn.innerHTML = '<div class="spinner" style="width:14px;height:14px;border-width:2px"></div>';
    btn.disabled = true;
    try {
      for (let i = 0; i < payrollIds.length; i++) {
        if (wins[i]) await Api.loadPayrollPdfInWindow(payrollIds[i], wins[i]);
      }
    } catch (err) {
      toast(err.message, 'error');
    } finally {
      btn.innerHTML = orig;
      btn.disabled = false;
    }
  }

  return { render, changeYear, printOne, printMonth };
})();
