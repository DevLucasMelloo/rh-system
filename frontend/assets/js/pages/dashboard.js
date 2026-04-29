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
        <div class="chart-title">Evolução do Custo Total (6 meses)</div>
        <canvas id="payroll-chart" height="90"></canvas>
      </div>

      <!-- Folha anual por funcionário -->
      <div class="card" style="margin-bottom:20px">
        <div class="card-header" style="display:flex;justify-content:space-between;align-items:center">
          <span>Folha Anual por Funcionário</span>
          <div style="display:flex;align-items:center;gap:12px;font-size:12px;color:var(--text-muted)">
            <span style="display:flex;align-items:center;gap:4px">
              <span style="display:inline-block;width:12px;height:12px;border-radius:2px;background:#fef08a;border:1px solid #ca8a04"></span>
              Aumento salarial
            </span>
            <span style="display:flex;align-items:center;gap:4px">
              <span style="display:inline-block;width:12px;height:12px;border-radius:2px;background:#fed7aa;border:1px solid #ea580c"></span>
              Aumento de auxílio
            </span>
          </div>
        </div>
        <div id="annual-table" style="overflow-x:auto;padding:0">
          <div style="padding:20px;text-align:center;color:var(--text-muted)">Carregando...</div>
        </div>
      </div>

      <!-- Bottom row 1: férias -->
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:20px">
        <div class="card">
          <div class="card-header" style="display:flex;align-items:center;gap:8px">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
            Férias Agendadas
          </div>
          <div id="scheduled-vacation-list" style="padding:8px 0">
            <div style="padding:16px 24px;color:var(--text-muted);font-size:13px">Carregando...</div>
          </div>
        </div>
        <div class="card">
          <div class="card-header" style="display:flex;align-items:center;gap:8px">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
            Em Férias
          </div>
          <div id="active-vacation-list" style="padding:8px 0">
            <div style="padding:16px 24px;color:var(--text-muted);font-size:13px">Carregando...</div>
          </div>
        </div>
      </div>

      <!-- Bottom row 2: vencidas + aniversariantes -->
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px">
        <div class="card">
          <div class="card-header" style="display:flex;align-items:center;gap:8px">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--warning)" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
            Férias — Vencidas e a Vencer
          </div>
          <div id="vacation-list" style="padding:8px 0">
            <div style="padding:16px 24px;color:var(--text-muted);font-size:13px">Carregando...</div>
          </div>
        </div>
        <div class="card">
          <div class="card-header" style="display:flex;align-items:center;gap:8px">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--success,#16a34a)" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
            <span id="birthday-header">Aniversariantes</span>
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
      renderScheduledVacations(d.scheduled_vacations || []);
      renderActiveVacations(d.active_vacations || []);
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

  function renderChart(d) {
    const ctx = document.getElementById('payroll-chart')?.getContext('2d');
    if (!ctx) return;
    if (chart) chart.destroy();

    const totals   = d.monthly_totals || [];
    const labels   = totals.map(t => MONTHS_SHORT[t.month - 1] + '/' + String(t.year).slice(2));
    const payroll  = totals.map(t => Number(t.payroll));
    const seam     = totals.map(t => Number(t.seamstress));
    const total    = totals.map(t => Number(t.total));

    const gradTotal = ctx.createLinearGradient(0, 0, 0, 280);
    gradTotal.addColorStop(0,   'rgba(37,99,235,0.25)');
    gradTotal.addColorStop(1,   'rgba(37,99,235,0.02)');

    const gradPayroll = ctx.createLinearGradient(0, 0, 0, 280);
    gradPayroll.addColorStop(0, 'rgba(16,185,129,0.20)');
    gradPayroll.addColorStop(1, 'rgba(16,185,129,0.02)');

    chart = new Chart(ctx, {
      type: 'line',
      data: {
        labels,
        datasets: [
          {
            label: 'Custo Total',
            data: total,
            borderColor: '#2563eb',
            backgroundColor: gradTotal,
            borderWidth: 2.5,
            pointBackgroundColor: '#2563eb',
            pointRadius: 4,
            pointHoverRadius: 6,
            tension: 0.4,
            fill: true,
            order: 1,
          },
          {
            label: 'Folha Líquida',
            data: payroll,
            borderColor: '#10b981',
            backgroundColor: gradPayroll,
            borderWidth: 2,
            pointBackgroundColor: '#10b981',
            pointRadius: 3,
            pointHoverRadius: 5,
            tension: 0.4,
            fill: true,
            order: 2,
            borderDash: [5, 3],
          },
          {
            label: 'Costureiras',
            data: seam,
            borderColor: '#f59e0b',
            backgroundColor: 'rgba(245,158,11,0.08)',
            borderWidth: 2,
            pointBackgroundColor: '#f59e0b',
            pointRadius: 3,
            pointHoverRadius: 5,
            tension: 0.4,
            fill: false,
            order: 3,
            borderDash: [3, 3],
          },
        ],
      },
      options: {
        responsive: true,
        interaction: { mode: 'index', intersect: false },
        plugins: {
          legend: {
            display: true,
            position: 'top',
            align: 'end',
            labels: { boxWidth: 12, boxHeight: 2, useBorderRadius: true, borderRadius: 2, font: { size: 12 }, color: '#64748b' },
          },
          tooltip: {
            backgroundColor: '#1e293b',
            titleColor: '#f1f5f9',
            bodyColor: '#cbd5e1',
            padding: 12,
            cornerRadius: 8,
            callbacks: {
              label: ctx => ` ${ctx.dataset.label}: ${fmt.brl(ctx.raw)}`,
            },
          },
        },
        scales: {
          y: {
            beginAtZero: true,
            ticks: {
              callback: v => v === 0 ? 'R$ 0' : 'R$ ' + (v >= 1000 ? (v/1000).toLocaleString('pt-BR', {maximumFractionDigits:1}) + 'k' : Number(v).toLocaleString('pt-BR')),
              color: '#94a3b8',
              font: { size: 11 },
            },
            grid: { color: '#f1f5f9' },
            border: { display: false },
          },
          x: {
            grid: { display: false },
            ticks: { color: '#94a3b8', font: { size: 12 } },
            border: { display: false },
          },
        },
      },
    });
  }

  function renderAnnualTable(data) {
    const el = document.getElementById('annual-table');
    if (!data || !data.employees || !data.employees.length) {
      el.innerHTML = `<div style="padding:20px;text-align:center;color:var(--text-muted);font-size:13px">Nenhuma folha fechada em ${data?.year || ''}.</div>`;
      return;
    }

    const year = data.year;
    const headerCells = MONTHS_SHORT.map(m =>
      `<th style="text-align:right;padding:8px 12px;font-weight:600;font-size:12px;color:var(--text-muted);white-space:nowrap">${m}</th>`
    ).join('');

    function fmtVal(v) {
      return Number(v).toLocaleString('pt-BR', { minimumFractionDigits: 0, maximumFractionDigits: 0 });
    }

    function monthCell(m, value, isIncrease, admMonth, admYear, color) {
      const beforeAdm = (year === admYear && m.month < admMonth) || year < admYear;
      if (beforeAdm) return `<td style="padding:8px 12px"></td>`;
      if (value === null || value === undefined)
        return `<td style="text-align:right;padding:8px 12px;color:var(--border)">—</td>`;
      const bg = isIncrease ? `background:${color}` : '';
      return `<td style="text-align:right;padding:8px 12px;font-size:13px;${bg}" title="${isIncrease ? 'Aumento' : ''}">${fmtVal(value)}</td>`;
    }

    const stickyStyle = 'padding:8px 12px;white-space:nowrap;font-size:13px;position:sticky;left:0;background:var(--card-bg);border-right:1px solid var(--border)';

    const rows = data.employees.map(emp => {
      const admMonth = emp.admission_month;
      const admYear  = emp.admission_year;

      const salCells = emp.months.map(m =>
        monthCell(m, m.gross_salary, m.is_salary_increase, admMonth, admYear, '#fef08a')
      ).join('');

      const auxCells = emp.months.map(m =>
        monthCell(m, m.auxilio, m.is_auxilio_increase, admMonth, admYear, '#fed7aa')
      ).join('');

      return `
        <tr style="border-top:1px solid var(--border)">
          <td style="${stickyStyle};font-weight:600">
            ${emp.name}
            <span style="font-weight:400;font-size:11px;color:var(--text-muted);margin-left:4px">salário</span>
          </td>
          ${salCells}
        </tr>
        <tr style="border-bottom:2px solid var(--border)">
          <td style="${stickyStyle};color:var(--text-muted)">
            ${emp.name}
            <span style="font-size:11px;margin-left:4px">auxílio</span>
          </td>
          ${auxCells}
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

  function renderScheduledVacations(list) {
    const el = document.getElementById('scheduled-vacation-list');
    if (!list.length) {
      el.innerHTML = `<div style="padding:16px 24px;color:var(--text-muted);font-size:13px">Nenhuma férias agendada.</div>`;
      return;
    }
    const fmtDate = d => { const [y, m, day] = d.split('-'); return `${day}/${m}/${y}`; };
    el.innerHTML = list.map(v => `
      <div style="display:flex;align-items:center;gap:12px;padding:10px 20px;border-radius:8px;
                  background:#eff6ff;border:1px solid #bfdbfe;margin:4px 16px">
        <div style="width:36px;height:36px;border-radius:50%;background:#fff;border:2px solid #bfdbfe;
                    display:flex;align-items:center;justify-content:center;flex-shrink:0;
                    font-size:13px;font-weight:700;color:#2563eb">${v.enjoyment_days}d</div>
        <div style="flex:1;min-width:0">
          <div style="font-weight:600;font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${v.employee_name}</div>
          <div style="font-size:11px;color:var(--text-muted);margin-top:1px">Início: ${fmtDate(v.enjoyment_start)}</div>
        </div>
        <div style="flex-shrink:0;text-align:right">
          <div style="font-size:11px;color:#2563eb;font-weight:600">${fmtDate(v.enjoyment_start)}</div>
          <div style="font-size:10px;color:var(--text-muted)">${v.enjoyment_days} dias</div>
        </div>
      </div>`).join('');
  }

  function renderActiveVacations(list) {
    const el = document.getElementById('active-vacation-list');
    if (!list.length) {
      el.innerHTML = `<div style="padding:16px 24px;color:var(--text-muted);font-size:13px">Nenhum funcionário em férias no momento.</div>`;
      return;
    }
    const fmtDate = d => { const [y, m, day] = d.split('-'); return `${day}/${m}/${y}`; };
    el.innerHTML = list.map(v => `
      <div style="display:flex;align-items:center;gap:12px;padding:10px 20px;border-radius:8px;
                  background:#eff6ff;border:1px solid #bfdbfe;margin:4px 16px">
        <div style="width:36px;height:36px;border-radius:50%;background:#fff;border:2px solid #bfdbfe;
                    display:flex;align-items:center;justify-content:center;flex-shrink:0">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="2.5">
            <path d="M3 17l4-8 4 4 4-6 4 10"/>
          </svg>
        </div>
        <div style="flex:1;min-width:0">
          <div style="font-weight:600;font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${v.employee_name}</div>
          <div style="font-size:11px;color:var(--text-muted);margin-top:1px">Em férias</div>
        </div>
        <div style="flex-shrink:0;text-align:right">
          <div style="font-size:11px;color:#2563eb;font-weight:600">${fmtDate(v.enjoyment_start)} → ${fmtDate(v.enjoyment_end)}</div>
        </div>
      </div>`).join('');
  }

  function renderVacationExpiring(list) {
    const el = document.getElementById('vacation-list');
    if (!list.length) {
      el.innerHTML = `<div style="padding:16px 24px;color:var(--text-muted);font-size:13px">Nenhuma férias vencida ou próxima de vencer.</div>`;
      return;
    }

    const fmtDate = d => {
      const [y, m, day] = d.split('-');
      return `${day}/${m}/${y}`;
    };

    el.innerHTML = list.map(v => {
      const expired = v.is_expired;
      const days    = Math.abs(v.days_until_expiry);

      const accentColor = expired ? 'var(--danger,#dc2626)' : 'var(--success,#16a34a)';
      const bgColor     = expired ? 'var(--danger-light,#fee2e2)' : 'var(--success-light,#dcfce7)';
      const borderColor = expired ? '#fca5a5' : '#86efac';

      const statusLabel = expired
        ? `<div style="font-size:11px;font-weight:700;color:${accentColor}">
             Venceu há ${days === 0 ? 'hoje' : days + 'd'}
           </div>
           <div style="font-size:10px;color:var(--text-muted)">${fmtDate(v.acquisition_end)}</div>`
        : days === 0
          ? `<div style="font-size:11px;font-weight:700;color:${accentColor}">Vence hoje!</div>`
          : `<div style="font-size:11px;color:var(--text-muted)">vence em <strong style="color:${accentColor}">${days}d</strong></div>
             <div style="font-size:10px;color:var(--text-muted)">${fmtDate(v.acquisition_end)}</div>`;

      const icon = expired
        ? `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="${accentColor}" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>`
        : `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="${accentColor}" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>`;

      return `
        <div style="display:flex;align-items:center;gap:12px;padding:10px 20px;border-radius:8px;
                    background:${bgColor};border:1px solid ${borderColor};
                    margin:4px 16px">
          <div style="width:36px;height:36px;border-radius:50%;background:#fff;border:2px solid ${borderColor};
                      display:flex;align-items:center;justify-content:center;flex-shrink:0">
            ${icon}
          </div>
          <div style="flex:1;min-width:0">
            <div style="font-weight:600;font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${v.employee_name}</div>
            ${v.role ? `<div style="font-size:11px;color:var(--text-muted);margin-top:1px">${v.role}</div>` : ''}
          </div>
          <div style="flex-shrink:0;text-align:right">${statusLabel}</div>
        </div>`;
    }).join('');
  }

  function renderBirthdays(list) {
    const el    = document.getElementById('birthday-list');
    const hdr   = document.getElementById('birthday-header');
    const MONTHS_PT = ['Janeiro','Fevereiro','Março','Abril','Maio','Junho',
                       'Julho','Agosto','Setembro','Outubro','Novembro','Dezembro'];
    const now   = new Date();
    if (hdr) hdr.textContent = `Aniversariantes — ${MONTHS_PT[now.getMonth()]}`;

    if (!list.length) {
      el.innerHTML = `<div style="padding:16px 24px;color:var(--text-muted);font-size:13px">Nenhum aniversariante este mês.</div>`;
      return;
    }

    el.innerHTML = list.map(b => {
      const isToday = b.days_until === 0;
      const isPast  = b.days_until < 0;
      const daysLabel = isToday
        ? `<span style="font-size:11px;font-weight:700;color:var(--success,#16a34a)">🎂 Hoje!</span>`
        : isPast
          ? `<span style="font-size:11px;color:var(--text-muted)">já passou</span>`
          : `<span style="font-size:11px;color:var(--text-muted)">faltam <strong style="color:var(--primary)">${b.days_until}d</strong></span>`;

      const role = b.role || '';
      return `
        <div style="display:flex;align-items:center;gap:12px;padding:10px 20px;border-radius:8px;
                    background:${isToday ? 'var(--success-light,#dcfce7)' : 'var(--bg-subtle,#f8f9fa)'};
                    margin:4px 16px;transition:background 0.2s">
          <div style="width:40px;height:40px;border-radius:50%;background:var(--success-light,#d1fae5);
                      border:2px solid var(--success,#16a34a);display:flex;align-items:center;
                      justify-content:center;flex-shrink:0">
            <span style="font-size:14px;font-weight:700;color:var(--success,#16a34a)">${b.birth_day}</span>
          </div>
          <div style="flex:1;min-width:0">
            <div style="font-weight:600;font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${b.name}</div>
            ${role ? `<div style="font-size:11px;color:var(--text-muted);margin-top:1px">${role}</div>` : ''}
          </div>
          <div style="flex-shrink:0;text-align:right">${daysLabel}</div>
        </div>`;
    }).join('');
  }

  return { render };
})();
