const PageLicense = (() => {

  async function render(container) {
    container.innerHTML = `
      <div class="page-header">
        <div>
          <h1>Gerenciar Licença</h1>
          <p>Renovar ou desativar a licença do sistema</p>
        </div>
      </div>

      <!-- Status atual -->
      <div class="card" style="margin-bottom:24px">
        <div class="card-header">Status da Licença</div>
        <div class="card-body" id="license-status-body">
          <div style="color:var(--text-muted)">Carregando...</div>
        </div>
      </div>

      <!-- Renovar -->
      <div class="card" style="margin-bottom:24px">
        <div class="card-header">Renovar Licença</div>
        <div class="card-body">
          <div class="form-row">
            <div class="form-group">
              <label>Senha Master *</label>
              <input class="form-control" type="password" id="lic-pwd" placeholder="Senha master">
            </div>
            <div class="form-group">
              <label>Válida até *</label>
              <input class="form-control" type="date" id="lic-date">
            </div>
          </div>
          <div id="lic-renew-msg"></div>
          <button class="btn btn-primary" onclick="PageLicense.renovar()">
            ✓ Renovar Licença
          </button>
        </div>
      </div>

      <!-- Desativar -->
      <div class="card">
        <div class="card-header" style="color:var(--danger)">Zona de Perigo</div>
        <div class="card-body">
          <p style="font-size:13px;color:var(--text-muted);margin-bottom:16px">
            Desativar a licença bloqueia imediatamente o acesso ao sistema para todos os usuários.
          </p>
          <div class="form-group">
            <label>Senha Master *</label>
            <input class="form-control" type="password" id="lic-deact-pwd" placeholder="Senha master">
          </div>
          <div id="lic-deact-msg"></div>
          <button class="btn btn-danger" onclick="PageLicense.desativar()">
            ✕ Desativar Licença
          </button>
        </div>
      </div>`;

    await _loadStatus();

    // Preenche data padrão: hoje + 30 dias
    const def = new Date();
    def.setDate(def.getDate() + 30);
    const dateEl = document.getElementById('lic-date');
    if (dateEl) dateEl.value = def.toISOString().split('T')[0];
  }

  async function _loadStatus() {
    const el = document.getElementById('license-status-body');
    if (!el) return;
    try {
      const lic = await Api.getLicense();
      const dataVenc = new Date(lic.valid_until + 'T00:00:00').toLocaleDateString('pt-BR');
      const cor = lic.expired ? 'var(--danger)' : lic.days_remaining <= 10 ? 'var(--warning)' : 'var(--success)';
      const status = lic.expired ? 'Expirada' : !lic.is_active ? 'Desativada' : 'Ativa';
      const statusBg = lic.expired || !lic.is_active ? 'var(--danger-light)' : 'var(--success-light)';
      const statusCor = lic.expired || !lic.is_active ? 'var(--danger)' : 'var(--success)';

      el.innerHTML = `
        <div style="display:flex;flex-wrap:wrap;gap:24px;align-items:center">
          <div>
            <div style="font-size:11px;font-weight:600;text-transform:uppercase;color:var(--text-muted);margin-bottom:4px">Status</div>
            <span style="background:${statusBg};color:${statusCor};padding:4px 14px;border-radius:20px;font-weight:600;font-size:14px">${status}</span>
          </div>
          <div>
            <div style="font-size:11px;font-weight:600;text-transform:uppercase;color:var(--text-muted);margin-bottom:4px">Válida até</div>
            <div style="font-size:18px;font-weight:700;color:${cor}">${dataVenc}</div>
          </div>
          <div>
            <div style="font-size:11px;font-weight:600;text-transform:uppercase;color:var(--text-muted);margin-bottom:4px">Dias restantes</div>
            <div style="font-size:18px;font-weight:700;color:${cor}">${lic.days_remaining >= 0 ? lic.days_remaining : 0}</div>
          </div>
        </div>`;
    } catch (e) {
      el.innerHTML = `<div class="alert alert-error">${e.message}</div>`;
    }
  }

  async function renovar() {
    const pwd    = document.getElementById('lic-pwd')?.value;
    const date   = document.getElementById('lic-date')?.value;
    const msgEl  = document.getElementById('lic-renew-msg');
    if (!msgEl) return;

    if (!pwd || !date) {
      msgEl.innerHTML = '<div class="alert alert-error">Preencha senha e data.</div>';
      return;
    }

    try {
      const r = await Api.renewLicense({ master_password: pwd, valid_until: date });
      msgEl.innerHTML = `<div class="alert alert-success">✓ ${r.message}</div>`;
      document.getElementById('lic-pwd').value = '';
      await _loadStatus();
    } catch (e) {
      msgEl.innerHTML = `<div class="alert alert-error">${e.message}</div>`;
    }
  }

  async function desativar() {
    const pwd   = document.getElementById('lic-deact-pwd')?.value;
    const msgEl = document.getElementById('lic-deact-msg');
    if (!msgEl) return;

    if (!pwd) {
      msgEl.innerHTML = '<div class="alert alert-error">Digite a senha master.</div>';
      return;
    }
    if (!confirm('Tem certeza? Isso vai bloquear o acesso de todos os usuários imediatamente.')) return;

    try {
      const r = await Api.deactivateLicense({ master_password: pwd });
      msgEl.innerHTML = `<div class="alert alert-warning">⚠ ${r.message}</div>`;
      document.getElementById('lic-deact-pwd').value = '';
      await _loadStatus();
    } catch (e) {
      msgEl.innerHTML = `<div class="alert alert-error">${e.message}</div>`;
    }
  }

  return { render, renovar, desativar };
})();
