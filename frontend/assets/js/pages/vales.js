const PageVales = (() => {
  let allVales = [];
  let activeTab = 'open';
  let searchTerm = '';

  async function render(container) {
    container.innerHTML = `
      <div class="page-header">
        <div>
          <h1>Vales</h1>
          <p>Vales e adiantamentos com parcelamento automático</p>
        </div>
        <button class="btn btn-primary" onclick="PageVales.openNew()">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
          Novo Vale
        </button>
      </div>

      <div class="stats-grid" id="vale-stats" style="grid-template-columns:repeat(3,1fr)">
        <div class="stat-card"><p class="stat-label">Vales Ativos</p><p class="stat-value" id="s-active">—</p></div>
        <div class="stat-card">
          <p class="stat-label">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="vertical-align:-2px;margin-right:4px"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
            Saldo em Aberto
          </p>
          <p class="stat-value" id="s-pending" style="color:var(--danger)">—</p>
        </div>
        <div class="stat-card">
          <p class="stat-label">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="vertical-align:-2px;margin-right:4px"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
            Desconto Mensal
          </p>
          <p class="stat-value" id="s-monthly" style="color:var(--primary)">—</p>
        </div>
      </div>

      <div style="display:flex;gap:12px;align-items:center;margin-bottom:16px">
        <div class="search-box" style="flex:1;max-width:360px">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
          <input type="text" id="vale-search" class="form-control" placeholder="Buscar por funcionário..."
            style="padding-left:32px" oninput="PageVales.onSearch(this.value)">
        </div>
      </div>

      <div class="tab-group" style="margin-bottom:20px">
        <button class="tab-btn active" id="tab-open" onclick="PageVales.setTab('open')">Em Aberto (<span id="count-open">0</span>)</button>
        <button class="tab-btn" id="tab-paid" onclick="PageVales.setTab('paid')">Quitados (<span id="count-paid">0</span>)</button>
      </div>

      <div id="vale-cards"></div>`;

    await loadAll();
  }

  async function loadAll() {
    document.getElementById('vale-cards').innerHTML =
      '<div style="padding:40px;text-align:center"><div class="spinner spinner-dark"></div></div>';
    try {
      allVales = await Api.getAllVales() || [];
      renderStats();
      renderCards();
    } catch (e) {
      document.getElementById('vale-cards').innerHTML =
        `<div class="alert alert-error">${e.message}</div>`;
    }
  }

  function renderStats() {
    const now = new Date();
    const month = now.getMonth() + 1;
    const year  = now.getFullYear();

    const active  = allVales.filter(v => (v.installment_items || []).some(i => !i.is_paid)).length;
    const pending = allVales.reduce((sum, v) =>
      sum + (v.installment_items || []).filter(i => !i.is_paid)
              .reduce((s, i) => s + parseFloat(i.amount), 0), 0);
    const monthly = allVales.reduce((sum, v) =>
      sum + (v.installment_items || [])
              .filter(i => !i.is_paid && i.due_month === month && i.due_year === year)
              .reduce((s, i) => s + parseFloat(i.amount), 0), 0);

    document.getElementById('s-active').textContent  = active;
    document.getElementById('s-pending').textContent = fmt.brl(pending);
    document.getElementById('s-monthly').textContent = fmt.brl(monthly);
  }

  function renderCards() {
    const open   = [];
    const paid   = [];

    const term = searchTerm.toLowerCase();
    for (const v of allVales) {
      const name    = (v.employee_name || '').toLowerCase();
      if (term && !name.includes(term)) continue;
      const isPaid  = (v.installment_items || []).every(i => i.is_paid);
      isPaid ? paid.push(v) : open.push(v);
    }

    document.getElementById('count-open').textContent = open.length;
    document.getElementById('count-paid').textContent = paid.length;

    const list = activeTab === 'open' ? open : paid;

    if (!list.length) {
      document.getElementById('vale-cards').innerHTML =
        `<div style="text-align:center;padding:48px;color:var(--text-muted)">
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="margin-bottom:12px;opacity:.4"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>
          <p>${activeTab === 'open' ? 'Nenhum vale em aberto.' : 'Nenhum vale quitado.'}</p>
        </div>`;
      return;
    }

    document.getElementById('vale-cards').innerHTML = list.map(v => valeCard(v)).join('');
  }

  function valeCard(v) {
    const items     = v.installment_items || [];
    const paidCount = items.filter(i => i.is_paid).length;
    const total     = items.length;
    const pct       = total ? Math.round((paidCount / total) * 100) : 0;
    const isPaid    = items.length > 0 && paidCount === total;
    const restante  = items.filter(i => !i.is_paid).reduce((s, i) => s + parseFloat(i.amount), 0);
    const parcela   = v.installments > 0 ? parseFloat(v.total_amount) / v.installments : parseFloat(v.total_amount);

    const badge = isPaid
      ? `<span class="badge badge-success">Quitado</span>`
      : `<span style="display:inline-flex;align-items:center;gap:4px;padding:3px 10px;border-radius:20px;font-size:12px;font-weight:600;background:#fff8e6;color:#b45309;border:1px solid #fcd34d">
           <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
           Em aberto
         </span>`;

    return `
      <div class="card" style="margin-bottom:12px;padding:20px 24px;cursor:pointer" onclick="PageVales.openDetail(${v.id})">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:4px">
          <div>
            <span style="font-weight:700;font-size:15px">${v.employee_name || '—'}</span>
            ${badge}
          </div>
          <span style="color:var(--text-muted);font-size:12px">${fmt.date(v.issued_date)}</span>
        </div>
        ${v.notes ? `<p style="color:var(--text-muted);font-size:13px;margin:0 0 14px">${v.notes}</p>` : '<div style="height:14px"></div>'}
        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:14px">
          <div>
            <p style="font-size:11px;color:var(--text-muted);margin-bottom:2px">Total</p>
            <p style="font-weight:600;font-size:14px">${fmt.brl(v.total_amount)}</p>
          </div>
          <div>
            <p style="font-size:11px;color:var(--text-muted);margin-bottom:2px">Parcela</p>
            <p style="font-weight:600;font-size:14px">${fmt.brl(parcela)}</p>
          </div>
          <div>
            <p style="font-size:11px;color:var(--text-muted);margin-bottom:2px">Restante</p>
            <p style="font-weight:600;font-size:14px;color:${isPaid ? 'var(--success)' : 'var(--danger)'}">${fmt.brl(restante)}</p>
          </div>
        </div>
        <div>
          <div style="display:flex;justify-content:space-between;font-size:12px;color:var(--text-muted);margin-bottom:4px">
            <span>${paidCount}/${total} parcela${total !== 1 ? 's' : ''} paga${paidCount !== 1 ? 's' : ''}</span>
            <span>${pct}%</span>
          </div>
          <div style="height:6px;background:var(--border);border-radius:4px;overflow:hidden">
            <div style="height:100%;width:${pct}%;background:${isPaid ? 'var(--success)' : 'var(--primary)'};border-radius:4px;transition:width .3s"></div>
          </div>
        </div>
      </div>`;
  }

  function setTab(tab) {
    activeTab = tab;
    document.getElementById('tab-open').classList.toggle('active', tab === 'open');
    document.getElementById('tab-paid').classList.toggle('active', tab === 'paid');
    renderCards();
  }

  function onSearch(val) {
    searchTerm = val;
    renderCards();
  }

  async function openNew() {
    const empOpts = await employeeSelectOptions();
    const now = new Date();
    const MONTHS = ['Janeiro','Fevereiro','Março','Abril','Maio','Junho',
                    'Julho','Agosto','Setembro','Outubro','Novembro','Dezembro'];
    const monthOpts = MONTHS.map((name, i) => {
      const sel = (i + 1 === now.getMonth() + 1) ? 'selected' : '';
      return `<option value="${i+1}" ${sel}>${name}</option>`;
    }).join('');
    const yearOpts = [now.getFullYear(), now.getFullYear()+1].map(y =>
      `<option value="${y}" ${y === now.getFullYear() ? 'selected' : ''}>${y}</option>`
    ).join('');

    openModal('Novo Vale', `
      <div class="form-group"><label>Funcionário *</label>
        <select class="form-control" id="nv-emp"><option value="">Selecione...</option>${empOpts}</select>
      </div>
      <div class="form-row">
        <div class="form-group"><label>Valor Total *</label>
          <input class="form-control" type="number" step="0.01" min="0.01" id="nv-amount" placeholder="0,00">
        </div>
        <div class="form-group"><label>Nº de Parcelas</label>
          <select class="form-control" id="nv-installments">
            <option value="1">1x (à vista)</option>
            <option value="2">2x</option>
            <option value="3">3x</option>
            <option value="4">4x</option>
            <option value="6">6x</option>
            <option value="12">12x</option>
          </select>
        </div>
      </div>
      <div class="form-row">
        <div class="form-group"><label>Data de Emissão *</label>
          <input class="form-control" type="date" id="nv-date" value="${now.toISOString().split('T')[0]}">
        </div>
        <div class="form-group"><label>1º Desconto em *</label>
          <div style="display:flex;gap:6px">
            <select class="form-control" id="nv-first-month" style="flex:2">${monthOpts}</select>
            <select class="form-control" id="nv-first-year" style="flex:1">${yearOpts}</select>
          </div>
        </div>
      </div>
      <div class="form-group"><label>Observações</label>
        <input class="form-control" id="nv-notes" placeholder="Ex: Compra de uniforme, adiantamento salarial...">
      </div>
      <div id="nv-error"></div>`, `
      <button class="btn btn-secondary" onclick="closeModal()">Cancelar</button>
      <button class="btn btn-primary" onclick="PageVales.saveNew()">Registrar Vale</button>`);
  }

  async function saveNew() {
    const empId = parseInt(document.getElementById('nv-emp').value);
    if (!empId) {
      document.getElementById('nv-error').innerHTML = '<div class="alert alert-error">Selecione um funcionário.</div>';
      return;
    }
    const amount = parseFloat(document.getElementById('nv-amount').value);
    if (!amount || amount <= 0) {
      document.getElementById('nv-error').innerHTML = '<div class="alert alert-error">Informe um valor válido.</div>';
      return;
    }
    const data = {
      total_amount:      amount,
      installments:      parseInt(document.getElementById('nv-installments').value),
      issued_date:       document.getElementById('nv-date').value,
      notes:             document.getElementById('nv-notes').value.trim() || null,
      first_due_month:   parseInt(document.getElementById('nv-first-month').value),
      first_due_year:    parseInt(document.getElementById('nv-first-year').value),
    };
    try {
      await Api.createVale(empId, data);
      closeModal();
      toast('Vale registrado com sucesso!');
      await loadAll();
    } catch (e) {
      document.getElementById('nv-error').innerHTML = `<div class="alert alert-error">${e.message}</div>`;
    }
  }

  async function openDetail(id) {
    openModal('Detalhes do Vale', '<div style="padding:32px;text-align:center"><div class="spinner spinner-dark"></div></div>', '', true);
    try {
      const v = await Api.getVale(id);
      _renderDetail(v);
    } catch (e) {
      document.getElementById('modal-body').innerHTML = `<div class="alert alert-error">${e.message}</div>`;
    }
  }

  function _renderDetail(v) {
    const items     = v.installment_items || [];
    const paidCount = items.filter(i => i.is_paid).length;
    const restante  = items.filter(i => !i.is_paid).reduce((s, i) => s + parseFloat(i.amount), 0);
    const hasPaid   = paidCount > 0;

    const rows = items.map(inst => `
      <tr>
        <td style="font-weight:500">${inst.installment_number}ª parcela</td>
        <td>${fmt.brl(inst.amount)}</td>
        <td>${inst.due_month ? `${String(inst.due_month).padStart(2,'0')}/${inst.due_year}` : '—'}</td>
        <td>${inst.is_paid
          ? '<span class="badge badge-success">Pago</span>'
          : '<span class="badge badge-gray">Pendente</span>'}</td>
      </tr>`).join('') || '<tr><td colspan="4" style="text-align:center;padding:16px;color:var(--text-muted)">Sem parcelas.</td></tr>';

    document.getElementById('modal-body').innerHTML = `
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:20px">
        <div class="detail-item"><label>Funcionário</label><span style="font-weight:600">${v.employee_name || '—'}</span></div>
        <div class="detail-item"><label>Emissão</label><span>${fmt.date(v.issued_date)}</span></div>
        <div class="detail-item"><label>Valor Total</label><span style="font-weight:600">${fmt.brl(v.total_amount)}</span></div>
        <div class="detail-item"><label>Parcelas</label><span>${v.installments}x de ${fmt.brl(parseFloat(v.total_amount)/v.installments)}</span></div>
        <div class="detail-item"><label>Pagas</label><span>${paidCount}/${items.length}</span></div>
        <div class="detail-item"><label>Restante</label><span style="color:${restante > 0 ? 'var(--danger)' : 'var(--success)'};font-weight:600">${fmt.brl(restante)}</span></div>
        ${v.notes ? `<div class="detail-item" style="grid-column:1/-1"><label>Observação</label><span>${v.notes}</span></div>` : ''}
      </div>
      <div class="table-wrapper" style="border:none;margin:0">
        <table>
          <thead><tr><th>Parcela</th><th>Valor</th><th>Vencimento</th><th>Status</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>`;

    document.getElementById('modal-footer').innerHTML = `
      <button class="btn btn-danger" onclick="PageVales.confirmDelete(${v.id})" style="margin-right:auto"
        ${hasPaid ? 'disabled title="Possui parcelas já pagas em folha fechada"' : ''}>
        Excluir
      </button>
      <button class="btn btn-secondary" onclick="PageVales.openEdit(${v.id})">Editar</button>
      <button class="btn btn-secondary" onclick="closeModal()">Fechar</button>`;
  }

  function confirmDelete(id) {
    openModal('Excluir Vale', `
      <p>Tem certeza que deseja excluir este vale? Esta ação não pode ser desfeita.</p>
      <p style="margin-top:8px;color:var(--text-muted);font-size:13px">Apenas vales sem parcelas descontadas em folha fechada podem ser excluídos.</p>`,
      `<button class="btn btn-secondary" onclick="PageVales.openDetail(${id})">Cancelar</button>
       <button class="btn btn-danger" onclick="PageVales.doDelete(${id})">Excluir</button>`);
  }

  async function doDelete(id) {
    try {
      await Api.deleteVale(id);
      closeModal();
      toast('Vale excluído.');
      await loadAll();
    } catch (e) {
      toast(e.message, 'error');
    }
  }

  async function openEdit(id) {
    const v = await Api.getVale(id);
    const items = v.installment_items || [];
    const unpaid = items.filter(i => !i.is_paid);
    const now = new Date();
    const MONTHS = ['Janeiro','Fevereiro','Março','Abril','Maio','Junho',
                    'Julho','Agosto','Setembro','Outubro','Novembro','Dezembro'];

    // Mês/ano da primeira parcela pendente como padrão
    const firstUnpaid = unpaid.sort((a,b) => a.due_year - b.due_year || a.due_month - b.due_month)[0];
    const defMonth = firstUnpaid ? firstUnpaid.due_month : now.getMonth() + 1;
    const defYear  = firstUnpaid ? firstUnpaid.due_year  : now.getFullYear();

    const monthOpts = MONTHS.map((name, i) =>
      `<option value="${i+1}" ${i+1 === defMonth ? 'selected' : ''}>${name}</option>`
    ).join('');
    const years = [now.getFullYear() - 1, now.getFullYear(), now.getFullYear() + 1];
    const yearOpts = years.map(y =>
      `<option value="${y}" ${y === defYear ? 'selected' : ''}>${y}</option>`
    ).join('');

    openModal('Editar Vale', `
      <div class="form-group">
        <label>Observações</label>
        <input class="form-control" id="ev-notes" value="${v.notes || ''}" placeholder="Ex: Adiantamento salarial...">
      </div>
      ${unpaid.length > 0 ? `
      <div class="form-group">
        <label>Reagendar parcelas pendentes (1º desconto em)</label>
        <div style="display:flex;gap:6px">
          <select class="form-control" id="ev-month" style="flex:2">${monthOpts}</select>
          <select class="form-control" id="ev-year"  style="flex:1">${yearOpts}</select>
        </div>
        <p style="font-size:12px;color:var(--text-muted);margin-top:4px">${unpaid.length} parcela(s) pendente(s) serão redistribuídas a partir deste mês.</p>
      </div>` : '<p style="color:var(--text-muted)">Todas as parcelas já foram pagas.</p>'}
      <div id="ev-error"></div>`,
      `<button class="btn btn-secondary" onclick="PageVales.openDetail(${id})">Cancelar</button>
       <button class="btn btn-primary" onclick="PageVales.saveEdit(${id},${unpaid.length > 0})">Salvar</button>`);
  }

  async function saveEdit(id, hasUnpaid) {
    const body = {
      notes: document.getElementById('ev-notes').value.trim() || null,
    };
    if (hasUnpaid) {
      body.first_due_month = parseInt(document.getElementById('ev-month').value);
      body.first_due_year  = parseInt(document.getElementById('ev-year').value);
    }
    try {
      const v = await Api.updateVale(id, body);
      toast('Vale atualizado!');
      _renderDetail({...v, employee_name: v.employee_name});
    } catch (e) {
      const err = document.getElementById('ev-error');
      if (err) err.innerHTML = `<div class="alert alert-error">${e.message}</div>`;
      else toast(e.message, 'error');
    }
  }

  return { render, setTab, onSearch, openNew, saveNew, openDetail, confirmDelete, doDelete, openEdit, saveEdit };
})();
