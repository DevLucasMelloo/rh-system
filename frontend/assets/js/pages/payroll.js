/**
 * Folha de Pagamento — listagem por período, criação, fechamento, PDF.
 */
const PagePayroll = (() => {
  let month = currentMonth();
  let year  = currentYear();
  let payrolls = [];

  async function render(container) {
    container.innerHTML = `
      <div class="page-header">
        <div><h1>Folha de Pagamento</h1><p>Holerites por competência</p></div>
        <button class="btn btn-primary" onclick="PagePayroll.openNew()">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
          Novo Holerite
        </button>
      </div>

      <div class="toolbar">
        <div class="period-selector">
          <label>Competência</label>
          <select id="sel-month" onchange="PagePayroll.changePeriod()">${monthOptions(month)}</select>
          <select id="sel-year"  onchange="PagePayroll.changePeriod()">${yearOptions(year)}</select>
        </div>
      </div>

      <div class="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>Funcionário</th><th>Dias Trab.</th><th>Horas Extras</th>
              <th>Bruto</th><th>Descontos</th><th>Líquido</th>
              <th>Status</th><th></th>
            </tr>
          </thead>
          <tbody id="payroll-tbody">${loadingRow(8)}</tbody>
        </table>
        <div id="payroll-total" style="padding:14px 20px;border-top:1px solid var(--border);font-size:13px;color:var(--text-muted)"></div>
      </div>`;

    await loadData();
  }

  async function loadData() {
    try {
      payrolls = await Api.getPayrollPeriod(month, year) || [];
      renderTable();
    } catch (e) {
      document.getElementById('payroll-tbody').innerHTML =
        `<tr><td colspan="8" style="padding:24px;text-align:center;color:var(--danger)">${e.message}</td></tr>`;
    }
  }

  function renderTable() {
    if (!payrolls.length) {
      document.getElementById('payroll-tbody').innerHTML = emptyRow('Nenhum holerite para este período.', 8);
      document.getElementById('payroll-total').textContent = '';
      return;
    }

    const totalNet = payrolls.reduce((s, p) => s + Number(p.net_salary || 0), 0);
    document.getElementById('payroll-total').innerHTML =
      `Total líquido: <strong>${fmt.brl(totalNet)}</strong> &nbsp;·&nbsp; ${payrolls.length} holerite(s)`;

    document.getElementById('payroll-tbody').innerHTML = payrolls.map(p => `
      <tr>
        <td><strong>${p.employee_name || '—'}</strong></td>
        <td>${p.worked_days}</td>
        <td>${Number(p.total_overtime_hours || 0).toFixed(1)}h</td>
        <td>${fmt.brl(p.gross_salary)}</td>
        <td style="color:var(--danger)">- ${fmt.brl(p.total_discounts)}</td>
        <td><strong>${fmt.brl(p.net_salary)}</strong></td>
        <td>${fmt.status(p.status)}</td>
        <td class="td-actions">
          <div class="dropdown">
            <button class="btn-icon" onclick="toggleDropdown('pdd-${p.id}')">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="5" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="12" cy="19" r="1"/></svg>
            </button>
            <div class="dropdown-menu" id="pdd-${p.id}">
              <button class="dropdown-item" onclick="PagePayroll.openDetail(${p.id})">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
                Ver Detalhes
              </button>
              ${p.status === 'rascunho' ? `
              <button class="dropdown-item" onclick="PagePayroll.recalc(${p.id})">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 .49-3"/></svg>
                Recalcular
              </button>
              <button class="dropdown-item" onclick="PagePayroll.openClose(${p.id})">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>
                Fechar Holerite
              </button>` : ''}
              <button class="dropdown-item" onclick="Api.getPayrollPdf(${p.id}).catch(e=>toast(e.message,'error'))">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                Baixar PDF
              </button>
            </div>
          </div>
        </td>
      </tr>`).join('');
  }

  function changePeriod() {
    month = parseInt(document.getElementById('sel-month').value);
    year  = parseInt(document.getElementById('sel-year').value);
    document.getElementById('payroll-tbody').innerHTML = loadingRow(8);
    loadData();
  }

  // ── Novo holerite ────────────────────────────────────────────────────────
  async function openNew() {
    const empOpts = await employeeSelectOptions();
    openModal('Novo Holerite', `
      <div class="form-group"><label>Funcionário *</label>
        <select class="form-control" id="new-emp"><option value="">Selecione...</option>${empOpts}</select>
      </div>
      <div class="form-row">
        <div class="form-group"><label>Mês *</label>
          <select class="form-control" id="new-month">${monthOptions(month)}</select>
        </div>
        <div class="form-group"><label>Ano *</label>
          <select class="form-control" id="new-year">${yearOptions(year)}</select>
        </div>
      </div>
      <div id="new-error"></div>`, `
      <button class="btn btn-secondary" onclick="closeModal()">Cancelar</button>
      <button class="btn btn-primary" onclick="PagePayroll.saveNew()">Criar e Calcular</button>`);
  }

  async function saveNew() {
    const empId = parseInt(document.getElementById('new-emp').value);
    const m = parseInt(document.getElementById('new-month').value);
    const y = parseInt(document.getElementById('new-year').value);
    if (!empId) { document.getElementById('new-error').innerHTML = '<div class="alert alert-error">Selecione um funcionário.</div>'; return; }
    try {
      await Api.createPayroll({ employee_id: empId, competence_month: m, competence_year: y });
      closeModal();
      month = m; year = y;
      toast('Holerite criado e calculado!');
      await loadData();
    } catch (e) {
      document.getElementById('new-error').innerHTML = `<div class="alert alert-error">${e.message}</div>`;
    }
  }

  // ── Detail ───────────────────────────────────────────────────────────────
  async function openDetail(id) {
    openModal('Detalhes do Holerite', '<div style="padding:20px;text-align:center"><div class="spinner spinner-dark"></div></div>', '', true);
    try {
      const p = await Api.getPayroll(id);
      const credits = (p.items || []).filter(i => i.is_credit);
      const debits  = (p.items || []).filter(i => !i.is_credit);

      const itemRows = items => items.map(i => `
        <li>
          <span>${i.description}${i.is_manual ? ' <span class="badge badge-gray" style="font-size:10px">manual</span>' : ''}</span>
          <span class="${i.is_credit ? 'credit' : 'debit'}">${i.is_credit ? '+' : '-'} ${fmt.brl(i.amount)}</span>
        </li>`).join('');

      document.getElementById('modal-body').innerHTML = `
        <div class="detail-grid" style="margin-bottom:20px">
          <div class="detail-item"><label>Funcionário</label><span>${p.employee_name||'—'}</span></div>
          <div class="detail-item"><label>Competência</label><span>${fmt.month(p.competence_month)}/${p.competence_year}</span></div>
          <div class="detail-item"><label>Dias Trabalhados</label><span>${p.worked_days}</span></div>
          <div class="detail-item"><label>Horas Extras</label><span>${Number(p.total_overtime_hours||0).toFixed(1)}h</span></div>
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px">
          <div><h4 style="margin-bottom:8px;font-size:13px;color:var(--success)">Proventos</h4>
            <ul class="items-list">${itemRows(credits)}</ul>
          </div>
          <div><h4 style="margin-bottom:8px;font-size:13px;color:var(--danger)">Descontos</h4>
            <ul class="items-list">${itemRows(debits)}</ul>
          </div>
        </div>
        <div style="border-top:2px solid var(--border);margin-top:16px;padding-top:16px;display:flex;justify-content:space-between;align-items:center">
          <span style="font-size:15px;font-weight:600">Salário Líquido</span>
          <span style="font-size:20px;font-weight:700;color:var(--primary)">${fmt.brl(p.net_salary)}</span>
        </div>
        ${p.status === 'rascunho' ? `
        <div style="margin-top:16px">
          <button class="btn btn-secondary btn-sm" onclick="PagePayroll.openAddItem(${id})">+ Item Manual</button>
        </div>` : ''}`;
    } catch (e) {
      document.getElementById('modal-body').innerHTML = `<div class="alert alert-error">${e.message}</div>`;
    }
  }

  // ── Add manual item ──────────────────────────────────────────────────────
  async function openAddItem(payrollId) {
    openModal('Adicionar Item Manual', `
      <div class="form-group"><label>Descrição *</label>
        <input class="form-control" id="item-desc" placeholder="Ex: Bônus de produtividade"></div>
      <div class="form-row">
        <div class="form-group"><label>Valor *</label>
          <input class="form-control" type="number" step="0.01" id="item-amount"></div>
        <div class="form-group"><label>Tipo</label>
          <select class="form-control" id="item-credit">
            <option value="true">Crédito (provento)</option>
            <option value="false">Débito (desconto)</option>
          </select>
        </div>
      </div>
      <div class="form-group"><label>Tipo de Item</label>
        <select class="form-control" id="item-type">
          <option value="outros_credito">Outros Crédito</option>
          <option value="outros_desconto">Outros Desconto</option>
          <option value="bonificacao">Bonificação</option>
          <option value="auxilio">Auxílio</option>
        </select>
      </div>
      <div id="item-error"></div>`, `
      <button class="btn btn-secondary" onclick="PagePayroll.openDetail(${payrollId})">Voltar</button>
      <button class="btn btn-primary" onclick="PagePayroll.saveItem(${payrollId})">Adicionar</button>`);
  }

  async function saveItem(payrollId) {
    const desc   = document.getElementById('item-desc').value.trim();
    const amount = parseFloat(document.getElementById('item-amount').value);
    const credit = document.getElementById('item-credit').value === 'true';
    const type   = document.getElementById('item-type').value;
    if (!desc || !amount) {
      document.getElementById('item-error').innerHTML = '<div class="alert alert-error">Preencha descrição e valor.</div>';
      return;
    }
    try {
      await Api.addPayrollItem(payrollId, { item_type: type, description: desc, amount, is_credit: credit });
      toast('Item adicionado!');
      openDetail(payrollId);
    } catch (e) {
      document.getElementById('item-error').innerHTML = `<div class="alert alert-error">${e.message}</div>`;
    }
  }

  // ── Close ────────────────────────────────────────────────────────────────
  function openClose(id) {
    const today = new Date().toISOString().split('T')[0];
    openModal('Fechar Holerite', `
      <p style="color:var(--text-muted);margin-bottom:16px">Esta ação é irreversível. O holerite não poderá ser editado após o fechamento.</p>
      <div class="form-group"><label>Data de Pagamento</label>
        <input class="form-control" type="date" id="close-date" value="${today}">
      </div>`, `
      <button class="btn btn-secondary" onclick="closeModal()">Cancelar</button>
      <button class="btn btn-primary" onclick="PagePayroll.doClose(${id})">Confirmar Fechamento</button>`);
  }

  async function doClose(id) {
    const dt = document.getElementById('close-date').value;
    try {
      await Api.closePayroll(id, dt);
      closeModal();
      toast('Holerite fechado!');
      await loadData();
    } catch (e) { toast(e.message, 'error'); }
  }

  async function recalc(id) {
    try {
      await Api.recalcPayroll(id);
      toast('Holerite recalculado!');
      await loadData();
    } catch (e) { toast(e.message, 'error'); }
  }

  return { render, changePeriod, openNew, saveNew, openDetail, openAddItem, saveItem, openClose, doClose, recalc };
})();
