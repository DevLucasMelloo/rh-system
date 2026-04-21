/**
 * API Client — RH System
 * Centraliza todas as chamadas ao backend FastAPI.
 */

const API_BASE = 'http://localhost:8080/api/v1';

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
  const getDashboard = () => get('/reports/dashboard');

  // ── Employees ─────────────────────────────────────────────────────────────
  const getEmployees         = ()           => get('/employees');
  const getInactiveEmployees = ()           => get('/employees', { inactive: true });
  const getEmployee          = (id)         => get(`/employees/${id}`);
  const getEmployeeHistory = (id)         => get(`/employees/${id}/history`);
  const createEmployee     = (body)       => post('/employees', body);
  const updateEmployee     = (id, body)   => patch(`/employees/${id}`, body);
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
  const getPayrollPeriod  = (month, year) => get('/payroll/period', { month, year });
  const getPayroll        = (id)          => get(`/payroll/${id}`);
  const createPayroll     = (body)        => post('/payroll', body);
  const closePayroll      = (id, date)    => post(`/payroll/${id}/close`, { payment_date: date });
  const recalcPayroll     = (id)          => post(`/payroll/${id}/recalculate`, {});
  const addPayrollItem    = (id, body)    => post(`/payroll/${id}/items`, body);
  const deletePayrollItem = (pid, iid)    => del(`/payroll/${pid}/items/${iid}`);
  const getPayrollPdf     = (id)          => download(`/payroll/${id}/pdf`, null, `holerite_${id}.pdf`);

  // ── Vales ─────────────────────────────────────────────────────────────────
  const getAllVales  = ()             => get('/payroll/vales');
  const getVales    = (empId)        => get(`/payroll/employees/${empId}/vales`);
  const createVale  = (empId, body)  => post(`/payroll/employees/${empId}/vales`, body);
  const getVale     = (id)           => get(`/payroll/vales/${id}`);

  // ── Vacation ──────────────────────────────────────────────────────────────
  const getVacations      = ()           => get('/vacation/active');
  const getEmpVacations   = (id)         => get(`/vacation/employee/${id}`);
  const createVacation    = (body)       => post('/vacation', body);
  const startVacation     = (id, body)   => post(`/vacation/${id}/start`, body);
  const completeVacation  = (id)         => post(`/vacation/${id}/complete`, {});
  const cancelVacation    = (id)         => post(`/vacation/${id}/cancel`, {});
  const getThirteenth     = (id, year, parcela) => get(`/vacation/thirteenth/${id}`, { year, parcela });

  // ── Termination ───────────────────────────────────────────────────────────
  const getTerminations   = ()      => get('/vacation/terminations');
  const createTermination = (body)  => post('/vacation/termination', body);
  const getTermination    = (id)    => get(`/vacation/termination/${id}`);

  // ── Timesheet ─────────────────────────────────────────────────────────────
  const getTimesheet  = (empId, month, year) => get(`/timesheet/${empId}/report`, { month, year });
  const createEntry   = (body)               => post(`/timesheet/${body.employee_id}`, body);
  const updateEntry   = (id, body)           => patch(`/timesheet/entry/${id}`, body);
  const getHourBank   = (empId)              => get(`/timesheet/${empId}/hour-bank`);
  // Períodos
  const getTimesheetPeriod    = (m, y)        => get(`/timesheet/periods/${m}/${y}`);
  const openTimesheetPeriod   = (body)        => post('/timesheet/periods', body);
  const closeTimesheetPeriod  = (m, y)        => post(`/timesheet/periods/${m}/${y}/close`, {});
  const getEmployeeDays       = (empId, m, y) => get(`/timesheet/periods/${m}/${y}/employee/${empId}/days`);
  const saveEmployeeDays      = (empId, m, y, body) => post(`/timesheet/periods/${m}/${y}/employee/${empId}/save`, body);

  // ── Reports ───────────────────────────────────────────────────────────────
  const dlPayroll      = (m, y) => download('/reports/payroll',      { month: m, year: y }, `folha_${m}_${y}.xlsx`);
  const dlTimesheet    = (m, y, eid) => download('/reports/timesheet', { month: m, year: y, employee_id: eid }, `ponto_${m}_${y}.xlsx`);
  const dlEmployees    = (inc) => download('/reports/employees',     { include_inactive: inc }, 'funcionarios.xlsx');
  const dlVacations    = ()    => download('/reports/vacations',     null, 'ferias.xlsx');
  const dlTerminations = ()    => download('/reports/terminations',  null, 'rescisoes.xlsx');
  const dlHourBank     = ()    => download('/reports/hour-bank',     null, 'banco_horas.xlsx');

  return {
    getToken, setToken, removeToken, getUser, setUser,
    login, setupAdmin, me,
    getUsers, createUser, updateUser, adminResetPwd, changeMyPwd,
    getDashboard,
    getEmployees, getInactiveEmployees, getEmployee, getEmployeeHistory, createEmployee, updateEmployee, inactivateEmp, reactivateEmp,
    getSeamstresses, getAllSeamstresses, createSeamstress, updateSeamstress, getSeamstressPayments, createPayment, deleteSeamstressPayment, getSeamstressMonthReport, closeSeamstressMonth,
    getPayrollPeriod, getPayroll, createPayroll, closePayroll, recalcPayroll,
    addPayrollItem, deletePayrollItem, getPayrollPdf,
    getAllVales, getVales, createVale, getVale,
    getVacations, getEmpVacations, createVacation, startVacation, completeVacation, cancelVacation, getThirteenth,
    getTerminations, createTermination, getTermination,
    getTimesheet, createEntry, updateEntry, getHourBank,
    getTimesheetPeriod, openTimesheetPeriod, closeTimesheetPeriod, getEmployeeDays, saveEmployeeDays,
    dlPayroll, dlTimesheet, dlEmployees, dlVacations, dlTerminations, dlHourBank,
  };
})();
