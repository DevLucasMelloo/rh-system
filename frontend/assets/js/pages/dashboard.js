/**
 * Dashboard — estatísticas gerais + gráfico de evolução de folha.
 */
const PageDashboard = (() => {
  let chart = null;

  async function render(container) {
    container.innerHTML = `
      <div class="page-header">
        <div>
          <h1>Dashboard</h1>
          <p>Visão geral do sistema de RH</p>
        </div>
      </div>

      <!-- Stats -->
      <div class="stats-grid" id="stats-grid">
        ${statSkeleton()} ${statSkeleton()} ${statSkeleton()} ${statSkeleton()} ${statSkeleton()}
      </div>

      <!-- Chart -->
      <div class="chart-container">
        <div class="chart-title">Evolução da Folha (6 meses)</div>
        <canvas id="payroll-chart" height="90"></canvas>
      </div>

      <!-- Bottom row -->
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px">
        <!-- Férias expirando -->
        <div class="card">
          <div class="card-header" style="display:flex;align-items:center;gap:8px">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--warning)" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
            Férias Expirando (60 dias)
          </div>
          <div id="vacation-list" style="padding:8px 0">
            <div style="padding:16px 24px;color:var(--text-muted);font-size:13px">Carregando...</div>
          </div>
        </div>

        <!-- Aniversários -->
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
    try {
      const d = await Api.getDashboard();
      renderStats(d);
      renderChart(d);
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
      <div class="stat-card">
        <div class="stat-info">
          <h3>Funcionários Ativos</h3>
          <div class="stat-value">${d.active_employees}</div>
          <div class="stat-sub">+${d.new_hires_30_days} este mês</div>
        </div>
        <div class="stat-icon blue">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-info">
          <h3>Folha de Pagamento</h3>
          <div class="stat-value primary">${fmt.brl(d.total_net_salary)}</div>
          <div class="stat-sub">Competência ${m}/${y}</div>
        </div>
        <div class="stat-icon blue">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="5" width="20" height="14" rx="2"/><line x1="2" y1="10" x2="22" y2="10"/></svg>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-info">
          <h3>Horas Extras (mês)</h3>
          <div class="stat-value">${Number(d.total_overtime_hours_month || 0).toFixed(1)}h</div>
          <div class="stat-sub">${d.total_absences_month} falta(s) registrada(s)</div>
        </div>
        <div class="stat-icon green">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-info">
          <h3>Férias Vencidas</h3>
          <div class="stat-value ${d.vacations_expiring_60d > 0 ? 'warning' : ''}">${d.vacations_expiring_60d}</div>
          <div class="stat-sub">${d.vacations_active} em gozo | ${d.vacations_scheduled} agendadas</div>
        </div>
        <div class="stat-icon ${d.vacations_expiring_60d > 0 ? 'orange' : 'green'}">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/></svg>
        </div>
      </div>
      <div class="stat-card" style="cursor:pointer" onclick="navigate('seamstresses')" title="Ver Folha de Costureiras">
        <div class="stat-info">
          <h3>Costureiras ${m}/${y}</h3>
          <div class="stat-value primary">${fmt.brl(d.seamstress_total_month)}</div>
          <div class="stat-sub">${Number(d.seamstress_pending_month) > 0 ? `⚠ Pendente ${fmt.brl(d.seamstress_pending_month)}` : 'Tudo pago'}${Number(d.seamstress_entrega_month) > 0 ? ` · Entrega ${fmt.brl(d.seamstress_entrega_month)}` : ''}</div>
        </div>
        <div class="stat-icon ${Number(d.seamstress_pending_month) > 0 ? 'orange' : 'green'}">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><line x1="12" y1="3" x2="12" y2="9"/><line x1="12" y1="15" x2="12" y2="21"/><line x1="3" y1="12" x2="9" y2="12"/><line x1="15" y1="12" x2="21" y2="12"/></svg>
        </div>
      </div>`;
  }

  async function renderChart(d) {
    // Build last 6 months labels
    const labels = [];
    const values = [];
    const now = new Date();
    for (let i = 5; i >= 0; i--) {
      const dt = new Date(now.getFullYear(), now.getMonth() - i, 1);
      labels.push(fmt.month(dt.getMonth()+1) + '/' + String(dt.getFullYear()).slice(2));
      values.push(0); // placeholder — could fetch per month
    }
    // Use current month value
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
          tooltip: {
            callbacks: { label: ctx => fmt.brl(ctx.raw) }
          }
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
