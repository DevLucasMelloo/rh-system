/**
 * app.js — Router, auth, sidebar, login.
 */

// ── Sidebar toggle ────────────────────────────────────────────────────────────
function toggleSidebar() {
  document.getElementById('sidebar').classList.toggle('collapsed');
}

// ── Auth ──────────────────────────────────────────────────────────────────────
async function doLogin() {
  const username = document.getElementById('login-username').value.trim();
  const pass     = document.getElementById('login-password').value;
  const errEl    = document.getElementById('login-error');
  const btn      = document.getElementById('btn-login');

  errEl.innerHTML = '';
  if (!username || !pass) {
    errEl.innerHTML = '<div class="alert alert-error">Preencha usuário e senha.</div>';
    return;
  }

  btn.disabled = true;
  btn.innerHTML = '<div class="spinner"></div> Entrando...';

  try {
    await Api.login(username, pass);
    await Api.me();
    showApp();
  } catch (e) {
    errEl.innerHTML = `<div class="alert alert-error">${e.message}</div>`;
    btn.disabled = false;
    btn.innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"/><polyline points="10 17 15 12 10 7"/><line x1="15" y1="12" x2="3" y2="12"/></svg> Entrar';
  }
}

async function doRegister() {
  const name         = document.getElementById('reg-name').value.trim();
  const username     = document.getElementById('reg-username').value.trim();
  const pass         = document.getElementById('reg-password').value;
  const confirm      = document.getElementById('reg-confirm').value;
  const company      = document.getElementById('reg-company').value.trim();
  const cnpj         = document.getElementById('reg-cnpj').value.replace(/\D/g, '');
  const companyEmail = document.getElementById('reg-company-email').value.trim();
  const errEl        = document.getElementById('register-error');
  const btn          = document.getElementById('btn-register');

  errEl.innerHTML = '';
  if (!name || !username || !pass || !company || !cnpj) {
    errEl.innerHTML = '<div class="alert alert-error">Preencha todos os campos obrigatórios.</div>';
    return;
  }
  if (pass !== confirm) {
    errEl.innerHTML = '<div class="alert alert-error">As senhas não coincidem.</div>';
    return;
  }

  btn.disabled = true;
  btn.innerHTML = '<div class="spinner"></div> Criando...';

  try {
    await Api.setupAdmin({ name, username, password: pass, razao_social: company, cnpj, company_email: companyEmail });
    await Api.me();
    showApp();
  } catch (e) {
    errEl.innerHTML = `<div class="alert alert-error">${e.message}</div>`;
    btn.disabled = false;
    btn.innerHTML = 'Criar Conta';
  }
}

function doLogout() {
  Api.removeToken();
  document.getElementById('app').classList.add('hidden');
  document.getElementById('login-page').classList.remove('hidden');
  document.getElementById('login-username').value = '';
  document.getElementById('login-password').value = '';
  document.getElementById('login-error').innerHTML = '';
  const btn = document.getElementById('btn-login');
  btn.disabled = false;
  btn.innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"/><polyline points="10 17 15 12 10 7"/><line x1="15" y1="12" x2="3" y2="12"/></svg> Entrar';
}

function showApp() {
  document.getElementById('login-page').classList.add('hidden');
  document.getElementById('app').classList.remove('hidden');
  applySidebarAccess();
  navigate('dashboard');
}

function applySidebarAccess() {
  const user = Api.getUser();
  if (!user || user.role === 'admin' || !user.allowed_modules) {
    document.querySelectorAll('.nav-item[data-page]').forEach(el => el.style.display = '');
    return;
  }
  let allowed;
  try { allowed = JSON.parse(user.allowed_modules); } catch { allowed = null; }
  if (!allowed) return;
  document.querySelectorAll('.nav-item[data-page]').forEach(el => {
    el.style.display = allowed.includes(el.dataset.page) ? '' : 'none';
  });
}

function switchLoginTab(tab) {
  document.getElementById('tab-login').classList.toggle('active', tab === 'login');
  document.getElementById('tab-register').classList.toggle('active', tab === 'register');
  document.getElementById('form-login').classList.toggle('hidden', tab !== 'login');
  document.getElementById('form-register').classList.toggle('hidden', tab !== 'register');
}

// ── Audit page ────────────────────────────────────────────────────────────────
// (PageSettings is defined in pages/settings.js loaded before this file)
const PageAudit = {
  async render(container) {
    container.innerHTML = `
      <div class="page-header">
        <div><h1>Auditoria</h1><p>Histórico de ações do sistema</p></div>
      </div>
      <div class="table-wrapper">
        <table>
          <thead><tr><th>Data</th><th>Ação</th><th>Entidade</th><th>Descrição</th></tr></thead>
          <tbody id="audit-tbody">${loadingRow(4)}</tbody>
        </table>
      </div>`;
    document.getElementById('audit-tbody').innerHTML = emptyRow('Nenhum registro de auditoria.', 4);
  }
};

// ── Router ────────────────────────────────────────────────────────────────────
// Declarado APÓS PageAudit e PageSettings para evitar temporal dead zone
const PAGES = {
  dashboard:    PageDashboard,
  employees:    PageEmployees,
  seamstresses: PageSeamstresses,
  payroll:      PagePayroll,
  vales:        PageVales,
  rescisao:     PageRescisao,
  vacation:     PageVacation,
  timesheet:    PageTimesheet,
  bankhours:    PageBankHours,
  reports:      PageReports,
  settings:     PageSettings,
  audit:        PageAudit,
};

let currentPage = null;

function navigate(page) {
  closeModal();
  document.querySelectorAll('.nav-item').forEach(el => {
    el.classList.toggle('active', el.dataset.page === page);
  });
  currentPage = page;
  const container = document.getElementById('page-content');
  const mod = PAGES[page];
  if (mod) {
    Promise.resolve(mod.render(container)).catch(err => {
      container.innerHTML = `<div style="padding:40px"><div class="alert alert-error"><strong>Erro ao carregar "${page}":</strong><br>${err.message}</div></div>`;
      console.error('navigate error:', err);
    });
  } else {
    container.innerHTML = `<div style="padding:40px"><h1>Página não encontrada: ${page}</h1></div>`;
  }
}

// ── Startup ───────────────────────────────────────────────────────────────────
(async function init() {
  // Verifica se precisa de setup inicial
  try {
    const res = await fetch('http://localhost:8080/api/v1/auth/setup-status');
    const { needs_setup } = await res.json();
    if (!needs_setup) {
      const tabReg = document.getElementById('tab-register');
      if (tabReg) tabReg.style.display = 'none';
    } else {
      switchLoginTab('register');
    }
  } catch { /* backend offline */ }

  // Auto-login se tiver token salvo
  if (Api.getToken()) {
    try {
      await Api.me();
      showApp();
    } catch {
      Api.removeToken();
    }
  }
})();
