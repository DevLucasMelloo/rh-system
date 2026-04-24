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
        <div style="display:flex;flex-direction:column;gap:8px;align-items:flex-end">
          <button class="btn btn-primary" onclick="PageEmployees.openNew()">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
            Novo Funcionário
          </button>
          <button class="btn" style="background:#16a34a;color:#fff;border-color:#16a34a" onclick="PageEmployees.openRaise()">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/></svg>
            Aumento
          </button>
        </div>
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
      const [active, inactive] = await Promise.all([
        Api.getEmployees(),
        Api.getInactiveEmployees(),
      ]);
      allEmployees = [...(active || []), ...(inactive || [])];
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
        <td>${e.needs_transport ? fmt.brl(e.vt_daily || 10.60) : '—'}</td>
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
    const needsTransport = e.needs_transport || false;
    return `
      <div class="form-row">
        <div class="form-group"><label>Nome *</label>
          <input class="form-control" id="f-name" value="${e.name||''}"></div>
        <div class="form-group"><label>CPF *</label>
          <input class="form-control" id="f-cpf" value="${fmt.cpf(e.cpf)||''}"
            placeholder="000.000.000-00" maxlength="14"
            oninput="applyCpfMask(this)"></div>
      </div>
      <div class="form-row">
        <div class="form-group"><label>Cargo *</label>
          <input class="form-control" id="f-role" value="${e.role||''}"></div>
        <div class="form-group"><label>Salário *</label>
          <input class="form-control" type="number" step="0.01" id="f-salary" value="${e.salary||''}"></div>
      </div>
      <div class="form-row">
        <div class="form-group"><label>Auxílio (R$)</label>
          <input class="form-control" type="number" step="0.01" id="f-auxilio"
            value="${e.auxilio||''}" placeholder="0.00"></div>
        <div class="form-group">
          <label style="display:flex;align-items:center;gap:8px;margin-bottom:8px">
            <input type="checkbox" id="f-transport" ${needsTransport?'checked':''}
              onchange="document.getElementById('vt-group').style.display=this.checked?'block':'none'">
            Precisa de condução (VT)
          </label>
          <div id="vt-group" style="display:${needsTransport?'block':'none'}">
            <input class="form-control" type="number" step="0.01" id="f-vt"
              value="${e.vt_daily||10.60}" placeholder="Valor VT diário">
          </div>
        </div>
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
    const needsTransport = document.getElementById('f-transport').checked;
    const auxilioVal = document.getElementById('f-auxilio').value;
    const salaryVal  = parseFloat(document.getElementById('f-salary').value);
    return {
      name:            document.getElementById('f-name').value.trim(),
      role:            document.getElementById('f-role').value.trim(),
      salary:          isNaN(salaryVal) ? undefined : salaryVal,
      auxilio:         auxilioVal === '' ? null : (parseFloat(auxilioVal) ?? null),
      needs_transport: needsTransport,
      vt_daily:        needsTransport ? (parseFloat(document.getElementById('f-vt').value) || 10.60) : null,
      rg:              document.getElementById('f-rg').value.trim() || null,
      date_of_birth:   document.getElementById('f-dob').value || null,
      phone:           document.getElementById('f-phone').value.trim() || null,
      weekly_hours:    parseInt(document.getElementById('f-hours').value) || 44,
      bank_name:       document.getElementById('f-bank').value.trim() || null,
      pix:             document.getElementById('f-pix').value.trim() || null,
      address:         document.getElementById('f-address').value.trim() || null,
      city:            document.getElementById('f-city').value.trim() || null,
      state:           document.getElementById('f-state').value.trim().toUpperCase() || null,
    };
  }

  function openNew() {
    openModal('Novo Funcionário', empForm(), `
      <button class="btn btn-secondary" onclick="closeModal()">Cancelar</button>
      <button class="btn btn-primary" onclick="PageEmployees.saveNew()">Salvar</button>`, true);
  }

  async function saveNew() {
    const data = {
      ...collectForm(),
      cpf:               document.getElementById('f-cpf').value.replace(/\D/g,''),
      admission_date:    document.getElementById('f-admission').value,
      registration_date: document.getElementById('f-registration').value,
    };
    try {
      await Api.createEmployee(data);
      closeModal();
      toast('Funcionário cadastrado com sucesso!');
      await loadData();
    } catch (e) {
      toast(e.message, 'error');
    }
  }

  async function openEdit(id) {
    openModal('Editar Funcionário', `<div style="padding:20px;text-align:center"><div class="spinner spinner-dark"></div> Carregando...</div>`, `
      <button class="btn btn-secondary" onclick="closeModal()">Cancelar</button>
      <button class="btn btn-primary" onclick="PageEmployees.saveEdit(${id})">Salvar</button>`, true);
    try {
      const emp = await Api.getEmployee(id);
      document.getElementById('modal-body').innerHTML = empForm(emp);
    } catch (e) {
      document.getElementById('modal-body').innerHTML = `<div class="alert alert-error">${e.message}</div>`;
    }
  }

  async function saveEdit(id) {
    const data = {
      ...collectForm(),
      admission_date:    document.getElementById('f-admission').value || null,
      registration_date: document.getElementById('f-registration').value || null,
    };
    const btn = document.querySelector('#modal-footer .btn-primary');
    if (btn) { btn.disabled = true; btn.textContent = 'Salvando...'; }
    try {
      await Api.updateEmployee(id, data);
      closeModal();
      toast('Funcionário atualizado!');
      await loadData();
    } catch (e) {
      toast(e.message, 'error');
      if (btn) { btn.disabled = false; btn.textContent = 'Salvar'; }
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

  function openRaise() {
    const empOptions = allEmployees
      .filter(e => e.status === 'ativo')
      .sort((a,b) => a.name.localeCompare(b.name))
      .map(e => `<option value="${e.id}">${e.name}</option>`)
      .join('');

    openModal('Aumento de Salário / Auxílio', `
      <div class="form-group">
        <label>Funcionário *</label>
        <select class="form-control" id="raise-emp" onchange="PageEmployees._onRaiseEmpChange()">
          <option value="">Selecione...</option>
          ${empOptions}
        </select>
      </div>

      <div id="raise-current" style="display:none;background:var(--bg);border-radius:8px;padding:12px;margin-bottom:16px;font-size:13px">
        <div style="display:flex;gap:24px">
          <span>Salário atual: <strong id="raise-cur-sal">—</strong></span>
          <span>Auxílio atual: <strong id="raise-cur-aux">—</strong></span>
        </div>
      </div>

      <div class="form-group" id="raise-type-group" style="display:none">
        <label>Tipo de Ajuste *</label>
        <div style="display:flex;flex-direction:column;gap:10px;margin-top:6px">
          <label style="display:flex;align-items:center;gap:8px;cursor:pointer;font-weight:400">
            <input type="radio" name="raise-type" value="salary" onchange="PageEmployees._onRaiseTypeChange()" checked>
            Aumento de Salário
          </label>
          <label style="display:flex;align-items:center;gap:8px;cursor:pointer;font-weight:400">
            <input type="radio" name="raise-type" value="auxilio" onchange="PageEmployees._onRaiseTypeChange()">
            Aumento de Auxílio
          </label>
          <label style="display:flex;align-items:flex-start;gap:8px;cursor:pointer;font-weight:400">
            <input type="radio" name="raise-type" value="incorporate" style="margin-top:3px" onchange="PageEmployees._onRaiseTypeChange()">
            <span>Incorporar Auxílio ao Salário
              <span style="display:block;font-size:12px;color:var(--text-muted)">Novo salário = salário + auxílio · auxílio será zerado</span>
            </span>
          </label>
        </div>
      </div>

      <div id="raise-fields" style="display:none">
        <div class="form-group" id="raise-salary-group">
          <label>Valor do Aumento de Salário (R$) *</label>
          <input class="form-control" type="number" step="0.01" id="raise-new-salary" placeholder="0.00" oninput="PageEmployees._onRaiseTypeChange()">
          <div id="raise-salary-preview" style="display:none;font-size:12px;color:var(--text-muted);margin-top:4px"></div>
        </div>
        <div class="form-group" id="raise-auxilio-group" style="display:none">
          <label>Valor do Aumento de Auxílio (R$) *</label>
          <input class="form-control" type="number" step="0.01" id="raise-new-auxilio" placeholder="0.00" oninput="PageEmployees._onRaiseTypeChange()">
          <div id="raise-auxilio-preview" style="display:none;font-size:12px;color:var(--text-muted);margin-top:4px"></div>
        </div>
        <div id="raise-incorporate-preview" style="display:none;background:#f0fdf4;border:1px solid #86efac;border-radius:8px;padding:12px;margin-bottom:16px;font-size:13px">
          Novo salário: <strong id="raise-inc-result">—</strong>
          <div style="color:var(--text-muted);font-size:12px;margin-top:4px">O campo auxílio será zerado após a incorporação.</div>
        </div>
        <div class="form-group">
          <label>Motivo *</label>
          <input class="form-control" id="raise-reason" placeholder="Ex: Reajuste anual, promoção...">
        </div>
      </div>
      <div id="form-error"></div>
    `, `
      <button class="btn btn-secondary" onclick="closeModal()">Cancelar</button>
      <button class="btn btn-primary" onclick="PageEmployees.saveRaise()">Aplicar Aumento</button>
    `);
  }

  function _onRaiseEmpChange() {
    const empId = parseInt(document.getElementById('raise-emp').value);
    const emp = allEmployees.find(e => e.id === empId);
    if (!emp) {
      document.getElementById('raise-current').style.display = 'none';
      document.getElementById('raise-type-group').style.display = 'none';
      document.getElementById('raise-fields').style.display = 'none';
      return;
    }
    document.getElementById('raise-cur-sal').textContent = fmt.brl(emp.salary);
    document.getElementById('raise-cur-aux').textContent = emp.auxilio ? fmt.brl(emp.auxilio) : '—';
    document.getElementById('raise-current').style.display = 'block';
    document.getElementById('raise-type-group').style.display = 'block';
    document.getElementById('raise-fields').style.display = 'block';
    _onRaiseTypeChange();
  }

  function _onRaiseTypeChange() {
    const type = document.querySelector('input[name="raise-type"]:checked')?.value;
    document.getElementById('raise-salary-group').style.display        = type === 'salary'      ? 'block' : 'none';
    document.getElementById('raise-auxilio-group').style.display       = type === 'auxilio'     ? 'block' : 'none';
    document.getElementById('raise-incorporate-preview').style.display = type === 'incorporate' ? 'block' : 'none';

    const empId = parseInt(document.getElementById('raise-emp').value);
    const emp = allEmployees.find(e => e.id === empId);
    if (!emp) return;

    if (type === 'salary') {
      const raise = parseFloat(document.getElementById('raise-new-salary').value) || 0;
      const prev  = document.getElementById('raise-salary-preview');
      if (raise > 0) {
        const result = parseFloat(emp.salary) + raise;
        prev.textContent = `${fmt.brl(emp.salary)} + ${fmt.brl(raise)} = ${fmt.brl(result)}`;
        prev.style.display = 'block';
      } else {
        prev.style.display = 'none';
      }
    } else if (type === 'auxilio') {
      const raise = parseFloat(document.getElementById('raise-new-auxilio').value) || 0;
      const prev  = document.getElementById('raise-auxilio-preview');
      if (raise > 0) {
        const result = parseFloat(emp.auxilio || 0) + raise;
        prev.textContent = `${fmt.brl(emp.auxilio || 0)} + ${fmt.brl(raise)} = ${fmt.brl(result)}`;
        prev.style.display = 'block';
      } else {
        prev.style.display = 'none';
      }
    } else if (type === 'incorporate') {
      const newSal = parseFloat(emp.salary) + parseFloat(emp.auxilio || 0);
      document.getElementById('raise-inc-result').textContent = fmt.brl(newSal);
    }
  }

  async function saveRaise() {
    const empId = parseInt(document.getElementById('raise-emp').value);
    if (!empId) { toast('Selecione um funcionário', 'error'); return; }

    const type   = document.querySelector('input[name="raise-type"]:checked')?.value;
    const reason = document.getElementById('raise-reason').value.trim();
    if (!reason) { toast('Informe o motivo do ajuste', 'error'); return; }

    const body = { raise_type: type, reason };

    if (type === 'salary') {
      const val = parseFloat(document.getElementById('raise-new-salary').value);
      if (isNaN(val) || val <= 0) { toast('Informe o novo salário', 'error'); return; }
      body.new_salary = val;
    } else if (type === 'auxilio') {
      const val = parseFloat(document.getElementById('raise-new-auxilio').value);
      if (isNaN(val) || val < 0) { toast('Informe o novo auxílio', 'error'); return; }
      body.new_auxilio = val;
    }

    const btn = document.querySelector('#modal-footer .btn-primary');
    if (btn) { btn.disabled = true; btn.textContent = 'Aplicando...'; }
    try {
      await Api.raiseEmployee(empId, body);
      closeModal();
      toast('Ajuste aplicado com sucesso!');
      await loadData();
    } catch (e) {
      toast(e.message, 'error');
      if (btn) { btn.disabled = false; btn.textContent = 'Aplicar Aumento'; }
    }
  }

  async function openHistory(id, name) {
    openModal(`Histórico — ${name}`, `<div style="padding:20px;text-align:center"><div class="spinner spinner-dark"></div> Carregando...</div>`, '', true);
    try {
      const hist = await Api.getEmployeeHistory(id) || [];
      const fieldLabels = {
        name: 'Nome', role: 'Cargo', salary: 'Salário', phone: 'Telefone',
        address: 'Endereço', city: 'Cidade', state: 'Estado', bank_name: 'Banco',
        weekly_hours: 'Horas semanais', auxilio: 'Auxílio', needs_transport: 'Condução',
        vt_daily: 'VT Diário', criacao: 'Cadastro', inactivation: 'Inativação',
        bank_account: 'Conta bancária', pix: 'PIX', rg: 'RG',
      };
      const rows = hist.length
        ? hist.map(h => `<tr>
            <td style="white-space:nowrap">${h.changed_at ? h.changed_at.slice(0,16).replace('T',' ') : '—'}</td>
            <td>${fieldLabels[h.field_changed] || h.field_changed}</td>
            <td style="color:var(--text-muted)">${h.old_value || '—'}</td>
            <td>${h.new_value || '—'}</td>
          </tr>`).join('')
        : emptyRow('Sem histórico registrado.', 4);
      document.getElementById('modal-body').innerHTML = `
        <div class="table-wrapper" style="border:none">
          <table><thead><tr><th>Data/Hora</th><th>Campo</th><th>Anterior</th><th>Novo</th></tr></thead>
          <tbody>${rows}</tbody></table>
        </div>`;
    } catch (e) {
      document.getElementById('modal-body').innerHTML = `<div class="alert alert-error">${e.message}</div>`;
    }
  }

  return { render, setTab, onSearch, openNew, saveNew, openEdit, saveEdit, confirmInactivate, doInactivate, reactivate, openHistory, openRaise, _onRaiseEmpChange, _onRaiseTypeChange, saveRaise };
})();
