/**
 * Dashboard — estatísticas gerais + gráfico de evolução + folha anual.
 */
const PageDashboard = (() => {
  const MONTHS_SHORT = ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez'];
  let chart = null;

  async function render(container) {
    container.innerHTML = `
      <div class="page-header">
        <div><h1>Dashboard</h1><p>Visão geral do sistema de RH</p></div>
      </div>

      <div class="stats-grid" id="stats-grid">
        ${statSkeleton()} ${statSkeleton()} ${statSkeleton()} ${statSkeleton()}
      </div>

      <div class="chart-container">
        <div class="chart-title">Evolução da Folha (6 meses)</div>
        <canvas id="payroll-chart" height="90"></canvas>
      </div>

      <!-- Folha anual por funcionário -->
      <div class="card" style="margin-bottom:20px">
        <div class="card-header" style="display:flex;justify-content:space-between;align-items:center">
          <span>Folha Anual por Funcionário</span>
          <div style="display:flex;align-items:center;gap:8px;font-size:12px;color:var(--text-muted)">
            <span style="display:inline-block;width:12px;height:12px;border-radius:2px;background:#fef08a;border:1px solid #ca8a04"></span>
            Aumento salarial
          </div>
        </div>
        <div id="annual-table" style="overflow-x:auto;padding:0">
          <div style="padding:20px;text-align:center;color:var(--text-muted)">Carregando...</div>
        </div>
      </div>

      <!-- Bottom row -->
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px">
        <div class="card">
          <div class="card-header" style="display:flex;align-items:center;gap:8px">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--warning)" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
            Férias Expirando (60 dias)
          </div>
          <div id="vacation-list" style="padding:8px 0">
            <div style="padding:16px 24px;color:var(--text-muted);font-size:13px">Carregando...</div>
          </div>
        </div>
        <div class="card">
          <div class="card-header" style="display:flex;align-items:center;gap:8px">
            🎂 Aniversários (30 dias)
          </div>
          <div id="birthday-list" style="padding:8px 0">
            <div style="padding:16px 24px;color:var(--text-muted);font-size:13px">Carregando...</div>
          </div>
        </div>
      </div>`;

    await loadData();
  }

  function statSkeleton() {
    return `<div class="stat-card"><div style="width:100%"><div style="height:12px;background:var(--border);border-radius:4px;width:60%;margin-bottom:12px"></div><div style="height:28px;background:var(--border);border-radius:4px;width:40%"></div></div></div>`;
  }

  async function loadData() {
    const year = new Date().getFullYear();
    try {
      const [d, annual] = await Promise.all([
        Api.getDashboard(),
        Api.getAnnualPayroll(year),
      ]);
      renderStats(d);
      renderChart(d);
      renderAnnualTable(annual);
      renderVacationExpiring(d.expiring_vacations || []);
      renderBirthdays(d.birthdays_next_30_days || []);
    } catch (e) {
      document.getElementById('stats-grid').innerHTML =
        `<div style="grid-column:1/-1"><div class="alert alert-error">Erro ao carregar dashboard: ${e.message}</div></div>`;
    }
  }

  function renderStats(d) {
    const m = fmt.month(d.current_month);
    const y = d.current_year;
    document.getElementById('stats-grid').innerHTML = `

      <!-- Funcionários Ativos -->
      <div class="stat-card" style="cursor:pointer" onclick="navigate('employees')" title="Ver Funcionários">
        <div class="stat-info">
          <h3>Funcionários Ativos</h3>
          <div class="stat-value">${d.active_employees}</div>
          <div class="stat-sub">+${d.new_hires_30_days} este mês</div>
        </div>
        <div class="stat-icon blue">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
        </div>
      </div>

      <!-- Folha de Pagamento -->
      <div class="stat-card" style="cursor:pointer" onclick="navigate('payroll')" title="Ver Folha de Pagamento">
        <div class="stat-info">
          <h3>Folha de Pagamento</h3>
          <div class="stat-value primary">${fmt.brl(d.total_net_salary)}</div>
          <div class="stat-sub">Competência ${m}/${y}${d.payrolls_draft > 0 ? ` · ${d.payrolls_draft} rascunho(s)` : ''}</div>
        </div>
        <div class="stat-icon blue">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="5" width="20" height="14" rx="2"/><line x1="2" y1="10" x2="22" y2="10"/></svg>
        </div>
      </div>

      <!-- Costureiras -->
      <div class="stat-card" style="cursor:pointer" onclick="navigate('seamstresses')" title="Ver Folha de Costureiras">
        <div class="stat-info">
          <h3>Costureiras ${m}/${y}</h3>
          <div class="stat-value primary">${fmt.brl(d.seamstress_total_month)}</div>
          <div class="stat-sub">${Number(d.seamstress_pending_month) > 0 ? `⚠ Pendente ${fmt.brl(d.seamstress_pending_month)}` : 'Tudo pago'}${Number(d.seamstress_entrega_month) > 0 ? ` · Entrega ${fmt.brl(d.seamstress_entrega_month)}` : ''}</div>
        </div>
        <div class="stat-icon ${Number(d.seamstress_pending_month) > 0 ? 'orange' : 'green'}">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><line x1="12" y1="3" x2="12" y2="9"/><line x1="12" y1="15" x2="12" y2="21"/><line x1="3" y1="12" x2="9" y2="12"/><line x1="15" y1="12" x2="21" y2="12"/></svg>
        </div>
      </div>

      <!-- Custo Total -->
      <div class="stat-card" style="cursor:pointer" onclick="navigate('payroll')" title="Folha + Costureiras">
        <div class="stat-info">
          <h3>Custo Total ${m}/${y}</h3>
          <div class="stat-value" style="color:var(--danger)">${fmt.brl(d.custo_total_month)}</div>
          <div class="stat-sub">Folha + Costureiras</div>
        </div>
        <div class="stat-icon orange">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>
        </div>
      </div>`;
  }

  async function renderChart(d) {
    const labels = [];
    const values = [];
    const now = new Date();
    for (let i = 5; i >= 0; i--) {
      const dt = new Date(now.getFullYear(), now.getMonth() - i, 1);
      labels.push(MONTHS_SHORT[dt.getMonth()] + '/' + String(dt.getFullYear()).slice(2));
      values.push(0);
    }
    values[5] = Number(d.total_net_salary || 0);

    const ctx = document.getElementById('payroll-chart')?.getContext('2d');
    if (!ctx) return;
    if (chart) chart.destroy();
    chart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels,
        datasets: [{
          label: 'Folha Líquida (R$)',
          data: values,
          backgroundColor: 'rgba(37,99,235,.15)',
          borderColor: '#2563eb',
          borderWidth: 2,
          borderRadius: 6,
        }]
      },
      options: {
        responsive: true,
        plugins: {
          legend: { display: false },
          tooltip: { callbacks: { label: ctx => fmt.brl(ctx.raw) } }
        },
        scales: {
          y: {
            ticks: { callback: v => 'R$ ' + Number(v).toLocaleString('pt-BR') },
            grid: { color: '#f1f5f9' }
          },
          x: { grid: { display: false } }
        }
      }
    });
  }

  function renderAnnualTable(data) {
    const el = document.getElementById('annual-table');
    if (!data || !data.employees || !data.employees.length) {
      el.innerHTML = `<div style="padding:20px;text-align:center;color:var(--text-muted);font-size:13px">Nenhuma folha fechada em ${data?.year || ''}.</div>`;
      return;
    }

    const headerCells = MONTHS_SHORT.map(m =>
      `<th style="text-align:right;padding:8px 12px;font-weight:600;font-size:12px;color:var(--text-muted);white-space:nowrap">${m}</th>`
    ).join('');

    const rows = data.employees.map(emp => {
      // Sublinhas: salário + auxílio (se tiver)
      const salaryCells = emp.months.map(m => {
        if (m.net_salary === null || m.net_salary === undefined) {
          return `<td style="text-align:right;padding:8px 12px;color:var(--border)">—</td>`;
        }
        const val = Number(m.net_salary).toLocaleString('pt-BR', { minimumFractionDigits: 0, maximumFractionDigits: 0 });
        const bg = m.is_salary_increase ? 'background:#fef08a' : '';
        return `<td style="text-align:right;padding:8px 12px;font-size:13px;${bg}" title="${m.is_salary_increase ? 'Aumento salarial' : ''}">${val}</td>`;
      }).join('');

      return `<tr>
        <td style="padding:8px 12px;white-space:nowrap;font-weight:600;font-size:13px;position:sticky;left:0;background:var(--card-bg);border-right:1px solid var(--border)">
          ${emp.name}
          <span style="font-weight:400;font-size:11px;color:var(--text-muted);margin-left:4px">salário</span>
        </td>
        ${salaryCells}
      </tr>`;
    }).join('');

    el.innerHTML = `
      <table style="width:100%;border-collapse:collapse;min-width:700px">
        <thead>
          <tr style="border-bottom:2px solid var(--border)">
            <th style="text-align:left;padding:8px 12px;font-size:12px;color:var(--text-muted);position:sticky;left:0;background:var(--card-bg)">Funcionário</th>
            ${headerCells}
          </tr>
        </thead>
        <tbody>
          ${rows}
        </tbody>
      </table>`;
  }

  function renderVacationExpiring(list) {
    const el = document.getElementById('vacation-list');
    if (!list.length) {
      el.innerHTML = `<div style="padding:16px 24px;color:var(--text-muted);font-size:13px">Nenhuma férias expirando.</div>`;
      return;
    }
    el.innerHTML = `<ul class="items-list" style="padding:0 24px">
      ${list.map(v => `
        <li>
          <span>${v.employee_name}</span>
          <span class="badge badge-warning">Vence em ${v.days_until_expiry}d</span>
        </li>`).join('')}
    </ul>`;
  }

  function renderBirthdays(list) {
    const el = document.getElementById('birthday-list');
    if (!list.length) {
      el.innerHTML = `<div style="padding:16px 24px;color:var(--text-muted);font-size:13px">Nenhum aniversário nos próximos 30 dias.</div>`;
      return;
    }
    el.innerHTML = `<ul class="items-list" style="padding:0 24px">
      ${list.map(b => `
        <li>
          <span>${b.name}</span>
          <span class="badge badge-primary">${b.days_until === 0 ? '🎂 Hoje!' : `em ${b.days_until}d`}</span>
        </li>`).join('')}
    </ul>`;
  }

  return { render };
})();
