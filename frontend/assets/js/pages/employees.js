/**
 * Funcionários — CRUD completo com tabs ativo/inativo.
 */
const PageEmployees = (() => {
  let allEmployees = [];
  let tab = 'ativo';
  let search = '';

  async function render(container) {
    container.innerHTML = `
      <div class="page-header">
        <div><h1>Funcionários</h1><p>Gerencie o cadastro de funcionários</p></div>
        <button class="btn btn-primary" onclick="PageEmployees.openNew()">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
          Novo Funcionário
        </button>
      </div>

      <div class="toolbar">
        <div class="search-box">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
          <input type="text" class="form-control" id="emp-search" placeholder="Buscar funcionário..."
                 oninput="PageEmployees.onSearch(this.value)">
        </div>
        <div class="tabs" id="emp-tabs">
          <button class="tab active" onclick="PageEmployees.setTab('ativo')">Ativos (<span id="count-ativo">…</span>)</button>
          <button class="tab" onclick="PageEmployees.setTab('inativo')">Inativos (<span id="count-inativo">…</span>)</button>
        </div>
      </div>

      <div class="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>Nome</th><th>CPF</th><th>Cargo</th>
              <th>Salário</th><th>VT Diário</th><th>Admissão</th>
              <th>Status</th><th></th>
            </tr>
          </thead>
          <tbody id="emp-tbody">${loadingRow(8)}</tbody>
        </table>
      </div>`;

    await loadData();
  }

  async function loadData() {
    try {
      allEmployees = await Api.getEmployees() || [];
      renderTable();
    } catch (e) {
      document.getElementById('emp-tbody').innerHTML =
        `<tr><td colspan="8" class="text-center" style="padding:24px;color:var(--danger)">${e.message}</td></tr>`;
    }
  }

  function renderTable() {
    const active   = allEmployees.filter(e => e.status === 'ativo');
    const inactive = allEmployees.filter(e => e.status === 'inativo');
    document.getElementById('count-ativo').textContent   = active.length;
    document.getElementById('count-inativo').textContent = inactive.length;

    document.querySelectorAll('#emp-tabs .tab').forEach((t,i) => {
      t.classList.toggle('active', i === (tab === 'ativo' ? 0 : 1));
    });

    let list = tab === 'ativo' ? active : inactive;
    if (search) {
      const q = search.toLowerCase();
      list = list.filter(e =>
        e.name.toLowerCase().includes(q) ||
        (e.cpf || '').replace(/\D/g,'').includes(q.replace(/\D/g,''))
      );
    }

    if (!list.length) {
      document.getElementById('emp-tbody').innerHTML = emptyRow('Nenhum funcionário encontrado.', 8);
      return;
    }

    document.getElementById('emp-tbody').innerHTML = list.map(e => `
      <tr>
        <td><strong>${e.name}</strong></td>
        <td style="color:var(--text-muted)">${fmt.cpf(e.cpf)}</td>
        <td>${e.role}</td>
        <td>${fmt.brl(e.salary)}</td>
        <td>R$ ${Number(e.vt_daily || 10.60).toFixed(2)}</td>
        <td>${fmt.date(e.admission_date)}</td>
        <td>${fmt.status(e.status)}</td>
        <td class="td-actions">
          <div class="dropdown">
            <button class="btn-icon" onclick="toggleDropdown('dd-${e.id}')" title="Ações">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="5" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="12" cy="19" r="1"/></svg>
            </button>
            <div class="dropdown-menu" id="dd-${e.id}">
              <button class="dropdown-item" onclick="PageEmployees.openEdit(${e.id})">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
                Editar Funcionário
              </button>
              <button class="dropdown-item" onclick="PageEmployees.openHistory(${e.id},'${e.name}')">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 .49-3"/></svg>
                Histórico
              </button>
              ${e.status === 'ativo'
                ? `<button class="dropdown-item danger" onclick="PageEmployees.confirmInactivate(${e.id},'${e.name}')">
                     <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><line x1="17" y1="11" x2="23" y2="11"/></svg>
                     Inativar
                   </button>`
                : `<button class="dropdown-item" onclick="PageEmployees.reactivate(${e.id})">
                     <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><line x1="19" y1="8" x2="19" y2="14"/><line x1="22" y1="11" x2="16" y2="11"/></svg>
                     Reativar
                   </button>`}
            </div>
          </div>
        </td>
      </tr>`).join('');
  }

  function setTab(t) { tab = t; renderTable(); }
  const onSearch = debounce(q => { search = q; renderTable(); });

  // ── Forms ──────────────────────────────────────────────────────────────────
  function empForm(e = {}) {
    return `
      <div class="form-row">
        <div class="form-group"><label>Nome *</label>
          <input class="form-control" id="f-name" value="${e.name||''}"></div>
        <div class="form-group"><label>CPF *</label>
          <input class="form-control" id="f-cpf" value="${fmt.cpf(e.cpf)||''}" placeholder="000.000.000-00"></div>
      </div>
      <div class="form-row">
        <div class="form-group"><label>Cargo *</label>
          <input class="form-control" id="f-role" value="${e.role||''}"></div>
        <div class="form-group"><label>Salário *</label>
          <input class="form-control" type="number" step="0.01" id="f-salary" value="${e.salary||''}"></div>
      </div>
      <div class="form-row">
        <div class="form-group"><label>Data Admissão *</label>
          <input class="form-control" type="date" id="f-admission" value="${e.admission_date||''}"></div>
        <div class="form-group"><label>Data Registro *</label>
          <input class="form-control" type="date" id="f-registration" value="${e.registration_date||''}"></div>
      </div>
      <div class="form-row">
        <div class="form-group"><label>RG</label>
          <input class="form-control" id="f-rg" value="${e.rg||''}"></div>
        <div class="form-group"><label>Data Nascimento</label>
          <input class="form-control" type="date" id="f-dob" value="${e.date_of_birth||''}"></div>
      </div>
      <div class="form-row">
        <div class="form-group"><label>Telefone</label>
          <input class="form-control" id="f-phone" value="${e.phone||''}"></div>
        <div class="form-group"><label>Carga Horária Semanal</label>
          <input class="form-control" type="number" id="f-hours" value="${e.weekly_hours||44}"></div>
      </div>
      <div class="form-row">
        <div class="form-group"><label>Banco</label>
          <input class="form-control" id="f-bank" value="${e.bank_name||''}"></div>
        <div class="form-group"><label>PIX</label>
          <input class="form-control" id="f-pix" value="${e.pix||''}"></div>
      </div>
      <div class="form-group"><label>Endereço</label>
        <input class="form-control" id="f-address" value="${e.address||''}"></div>
      <div class="form-row">
        <div class="form-group"><label>Cidade</label>
          <input class="form-control" id="f-city" value="${e.city||''}"></div>
        <div class="form-group"><label>Estado</label>
          <input class="form-control" id="f-state" value="${e.state||''}" maxlength="2" placeholder="SP"></div>
      </div>
      <div id="form-error"></div>`;
  }

  function collectForm() {
    return {
      name:              document.getElementById('f-name').value.trim(),
      cpf:               document.getElementById('f-cpf').value.trim(),
      role:              document.getElementById('f-role').value.trim(),
      salary:            parseFloat(document.getElementById('f-salary').value),
      admission_date:    document.getElementById('f-admission').value,
      registration_date: document.getElementById('f-registration').value,
      rg:                document.getElementById('f-rg').value.trim() || null,
      date_of_birth:     document.getElementById('f-dob').value || null,
      phone:             document.getElementById('f-phone').value.trim() || null,
      weekly_hours:      parseInt(document.getElementById('f-hours').value) || 44,
      bank_name:         document.getElementById('f-bank').value.trim() || null,
      pix:               document.getElementById('f-pix').value.trim() || null,
      address:           document.getElementById('f-address').value.trim() || null,
      city:              document.getElementById('f-city').value.trim() || null,
      state:             document.getElementById('f-state').value.trim().toUpperCase() || null,
    };
  }

  function openNew() {
    openModal('Novo Funcionário', empForm(), `
      <button class="btn btn-secondary" onclick="closeModal()">Cancelar</button>
      <button class="btn btn-primary" onclick="PageEmployees.saveNew()">Salvar</button>`, true);
  }

  async function saveNew() {
    const data = collectForm();
    try {
      await Api.createEmployee(data);
      closeModal();
      toast('Funcionário cadastrado com sucesso!');
      await loadData();
    } catch (e) {
      document.getElementById('form-error').innerHTML = `<div class="alert alert-error">${e.message}</div>`;
    }
  }

  async function openEdit(id) {
    const emp = allEmployees.find(e => e.id === id);
    if (!emp) return;
    openModal('Editar Funcionário', empForm(emp), `
      <button class="btn btn-secondary" onclick="closeModal()">Cancelar</button>
      <button class="btn btn-primary" onclick="PageEmployees.saveEdit(${id})">Salvar</button>`, true);
  }

  async function saveEdit(id) {
    const data = collectForm();
    try {
      await Api.updateEmployee(id, data);
      closeModal();
      toast('Funcionário atualizado!');
      await loadData();
    } catch (e) {
      document.getElementById('form-error').innerHTML = `<div class="alert alert-error">${e.message}</div>`;
    }
  }

  function confirmInactivate(id, name) {
    openModal('Inativar Funcionário', `
      <p>Tem certeza que deseja inativar <strong>${name}</strong>?</p>
      <div class="form-group mt-3"><label>Motivo</label>
        <input class="form-control" id="inact-reason" placeholder="Ex: Demissão, aposentadoria...">
      </div>`, `
      <button class="btn btn-secondary" onclick="closeModal()">Cancelar</button>
      <button class="btn btn-danger" onclick="PageEmployees.doInactivate(${id})">Inativar</button>`);
  }

  async function doInactivate(id) {
    const reason = document.getElementById('inact-reason').value.trim() || 'Sem motivo informado';
    try {
      await Api.inactivateEmp(id, reason);
      closeModal();
      toast('Funcionário inativado.', 'warning');
      await loadData();
    } catch (e) { toast(e.message, 'error'); }
  }

  async function reactivate(id) {
    try {
      await Api.reactivateEmp(id);
      toast('Funcionário reativado!');
      await loadData();
    } catch (e) { toast(e.message, 'error'); }
  }

  async function openHistory(id, name) {
    openModal(`Histórico — ${name}`, '<div class="flex items-center gap-2" style="padding:20px"><div class="spinner spinner-dark"></div> Carregando...</div>', '', true);
    try {
      const emp = await Api.getEmployee(id);
      const hist = emp?.history || [];
      const rows = hist.length
        ? hist.map(h => `<tr>
            <td>${h.changed_at ? h.changed_at.slice(0,16).replace('T',' ') : '—'}</td>
            <td>${h.field_changed}</td>
            <td>${h.old_value || '—'}</td>
            <td>${h.new_value || '—'}</td>
          </tr>`).join('')
        : emptyRow('Sem histórico.', 4);
      document.getElementById('modal-body').innerHTML = `
        <div class="table-wrapper">
          <table><thead><tr><th>Data</th><th>Campo</th><th>Anterior</th><th>Novo</th></tr></thead>
          <tbody>${rows}</tbody></table>
        </div>`;
    } catch (e) { document.getElementById('modal-body').innerHTML = `<div class="alert alert-error">${e.message}</div>`; }
  }

  return { render, setTab, onSearch, openNew, saveNew, openEdit, saveEdit, confirmInactivate, doInactivate, reactivate, openHistory };
})();
