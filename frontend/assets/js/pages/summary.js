const PageSummary = (() => {

  const MONTH_NAMES = ['Janeiro','Fevereiro','Março','Abril','Maio','Junho',
                       'Julho','Agosto','Setembro','Outubro','Novembro','Dezembro'];

  function fmtMoney(v) {
    return 'R$ ' + Number(v || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  async function render(container) {
    const el = document.getElementById('page-content');
    if (!el) return;

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
      </div>
    `;

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

      if (!data || data.length === 0) {
        body.innerHTML = `
          <div class="card" style="padding:48px;text-align:center;color:var(--text-light)">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="margin:0 auto 16px;display:block;opacity:.4"><rect x="2" y="5" width="20" height="14" rx="2"/><line x1="2" y1="10" x2="22" y2="10"/></svg>
            <div style="font-size:15px;font-weight:600;margin-bottom:6px">Nenhum pagamento em ${year}</div>
            <div style="font-size:13px">Gere folhas de pagamento ou registre pagamentos de costureiras para ver o resumo aqui.</div>
          </div>`;
        return;
      }

      // Total anual
      const totalAno = data.reduce((s, m) => s + m.total, 0);
      const totalEmpAno  = data.reduce((s, m) => s + m.total_employees, 0);
      const totalSeamAno = data.reduce((s, m) => s + m.total_seamstresses, 0);

      let html = `
        <!-- Totalizador anual -->
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:16px;margin-bottom:28px">
          <div class="card" style="padding:20px 24px">
            <div style="font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:.5px;color:var(--text-light);margin-bottom:6px">Total Funcionários ${year}</div>
            <div style="font-size:22px;font-weight:800;color:#2563eb">${fmtMoney(totalEmpAno)}</div>
          </div>
          <div class="card" style="padding:20px 24px">
            <div style="font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:.5px;color:var(--text-light);margin-bottom:6px">Total Costureiras ${year}</div>
            <div style="font-size:22px;font-weight:800;color:#7c3aed">${fmtMoney(totalSeamAno)}</div>
          </div>
          <div class="card" style="padding:20px 24px">
            <div style="font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:.5px;color:var(--text-light);margin-bottom:6px">Total Geral ${year}</div>
            <div style="font-size:22px;font-weight:800;color:#16a34a">${fmtMoney(totalAno)}</div>
          </div>
        </div>
      `;

      // Card por mês
      for (const m of data) {
        const payIds = m.employees.map(e => e.payroll_id).filter(Boolean);

        // Linhas de funcionários
        let empRows = m.employees.length
          ? m.employees.map(e => `
              <tr>
                <td style="padding:8px 12px;font-size:13px;color:var(--text)">${e.name}</td>
                <td style="padding:8px 12px;font-size:13px;font-weight:600;color:var(--text);text-align:right">${fmtMoney(e.net_salary)}</td>
              </tr>`).join('')
          : `<tr><td colspan="2" style="padding:12px;text-align:center;color:var(--text-light);font-size:13px">Sem holerites</td></tr>`;

        // Linhas de costureiras
        let seamRows = m.seamstresses.length
          ? m.seamstresses.map(s => `
              <tr>
                <td style="padding:8px 12px;font-size:13px;color:var(--text)">${s.name}</td>
                <td style="padding:8px 12px;font-size:13px;font-weight:600;color:var(--text);text-align:right">${fmtMoney(s.amount)}</td>
              </tr>`).join('')
          : `<tr><td colspan="2" style="padding:12px;text-align:center;color:var(--text-light);font-size:13px">Sem pagamentos</td></tr>`;

        html += `
          <div class="card" style="margin-bottom:20px;overflow:hidden">
            <!-- Cabeçalho do mês -->
            <div style="display:flex;align-items:center;justify-content:space-between;padding:16px 20px;background:var(--bg);border-bottom:1px solid var(--border)">
              <div style="display:flex;align-items:center;gap:14px">
                <div style="width:40px;height:40px;border-radius:10px;background:#eff6ff;display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:800;color:#2563eb">${m.month.toString().padStart(2,'0')}</div>
                <div>
                  <div style="font-size:16px;font-weight:700;color:var(--text)">${m.month_name} / ${m.year}</div>
                  <div style="font-size:12px;color:var(--text-light)">
                    ${m.employees.length} func. · ${m.seamstresses.length} costureira${m.seamstresses.length !== 1 ? 's' : ''}
                  </div>
                </div>
              </div>
              <div style="display:flex;align-items:center;gap:16px">
                <div style="text-align:right">
                  <div style="font-size:11px;color:var(--text-light);font-weight:600;text-transform:uppercase">Total do mês</div>
                  <div style="font-size:18px;font-weight:800;color:#16a34a">${fmtMoney(m.total)}</div>
                </div>
                ${payIds.length > 0 ? `
                <button
                  title="Imprimir todos os holerites de ${m.month_name}"
                  onclick="PageSummary.printMonth(${JSON.stringify(payIds)}, '${m.month_name}', ${m.year})"
                  style="width:38px;height:38px;border-radius:9px;border:1px solid var(--border);background:#fff;cursor:pointer;display:flex;align-items:center;justify-content:center;transition:all .2s;flex-shrink:0"
                  onmouseover="this.style.background='#eff6ff';this.style.borderColor='#2563eb'"
                  onmouseout="this.style.background='#fff';this.style.borderColor='var(--border)'">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="2"><polyline points="6 9 6 2 18 2 18 9"/><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><rect x="6" y="14" width="12" height="8"/></svg>
                </button>` : ''}
              </div>
            </div>

            <!-- Tabelas lado a lado -->
            <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr))">

              <!-- Funcionários -->
              <div style="border-right:1px solid var(--border)">
                <div style="padding:10px 12px;background:#f8fafc;border-bottom:1px solid var(--border);display:flex;justify-content:space-between;align-items:center">
                  <span style="font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.4px;color:#2563eb">Funcionários</span>
                  <span style="font-size:12px;font-weight:700;color:#2563eb">${fmtMoney(m.total_employees)}</span>
                </div>
                <table style="width:100%;border-collapse:collapse">
                  <thead>
                    <tr style="background:#fafafa">
                      <th style="padding:7px 12px;font-size:11px;font-weight:600;color:var(--text-light);text-align:left;border-bottom:1px solid var(--border)">Funcionário</th>
                      <th style="padding:7px 12px;font-size:11px;font-weight:600;color:var(--text-light);text-align:right;border-bottom:1px solid var(--border)">Valor Líquido</th>
                    </tr>
                  </thead>
                  <tbody>${empRows}</tbody>
                </table>
              </div>

              <!-- Costureiras -->
              <div>
                <div style="padding:10px 12px;background:#f8fafc;border-bottom:1px solid var(--border);display:flex;justify-content:space-between;align-items:center">
                  <span style="font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.4px;color:#7c3aed">Costureiras</span>
                  <span style="font-size:12px;font-weight:700;color:#7c3aed">${fmtMoney(m.total_seamstresses)}</span>
                </div>
                <table style="width:100%;border-collapse:collapse">
                  <thead>
                    <tr style="background:#fafafa">
                      <th style="padding:7px 12px;font-size:11px;font-weight:600;color:var(--text-light);text-align:left;border-bottom:1px solid var(--border)">Costureira</th>
                      <th style="padding:7px 12px;font-size:11px;font-weight:600;color:var(--text-light);text-align:right;border-bottom:1px solid var(--border)">Valor</th>
                    </tr>
                  </thead>
                  <tbody>${seamRows}</tbody>
                </table>
              </div>

            </div>
          </div>
        `;
      }

      body.innerHTML = html;

    } catch (err) {
      if (!body) return;
      body.innerHTML = `<div class="alert alert-error">${err.message}</div>`;
    }
  }

  async function printMonth(payrollIds, monthName, year) {
    if (!payrollIds || payrollIds.length === 0) return;

    const btn = event.currentTarget;
    const origInner = btn.innerHTML;
    btn.innerHTML = '<div class="spinner" style="width:14px;height:14px;border-width:2px"></div>';
    btn.disabled = true;

    try {
      // Busca dados de todos os holerites do mês
      const payrolls = await Promise.all(
        payrollIds.map(id => Api.request('GET', `/payroll/${id}`))
      );

      const win = window.open('', '_blank');
      if (!win) {
        toast('Permita pop-ups para imprimir.', 'error');
        return;
      }

      const rows = payrolls.map(p => {
        const items = (p.items || []);
        const credits  = items.filter(i => i.is_credit).map(i =>
          `<tr><td style="padding:4px 8px;font-size:12px">${i.description}</td><td style="padding:4px 8px;font-size:12px;text-align:right;color:#16a34a">+ ${fmtMoney(i.amount)}</td></tr>`
        ).join('');
        const discounts = items.filter(i => !i.is_credit).map(i =>
          `<tr><td style="padding:4px 8px;font-size:12px">${i.description}</td><td style="padding:4px 8px;font-size:12px;text-align:right;color:#dc2626">- ${fmtMoney(i.amount)}</td></tr>`
        ).join('');

        return `
          <div style="border:1px solid #e2e8f0;border-radius:8px;padding:20px;margin-bottom:20px;page-break-inside:avoid">
            <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:14px;padding-bottom:10px;border-bottom:2px solid #2563eb">
              <div>
                <div style="font-size:16px;font-weight:800;color:#1e293b">${p.employee_name || '—'}</div>
                <div style="font-size:12px;color:#64748b">${p.employee_role || ''}</div>
              </div>
              <div style="text-align:right">
                <div style="font-size:11px;color:#64748b">Competência</div>
                <div style="font-size:13px;font-weight:700">${String(p.competence_month).padStart(2,'0')}/${p.competence_year}</div>
              </div>
            </div>
            <table style="width:100%;border-collapse:collapse;margin-bottom:10px">
              ${credits}${discounts}
            </table>
            <div style="display:flex;justify-content:space-between;align-items:center;padding-top:10px;border-top:1px solid #e2e8f0">
              <span style="font-size:13px;font-weight:700;color:#1e293b">Salário Líquido</span>
              <span style="font-size:16px;font-weight:800;color:#16a34a">${fmtMoney(p.net_salary)}</span>
            </div>
          </div>`;
      }).join('');

      win.document.write(`<!DOCTYPE html><html><head>
        <meta charset="UTF-8">
        <title>Holerites — ${monthName} ${year}</title>
        <style>
          * { box-sizing: border-box; margin: 0; padding: 0; }
          body { font-family: 'Segoe UI', Arial, sans-serif; padding: 24px; background: #fff; color: #1e293b; }
          h1 { font-size: 18px; margin-bottom: 20px; color: #0f172a; }
          @media print {
            @page { margin: 15mm; }
            body { padding: 0; }
          }
        </style>
      </head><body>
        <h1>Holerites — ${monthName} / ${year}</h1>
        ${rows}
        <script>window.onload = function(){ window.print(); }<\/script>
      </body></html>`);
      win.document.close();

    } catch (err) {
      toast('Erro ao gerar impressão: ' + err.message, 'error');
    } finally {
      btn.innerHTML = origInner;
      btn.disabled = false;
    }
  }

  return { render, changeYear, printMonth };
})();
