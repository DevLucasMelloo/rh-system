const PageSeamstresses = (() => {
  let all = [];
  let activeTab = 'ativas';
  let search = '';

  const MONTHS = ['Janeiro','Fevereiro','Março','Abril','Maio','Junho','Julho','Agosto','Setembro','Outubro','Novembro','Dezembro'];

  function monthOptions(selMonth, selYear) {
    const now = new Date();
    let html = '';
    for (let i = 0; i < 12; i++) {
      const m = i + 1;
      const y = now.getFullYear();
      const sel = (m === selMonth && y === selYear) ? 'selected' : '';
      html += `<option value="${m}|${y}" ${sel}>${MONTHS[i]}/${y}</option>`;
    }
    // previous year
    for (let i = 0; i < 12; i++) {
      const m = i + 1;
      const y = now.getFullYear() - 1;
      const sel = (m === selMonth && y === selYear) ? 'selected' : '';
      html += `<option value="${m}|${y}" ${sel}>${MONTHS[i]}/${y}</option>`;
    }
    return html;
  }

  async function render(container) {
    const now = new Date();
    container.innerHTML = `
      <div class="page-header">
        <div><h1>Costureiras</h1><p>Cadastro e pagamentos</p></div>
        <button class="btn btn-primary" id="btn-new-sea" onclick="PageSeamstresses.openNew()">+ Nova Costureira</button>
      </div>
      <div class="tab-bar" style="margin-bottom:16px">
        <button class="tab-btn active" id="tab-ativas"  onclick="PageSeamstresses.switchTab('ativas')">Ativas</button>
        <button class="tab-btn"        id="tab-inativas" onclick="PageSeamstresses.switchTab('inativas')">Inativas</button>
        <button class="tab-btn"        id="tab-folha"   onclick="PageSeamstresses.switchTab('folha')">Folha Mensal</button>
      </div>

      <!-- Ativas / Inativas -->
      <div id="sea-list-view">
        <div class="toolbar" style="margin-bottom:12px">
          <div class="search-box">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
            <input type="text" class="form-control" id="sea-search" placeholder="Buscar costureira..."
                   oninput="PageSeamstresses.onSearch(this.value)">
          </div>
        </div>
        <div class="table-wrapper">
          <table>
            <thead><tr><th>Nome</th><th>CPF</th><th>Telefone</th><th>Endereço</th><th></th></tr></thead>
            <tbody id="sea-tbody">${loadingRow(5)}</tbody>
          </table>
        </div>
      </div>

      <!-- Folha Mensal -->
      <div id="sea-folha-view" class="hidden">
        <div style="display:flex;gap:12px;align-items:center;margin-bottom:16px;flex-wrap:wrap">
          <select class="form-control" id="folha-period" style="width:200px" onchange="PageSeamstresses.loadFolha()">
            ${monthOptions(now.getMonth()+1, now.getFullYear())}
          </select>
          <button class="btn btn-primary" id="btn-fechar-mes" onclick="PageSeamstresses.openCloseMonth()">Fechar Mês</button>
        </div>
        <div id="folha-content">${loadingRow(5)}</div>
      </div>`;

    await load();
  }

  async function load() {
    try {
      all = await Api.getAllSeamstresses() || [];
      renderTable();
    } catch (e) {
      const tb = document.getElementById('sea-tbody');
      if (tb) tb.innerHTML = emptyRow(e.message, 5);
    }
  }

  function switchTab(tab) {
    activeTab = tab;
    ['ativas','inativas','folha'].forEach(t => {
      document.getElementById(`tab-${t}`)?.classList.toggle('active', t === tab);
    });
    const listView  = document.getElementById('sea-list-view');
    const folhaView = document.getElementById('sea-folha-view');
    const btnNew    = document.getElementById('btn-new-sea');
    if (tab === 'folha') {
      listView?.classList.add('hidden');
      folhaView?.classList.remove('hidden');
      if (btnNew) btnNew.style.display = 'none';
      loadFolha();
    } else {
      listView?.classList.remove('hidden');
      folhaView?.classList.add('hidden');
      if (btnNew) btnNew.style.display = '';
      renderTable();
    }
  }

  const onSearch = debounce(q => { search = q; renderTable(); });

  function renderTable() {
    const tb = document.getElementById('sea-tbody');
    if (!tb) return;
    let list = all.filter(s => activeTab === 'ativas' ? s.is_active : !s.is_active);
    if (search) {
      const q = search.toLowerCase();
      list = list.filter(s => s.name.toLowerCase().includes(q));
    }
    if (!list.length) {
      tb.innerHTML = emptyRow(activeTab === 'ativas' ? 'Nenhuma costureira ativa.' : 'Nenhuma costureira inativa.', 5);
      return;
    }
    tb.innerHTML = list.map(s => `
      <tr>
        <td><strong>${esc(s.name)}</strong></td>
        <td style="color:var(--text-muted)">${fmtCpf(s.cpf)}</td>
        <td>${esc(s.phone) || '—'}</td>
        <td>${esc(s.address) || '—'}</td>
        <td class="td-actions">
          <div class="dropdown">
            <button class="btn-icon" onclick="toggleDropdown('sdd-${s.id}')">⋮</button>
            <div class="dropdown-menu" id="sdd-${s.id}">
              ${s.is_active ? `<button class="dropdown-item" onclick="PageSeamstresses.openPayments(${s.id},'${esc(s.name)}')">Ver Pagamentos</button>
              <button class="dropdown-item" onclick="PageSeamstresses.openNewPayment(${s.id},'${esc(s.name)}')">Lançar Pagamento</button>` : ''}
              <button class="dropdown-item" onclick="PageSeamstresses.openEdit(${s.id})">Editar</button>
              ${s.is_active
                ? `<button class="dropdown-item text-danger" onclick="PageSeamstresses.toggleActive(${s.id},false)">Inativar</button>`
                : `<button class="dropdown-item text-success" onclick="PageSeamstresses.toggleActive(${s.id},true)">Reativar</button>`}
            </div>
          </div>
        </td>
      </tr>`).join('');
  }

  // ── Folha Mensal ────────────────────────────────────────────────────────────

  async function loadFolha() {
    const sel = document.getElementById('folha-period');
    if (!sel) return;
    const [month, year] = sel.value.split('|').map(Number);
    const content = document.getElementById('folha-content');
    content.innerHTML = `<div style="padding:20px;text-align:center"><div class="spinner spinner-dark"></div></div>`;
    try {
      const r = await Api.getSeamstressMonthReport(month, year);
      renderFolha(r);
    } catch (e) {
      content.innerHTML = `<div class="alert alert-error">${e.message}</div>`;
    }
  }

  function renderFolha(r) {
    const hasPending = r.seamstresses.some(s => s.status === 'pendente' && s.mensal_amount > 0);
    const btn = document.getElementById('btn-fechar-mes');
    if (btn) btn.style.display = hasPending ? '' : 'none';

    const rows = r.seamstresses.length ? r.seamstresses.map(s => `
      <tr>
        <td><strong>${esc(s.seamstress_name)}</strong></td>
        <td>${fmt.brl(s.mensal_amount) || '—'}</td>
        <td>${fmt.brl(s.entrega_amount) || '—'}</td>
        <td><span class="badge ${s.status === 'pago' ? 'badge-success' : 'badge-warning'}">${s.status === 'pago' ? 'Pago' : 'Pendente'}</span></td>
        <td>${s.payment_date ? fmt.date(s.payment_date) : '—'}</td>
      </tr>`).join('') : `<tr><td colspan="5" style="text-align:center;color:var(--text-muted);padding:24px">Nenhum lançamento nesta competência.</td></tr>`;

    document.getElementById('folha-content').innerHTML = `
      <div class="table-wrapper">
        <table>
          <thead><tr><th>Costureira</th><th>Valor Mensal</th><th>Entregas no Mês</th><th>Status</th><th>Data Pag.</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
      <div style="display:flex;gap:24px;margin-top:16px;flex-wrap:wrap">
        <div class="stat-card" style="flex:1;min-width:160px">
          <div class="stat-info"><h3>Mensal Pendente</h3><div class="stat-value warning">${fmt.brl(r.total_mensal_pendente)}</div></div>
        </div>
        <div class="stat-card" style="flex:1;min-width:160px">
          <div class="stat-info"><h3>Mensal Pago</h3><div class="stat-value">${fmt.brl(r.total_mensal_pago)}</div></div>
        </div>
        <div class="stat-card" style="flex:1;min-width:160px">
          <div class="stat-info"><h3>Entregas (Pago)</h3><div class="stat-value">${fmt.brl(r.total_entrega)}</div></div>
        </div>
        <div class="stat-card" style="flex:1;min-width:160px">
          <div class="stat-info"><h3>Total Geral</h3><div class="stat-value primary">${fmt.brl(r.total_geral)}</div></div>
        </div>
      </div>`;
  }

  function openCloseMonth() {
    const sel = document.getElementById('folha-period');
    const [month, year] = sel.value.split('|').map(Number);
    const monthName = MONTHS[month - 1];
    const nextMonth = month === 12 ? 1 : month + 1;
    const nextYear  = month === 12 ? year + 1 : year;
    const payDate   = `${nextYear}-${String(nextMonth).padStart(2,'0')}-05`;

    openModal(`Fechar Mês — ${monthName}/${year}`, `
      <p style="margin-bottom:16px">Todos os pagamentos mensais <strong>pendentes</strong> da competência <strong>${monthName}/${year}</strong> serão marcados como <strong>pagos</strong>.</p>
      <div class="form-group">
        <label>Data de Pagamento</label>
        <input class="form-control" type="date" id="close-paydate" value="${payDate}">
      </div>
      <div id="close-error"></div>`, `
      <button class="btn btn-secondary" onclick="closeModal()">Cancelar</button>
      <button class="btn btn-primary" onclick="PageSeamstresses.confirmCloseMonth(${month},${year})">Confirmar Fechamento</button>`);
  }

  async function confirmCloseMonth(month, year) {
    const payDate = document.getElementById('close-paydate').value;
    if (!payDate) { document.getElementById('close-error').innerHTML = '<div class="alert alert-error">Informe a data de pagamento.</div>'; return; }
    try {
      const r = await Api.closeSeamstressMonth({ competence_month: month, competence_year: year, payment_date: payDate });
      closeModal();
      toast(`${r.closed} costureira(s) pagas em ${fmt.date(r.payment_date)}!`);
      loadFolha();
    } catch (e) {
      document.getElementById('close-error').innerHTML = `<div class="alert alert-error">${e.message}</div>`;
    }
  }

  // ── Cadastro ────────────────────────────────────────────────────────────────

  function esc(v) {
    if (!v) return '';
    return String(v).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }

  function fmtCpf(v) {
    if (!v) return '—';
    const d = String(v).replace(/\D/g,'');
    if (d.length !== 11) return v;
    return d.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, '$1.$2.$3-$4');
  }

  function seamstressForm(s = {}) {
    const cpfVal = s.cpf ? fmtCpf(s.cpf) : '';
    return `
      <div class="form-row">
        <div class="form-group"><label>Nome *</label><input class="form-control" id="sf-name" value="${esc(s.name||'')}"></div>
        <div class="form-group"><label>CPF</label><input class="form-control" id="sf-cpf" maxlength="14" placeholder="000.000.000-00" oninput="applyCpfMask(this)" value="${cpfVal}"></div>
      </div>
      <div class="form-row">
        <div class="form-group"><label>Telefone</label><input class="form-control" id="sf-phone" value="${esc(s.phone||'')}"></div>
        <div class="form-group"><label>Endereço</label><input class="form-control" id="sf-address" value="${esc(s.address||'')}"></div>
      </div>
      <div id="sf-error"></div>`;
  }

  function collectSeamstressForm() {
    return {
      name: document.getElementById('sf-name').value.trim(),
      cpf: document.getElementById('sf-cpf').value.replace(/\D/g,'') || null,
      phone: document.getElementById('sf-phone').value.trim() || null,
      address: document.getElementById('sf-address').value.trim() || null,
    };
  }

  function openNew() {
    openModal('Nova Costureira', seamstressForm(), `
      <button class="btn btn-secondary" onclick="closeModal()">Cancelar</button>
      <button class="btn btn-primary" onclick="PageSeamstresses.saveNew()">Salvar</button>`);
  }

  async function saveNew() {
    const data = collectSeamstressForm();
    if (!data.name) { document.getElementById('sf-error').innerHTML = '<div class="alert alert-error">Nome é obrigatório.</div>'; return; }
    try {
      await Api.createSeamstress(data);
      closeModal(); toast('Costureira cadastrada!'); await load();
    } catch (e) {
      document.getElementById('sf-error').innerHTML = `<div class="alert alert-error">${e.message}</div>`;
    }
  }

  function openEdit(id) {
    const s = all.find(x => x.id === id);
    if (!s) return;
    openModal('Editar Costureira', seamstressForm(s), `
      <button class="btn btn-secondary" onclick="closeModal()">Cancelar</button>
      <button class="btn btn-primary" onclick="PageSeamstresses.saveEdit(${id})">Salvar</button>`);
  }

  async function saveEdit(id) {
    const data = collectSeamstressForm();
    if (!data.name) { document.getElementById('sf-error').innerHTML = '<div class="alert alert-error">Nome é obrigatório.</div>'; return; }
    try {
      await Api.updateSeamstress(id, data);
      closeModal(); toast('Costureira atualizada!'); await load();
    } catch (e) {
      document.getElementById('sf-error').innerHTML = `<div class="alert alert-error">${e.message}</div>`;
    }
  }

  async function toggleActive(id, activate) {
    try {
      await Api.updateSeamstress(id, { is_active: activate });
      toast(activate ? 'Costureira reativada!' : 'Costureira inativada!');
      await load();
    } catch (e) { toast(e.message, 'error'); }
  }

  // ── Pagamentos ──────────────────────────────────────────────────────────────

  async function openPayments(id, name) {
    openModal(`Pagamentos — ${esc(name)}`,
      '<div style="padding:20px;text-align:center"><div class="spinner spinner-dark"></div></div>',
      `<button class="btn btn-secondary" onclick="closeModal()">Fechar</button>
       <button class="btn btn-primary" onclick="PageSeamstresses.openNewPayment(${id},'${esc(name)}')">+ Lançar Pagamento</button>`,
      true);
    await _renderPaymentList(id, name);
  }

  async function _renderPaymentList(id, name) {
    try {
      const payments = await Api.getSeamstressPayments(id) || [];
      const rows = payments.length ? payments.map(p => {
        const typeBadge = p.payment_type === 'mensal'
          ? '<span class="badge badge-primary">Mensal</span>'
          : '<span class="badge" style="background:var(--text-muted);color:#fff">Entrega</span>';
        const stBadge = p.status === 'pago'
          ? '<span class="badge badge-success">Pago</span>'
          : '<span class="badge badge-warning">Pendente</span>';
        const period = p.payment_type === 'mensal' && p.competence_month
          ? `${String(p.competence_month).padStart(2,'0')}/${p.competence_year}`
          : (p.payment_date ? fmt.date(p.payment_date) : '—');
        return `<tr>
          <td>${typeBadge}</td>
          <td>${period}</td>
          <td>${fmt.brl(p.amount)}</td>
          <td>${stBadge}</td>
          <td>${p.payment_date ? fmt.date(p.payment_date) : '—'}</td>
          <td>${esc(p.notes) || '—'}</td>
          <td>
            ${p.status === 'pendente' ? `<button class="btn-icon" style="color:var(--danger)" title="Excluir" onclick="PageSeamstresses.deletePayment(${p.id},${id},'${esc(name)}')">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4h6v2"/></svg>
            </button>` : ''}
          </td>
        </tr>`;
      }).join('') : emptyRow('Nenhum pagamento.', 7);
      document.getElementById('modal-body').innerHTML = `
        <div class="table-wrapper"><table>
          <thead><tr><th>Tipo</th><th>Competência/Data</th><th>Valor</th><th>Status</th><th>Pago em</th><th>Obs.</th><th></th></tr></thead>
          <tbody>${rows}</tbody>
        </table></div>`;
    } catch (e) {
      if (document.getElementById('modal-body'))
        document.getElementById('modal-body').innerHTML = `<div class="alert alert-error">${e.message}</div>`;
    }
  }

  function openNewPayment(id, name) {
    const now = new Date();
    const curMonth = now.getMonth() + 1;
    const curYear = now.getFullYear();
    const today = now.toISOString().split('T')[0];
    openModal(`Lançar Pagamento — ${esc(name)}`, `
      <div class="form-group">
        <label>Tipo de Pagamento</label>
        <select class="form-control" id="pay-type" onchange="PageSeamstresses._togglePayType()">
          <option value="mensal">Mensal (fechamento)</option>
          <option value="entrega">Na Entrega (pago imediatamente)</option>
        </select>
      </div>
      <div id="pay-mensal-fields">
        <div class="form-group">
          <label>Competência</label>
          <select class="form-control" id="pay-period">${monthOptions(curMonth, curYear)}</select>
        </div>
      </div>
      <div id="pay-entrega-fields" class="hidden">
        <div class="form-group">
          <label>Data do Pagamento *</label>
          <input class="form-control" type="date" id="pay-date" value="${today}">
        </div>
      </div>
      <div class="form-group">
        <label>Valor (R$) *</label>
        <input class="form-control" type="number" step="0.01" min="0.01" id="pay-amount" placeholder="0,00">
      </div>
      <div class="form-group">
        <label>Observações</label>
        <input class="form-control" id="pay-notes" placeholder="Opcional">
      </div>
      <div id="pay-error"></div>`, `
      <button class="btn btn-secondary" onclick="PageSeamstresses.openPayments(${id},'${esc(name)}')">Voltar</button>
      <button class="btn btn-primary" onclick="PageSeamstresses.savePayment(${id},'${esc(name)}')">Salvar</button>`);
  }

  function _togglePayType() {
    const type = document.getElementById('pay-type').value;
    document.getElementById('pay-mensal-fields').classList.toggle('hidden', type !== 'mensal');
    document.getElementById('pay-entrega-fields').classList.toggle('hidden', type !== 'entrega');
  }

  async function savePayment(id, name) {
    const type   = document.getElementById('pay-type').value;
    const amount = parseFloat(document.getElementById('pay-amount').value);
    const notes  = document.getElementById('pay-notes').value.trim() || null;
    if (!amount || amount <= 0) { document.getElementById('pay-error').innerHTML = '<div class="alert alert-error">Informe um valor válido.</div>'; return; }

    let body = { payment_type: type, amount, notes };

    if (type === 'mensal') {
      const [m, y] = document.getElementById('pay-period').value.split('|').map(Number);
      body.competence_month = m;
      body.competence_year  = y;
    } else {
      const dt = document.getElementById('pay-date').value;
      if (!dt) { document.getElementById('pay-error').innerHTML = '<div class="alert alert-error">Informe a data de pagamento.</div>'; return; }
      body.payment_date = dt;
    }

    try {
      await Api.createPayment(id, body);
      toast('Pagamento lançado!');
      openPayments(id, name);
    } catch (e) {
      document.getElementById('pay-error').innerHTML = `<div class="alert alert-error">${e.message}</div>`;
    }
  }

  async function deletePayment(paymentId, seamstressId, name) {
    if (!confirm('Excluir este lançamento?')) return;
    try {
      await Api.deleteSeamstressPayment(paymentId);
      toast('Lançamento excluído!');
      await _renderPaymentList(seamstressId, name);
    } catch (e) { toast(e.message, 'error'); }
  }

  return {
    render, switchTab, onSearch, loadFolha, openCloseMonth, confirmCloseMonth,
    openNew, saveNew, openEdit, saveEdit, toggleActive,
    openPayments, openNewPayment, _togglePayType, savePayment, deletePayment,
  };
})();
