/**
 * API Client — RH System
 * Centraliza todas as chamadas ao backend FastAPI.
 */

const API_BASE = window.location.port === '3000'
  ? 'http://localhost:8080/api/v1'
  : `${window.location.origin}/api/v1`;

function _showLicenseBlock(validUntil, isActive) {
  const dataVenc = validUntil
    ? new Date(validUntil + 'T00:00:00').toLocaleDateString('pt-BR')
    : 'data não disponível';
  const mensagem = isActive === false
    ? 'O acesso ao sistema foi suspenso pelo administrador.<br>Entre em contato para reativar.'
    : `Sua licença venceu em <strong>${dataVenc}</strong>.<br>Entre em contato para renovar o acesso ao sistema.`;

  document.body.innerHTML = `
    <div style="
      min-height:100vh; display:flex; align-items:center; justify-content:center;
      background:linear-gradient(135deg,#f8fafc 0%,#e2e8f0 100%); font-family:'Segoe UI',sans-serif;
    ">
      <div style="
        background:#fff; border-radius:20px; padding:56px 48px; max-width:440px;
        width:100%; text-align:center; box-shadow:0 8px 40px rgba(0,0,0,0.12);
        border-top:5px solid #ef4444;
      ">
        <div style="
          width:72px; height:72px; background:#fef2f2; border-radius:50%;
          display:flex; align-items:center; justify-content:center;
          margin:0 auto 20px; font-size:36px;
        ">⚠️</div>

        <h2 style="color:#1e293b; margin:0 0 6px; font-size:24px; font-weight:700;">
          Acesso Suspenso
        </h2>
        <p style="color:#94a3b8; margin:0 0 24px; font-size:13px; font-weight:500; letter-spacing:0.5px; text-transform:uppercase;">
          Licença vencida
        </p>

        <div style="background:#fef2f2; border-radius:10px; padding:14px 20px; margin-bottom:28px;">
          <p style="margin:0; color:#b91c1c; font-size:14px; line-height:1.6;">
            ${mensagem}
          </p>
        </div>

        <div style="background:#f8fafc; border-radius:12px; padding:20px; text-align:left; border:1px solid #e2e8f0;">
          <p style="margin:0 0 4px; color:#64748b; font-size:11px; font-weight:600; text-transform:uppercase; letter-spacing:0.5px;">
            Contato para renovação
          </p>
          <a href="tel:+5511937209330" style="
            display:flex; align-items:center; gap:10px; margin-top:12px;
            color:#1e293b; text-decoration:none; font-size:15px; font-weight:500;
          ">
            <span style="font-size:20px;">📱</span> (11) 93720-9330
          </a>
          <a href="mailto:lucassmello29@gmail.com" style="
            display:flex; align-items:center; gap:10px; margin-top:10px;
            color:#1e293b; text-decoration:none; font-size:15px; font-weight:500;
          ">
            <span style="font-size:20px;">📧</span> lucassmello29@gmail.com
          </a>
        </div>
      </div>
    </div>
  `;
}

const Api = (() => {
  // ── Token management ──────────────────────────────────────────────────────
  function getToken()         { return localStorage.getItem('rh_token'); }
  function setToken(t)        { localStorage.setItem('rh_token', t); }
  function removeToken()      { localStorage.removeItem('rh_token'); localStorage.removeItem('rh_user'); }
  function getUser()          { try { return JSON.parse(localStorage.getItem('rh_user')); } catch { return null; } }
  function setUser(u)         { localStorage.setItem('rh_user', JSON.stringify(u)); }

  // ── Base request ──────────────────────────────────────────────────────────
  async function request(method, path, body = null, params = null) {
    let url = API_BASE + path;
    if (params) {
      const q = new URLSearchParams(
        Object.fromEntries(Object.entries(params).filter(([,v]) => v != null))
      );
      if (q.toString()) url += '?' + q;
    }

    const headers = { 'Content-Type': 'application/json' };
    const token = getToken();
    if (token) headers['Authorization'] = 'Bearer ' + token;

    const opts = { method, headers };
    if (body) opts.body = JSON.stringify(body);

    const res = await fetch(url, opts);

    if (res.status === 401) {
      removeToken();
      window.location.reload();
      return;
    }

    if (res.status === 402) {
      const data = await res.json().catch(() => ({}));
      _showLicenseBlock(data.valid_until, data.is_active);
      throw new Error('licenca_vencida');
    }

    if (res.status === 204) return null;

    const data = await res.json().catch(() => ({}));

    if (!res.ok) {
      const msg = data?.detail || data?.message || `Erro ${res.status}`;
      throw new Error(Array.isArray(msg) ? msg.map(e => e.msg).join('; ') : String(msg));
    }

    return data;
  }

  const get    = (path, params) => request('GET',    path, null, params);
  const post   = (path, body)   => request('POST',   path, body);
  const put    = (path, body)   => request('PUT',    path, body);
  const patch  = (path, body)   => request('PATCH',  path, body);
  const del    = (path)         => request('DELETE', path);

  // ── Download (Excel) ──────────────────────────────────────────────────────
  async function download(path, params, filename) {
    let url = API_BASE + path;
    if (params) {
      const q = new URLSearchParams(
        Object.fromEntries(Object.entries(params).filter(([,v]) => v != null))
      );
      if (q.toString()) url += '?' + q;
    }
    const token = getToken();
    const res = await fetch(url, {
      headers: token ? { Authorization: 'Bearer ' + token } : {}
    });
    if (!res.ok) throw new Error('Falha ao baixar arquivo');
    const blob = await res.blob();
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    a.click();
    URL.revokeObjectURL(a.href);
  }

  // ── Auth ──────────────────────────────────────────────────────────────────
  async function login(username, password) {
    const res = await fetch(API_BASE + '/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data?.detail || 'Credenciais inválidas');
    setToken(data.access_token);
    return data;
  }

  async function setupAdmin(payload) {
    const res = await fetch(API_BASE + '/auth/setup', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data?.detail || 'Erro no cadastro');
    setToken(data.access_token);
    return data;
  }

  async function me() {
    const data = await get('/auth/me');
    if (data) setUser(data);
    return data;
  }

  // ── Users ─────────────────────────────────────────────────────────────────
  const getUsers         = ()           => get('/users');
  const createUser       = (body)       => post('/users', body);
  const updateUser       = (id, body)   => patch(`/users/${id}`, body);
  const adminResetPwd    = (id, body)   => patch(`/users/${id}/password`, body);
  const changeMyPwd      = (body)       => patch('/users/me/password', body);

  // ── Dashboard ─────────────────────────────────────────────────────────────
  const getDashboard      = ()     => get('/reports/dashboard');
  const getAnnualPayroll  = (year) => get('/reports/annual-payroll', { year });

  // ── Employees ─────────────────────────────────────────────────────────────
  const getEmployees         = ()           => get('/employees');
  const getInactiveEmployees = ()           => get('/employees', { inactive: true });
  const getEmployee          = (id)         => get(`/employees/${id}`);
  const getEmployeeHistory = (id)         => get(`/employees/${id}/history`);
  const createEmployee     = (body)       => post('/employees', body);
  const updateEmployee     = (id, body)   => patch(`/employees/${id}`, body);
  const raiseEmployee      = (id, body)   => patch(`/employees/${id}/raise`, body);
  const inactivateEmp      = (id, reason) => post(`/employees/${id}/inactivate`, { reason });
  const reactivateEmp      = (id)         => post(`/employees/${id}/reactivate`, {});

  // ── Seamstresses ──────────────────────────────────────────────────────────
  const getSeamstresses          = ()           => get('/seamstresses');
  const getAllSeamstresses       = ()           => get('/seamstresses', { inactive: true });
  const createSeamstress         = (body)       => post('/seamstresses', body);
  const updateSeamstress         = (id, body)   => patch(`/seamstresses/${id}`, body);
  const getSeamstressPayments    = (id)         => get(`/seamstresses/${id}/payments`);
  const createPayment            = (id, body)   => post(`/seamstresses/${id}/payments`, body);
  const deleteSeamstressPayment  = (id)         => del(`/seamstresses/payments/${id}`);
  const getSeamstressMonthReport = (m, y)       => get('/seamstresses/report/month', { month: m, year: y });
  const closeSeamstressMonth     = (body)       => post('/seamstresses/close-month', body);

  // ── Payroll ───────────────────────────────────────────────────────────────
  const getPayrollPeriod    = (month, year) => get('/payroll/period', { month, year });
  const getEligible         = (month, year) => get('/payroll/eligible', { month, year });
  const batchCreatePayroll  = (body)        => post('/payroll/batch', body);
  const closeAllPayrolls    = (month, year, payment_date) => request('POST', `/payroll/period/close-all?month=${month}&year=${year}${payment_date ? '&payment_date='+payment_date : ''}`);
  const deletePayroll       = (id)          => del(`/payroll/${id}`);
  const updatePayrollFlags  = (id, body)    => patch(`/payroll/${id}/flags`, body);
  const updatePayrollItem   = (pid, iid, body) => patch(`/payroll/${pid}/items/${iid}`, body);
  const getPayroll        = (id)          => get(`/payroll/${id}`);
  const createPayroll     = (body)        => post('/payroll', body);
  const closePayroll      = (id, date)    => post(`/payroll/${id}/close`, { payment_date: date });
  const recalcPayroll     = (id)          => post(`/payroll/${id}/recalculate`, {});
  const addPayrollItem    = (id, body)    => post(`/payroll/${id}/items`, body);
  const deletePayrollItem = (pid, iid)    => del(`/payroll/${pid}/items/${iid}`);
  const getPayrollPdf     = (id)          => download(`/payroll/${id}/pdf`, null, `holerite_${id}.pdf`);

  async function openPayrollPdfTab(id) {
    const token = getToken();
    const res   = await fetch(`${API_BASE}/payroll/${id}/pdf`, {
      headers: token ? { Authorization: 'Bearer ' + token } : {}
    });
    if (!res.ok) throw new Error('Falha ao abrir holerite');
    const blob = await res.blob();
    const url  = URL.createObjectURL(blob);
    const tab  = window.open(url, '_blank');
    if (!tab) throw new Error('Permita pop-ups para abrir o holerite');
    setTimeout(() => URL.revokeObjectURL(url), 60000);
  }

  async function loadPayrollPdfInWindow(id, win) {
    const token = getToken();
    const res   = await fetch(`${API_BASE}/payroll/${id}/pdf`, {
      headers: token ? { Authorization: 'Bearer ' + token } : {}
    });
    if (!res.ok) throw new Error('Falha ao carregar holerite');
    const blob = await res.blob();
    const url  = URL.createObjectURL(blob);
    win.location.href = url;
    setTimeout(() => URL.revokeObjectURL(url), 60000);
  }

  // ── Vales ─────────────────────────────────────────────────────────────────
  const getAllVales  = ()             => get('/payroll/vales');
  const getVales    = (empId)        => get(`/payroll/employees/${empId}/vales`);
  const createVale  = (empId, body)  => post(`/payroll/employees/${empId}/vales`, body);
  const getVale     = (id)           => get(`/payroll/vales/${id}`);
  const updateVale  = (id, body)     => patch(`/payroll/vales/${id}`, body);
  const deleteVale  = (id)           => del(`/payroll/vales/${id}`);

  // ── Vacation ──────────────────────────────────────────────────────────────
  const getVacationOverview    = ()                => get('/vacation/company-overview');
  const getVacations           = ()                => get('/vacation/active');
  const getEmpVacations        = (id)              => get(`/vacation/employee/${id}`);
  const getVacation            = (id)              => get(`/vacation/${id}`);
  const getVacationEligibility = (id)              => get(`/vacation/employee/${id}/eligibility`);
  const previewVacation        = (body)            => post('/vacation/preview', body);
  const createVacation         = (body)            => post('/vacation', body);
  const updateVacation         = (id, body)        => patch(`/vacation/${id}`, body);
  const deleteVacation         = (id)              => del(`/vacation/${id}`);
  const startVacation          = (id, body)        => post(`/vacation/${id}/start`, body);
  const completeVacation       = (id)              => post(`/vacation/${id}/complete`, {});
  const cancelVacation         = (id)              => post(`/vacation/${id}/cancel`, {});
  const addVacationItem        = (id, body)        => post(`/vacation/${id}/items`, body);
  const updateVacationItem     = (id, iid, body)   => patch(`/vacation/${id}/items/${iid}`, body);
  const deleteVacationItem     = (id, iid)         => del(`/vacation/${id}/items/${iid}`);
  const waiveVacationPeriods   = (body)              => post('/vacation/waive-periods', body);
  const getThirteenth          = (id, year, parcela) => get(`/vacation/thirteenth/${id}`, { year, parcela });
  const getThirteenthBatch     = (year, parcela)     => get(`/vacation/thirteenth-batch`, { year, parcela });

  // ── 13º Salário (persistido) ──────────────────────────────────────────────
  const generateThirteenth      = (body)            => post('/thirteenth/generate', body);
  const generateThirteenthBatch = (body)            => post('/thirteenth/generate-batch', body);
  const listThirteenth          = (year, parcela)   => get('/thirteenth', { year, parcela });
  const updateThirteenth        = (id, body)        => patch(`/thirteenth/${id}`, body);
  const markThirteenthPaid      = (id)              => patch(`/thirteenth/${id}/mark-paid`);
  const deleteThirteenth        = (id)              => del(`/thirteenth/${id}`);
  const exportThirteenth        = (year, parcela)   => download('/thirteenth/export', { year, parcela }, '13_salario.xlsx');

  // ── Termination ───────────────────────────────────────────────────────────
  const getTerminations    = ()         => get('/vacation/terminations');
  const createTermination  = (body)     => post('/vacation/termination', body);
  const getTermination     = (id)       => get(`/vacation/termination/${id}`);
  const updateTermination  = (id, body) => put(`/vacation/termination/${id}`, body);
  const closeTermination   = (id)       => post(`/vacation/termination/${id}/close`, {});
  const deleteTermination  = (id)       => del(`/vacation/termination/${id}`);

  // ── Timesheet ─────────────────────────────────────────────────────────────
  const getTimesheet  = (empId, month, year) => get(`/timesheet/${empId}/report`, { month, year });
  const createEntry   = (body)               => post(`/timesheet/${body.employee_id}`, body);
  const updateEntry   = (id, body)           => patch(`/timesheet/entry/${id}`, body);
  const getHourBank         = (empId) => get(`/timesheet/${empId}/hour-bank`);
  const recalculateHourBank = (empId) => post(`/timesheet/${empId}/hour-bank/recalculate`, {});
  // Períodos
  const getTimesheetPeriod    = (m, y)        => get(`/timesheet/periods/${m}/${y}`);
  const openTimesheetPeriod   = (body)        => post('/timesheet/periods', body);
  const closeTimesheetPeriod  = (m, y)        => post(`/timesheet/periods/${m}/${y}/close`, {});
  const getEmployeeDays       = (empId, m, y) => get(`/timesheet/periods/${m}/${y}/employee/${empId}/days`);
  const saveEmployeeDays      = (empId, m, y, body) => post(`/timesheet/periods/${m}/${y}/employee/${empId}/save`, body);
  const getBankSummary        = (year)              => get('/timesheet/bank-summary', { year });
  const recalculateAllBanks  = ()                  => post('/timesheet/recalculate-all-banks', {});
  const batchDayLaunch       = (body)               => post('/timesheet/batch-day', body);

  // ── Audit ─────────────────────────────────────────────────────────────────
  const getAuditLogs     = (p) => get('/audit/logs',    p);
  const getAuditStats    = ()  => get('/audit/stats');
  const getAuditUsers    = ()  => get('/audit/users');
  const getAuditActions  = ()  => get('/audit/actions');
  const dlAuditLogs      = (p) => download('/audit/export', p, 'auditoria.xlsx');

  // ── Reports ───────────────────────────────────────────────────────────────
  const dlPayroll      = (m, y) => download('/reports/payroll',      { month: m, year: y }, `folha_${m}_${y}.xlsx`);
  const dlTimesheet    = (m, y, eid) => download('/reports/timesheet', { month: m, year: y, employee_id: eid }, `ponto_${m}_${y}.xlsx`);
  const dlEmployees    = (inc) => download('/reports/employees',     { include_inactive: inc }, 'funcionarios.xlsx');
  const dlVacations    = ()    => download('/reports/vacations',     null, 'ferias.xlsx');
  const dlTerminations = ()    => download('/reports/terminations',  null, 'rescisoes.xlsx');
  const dlHourBank     = ()    => download('/reports/hour-bank',     null, 'banco_horas.xlsx');

  // ── Licença ────────────────────────────────────────────────────────────────
  const getLicense        = () => request('GET', '/license');
  const renewLicense      = (data) => request('POST', '/license/renew', data);
  const deactivateLicense = (data) => request('POST', '/license/deactivate', data);

  const getBackupInfo = () => request('GET', '/backup/info');

  return {
    request,
    getToken, setToken, removeToken, getUser, setUser,
    login, setupAdmin, me,
    getUsers, createUser, updateUser, adminResetPwd, changeMyPwd,
    getDashboard, getAnnualPayroll,
    getEmployees, getInactiveEmployees, getEmployee, getEmployeeHistory, createEmployee, updateEmployee, raiseEmployee, inactivateEmp, reactivateEmp,
    getSeamstresses, getAllSeamstresses, createSeamstress, updateSeamstress, getSeamstressPayments, createPayment, deleteSeamstressPayment, getSeamstressMonthReport, closeSeamstressMonth,
    getPayrollPeriod, getEligible, batchCreatePayroll, closeAllPayrolls,
    getPayroll, createPayroll, deletePayroll, closePayroll, recalcPayroll,
    updatePayrollFlags, addPayrollItem, updatePayrollItem, deletePayrollItem, getPayrollPdf,
    getAllVales, getVales, createVale, getVale, updateVale, deleteVale,
    getVacationOverview, getVacations, getEmpVacations, getVacation, getVacationEligibility, previewVacation,
    createVacation, updateVacation, deleteVacation, waiveVacationPeriods,
    startVacation, completeVacation, cancelVacation,
    addVacationItem, updateVacationItem, deleteVacationItem, getThirteenth, getThirteenthBatch,
    getTerminations, createTermination, getTermination, updateTermination, closeTermination, deleteTermination,
    getTimesheet, createEntry, updateEntry, getHourBank, recalculateHourBank, recalculateAllBanks,
    getTimesheetPeriod, openTimesheetPeriod, closeTimesheetPeriod, getEmployeeDays, saveEmployeeDays, getBankSummary, batchDayLaunch,
    getAuditLogs, getAuditStats, getAuditUsers, getAuditActions, dlAuditLogs,
    dlPayroll, dlTimesheet, dlEmployees, dlVacations, dlTerminations, dlHourBank,
    generateThirteenth, generateThirteenthBatch, listThirteenth, updateThirteenth, markThirteenthPaid, deleteThirteenth, exportThirteenth,
    getLicense, renewLicense, deactivateLicense,
    getBackupInfo,
    openPayrollPdfTab,
    loadPayrollPdfInWindow,
  };
})();
