const PageSettings = (() => {
  let users = [];

  const ALL_MODULES = [
    { key: 'dashboard',    label: 'Dashboard' },
    { key: 'employees',    label: 'Funcionários' },
    { key: 'seamstresses', label: 'Costureiras' },
    { key: 'payroll',      label: 'Folha de Pagamento' },
    { key: 'vales',        label: 'Vales' },
    { key: 'rescisao',     label: 'Rescisão' },
    { key: 'vacation',     label: 'Férias' },
    { key: 'timesheet',    label: 'Ponto' },
    { key: 'reports',      label: 'Relatórios' },
    { key: 'audit',        label: 'Auditoria' },
  ];

  function fmtRole(role) {
    const map = { admin: 'Administrador', rh: 'RH', financeiro: 'Financeiro' };
    return map[role] || role || '—';
  }

  function parseModules(str) {
    if (!str) return null;
    try { return JSON.parse(str); } catch { return null; }
  }

  async function render(container) {
    let user = Api.getUser();
    if (!user) {
      try { user = await Api.me(); } catch {}
    }

    const admin = user?.role === 'admin';

    container.innerHTML = `
      <div class="page-header">
        <div><h1>Configurações</h1><p>Conta, senha e usuários do sistema</p></div>
      </div>

      <div style="display:grid;grid-template-columns:${admin ? '1fr 1fr' : '400px'};gap:24px;align-items:start">

        <!-- Minha conta -->
        <div class="card">
          <div class="card-header">Minha Conta</div>
          <div class="card-body">
            <div class="detail-grid" style="margin-bottom:20px">
              <div class="detail-item"><label>Nome</label><span>${user?.name || '—'}</span></div>
              <div class="detail-item"><label>Usuário</label><span>${user?.username || '—'}</span></div>
              <div class="detail-item"><label>Perfil</label><span>${fmtRole(user?.role)}</span></div>
            </div>
            <button class="btn btn-secondary" style="width:100%;margin-bottom:8px"
              onclick="PageSettings.openChangePwd()">Alterar Senha</button>
            <button class="btn btn-danger" style="width:100%"
              onclick="doLogout()">Sair da conta</button>
          </div>
        </div>

        <!-- Usuários do sistema (só admin) -->
        ${admin ? `
        <div class="card">
          <div class="card-header" style="display:flex;justify-content:space-between;align-items:center">
            <span>Usuários do Sistema</span>
            <button class="btn btn-primary btn-sm" onclick="PageSettings.openNewUser()">+ Novo Usuário</button>
          </div>
          <div class="table-wrapper" style="border:none">
            <table>
              <thead>
                <tr><th>Nome</th><th>Email</th><th>Perfil</th><th>Status</th><th></th></tr>
              </thead>
              <tbody id="settings-users-tbody">${loadingRow(5)}</tbody>
            </table>
          </div>
        </div>` : ''}

      </div>`;

    if (admin) loadUsers();
  }

  async function loadUsers() {
    const tbody = document.getElementById('settings-users-tbody');
    if (!tbody) return;
    try {
      users = await Api.getUsers() || [];
      if (!users.length) {
        tbody.innerHTML = emptyRow('Nenhum usuário cadastrado.', 5);
        return;
      }
      tbody.innerHTML = users.map(u => `
        <tr>
          <td><strong>${u.name}</strong></td>
          <td style="color:var(--text-muted);font-size:12px">${u.username}</td>
          <td>${fmtRole(u.role)}</td>
          <td>${u.is_active
            ? '<span class="badge badge-success">Ativo</span>'
            : '<span class="badge badge-gray">Inativo</span>'}</td>
          <td class="td-actions">
            <button class="btn-icon" onclick="PageSettings.openEditUser(${u.id})" title="Editar">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
              </svg>
            </button>
          </td>
        </tr>`).join('');
    } catch (e) {
      tbody.innerHTML = emptyRow(e.message, 5);
    }
  }

  function openNewUser() {
    openModal('Novo Usuário', `
      <div class="form-row">
        <div class="form-group"><label>Nome *</label>
          <input class="form-control" id="nu-name" placeholder="Nome completo">
        </div>
        <div class="form-group"><label>Usuário (login) *</label>
          <input class="form-control" type="text" id="nu-username" placeholder="ex: MariaOliveira">
        </div>
      </div>
      <div class="form-row">
        <div class="form-group"><label>Senha *</label>
          <input class="form-control" type="password" id="nu-pwd" placeholder="Mínimo 8 caracteres">
        </div>
        <div class="form-group"><label>Perfil *</label>
          <select class="form-control" id="nu-role">
            <option value="rh">RH</option>
            <option value="financeiro">Financeiro</option>
            <option value="admin">Administrador</option>
          </select>
        </div>
      </div>
      <div class="form-group">
        <label>Módulos permitidos <small style="color:var(--text-muted)">(deixe tudo marcado para acesso total)</small></label>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px 16px;margin-top:8px">
          ${ALL_MODULES.map(m => `
            <label style="display:flex;align-items:center;gap:8px;font-weight:normal;cursor:pointer">
              <input type="checkbox" class="nu-module" value="${m.key}" checked> ${m.label}
            </label>`).join('')}
        </div>
      </div>
      <div id="nu-error"></div>`, `
      <button class="btn btn-secondary" onclick="closeModal()">Cancelar</button>
      <button class="btn btn-primary" onclick="PageSettings.saveNewUser()">Criar Usuário</button>`);
  }

  async function saveNewUser() {
    const name     = document.getElementById('nu-name').value.trim();
    const username = document.getElementById('nu-username').value.trim();
    const pwd      = document.getElementById('nu-pwd').value;
    const role     = document.getElementById('nu-role').value;
    const errEl    = document.getElementById('nu-error');

    const checked = [...document.querySelectorAll('.nu-module:checked')].map(el => el.value);
    const allChecked = checked.length === ALL_MODULES.length;
    const allowed_modules = allChecked ? null : JSON.stringify(checked);

    if (!name || !username || !pwd) {
      errEl.innerHTML = '<div class="alert alert-error">Preencha todos os campos.</div>';
      return;
    }
    try {
      const newUser = await Api.createUser({ name, username, password: pwd, role });
      if (!allChecked) {
        await Api.updateUser(newUser.id, { allowed_modules });
      }
      closeModal();
      toast('Usuário criado com sucesso!');
      loadUsers();
    } catch (e) {
      errEl.innerHTML = `<div class="alert alert-error">${e.message}</div>`;
    }
  }

  function openEditUser(id) {
    const u = users.find(x => x.id === id);
    if (!u) return;
    const mods = parseModules(u.allowed_modules);
    const hasAll = mods === null;

    openModal('Editar Usuário', `
      <div class="form-row">
        <div class="form-group"><label>Nome</label>
          <input class="form-control" id="eu-name" value="${u.name}">
        </div>
        <div class="form-group"><label>Usuário (login)</label>
          <input class="form-control" type="text" id="eu-username" value="${u.username}">
        </div>
      </div>
      <div class="form-row">
        <div class="form-group"><label>Perfil</label>
          <select class="form-control" id="eu-role">
            <option value="rh"        ${u.role === 'rh'         ? 'selected' : ''}>RH</option>
            <option value="financeiro" ${u.role === 'financeiro' ? 'selected' : ''}>Financeiro</option>
            <option value="admin"     ${u.role === 'admin'      ? 'selected' : ''}>Administrador</option>
          </select>
        </div>
        <div class="form-group"><label>Status</label>
          <select class="form-control" id="eu-active">
            <option value="true"  ${u.is_active  ? 'selected' : ''}>Ativo</option>
            <option value="false" ${!u.is_active ? 'selected' : ''}>Inativo</option>
          </select>
        </div>
      </div>
      <div class="form-group">
        <label>Módulos permitidos <small style="color:var(--text-muted)">(deixe tudo marcado para acesso total)</small></label>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px 16px;margin-top:8px">
          ${ALL_MODULES.map(m => `
            <label style="display:flex;align-items:center;gap:8px;font-weight:normal;cursor:pointer">
              <input type="checkbox" class="eu-module" value="${m.key}" ${hasAll || (mods && mods.includes(m.key)) ? 'checked' : ''}> ${m.label}
            </label>`).join('')}
        </div>
      </div>
      <div id="eu-error"></div>`, `
      <button class="btn btn-secondary" onclick="closeModal()">Cancelar</button>
      <button class="btn btn-warning" onclick="PageSettings.openResetUserPwd(${id})" style="margin-right:auto">Redefinir Senha</button>
      <button class="btn btn-primary" onclick="PageSettings.saveEditUser(${id})">Salvar</button>`);
  }

  async function saveEditUser(id) {
    const errEl = document.getElementById('eu-error');
    const checked = [...document.querySelectorAll('.eu-module:checked')].map(el => el.value);
    const allChecked = checked.length === ALL_MODULES.length;
    const allowed_modules = allChecked ? null : JSON.stringify(checked);

    try {
      await Api.updateUser(id, {
        name:            document.getElementById('eu-name').value.trim(),
        username:        document.getElementById('eu-username').value.trim(),
        role:            document.getElementById('eu-role').value,
        is_active:       document.getElementById('eu-active').value === 'true',
        allowed_modules,
      });
      closeModal();
      toast('Usuário atualizado!');
      loadUsers();
    } catch (e) {
      errEl.innerHTML = `<div class="alert alert-error">${e.message}</div>`;
    }
  }

  function openResetUserPwd(id) {
    const u = users.find(x => x.id === id);
    openModal('Redefinir Senha — ' + (u?.name || ''), `
      <p style="color:var(--text-muted);margin-bottom:16px">Defina uma nova senha para este usuário. Ele será desconectado de sessões ativas.</p>
      <div class="form-group"><label>Nova Senha *</label>
        <input class="form-control" type="password" id="rp-new" placeholder="Mínimo 8 caracteres">
      </div>
      <div class="form-group"><label>Confirmar Nova Senha *</label>
        <input class="form-control" type="password" id="rp-confirm" placeholder="Mínimo 8 caracteres">
      </div>
      <div id="rp-error"></div>`, `
      <button class="btn btn-secondary" onclick="closeModal()">Cancelar</button>
      <button class="btn btn-primary" onclick="PageSettings.saveResetUserPwd(${id})">Redefinir</button>`);
  }

  async function saveResetUserPwd(id) {
    const novo    = document.getElementById('rp-new').value;
    const confirm = document.getElementById('rp-confirm').value;
    const errEl   = document.getElementById('rp-error');

    if (!novo || !confirm) {
      errEl.innerHTML = '<div class="alert alert-error">Preencha os dois campos.</div>';
      return;
    }
    if (novo !== confirm) {
      errEl.innerHTML = '<div class="alert alert-error">As senhas não coincidem.</div>';
      return;
    }
    try {
      await Api.adminResetPwd(id, { new_password: novo });
      closeModal();
      toast('Senha redefinida com sucesso!');
    } catch (e) {
      errEl.innerHTML = `<div class="alert alert-error">${e.message}</div>`;
    }
  }

  function openChangePwd() {
    openModal('Alterar Senha', `
      <div class="form-group"><label>Senha Atual *</label>
        <input class="form-control" type="password" id="cp-current">
      </div>
      <div class="form-group"><label>Nova Senha *</label>
        <input class="form-control" type="password" id="cp-new" placeholder="Mínimo 8 caracteres">
      </div>
      <div class="form-group"><label>Confirmar Nova Senha *</label>
        <input class="form-control" type="password" id="cp-confirm">
      </div>
      <div id="cp-error"></div>`, `
      <button class="btn btn-secondary" onclick="closeModal()">Cancelar</button>
      <button class="btn btn-primary" onclick="PageSettings.saveChangePwd()">Alterar</button>`);
  }

  async function saveChangePwd() {
    const current = document.getElementById('cp-current').value;
    const novo    = document.getElementById('cp-new').value;
    const confirm = document.getElementById('cp-confirm').value;
    const errEl   = document.getElementById('cp-error');

    if (novo !== confirm) {
      errEl.innerHTML = '<div class="alert alert-error">As senhas não coincidem.</div>';
      return;
    }
    try {
      await Api.changeMyPwd({ current_password: current, new_password: novo });
      closeModal();
      toast('Senha alterada com sucesso!');
    } catch (e) {
      errEl.innerHTML = `<div class="alert alert-error">${e.message}</div>`;
    }
  }

  return {
    render,
    openNewUser, saveNewUser,
    openEditUser, saveEditUser,
    openResetUserPwd, saveResetUserPwd,
    openChangePwd, saveChangePwd,
  };
})();
