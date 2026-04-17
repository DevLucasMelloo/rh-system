const PageReports = (() => {
  async function render(container) {
    container.innerHTML = `
      <div class="page-header">
        <div><h1>Relatórios</h1><p>Exportação de dados em planilha Excel</p></div>
      </div>

      <div class="report-grid">

        <!-- Folha de Pagamento -->
        <div class="card">
          <div class="card-body" style="display:flex;flex-direction:column;gap:12px">
            <div style="display:flex;align-items:center;gap:12px">
              <div style="width:40px;height:40px;border-radius:10px;background:rgba(37,99,235,0.1);display:flex;align-items:center;justify-content:center;flex-shrink:0">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--primary)" stroke-width="2"><rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8M12 17v4"/></svg>
              </div>
              <div>
                <h3 style="font-size:15px;font-weight:600;margin-bottom:2px">Folha de Pagamento</h3>
                <p style="font-size:12px;color:var(--text-muted)">Holerites por competência</p>
              </div>
            </div>
            <div class="form-row" style="margin:0">
              <div class="form-group" style="margin:0">
                <select class="form-control" id="rpt-pay-month">${monthOptions(currentMonth())}</select>
              </div>
              <div class="form-group" style="margin:0">
                <select class="form-control" id="rpt-pay-year">${yearOptions(currentYear())}</select>
              </div>
            </div>
            <button class="btn btn-primary" onclick="PageReports.dlPayroll()">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
              Baixar Excel
            </button>
          </div>
        </div>

        <!-- Ponto / Timesheet -->
        <div class="card">
          <div class="card-body" style="display:flex;flex-direction:column;gap:12px">
            <div style="display:flex;align-items:center;gap:12px">
              <div style="width:40px;height:40px;border-radius:10px;background:rgba(16,185,129,0.1);display:flex;align-items:center;justify-content:center;flex-shrink:0">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--success)" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
              </div>
              <div>
                <h3 style="font-size:15px;font-weight:600;margin-bottom:2px">Controle de Ponto</h3>
                <p style="font-size:12px;color:var(--text-muted)">Registros de jornada por período</p>
              </div>
            </div>
            <div class="form-row" style="margin:0">
              <div class="form-group" style="margin:0">
                <select class="form-control" id="rpt-ts-month">${monthOptions(currentMonth())}</select>
              </div>
              <div class="form-group" style="margin:0">
                <select class="form-control" id="rpt-ts-year">${yearOptions(currentYear())}</select>
              </div>
            </div>
            <button class="btn btn-primary" onclick="PageReports.dlTimesheet()">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
              Baixar Excel
            </button>
          </div>
        </div>

        <!-- Funcionários -->
        <div class="card">
          <div class="card-body" style="display:flex;flex-direction:column;gap:12px">
            <div style="display:flex;align-items:center;gap:12px">
              <div style="width:40px;height:40px;border-radius:10px;background:rgba(245,158,11,0.1);display:flex;align-items:center;justify-content:center;flex-shrink:0">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
              </div>
              <div>
                <h3 style="font-size:15px;font-weight:600;margin-bottom:2px">Funcionários</h3>
                <p style="font-size:12px;color:var(--text-muted)">Cadastro completo de colaboradores</p>
              </div>
            </div>
            <div class="form-row" style="margin:0">
              <div class="form-group" style="margin:0">
                <select class="form-control" id="rpt-emp-inactive">
                  <option value="false">Somente Ativos</option>
                  <option value="true">Incluir Inativos</option>
                </select>
              </div>
            </div>
            <button class="btn btn-primary" onclick="PageReports.dlEmployees()">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
              Baixar Excel
            </button>
          </div>
        </div>

        <!-- Férias -->
        <div class="card">
          <div class="card-body" style="display:flex;flex-direction:column;gap:12px">
            <div style="display:flex;align-items:center;gap:12px">
              <div style="width:40px;height:40px;border-radius:10px;background:rgba(139,92,246,0.1);display:flex;align-items:center;justify-content:center;flex-shrink:0">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#8b5cf6" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
              </div>
              <div>
                <h3 style="font-size:15px;font-weight:600;margin-bottom:2px">Férias</h3>
                <p style="font-size:12px;color:var(--text-muted)">Períodos aquisitivos e gozos</p>
              </div>
            </div>
            <div style="flex:1"></div>
            <button class="btn btn-primary" onclick="PageReports.dlVacations()">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
              Baixar Excel
            </button>
          </div>
        </div>

        <!-- Rescisões -->
        <div class="card">
          <div class="card-body" style="display:flex;flex-direction:column;gap:12px">
            <div style="display:flex;align-items:center;gap:12px">
              <div style="width:40px;height:40px;border-radius:10px;background:rgba(239,68,68,0.1);display:flex;align-items:center;justify-content:center;flex-shrink:0">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--danger)" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="9" y1="15" x2="15" y2="15"/></svg>
              </div>
              <div>
                <h3 style="font-size:15px;font-weight:600;margin-bottom:2px">Rescisões</h3>
                <p style="font-size:12px;color:var(--text-muted)">Verbas e histórico de desligamentos</p>
              </div>
            </div>
            <div style="flex:1"></div>
            <button class="btn btn-primary" onclick="PageReports.dlTerminations()">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
              Baixar Excel
            </button>
          </div>
        </div>

        <!-- Banco de Horas -->
        <div class="card">
          <div class="card-body" style="display:flex;flex-direction:column;gap:12px">
            <div style="display:flex;align-items:center;gap:12px">
              <div style="width:40px;height:40px;border-radius:10px;background:rgba(6,182,212,0.1);display:flex;align-items:center;justify-content:center;flex-shrink:0">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#06b6d4" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
              </div>
              <div>
                <h3 style="font-size:15px;font-weight:600;margin-bottom:2px">Banco de Horas</h3>
                <p style="font-size:12px;color:var(--text-muted)">Saldo de horas de todos os funcionários</p>
              </div>
            </div>
            <div style="flex:1"></div>
            <button class="btn btn-primary" onclick="PageReports.dlHourBank()">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
              Baixar Excel
            </button>
          </div>
        </div>

      </div>`;
  }

  async function dlPayroll() {
    const month = parseInt(document.getElementById('rpt-pay-month').value);
    const year  = parseInt(document.getElementById('rpt-pay-year').value);
    try {
      await Api.dlPayroll(month, year);
      toast('Relatório baixado!');
    } catch (e) { toast(e.message, 'error'); }
  }

  async function dlTimesheet() {
    const month = parseInt(document.getElementById('rpt-ts-month').value);
    const year  = parseInt(document.getElementById('rpt-ts-year').value);
    try {
      await Api.dlTimesheet(month, year);
      toast('Relatório baixado!');
    } catch (e) { toast(e.message, 'error'); }
  }

  async function dlEmployees() {
    const includeInactive = document.getElementById('rpt-emp-inactive').value === 'true';
    try {
      await Api.dlEmployees(includeInactive);
      toast('Relatório baixado!');
    } catch (e) { toast(e.message, 'error'); }
  }

  async function dlVacations() {
    try {
      await Api.dlVacations();
      toast('Relatório baixado!');
    } catch (e) { toast(e.message, 'error'); }
  }

  async function dlTerminations() {
    try {
      await Api.dlTerminations();
      toast('Relatório baixado!');
    } catch (e) { toast(e.message, 'error'); }
  }

  async function dlHourBank() {
    try {
      await Api.dlHourBank();
      toast('Relatório baixado!');
    } catch (e) { toast(e.message, 'error'); }
  }

  return { render, dlPayroll, dlTimesheet, dlEmployees, dlVacations, dlTerminations, dlHourBank };
})();
