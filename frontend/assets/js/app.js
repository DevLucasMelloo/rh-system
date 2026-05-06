/**
 * app.js — Router, auth, sidebar, login.
 */

// ── Sidebar toggle ────────────────────────────────────────────────────────────
function toggleSidebar() {
  const sidebar  = document.getElementById('sidebar');
  const overlay  = document.getElementById('sidebar-overlay');
  const isMobile = window.innerWidth <= 768;
  if (isMobile) {
    const open = sidebar.classList.toggle('mobile-open');
    if (overlay) overlay.style.display = open ? 'block' : 'none';
  } else {
    sidebar.classList.toggle('collapsed');
  }
}

function closeSidebar() {
  const isMobile = window.innerWidth <= 768;
  if (!isMobile) return;
  const sidebar = document.getElementById('sidebar');
  const overlay = document.getElementById('sidebar-overlay');
  sidebar.classList.remove('mobile-open');
  if (overlay) overlay.style.display = 'none';
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

// ── Esqueceu a senha ───────────────────────────────────────────────────────────
function openForgotPassword() {
  openModal('Recuperar Senha', `
    <p style="color:var(--text-muted);font-size:13px;margin-bottom:16px;line-height:1.5">
      Informe seu usuário de login. Se houver um e-mail de recuperação cadastrado,
      você receberá um link para redefinir sua senha.
    </p>
    <div class="form-group">
      <label>Usuário (login)</label>
      <input class="form-control" id="fp-username" placeholder="Ex: admin" autocomplete="username">
    </div>
    <div id="fp-msg"></div>`, `
    <button class="btn btn-secondary" onclick="closeModal()">Cancelar</button>
    <button class="btn btn-primary" id="fp-btn" onclick="doForgotPassword()">Enviar Link</button>`);
}

async function doForgotPassword() {
  const username = (document.getElementById('fp-username')?.value || '').trim();
  const msgEl    = document.getElementById('fp-msg');
  const btn      = document.getElementById('fp-btn');
  if (!username) {
    if (msgEl) msgEl.innerHTML = '<div class="alert alert-error">Informe o usuário.</div>';
    return;
  }
  if (btn) { btn.disabled = true; btn.textContent = 'Enviando...'; }
  try {
    await Api.forgotPassword(username);
    if (msgEl) msgEl.innerHTML = `
      <div class="alert" style="background:#f0fdf4;border-color:#86efac;color:#166534">
        Se o usuário existir e tiver e-mail cadastrado, o link foi enviado.
      </div>`;
    if (btn) btn.style.display = 'none';
  } catch (e) {
    if (msgEl) msgEl.innerHTML = `<div class="alert alert-error">${e.message}</div>`;
    if (btn) { btn.disabled = false; btn.textContent = 'Enviar Link'; }
  }
}

// ── Redefinição de senha via link (token na URL) ────────────────────────────
function showResetPasswordForm(token) {
  document.getElementById('login-page').classList.remove('hidden');
  document.getElementById('app').classList.add('hidden');

  // Substitui o conteúdo do login-card por um formulário de reset
  const card = document.querySelector('.login-card');
  if (!card) return;
  card.innerHTML = `
    <h1>RH System</h1>
    <p class="subtitle">Redefinição de Senha</p>
    <div id="reset-error"></div>
    <div class="form-group">
      <label>Nova Senha</label>
      <input type="password" class="form-control" id="reset-pwd" placeholder="Mínimo 4 caracteres"
             onkeydown="if(event.key==='Enter') document.getElementById('reset-pwd2').focus()">
    </div>
    <div class="form-group">
      <label>Confirmar Nova Senha</label>
      <input type="password" class="form-control" id="reset-pwd2" placeholder="Repita a senha"
             onkeydown="if(event.key==='Enter') doResetPassword('${token}')">
    </div>
    <button class="btn btn-primary btn-lg" id="btn-reset" onclick="doResetPassword('${token}')">
      Redefinir Senha
    </button>
    <button type="button" onclick="window.location.href='/'"
      style="background:none;border:none;color:var(--text-muted);font-size:13px;
             cursor:pointer;margin-top:8px;width:100%;text-align:center">
      Voltar para o login
    </button>`;
}

async function doResetPassword(token) {
  const pwd    = document.getElementById('reset-pwd')?.value || '';
  const pwd2   = document.getElementById('reset-pwd2')?.value || '';
  const errEl  = document.getElementById('reset-error');
  const btn    = document.getElementById('btn-reset');

  if (!pwd || pwd !== pwd2) {
    if (errEl) errEl.innerHTML = '<div class="alert alert-error">As senhas não coincidem ou estão vazias.</div>';
    return;
  }
  if (btn) { btn.disabled = true; btn.textContent = 'Redefinindo...'; }
  try {
    await Api.resetPassword(token, pwd);
    if (errEl) errEl.innerHTML = `
      <div class="alert" style="background:#f0fdf4;border-color:#86efac;color:#166534">
        Senha redefinida! Redirecionando para o login...
      </div>`;
    setTimeout(() => window.location.href = '/', 2000);
  } catch (e) {
    if (errEl) errEl.innerHTML = `<div class="alert alert-error">${e.message}</div>`;
    if (btn) { btn.disabled = false; btn.textContent = 'Redefinir Senha'; }
  }
}

async function checkLicenseBanner() {
  try {
    const lic = await Api.getLicense();
    const banner = document.getElementById('license-banner');
    if (!banner) return;
    if (lic.days_remaining <= 10 && !lic.expired) {
      const cor = lic.days_remaining <= 3 ? '#dc2626' : '#d97706';
      const bg  = lic.days_remaining <= 3 ? '#fef2f2' : '#fffbeb';
      const borda = lic.days_remaining <= 3 ? '#fca5a5' : '#fcd34d';
      const dataVenc = new Date(lic.valid_until + 'T00:00:00').toLocaleDateString('pt-BR');
      banner.style.display = 'block';
      banner.innerHTML = `
        <div style="
          background:${bg}; border:1px solid ${borda}; border-left:4px solid ${cor};
          border-radius:8px; padding:12px 20px; margin:16px 24px 0;
          display:flex; align-items:center; gap:12px; font-size:14px; color:${cor};
        ">
          <span style="font-size:20px;">${lic.days_remaining <= 3 ? '🚨' : '⚠️'}</span>
          <span>
            <strong>Atenção:</strong> sua licença vence em
            <strong>${dataVenc}</strong>
            (${lic.days_remaining === 0 ? 'hoje' : `${lic.days_remaining} dia${lic.days_remaining > 1 ? 's' : ''}`}).
            Entre em contato para renovar.
          </span>
        </div>`;
    } else {
      banner.style.display = 'none';
    }
  } catch { /* silencioso — não bloqueia o app */ }
}

function showApp() {
  document.getElementById('login-page').classList.add('hidden');
  document.getElementById('app').classList.remove('hidden');
  applySidebarAccess();
  navigate(_firstAllowedPage());
  checkLicenseBanner();
}

function _firstAllowedPage() {
  const user = Api.getUser();
  if (!user || user.role === 'admin' || !user.allowed_modules) return 'dashboard';
  let allowed;
  try { allowed = JSON.parse(user.allowed_modules); } catch { return 'dashboard'; }
  if (!allowed || !allowed.length) return 'dashboard';
  return allowed[0];
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

// PageAudit is defined in pages/audit.js

// ── Router ────────────────────────────────────────────────────────────────────
// Declarado APÓS PageAudit e PageSettings para evitar temporal dead zone
const PAGES = {
  dashboard:    PageDashboard,
  employees:    PageEmployees,
  seamstresses: PageSeamstresses,
  payroll:      PagePayroll,
  summary:      PageSummary,
  vales:        PageVales,
  rescisao:     PageRescisao,
  vacation:     PageVacation,
  thirteenth:   PageThirteenth,
  timesheet:    PageTimesheet,
  bankhours:    PageBankHours,
  reports:      PageReports,
  backup:       PageBackup,
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
    const base = window.location.port === '3000' ? 'http://localhost:8080/api/v1' : `${window.location.origin}/api/v1`;
    const res = await fetch(`${base}/auth/setup-status`);
    const { needs_setup } = await res.json();
    if (!needs_setup) {
      const tabReg = document.getElementById('tab-register');
      if (tabReg) tabReg.style.display = 'none';
    } else {
      switchLoginTab('register');
    }
  } catch { /* backend offline */ }

  // Verifica se há token de reset na URL
  const urlParams = new URLSearchParams(window.location.search);
  const resetToken = urlParams.get('reset_token');
  if (resetToken) {
    showResetPasswordForm(resetToken);
    return;
  }

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
