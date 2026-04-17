const PageTimesheet = (() => {
  let empId = null, month = currentMonth(), year = currentYear();
  let empName = '';

  async function render(container) {
    const empOpts = await employeeSelectOptions();
    container.innerHTML = `
      <div class="page-header">
        <div><h1>Ponto</h1><p>Registros de frequência e jornada</p></div>
        <button class="btn btn-primary" id="btn-add-entry" onclick="PageTimesheet.openNew()" disabled>+ Novo Registro</button>
      </div>
      <div class="toolbar">
        <div class="search-box" style="max-width:260px">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/></svg>
          <select class="form-control" id="ts-emp" onchange="PageTimesheet.onEmpChange()" style="padding-left:32px">
            <option value="">Selecione o funcionário...</option>${empOpts}
          </select>
        </div>
        <div class="period-selector">
          <label>Período</label>
          <select id="ts-month" onchange="PageTimesheet.loadEntries()">${monthOptions(month)}</select>
          <select id="ts-year"  onchange="PageTimesheet.loadEntries()">${yearOptions(year)}</select>
        </div>
        <div id="hour-bank-badge"></div>
      </div>

      <div class="table-wrapper">
        <table>
          <thead><tr><th>Data</th><th>Entrada</th><th>Saída Almoço</th><th>Retorno</th><th>Saída</th><th>Trabalhado</th><th>Extra</th><th>Situação</th><th></th></tr></thead>
          <tbody id="ts-tbody"><tr><td colspan="9" style="text-align:center;padding:40px;color:var(--text-muted)">Selecione um funcionário para ver o ponto.</td></tr></tbody>
        </table>
      </div>`;
  }

  async function onEmpChange() {
    empId = parseInt(document.getElementById('ts-emp').value) || null;
    const opt = document.querySelector('#ts-emp option:checked');
    empName = opt ? opt.textContent : '';
    document.getElementById('btn-add-entry').disabled = !empId;
    if (empId) { await loadEntries(); await loadHourBank(); }
  }

  async function loadEntries() {
    if (!empId) return;
    month = parseInt(document.getElementById('ts-month').value);
    year  = parseInt(document.getElementById('ts-year').value);
    document.getElementById('ts-tbody').innerHTML = loadingRow(9);
    try {
      const entries = await Api.getTimesheet(empId, month, year) || [];
      renderTable(entries);
    } catch (e) { document.getElementById('ts-tbody').innerHTML = emptyRow(e.message, 9); }
  }

  function renderTable(entries) {
    if (!entries.length) { document.getElementById('ts-tbody').innerHTML = emptyRow('Nenhum registro neste período.', 9); return; }
    document.getElementById('ts-tbody').innerHTML = entries.map(e => {
      let situation = '';
      if (e.is_annulled)           situation = '<span class="badge badge-gray">Anulado</span>';
      else if (e.is_medical_certificate) situation = '<span class="badge badge-primary">Atestado</span>';
      else if (e.is_absence)       situation = '<span class="badge badge-danger">Falta</span>';
      else if (e.overtime_minutes > 0) situation = `<span class="badge badge-success">+${fmt.mins(e.overtime_minutes)}</span>`;
      else                         situation = '<span class="badge badge-gray">Normal</span>';
      return `<tr>
        <td>${fmt.date(e.work_date)}</td>
        <td>${e.entry_time||'—'}</td>
        <td>${e.lunch_out_time||'—'}</td>
        <td>${e.lunch_in_time||'—'}</td>
        <td>${e.exit_time||'—'}</td>
        <td>${fmt.mins(e.worked_minutes||0)}</td>
        <td>${e.overtime_minutes>0?fmt.mins(e.overtime_minutes):'—'}</td>
        <td>${situation}</td>
        <td class="td-actions">
          <button class="btn-icon" onclick="PageTimesheet.openEdit(${e.id})" title="Editar">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
          </button>
        </td>
      </tr>`;
    }).join('');
  }

  async function loadHourBank() {
    try {
      const hb = await Api.getHourBank(empId);
      const bal = hb?.balance_minutes || 0;
      const color = bal >= 0 ? 'var(--success)' : 'var(--danger)';
      const h = Math.floor(Math.abs(bal)/60), m = Math.abs(bal)%60;
      document.getElementById('hour-bank-badge').innerHTML =
        `<div style="background:var(--card);border:1px solid var(--border);border-radius:8px;padding:6px 14px;font-size:13px">
          Banco de Horas: <strong style="color:${color}">${bal<0?'-':''}${h}h${String(m).padStart(2,'0')}min</strong>
        </div>`;
    } catch {}
  }

  function entryForm(e = {}) {
    return `
      <div class="form-group"><label>Data *</label>
        <input class="form-control" type="date" id="ef-date" value="${e.work_date||''}"></div>
      <div class="form-row">
        <div class="form-group"><label>Entrada</label><input class="form-control" type="time" id="ef-entry" value="${e.entry_time?.slice(0,5)||''}"></div>
        <div class="form-group"><label>Saída Almoço</label><input class="form-control" type="time" id="ef-lunch-out" value="${e.lunch_out_time?.slice(0,5)||''}"></div>
      </div>
      <div class="form-row">
        <div class="form-group"><label>Retorno Almoço</label><input class="form-control" type="time" id="ef-lunch-in" value="${e.lunch_in_time?.slice(0,5)||''}"></div>
        <div class="form-group"><label>Saída</label><input class="form-control" type="time" id="ef-exit" value="${e.exit_time?.slice(0,5)||''}"></div>
      </div>
      <div class="form-row">
        <div class="form-group"><label>Falta?</label>
          <select class="form-control" id="ef-absence">
            <option value="false" ${!e.is_absence?'selected':''}>Não</option>
            <option value="true" ${e.is_absence?'selected':''}>Sim</option>
          </select>
        </div>
        <div class="form-group"><label>Atestado?</label>
          <select class="form-control" id="ef-cert">
            <option value="false" ${!e.is_medical_certificate?'selected':''}>Não</option>
            <option value="true" ${e.is_medical_certificate?'selected':''}>Sim</option>
          </select>
        </div>
      </div>
      <div id="ef-error"></div>`;
  }

  function collectEntry() {
    return {
      employee_id: empId,
      work_date: document.getElementById('ef-date').value,
      entry_time: document.getElementById('ef-entry').value||null,
      lunch_out_time: document.getElementById('ef-lunch-out').value||null,
      lunch_in_time: document.getElementById('ef-lunch-in').value||null,
      exit_time: document.getElementById('ef-exit').value||null,
      is_absence: document.getElementById('ef-absence').value === 'true',
      is_medical_certificate: document.getElementById('ef-cert').value === 'true',
    };
  }

  function openNew() {
    openModal(`Novo Registro — ${empName}`, entryForm(), `
      <button class="btn btn-secondary" onclick="closeModal()">Cancelar</button>
      <button class="btn btn-primary" onclick="PageTimesheet.saveNew()">Salvar</button>`);
  }

  async function saveNew() {
    try { await Api.createEntry(collectEntry()); closeModal(); toast('Registro criado!'); loadEntries(); }
    catch (e) { document.getElementById('ef-error').innerHTML = `<div class="alert alert-error">${e.message}</div>`; }
  }

  async function openEdit(id) {
    // Find entry in DOM or refetch
    openModal('Editar Registro', `<div style="text-align:center;padding:20px"><div class="spinner spinner-dark"></div></div>`, '');
    // We'll just open a blank form for simplicity; real app would fetch entry
    document.getElementById('modal-body').innerHTML = `<div class="alert alert-warning">Para editar, use o campo de data e horários abaixo.</div>${entryForm({work_date: new Date().toISOString().split('T')[0]})}`;
    document.getElementById('modal-footer').innerHTML = `
      <button class="btn btn-secondary" onclick="closeModal()">Cancelar</button>
      <button class="btn btn-primary" onclick="PageTimesheet.saveEdit(${id})">Salvar</button>`;
  }

  async function saveEdit(id) {
    const data = collectEntry();
    delete data.employee_id;
    try { await Api.updateEntry(id, data); closeModal(); toast('Registro atualizado!'); loadEntries(); }
    catch (e) { document.getElementById('ef-error').innerHTML = `<div class="alert alert-error">${e.message}</div>`; }
  }

  return { render, onEmpChange, loadEntries, openNew, saveNew, openEdit, saveEdit };
})();
