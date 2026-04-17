const PageVacation = (() => {
  async function render(container) {
    const empOpts = await employeeSelectOptions();
    container.innerHTML = `
      <div class="page-header">
        <div><h1>Férias</h1><p>Gestão de períodos de férias e 13º salário</p></div>
        <button class="btn btn-primary" onclick="PageVacation.openNew()">+ Agendar Férias</button>
      </div>

      <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:20px">
        <div class="card">
          <div class="card-header">Consultar por Funcionário</div>
          <div class="card-body">
            <div class="form-group">
              <select class="form-control" id="vac-emp-sel" onchange="PageVacation.loadEmployee()">
                <option value="">Selecione...</option>${empOpts}
              </select>
            </div>
          </div>
        </div>
        <div class="card">
          <div class="card-header">13º Salário</div>
          <div class="card-body">
            <div class="form-row">
              <div class="form-group">
                <select class="form-control" id="13-emp">${empOpts}</select>
              </div>
              <div class="form-group">
                <select class="form-control" id="13-year">${yearOptions(currentYear())}</select>
              </div>
            </div>
            <div class="form-row">
              <div class="form-group">
                <select class="form-control" id="13-parcela">
                  <option value="1">1ª Parcela (adiantamento)</option>
                  <option value="2" selected>2ª Parcela (saldo)</option>
                </select>
              </div>
              <div class="form-group">
                <button class="btn btn-primary w-full" onclick="PageVacation.calc13()">Calcular</button>
              </div>
            </div>
            <div id="13-result"></div>
          </div>
        </div>
      </div>

      <div class="table-wrapper" id="vac-table-wrap">
        <table>
          <thead><tr><th>Funcionário</th><th>Período Aquisitivo</th><th>Início Gozo</th><th>Dias</th><th>Líquido</th><th>Status</th><th></th></tr></thead>
          <tbody id="vac-tbody"><tr><td colspan="7" style="text-align:center;padding:40px;color:var(--text-muted)">Selecione um funcionário para ver as férias.</td></tr></tbody>
        </table>
      </div>`;
  }

  async function loadEmployee() {
    const id = parseInt(document.getElementById('vac-emp-sel').value) || null;
    if (!id) return;
    document.getElementById('vac-tbody').innerHTML = loadingRow(7);
    try {
      const vacs = await Api.getEmpVacations(id) || [];
      if (!vacs.length) { document.getElementById('vac-tbody').innerHTML = emptyRow('Nenhuma férias cadastrada.', 7); return; }
      document.getElementById('vac-tbody').innerHTML = vacs.map(v => `
        <tr>
          <td>—</td>
          <td>${fmt.date(v.acquisition_start)} – ${fmt.date(v.acquisition_end)}</td>
          <td>${v.enjoyment_start ? fmt.date(v.enjoyment_start) : '—'}</td>
          <td>${v.enjoyment_days} dias</td>
          <td>${v.net_vacation_pay ? fmt.brl(v.net_vacation_pay) : '—'}</td>
          <td>${fmt.status(v.status)}</td>
          <td class="td-actions">
            ${v.status === 'agendada' ? `
              <div class="dropdown">
                <button class="btn-icon" onclick="toggleDropdown('vdd-${v.id}')">⋮</button>
                <div class="dropdown-menu" id="vdd-${v.id}">
                  <button class="dropdown-item" onclick="PageVacation.startVac(${v.id})">Iniciar Gozo</button>
                  <button class="dropdown-item danger" onclick="PageVacation.cancelVac(${v.id})">Cancelar</button>
                </div>
              </div>` : ''}
            ${v.status === 'em_gozo' ? `<button class="btn btn-success btn-sm" onclick="PageVacation.completeVac(${v.id})">Concluir</button>` : ''}
          </td>
        </tr>`).join('');
    } catch (e) { document.getElementById('vac-tbody').innerHTML = emptyRow(e.message, 7); }
  }

  async function openNew() {
    const empOpts = await employeeSelectOptions();
    openModal('Agendar Férias', `
      <div class="form-group"><label>Funcionário *</label>
        <select class="form-control" id="nv-emp"><option value="">Selecione...</option>${empOpts}</select>
      </div>
      <div class="form-row">
        <div class="form-group"><label>Início Período Aquisitivo *</label>
          <input class="form-control" type="date" id="nv-acq-start">
        </div>
        <div class="form-group"><label>Fim Período Aquisitivo *</label>
          <input class="form-control" type="date" id="nv-acq-end">
        </div>
      </div>
      <div class="form-row">
        <div class="form-group"><label>Início do Gozo</label>
          <input class="form-control" type="date" id="nv-enjoy-start">
        </div>
        <div class="form-group"><label>Dias de Gozo</label>
          <input class="form-control" type="number" id="nv-days" value="30" min="5" max="30">
        </div>
      </div>
      <div id="nv-error"></div>`, `
      <button class="btn btn-secondary" onclick="closeModal()">Cancelar</button>
      <button class="btn btn-primary" onclick="PageVacation.saveNew()">Agendar</button>`);
  }

  async function saveNew() {
    const data = {
      employee_id: parseInt(document.getElementById('nv-emp').value),
      acquisition_start: document.getElementById('nv-acq-start').value,
      acquisition_end: document.getElementById('nv-acq-end').value,
      enjoyment_start: document.getElementById('nv-enjoy-start').value || null,
      enjoyment_days: parseInt(document.getElementById('nv-days').value) || 30,
    };
    try { await Api.createVacation(data); closeModal(); toast('Férias agendadas!'); }
    catch (e) { document.getElementById('nv-error').innerHTML = `<div class="alert alert-error">${e.message}</div>`; }
  }

  async function startVac(id) {
    const dt = prompt('Data de início do gozo (AAAA-MM-DD):');
    if (!dt) return;
    try { await Api.startVacation(id, { enjoyment_start: dt }); toast('Gozo iniciado!'); loadEmployee(); }
    catch (e) { toast(e.message, 'error'); }
  }

  async function completeVac(id) {
    try { await Api.completeVacation(id); toast('Férias concluídas!'); loadEmployee(); }
    catch (e) { toast(e.message, 'error'); }
  }

  async function cancelVac(id) {
    if (!confirm('Cancelar estas férias?')) return;
    try { await Api.cancelVacation(id); toast('Férias canceladas.', 'warning'); loadEmployee(); }
    catch (e) { toast(e.message, 'error'); }
  }

  async function calc13() {
    const empId  = parseInt(document.getElementById('13-emp').value);
    const year   = parseInt(document.getElementById('13-year').value);
    const parcela = parseInt(document.getElementById('13-parcela').value);
    const el     = document.getElementById('13-result');
    if (!empId) { el.innerHTML = '<div class="alert alert-warning">Selecione um funcionário.</div>'; return; }
    try {
      const r = await Api.getThirteenth(empId, year, parcela);
      el.innerHTML = `
        <div style="background:var(--bg);border-radius:8px;padding:14px;margin-top:12px;font-size:13px">
          <div style="display:flex;justify-content:space-between;margin-bottom:6px"><span>Meses trabalhados</span><strong>${r.worked_months}</strong></div>
          <div style="display:flex;justify-content:space-between;margin-bottom:6px"><span>13º Bruto</span><strong>${fmt.brl(r.bruto_13)}</strong></div>
          <div style="display:flex;justify-content:space-between;margin-bottom:6px"><span>INSS</span><strong style="color:var(--danger)">- ${fmt.brl(r.inss)}</strong></div>
          ${parcela===2?`<div style="display:flex;justify-content:space-between;margin-bottom:6px"><span>1ª Parcela (adiantamento)</span><strong style="color:var(--danger)">- ${fmt.brl(r.primeira_parcela)}</strong></div>`:''}
          <div style="border-top:1px solid var(--border);padding-top:8px;margin-top:8px;display:flex;justify-content:space-between"><span style="font-weight:600">Líquido ${parcela}ª Parcela</span><strong style="color:var(--primary);font-size:16px">${fmt.brl(r.liquido)}</strong></div>
        </div>`;
    } catch (e) { el.innerHTML = `<div class="alert alert-error">${e.message}</div>`; }
  }

  return { render, loadEmployee, openNew, saveNew, startVac, completeVac, cancelVac, calc13 };
})();
