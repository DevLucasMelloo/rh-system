const PageSeamstresses = (() => {
  let list = [];
  async function render(container) {
    container.innerHTML = `
      <div class="page-header">
        <div><h1>Costureiras</h1><p>Produção e pagamentos por peça</p></div>
        <button class="btn btn-primary" onclick="PageSeamstresses.openNew()">+ Nova Costureira</button>
      </div>
      <div class="table-wrapper">
        <table>
          <thead><tr><th>Nome</th><th>CPF</th><th>Telefone</th><th>Valor/Peça</th><th>Status</th><th></th></tr></thead>
          <tbody id="sea-tbody">${loadingRow(6)}</tbody>
        </table>
      </div>`;
    try {
      list = await Api.getSeamstresses() || [];
      renderTable();
    } catch (e) {
      document.getElementById('sea-tbody').innerHTML = emptyRow(e.message, 6);
    }
  }

  function renderTable() {
    if (!list.length) { document.getElementById('sea-tbody').innerHTML = emptyRow('Nenhuma costureira cadastrada.', 6); return; }
    document.getElementById('sea-tbody').innerHTML = list.map(s => `
      <tr>
        <td><strong>${s.name}</strong></td>
        <td style="color:var(--text-muted)">${fmt.cpf(s.cpf)}</td>
        <td>${s.phone || '—'}</td>
        <td>${fmt.brl(s.price_per_piece)}</td>
        <td>${fmt.status(s.status)}</td>
        <td class="td-actions">
          <div class="dropdown">
            <button class="btn-icon" onclick="toggleDropdown('sdd-${s.id}')">⋮</button>
            <div class="dropdown-menu" id="sdd-${s.id}">
              <button class="dropdown-item" onclick="PageSeamstresses.openPayments(${s.id},'${s.name}')">Ver Pagamentos</button>
              <button class="dropdown-item" onclick="PageSeamstresses.openEdit(${s.id})">Editar</button>
            </div>
          </div>
        </td>
      </tr>`).join('');
  }

  function seamstressForm(s = {}) {
    return `
      <div class="form-row">
        <div class="form-group"><label>Nome *</label><input class="form-control" id="sf-name" value="${s.name||''}"></div>
        <div class="form-group"><label>CPF *</label><input class="form-control" id="sf-cpf" value="${fmt.cpf(s.cpf)||''}"></div>
      </div>
      <div class="form-row">
        <div class="form-group"><label>Telefone</label><input class="form-control" id="sf-phone" value="${s.phone||''}"></div>
        <div class="form-group"><label>Valor por Peça (R$) *</label><input class="form-control" type="number" step="0.01" id="sf-price" value="${s.price_per_piece||''}"></div>
      </div>
      <div id="sf-error"></div>`;
  }

  function openNew() {
    openModal('Nova Costureira', seamstressForm(), `
      <button class="btn btn-secondary" onclick="closeModal()">Cancelar</button>
      <button class="btn btn-primary" onclick="PageSeamstresses.saveNew()">Salvar</button>`);
  }

  async function saveNew() {
    const data = { name: document.getElementById('sf-name').value.trim(), cpf: document.getElementById('sf-cpf').value.trim(), phone: document.getElementById('sf-phone').value.trim()||null, price_per_piece: parseFloat(document.getElementById('sf-price').value) };
    try { await Api.createSeamstress(data); closeModal(); toast('Costureira cadastrada!'); render(document.getElementById('page-content')); }
    catch (e) { document.getElementById('sf-error').innerHTML = `<div class="alert alert-error">${e.message}</div>`; }
  }

  async function openEdit(id) {
    const s = list.find(x => x.id === id);
    openModal('Editar Costureira', seamstressForm(s), `
      <button class="btn btn-secondary" onclick="closeModal()">Cancelar</button>
      <button class="btn btn-primary" onclick="PageSeamstresses.saveEdit(${id})">Salvar</button>`);
  }

  async function saveEdit(id) {
    const data = { name: document.getElementById('sf-name').value.trim(), phone: document.getElementById('sf-phone').value.trim()||null, price_per_piece: parseFloat(document.getElementById('sf-price').value) };
    try { await Api.updateSeamstress(id, data); closeModal(); toast('Costureira atualizada!'); render(document.getElementById('page-content')); }
    catch (e) { document.getElementById('sf-error').innerHTML = `<div class="alert alert-error">${e.message}</div>`; }
  }

  async function openPayments(id, name) {
    openModal(`Pagamentos — ${name}`, '<div style="padding:20px;text-align:center"><div class="spinner spinner-dark"></div></div>', `
      <button class="btn btn-secondary" onclick="closeModal()">Fechar</button>
      <button class="btn btn-primary" onclick="PageSeamstresses.openNewPayment(${id})">+ Registrar Pagamento</button>`, true);
    try {
      const payments = await Api.getSeamstressPayments(id) || [];
      const rows = payments.length
        ? payments.map(p => `<tr><td>${fmt.date(p.payment_date)}</td><td>${p.pieces_count}</td><td>${fmt.brl(p.amount)}</td><td>${p.notes||'—'}</td></tr>`).join('')
        : emptyRow('Nenhum pagamento.', 4);
      document.getElementById('modal-body').innerHTML = `
        <div class="table-wrapper"><table>
          <thead><tr><th>Data</th><th>Peças</th><th>Valor</th><th>Obs.</th></tr></thead>
          <tbody>${rows}</tbody>
        </table></div>`;
    } catch {}
  }

  async function openNewPayment(id) {
    openModal('Registrar Pagamento', `
      <div class="form-row">
        <div class="form-group"><label>Qtd Peças *</label><input class="form-control" type="number" id="pay-pieces"></div>
        <div class="form-group"><label>Data *</label><input class="form-control" type="date" id="pay-date" value="${new Date().toISOString().split('T')[0]}"></div>
      </div>
      <div class="form-group"><label>Observações</label><input class="form-control" id="pay-notes"></div>
      <div id="pay-error"></div>`, `
      <button class="btn btn-secondary" onclick="PageSeamstresses.openPayments(${id},'')">Voltar</button>
      <button class="btn btn-primary" onclick="PageSeamstresses.savePayment(${id})">Salvar</button>`);
  }

  async function savePayment(id) {
    const pieces = parseInt(document.getElementById('pay-pieces').value);
    const dt = document.getElementById('pay-date').value;
    try {
      await Api.createPayment(id, { pieces_count: pieces, payment_date: dt, notes: document.getElementById('pay-notes').value.trim()||null });
      toast('Pagamento registrado!');
      openPayments(id, '');
    } catch (e) { document.getElementById('pay-error').innerHTML = `<div class="alert alert-error">${e.message}</div>`; }
  }

  return { render, openNew, saveNew, openEdit, saveEdit, openPayments, openNewPayment, savePayment };
})();
