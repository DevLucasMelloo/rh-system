/**
 * Auditoria — Logs de ações do sistema com filtros e estatísticas.
 */
const PageAudit = (() => {
  const ACTION_CFG = {
    // Funcionários
    employee_created:          { label: 'Cadastro',           bg: '#dcfce7', color: '#16a34a' },
    employee_updated:          { label: 'Edição',             bg: '#ede9fe', color: '#7c3aed' },
    salary_change:             { label: 'Alteração Salarial', bg: '#ede9fe', color: '#7c3aed' },
    raise_applied:             { label: 'Aumento',            bg: '#ede9fe', color: '#7c3aed' },
    employee_inactivated:      { label: 'Inativação',         bg: '#fee2e2', color: '#dc2626' },
    employee_reactivated:      { label: 'Reativação',         bg: '#dcfce7', color: '#16a34a' },
    // Folha de Pagamento
    payroll_created:           { label: 'Folha Criada',       bg: '#f3e8ff', color: '#9333ea' },
    payroll_batch_created:     { label: 'Folha em Lote',      bg: '#f3e8ff', color: '#9333ea' },
    payroll_closed:            { label: 'Folha Fechada',      bg: '#f3e8ff', color: '#9333ea' },
    payroll_batch_closed:      { label: 'Folha Lote Fechada', bg: '#f3e8ff', color: '#9333ea' },
    payroll_deleted:           { label: 'Folha Excluída',     bg: '#fee2e2', color: '#dc2626' },
    // Vales
    vale_created:              { label: 'Vale',               bg: '#fef9c3', color: '#ca8a04' },
    vale_updated:              { label: 'Vale Editado',        bg: '#fef9c3', color: '#ca8a04' },
    vale_deleted:              { label: 'Vale Excluído',       bg: '#fef9c3', color: '#ca8a04' },
    // Férias
    vacation_scheduled:        { label: 'Férias Agendadas',   bg: '#ccfbf1', color: '#0d9488' },
    vacation_created:          { label: 'Férias Criadas',     bg: '#ccfbf1', color: '#0d9488' },
    vacation_updated:          { label: 'Férias Editadas',    bg: '#ccfbf1', color: '#0d9488' },
    vacation_started:          { label: 'Férias Iniciadas',   bg: '#ccfbf1', color: '#0d9488' },
    vacation_completed:        { label: 'Férias Concluídas',  bg: '#ccfbf1', color: '#0d9488' },
    vacation_cancelled:        { label: 'Férias Canceladas',  bg: '#ccfbf1', color: '#0d9488' },
    vacation_deleted:          { label: 'Férias Excluídas',   bg: '#fee2e2', color: '#dc2626' },
    // Rescisão
    termination_created:       { label: 'Rescisão',           bg: '#ffedd5', color: '#ea580c' },
    // Costureiras
    seamstress_created:        { label: 'Costureira Cadastro',bg: '#fce7f3', color: '#db2777' },
    seamstress_updated:        { label: 'Costureira Edição',  bg: '#fce7f3', color: '#db2777' },
    seamstress_payment_created:{ label: 'Pgto Costureira',    bg: '#fce7f3', color: '#db2777' },
    seamstress_payment_deleted:{ label: 'Pgto Excluído',      bg: '#fee2e2', color: '#dc2626' },
    seamstress_month_closed:   { label: 'Mês Costureira',     bg: '#fce7f3', color: '#db2777' },
    // Ponto
    timesheet_updated:         { label: 'Ponto Lançado',      bg: '#e0f2fe', color: '#0284c7' },
    timesheet_annulled:        { label: 'Ponto Anulado',      bg: '#fee2e2', color: '#dc2626' },
    timesheet_period_opened:   { label: 'Período Aberto',     bg: '#e0f2fe', color: '#0284c7' },
    timesheet_period_closed:   { label: 'Período Fechado',    bg: '#e0f2fe', color: '#0284c7' },
    // Usuários / Sistema
    user_created:              { label: 'Usuário Criado',     bg: '#f0fdf4', color: '#15803d' },
    user_updated:              { label: 'Usuário Editado',    bg: '#ede9fe', color: '#7c3aed' },
    password_reset:            { label: 'Senha Redefinida',   bg: '#fef9c3', color: '#ca8a04' },
    password_changed:          { label: 'Senha Alterada',     bg: '#fef9c3', color: '#ca8a04' },
    login:                     { label: 'Login',              bg: '#dbeafe', color: '#2563eb' },
    login_failed:              { label: 'Login Falhou',       bg: '#fee2e2', color: '#dc2626' },
    logout:                    { label: 'Logout',             bg: '#dbeafe', color: '#2563eb' },
  };

  const ENTITY_LABEL = {
    employee:           'Funcionários',
    payroll:            'Folha de Pagamento',
    vale:               'Vales',
    vacation:           'Férias',
    termination:        'Rescisão',
    seamstress:         'Costureiras',
    seamstress_payment: 'Pgto Costureira',
    timesheet:          'Ponto',
    timesheet_period:   'Período de Ponto',
    user:               'Usuários',
    system:             'Sistema',
  };

  function actionBadge(action) {
    const cfg = ACTION_CFG[action] || { label: action, bg: '#f1f5f9', color: '#64748b' };
    return `<span style="display:inline-block;padding:3px 10px;border-radius:20px;font-size:11px;font-weight:600;background:${cfg.bg};color:${cfg.color};white-space:nowrap">${cfg.label}</span>`;
  }

  function entityLabel(entity) {
    return ENTITY_LABEL[entity] || entity || 'Sistema';
  }

  function fmtDateTime(iso) {
    if (!iso) return '—';
    const d = new Date(iso);
    return d.toLocaleDateString('pt-BR') + ' ' + d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
  }

  let _filters = {};

  async function render(container) {
    container.innerHTML = `
      <div class="page-header" style="align-items:flex-start">
        <div style="display:flex;align-items:center;gap:10px">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="var(--primary)" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
          <div><h1>Logs de Auditoria</h1><p>Histórico de todas as ações realizadas no sistema</p></div>
        </div>
        <button class="btn btn-secondary" onclick="PageAudit.exportar()">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
          Exportar Excel
        </button>
      </div>

      <!-- Stats -->
      <div class="stats-grid" id="audit-stats" style="grid-template-columns:repeat(4,1fr);margin-bottom:20px">
        ${[1,2,3,4].map(() => `<div class="stat-card"><div style="height:40px;background:var(--border);border-radius:4px"></div></div>`).join('')}
      </div>

      <!-- Filtros -->
      <div class="card" style="margin-bottom:20px">
        <div class="card-header" style="display:flex;align-items:center;gap:6px">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/></svg>
          Filtros
        </div>
        <div style="padding:16px;display:grid;grid-template-columns:1fr 1fr;gap:12px">
          <div style="position:relative">
            <svg style="position:absolute;left:10px;top:50%;transform:translateY(-50%);color:var(--text-muted)" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
            <input class="form-control" id="audit-search" placeholder="Buscar..." style="padding-left:32px" oninput="PageAudit._applyFilters()">
          </div>
          <select class="form-control" id="audit-user" onchange="PageAudit._applyFilters()">
            <option value="">Todos os usuários</option>
          </select>
          <select class="form-control" id="audit-action" onchange="PageAudit._applyFilters()">
            <option value="">Todas as ações</option>
          </select>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px">
            <div style="position:relative">
              <svg style="position:absolute;left:8px;top:50%;transform:translateY(-50%);color:var(--text-muted)" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
              <input class="form-control" type="date" id="audit-date-start" style="padding-left:28px" onchange="PageAudit._applyFilters()">
            </div>
            <div style="position:relative">
              <svg style="position:absolute;left:8px;top:50%;transform:translateY(-50%);color:var(--text-muted)" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
              <input class="form-control" type="date" id="audit-date-end" style="padding-left:28px" onchange="PageAudit._applyFilters()">
            </div>
          </div>
        </div>
      </div>

      <!-- Tabela -->
      <div class="card">
        <div class="table-wrapper" style="border:none">
          <table>
            <thead>
              <tr>
                <th>Data/Hora</th><th>Usuário</th><th>Ação</th>
                <th>Módulo</th><th>Descrição</th><th></th>
              </tr>
            </thead>
            <tbody id="audit-tbody">${loadingRow(6)}</tbody>
          </table>
        </div>
      </div>`;

    await Promise.all([loadStats(), loadFilters(), loadLogs()]);
  }

  async function loadStats() {
    try {
      const s = await Api.getAuditStats();
      document.getElementById('audit-stats').innerHTML = `
        ${statCard('Total de Registros', s.total)}
        ${statCard('Usuários Ativos',    s.active_users)}
        ${statCard('Ações Hoje',         s.today)}
        ${statCard('Tipos de Ação',      s.action_types)}`;
    } catch {}
  }

  function statCard(label, value) {
    return `<div class="stat-card">
      <div class="stat-info"><h3>${label}</h3><div class="stat-value">${value ?? '—'}</div></div>
    </div>`;
  }

  async function loadFilters() {
    try {
      const [users, actions] = await Promise.all([Api.getAuditUsers(), Api.getAuditActions()]);
      const selUser = document.getElementById('audit-user');
      users.forEach(u => selUser.insertAdjacentHTML('beforeend', `<option value="${u.id}">${u.name}</option>`));

      const selAction = document.getElementById('audit-action');
      const seenLabels = new Set();
      actions.forEach(a => {
        const cfg = ACTION_CFG[a] || { label: a };
        const label = cfg.label;
        if (seenLabels.has(label)) return;
        seenLabels.add(label);
        // value: todos os action keys que compartilham esse label
        const keys = actions.filter(k => (ACTION_CFG[k]?.label || k) === label).join(',');
        selAction.insertAdjacentHTML('beforeend', `<option value="${keys}">${label}</option>`);
      });
    } catch {}
  }

  async function loadLogs() {
    const tbody = document.getElementById('audit-tbody');
    if (!tbody) return;
    try {
      const params = {
        search:     document.getElementById('audit-search')?.value     || undefined,
        user_id:    document.getElementById('audit-user')?.value       || undefined,
        actions:    document.getElementById('audit-action')?.value     || undefined,
        date_start: document.getElementById('audit-date-start')?.value || undefined,
        date_end:   document.getElementById('audit-date-end')?.value   || undefined,
      };
      const logs = await Api.getAuditLogs(params);
      if (!logs.length) {
        tbody.innerHTML = emptyRow('Nenhum registro encontrado.', 6);
        return;
      }
      tbody.innerHTML = logs.map(l => `
        <tr>
          <td style="white-space:nowrap;color:var(--text-muted);font-size:13px">${fmtDateTime(l.created_at)}</td>
          <td style="font-weight:600;font-size:13px">${l.user_name || 'Sistema'}</td>
          <td>${actionBadge(l.action)}</td>
          <td style="font-size:13px">${entityLabel(l.entity)}</td>
          <td style="font-size:13px;max-width:320px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${(l.description||'').replace(/"/g,"'")}">${l.description || '—'}</td>
          <td>
            ${l.description ? `<button class="btn-icon" title="Ver detalhes" onclick="PageAudit._detail(${JSON.stringify(l.description).replace(/'/g,'&apos;')}, '${fmtDateTime(l.created_at)}', '${(l.user_name||'Sistema').replace(/'/g,'&apos;')}')">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
            </button>` : ''}
          </td>
        </tr>`).join('');
    } catch (e) {
      tbody.innerHTML = `<tr><td colspan="6" style="padding:24px;text-align:center;color:var(--danger)">${e.message}</td></tr>`;
    }
  }

  const _applyFilters = debounce(() => loadLogs(), 300);

  function _detail(description, datetime, user) {
    openModal('Detalhes do Registro', `
      <div style="font-size:13px;display:flex;flex-direction:column;gap:12px">
        <div><span style="color:var(--text-muted);font-size:12px">Data/Hora</span><div style="font-weight:500;margin-top:2px">${datetime}</div></div>
        <div><span style="color:var(--text-muted);font-size:12px">Usuário</span><div style="font-weight:500;margin-top:2px">${user}</div></div>
        <div><span style="color:var(--text-muted);font-size:12px">Descrição</span><div style="margin-top:4px;background:var(--bg);padding:10px;border-radius:6px;line-height:1.5">${description}</div></div>
      </div>`, '');
  }

  async function exportar() {
    try {
      await Api.dlAuditLogs({
        search:     document.getElementById('audit-search')?.value     || undefined,
        user_id:    document.getElementById('audit-user')?.value       || undefined,
        actions:    document.getElementById('audit-action')?.value     || undefined,
        date_start: document.getElementById('audit-date-start')?.value || undefined,
        date_end:   document.getElementById('audit-date-end')?.value   || undefined,
      });
    } catch (e) { toast(e.message, 'error'); }
  }

  return { render, exportar, _applyFilters, _detail };
})();
