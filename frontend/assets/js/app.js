/**
 * app.js — Router, auth, sidebar, login.
 */

// ── Router ────────────────────────────────────────────────────────────────────
const PAGES = {
  dashboard:    PageDashboard,
  employees:    PageEmployees,
  seamstresses: PageSeamstresses,
  payroll:      PagePayroll,
  vales:        PageVales,
  rescisao:     PageRescisao,
  vacation:     PageVacation,
  timesheet:    PageTimesheet,
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
    mod.render(container);
  } else {
    container.innerHTML = `<div class="page-wrapper"><h1>Página não encontrada</h1></div>`;
  }
}

// ── Sidebar toggle ────────────────────────────────────────────────────────────
function toggleSidebar() {
  document.getElementById('sidebar').classList.toggle('collapsed');
}

// ── Auth ──────────────────────────────────────────────────────────────────────
async function doLogin() {
  const email = document.getElementById('login-email').value.trim();
  const pass  = document.getElementById('login-password').value;
  const errEl = document.getElementById('login-error');
  const btn   = document.getElementById('btn-login');

  errEl.innerHTML = '';
  if (!email || !pass) {
    errEl.innerHTML = '<div class="alert alert-error">Preencha email e senha.</div>';
    return;
  }

  btn.disabled = true;
  btn.innerHTML = '<div class="spinner"></div> Entrando...';

  try {
    await Api.login(email, pass);
    await Api.me();
    showApp();
  } catch (e) {
    errEl.innerHTML = `<div class="alert alert-error">${e.message}</div>`;
    btn.disabled = false;
    btn.innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"/><polyline points="10 17 15 12 10 7"/><line x1="15" y1="12" x2="3" y2="12"/></svg> Entrar';
  }
}

async function doRegister() {
  const name    = document.getElementById('reg-name').value.trim();
  const email   = document.getElementById('reg-email').value.trim();
  const pass    = document.getElementById('reg-password').value;
  const confirm = document.getElementById('reg-confirm').value;
  const company = document.getElementById('reg-company').value.trim();
  const cnpj    = document.getElementById('reg-cnpj').value.replace(/\D/g,'');
  const companyEmail = document.getElementById('reg-company-email').value.trim();
  const errEl   = document.getElementById('register-error');
  const btn     = document.getElementById('btn-register');

  errEl.innerHTML = '';
  if (!name || !email || !pass || !company || !cnpj) {
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
    await Api.setupAdmin({ name, email, password: pass, razao_social: company, cnpj, company_email: companyEmail });
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
  document.getElementById('login-email').value = '';
  document.getElementById('login-password').value = '';
}

function showApp() {
  document.getElementById('login-page').classList.add('hidden');
  document.getElementById('app').classList.remove('hidden');
  navigate('dashboard');
}

function switchLoginTab(tab) {
  document.getElementById('tab-login').classList.toggle('active', tab === 'login');
  document.getElementById('tab-register').classList.toggle('active', tab === 'register');
  document.getElementById('form-login').classList.toggle('hidden', tab !== 'login');
  document.getElementById('form-register').classList.toggle('hidden', tab !== 'register');
}

// ── Stub pages (settings, audit) ──────────────────────────────────────────────
const PageSettings = {
  render(container) {
    const user = Api.getUser();
    container.innerHTML = `
      <div class="page-header">
        <div><h1>Configurações</h1><p>Configurações da conta e da empresa</p></div>
      </div>
      <div class="card" style="max-width:500px">
        <div class="card-body">
          <h3 style="margin-bottom:16px;font-size:15px">Usuário logado</h3>
          <div class="detail-grid">
            <div class="detail-item"><label>Nome</label><span>${user?.name || '—'}</span></div>
            <div class="detail-item"><label>Email</label><span>${user?.email || '—'}</span></div>
            <div class="detail-item"><label>Perfil</label><span>${user?.role || '—'}</span></div>
          </div>
          <div style="margin-top:20px">
            <button class="btn btn-danger" onclick="doLogout()">Sair da conta</button>
          </div>
        </div>
      </div>`;
  }
};

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
    try {
      // audit endpoint may not exist — graceful fallback
      const data = await fetch(Api.getToken ? `${window.location.origin}/api/v1/audit` : null).catch(() => null);
      document.getElementById('audit-tbody').innerHTML = emptyRow('Nenhum registro de auditoria.', 4);
    } catch {
      document.getElementById('audit-tbody').innerHTML = emptyRow('Nenhum registro de auditoria.', 4);
    }
  }
};

// ── Startup ───────────────────────────────────────────────────────────────────
(async function init() {
  if (Api.getToken()) {
    try {
      await Api.me();
      showApp();
    } catch {
      Api.removeToken();
    }
  }
})();
