const PageBackup = (() => {

  let _selectedFile = null;
  let _mode = 'add';

  async function render(container) {
    const el = document.getElementById('page-content');
    if (!el) return;

    container.innerHTML = `
      <div class="page-header">
        <div>
          <h1>Backup e Restauração</h1>
          <p>Exporte e importe todos os dados da empresa com segurança</p>
        </div>
      </div>

      <div id="backup-info-banner" style="display:none;margin-bottom:20px"></div>

      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:24px;margin-bottom:28px">

        <!-- ── Exportar ── -->
        <div class="card" style="padding:28px">
          <div style="display:flex;align-items:center;gap:14px;margin-bottom:16px">
            <div style="width:48px;height:48px;background:#eff6ff;border-radius:12px;display:flex;align-items:center;justify-content:center">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
            </div>
            <div>
              <div style="font-size:16px;font-weight:700;color:var(--text)">Exportar Dados</div>
              <div style="font-size:12px;color:var(--text-light)">Segurança e Portabilidade</div>
            </div>
          </div>

          <p style="font-size:13px;color:var(--text-light);line-height:1.6;margin-bottom:20px">
            Exporte todas as informações do sistema (funcionários, folhas, registros) para um arquivo de segurança. Este processo pode levar alguns segundos dependendo do volume de dados.
          </p>

          <div id="backup-stats" style="background:var(--bg);border-radius:10px;padding:14px 18px;margin-bottom:20px">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
              <span style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--text-light)">Estatísticas dos Dados</span>
              <div class="spinner" id="stats-spinner" style="width:14px;height:14px;border-width:2px"></div>
            </div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px" id="stats-grid">
              <div>
                <div style="font-size:11px;color:var(--text-light);margin-bottom:2px">Funcionários</div>
                <div style="font-size:18px;font-weight:700;color:var(--text)" id="stat-emp">—</div>
              </div>
              <div>
                <div style="font-size:11px;color:var(--text-light);margin-bottom:2px">Costureiras</div>
                <div style="font-size:18px;font-weight:700;color:var(--text)" id="stat-seam">—</div>
              </div>
              <div>
                <div style="font-size:11px;color:var(--text-light);margin-bottom:2px">Total de registros</div>
                <div style="font-size:18px;font-weight:700;color:var(--text)" id="stat-total">—</div>
              </div>
              <div>
                <div style="font-size:11px;color:var(--text-light);margin-bottom:2px">Tamanho aprox.</div>
                <div style="font-size:18px;font-weight:700;color:var(--text)" id="stat-size">—</div>
              </div>
            </div>
          </div>

          <button id="btn-export" class="btn btn-primary" style="width:100%;justify-content:center;gap:8px" onclick="PageBackup.exportBackup()">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
            Gerar Backup (.zip)
          </button>
        </div>

        <!-- ── Importar ── -->
        <div class="card" style="padding:28px">
          <div style="display:flex;align-items:center;gap:14px;margin-bottom:16px">
            <div style="width:48px;height:48px;background:#f0fdf4;border-radius:12px;display:flex;align-items:center;justify-content:center">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#16a34a" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
            </div>
            <div>
              <div style="font-size:16px;font-weight:700;color:var(--text)">Importar Dados</div>
              <div style="font-size:12px;color:var(--text-light)">Restauração de Sistema</div>
            </div>
          </div>

          <!-- Zona de drop -->
          <div id="drop-zone"
            style="border:2px dashed var(--border);border-radius:12px;padding:32px 20px;text-align:center;cursor:pointer;transition:all .2s;margin-bottom:16px"
            onclick="document.getElementById('file-input').click()"
            ondragover="PageBackup.onDragOver(event)"
            ondragleave="PageBackup.onDragLeave(event)"
            ondrop="PageBackup.onDrop(event)">
            <div id="drop-icon" style="margin-bottom:10px">
              <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" stroke-width="1.5"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="12" y1="18" x2="12" y2="12"/><line x1="9" y1="15" x2="15" y2="15"/></svg>
            </div>
            <div id="drop-label" style="font-size:14px;font-weight:600;color:var(--text);margin-bottom:4px">Arraste seu arquivo aqui</div>
            <div id="drop-sub" style="font-size:12px;color:var(--text-light);margin-bottom:10px">Formatos suportados: .zip, .json (Máx 100MB)</div>
            <span style="font-size:13px;color:#2563eb;font-weight:500;text-decoration:underline">Ou procure no computador</span>
            <input type="file" id="file-input" accept=".zip,.json" style="display:none" onchange="PageBackup.onFileSelect(event)">
          </div>

          <!-- Modo de importação -->
          <div style="margin-bottom:16px">
            <div id="mode-replace"
              style="border:2px solid var(--border);border-radius:10px;padding:14px 16px;cursor:pointer;margin-bottom:10px;transition:all .2s"
              onclick="PageBackup.setMode('replace')">
              <div style="display:flex;align-items:center;gap:10px">
                <div id="radio-replace" style="width:18px;height:18px;border-radius:50%;border:2px solid var(--border);flex-shrink:0;transition:all .2s"></div>
                <div>
                  <div style="font-size:14px;font-weight:600;color:var(--text)">Substituir tudo</div>
                  <div style="font-size:12px;color:var(--text-light)">Remove todos os dados atuais e substitui pelo arquivo.</div>
                </div>
              </div>
            </div>
            <div id="mode-add"
              style="border:2px solid #2563eb;border-radius:10px;padding:14px 16px;cursor:pointer;transition:all .2s;background:#eff6ff"
              onclick="PageBackup.setMode('add')">
              <div style="display:flex;align-items:center;gap:10px">
                <div id="radio-add" style="width:18px;height:18px;border-radius:50%;border:2px solid #2563eb;background:#2563eb;flex-shrink:0;display:flex;align-items:center;justify-content:center">
                  <div style="width:6px;height:6px;border-radius:50%;background:#fff"></div>
                </div>
                <div>
                  <div style="font-size:14px;font-weight:600;color:var(--text)">Adicionar apenas novos</div>
                  <div style="font-size:12px;color:var(--text-light)">Mantém os dados atuais e adiciona apenas o que não existe.</div>
                </div>
              </div>
            </div>
          </div>

          <button id="btn-import" class="btn" disabled
            style="width:100%;justify-content:center;gap:8px;background:#e2e8f0;color:#94a3b8;cursor:not-allowed"
            onclick="PageBackup.importBackup()">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg>
            Iniciar Importação
          </button>
          <div id="import-msg" style="margin-top:10px;display:none"></div>
        </div>
      </div>

      <!-- ── Dica de segurança ── -->
      <div class="card" style="padding:24px;display:flex;gap:20px;align-items:flex-start">
        <div style="width:44px;height:44px;background:#eff6ff;border-radius:12px;display:flex;align-items:center;justify-content:center;flex-shrink:0">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
        </div>
        <div>
          <div style="font-size:15px;font-weight:700;color:var(--text);margin-bottom:6px">Segurança em primeiro lugar</div>
          <div style="font-size:13px;color:var(--text-light);line-height:1.6">
            Recomendamos realizar backups regularmente. O arquivo gerado contém todos os dados da empresa
            criptografados. Guarde em local seguro e nunca compartilhe com terceiros.
            Em caso de restauração com "Substituir tudo", todos os dados atuais serão apagados permanentemente.
          </div>
        </div>
      </div>
    `;

    loadStats();
  }

  async function loadStats() {
    try {
      const info = await Api.request('GET', '/backup/info');
      const spin = document.getElementById('stats-spinner');
      if (spin) spin.style.display = 'none';
      const e = (id, v) => { const el = document.getElementById(id); if (el) el.textContent = v; };
      e('stat-emp',   info.employee_count);
      e('stat-seam',  info.seamstress_count);
      e('stat-total', info.total_records.toLocaleString('pt-BR'));
      e('stat-size',  `${info.approx_size_mb} MB`);
    } catch (err) {
      const spin = document.getElementById('stats-spinner');
      if (spin) spin.style.display = 'none';
    }
  }

  async function exportBackup() {
    const btn = document.getElementById('btn-export');
    if (!btn) return;
    btn.disabled = true;
    btn.innerHTML = '<div class="spinner" style="width:16px;height:16px;border-width:2px"></div> Gerando...';
    try {
      const token = Api.getToken();
      const base  = window.location.port === '3000' ? 'http://localhost:8080/api/v1' : `${window.location.origin}/api/v1`;
      const res = await fetch(`${base}/backup/export`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || 'Erro ao gerar backup');
      }
      const blob = await res.blob();
      const cd   = res.headers.get('Content-Disposition') || '';
      const match = cd.match(/filename="([^"]+)"/);
      const filename = match ? match[1] : 'backup_rh.zip';
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      toast('Backup gerado com sucesso!', 'success');
    } catch (err) {
      toast(err.message, 'error');
    } finally {
      btn.disabled = false;
      btn.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg> Gerar Backup (.zip)';
    }
  }

  function setMode(mode) {
    _mode = mode;
    const activeStyle  = 'border:2px solid #2563eb;border-radius:10px;padding:14px 16px;cursor:pointer;transition:all .2s;background:#eff6ff';
    const inactiveStyle = 'border:2px solid var(--border);border-radius:10px;padding:14px 16px;cursor:pointer;margin-bottom:10px;transition:all .2s';
    const radioOnStyle  = 'width:18px;height:18px;border-radius:50%;border:2px solid #2563eb;background:#2563eb;flex-shrink:0;display:flex;align-items:center;justify-content:center';
    const radioOffStyle = 'width:18px;height:18px;border-radius:50%;border:2px solid var(--border);flex-shrink:0;transition:all .2s';

    const modeReplace = document.getElementById('mode-replace');
    const modeAdd     = document.getElementById('mode-add');
    const radioReplace = document.getElementById('radio-replace');
    const radioAdd     = document.getElementById('radio-add');

    if (mode === 'replace') {
      if (modeReplace) { modeReplace.style.cssText = activeStyle; modeReplace.style.marginBottom = '10px'; }
      if (modeAdd)     modeAdd.style.cssText = inactiveStyle.replace('margin-bottom:10px;','');
      if (radioReplace) radioReplace.innerHTML = `<div style="width:6px;height:6px;border-radius:50%;background:#fff"></div>`;
      if (radioReplace) radioReplace.style.cssText = radioOnStyle;
      if (radioAdd)    radioAdd.style.cssText = radioOffStyle;
      if (radioAdd)    radioAdd.innerHTML = '';
    } else {
      if (modeAdd)     modeAdd.style.cssText = activeStyle;
      if (modeReplace) { modeReplace.style.cssText = inactiveStyle; }
      if (radioAdd) { radioAdd.innerHTML = `<div style="width:6px;height:6px;border-radius:50%;background:#fff"></div>`; radioAdd.style.cssText = radioOnStyle; }
      if (radioReplace) { radioReplace.style.cssText = radioOffStyle; radioReplace.innerHTML = ''; }
    }
  }

  function onFileSelect(event) {
    const file = event.target.files[0];
    if (file) _setFile(file);
  }

  function onDragOver(event) {
    event.preventDefault();
    const dz = document.getElementById('drop-zone');
    if (dz) { dz.style.borderColor = '#2563eb'; dz.style.background = '#eff6ff'; }
  }

  function onDragLeave(event) {
    const dz = document.getElementById('drop-zone');
    if (dz) { dz.style.borderColor = 'var(--border)'; dz.style.background = ''; }
  }

  function onDrop(event) {
    event.preventDefault();
    onDragLeave(event);
    const file = event.dataTransfer.files[0];
    if (file) _setFile(file);
  }

  function _setFile(file) {
    _selectedFile = file;
    const label = document.getElementById('drop-label');
    const sub   = document.getElementById('drop-sub');
    const icon  = document.getElementById('drop-icon');
    const btn   = document.getElementById('btn-import');
    if (label) label.textContent = file.name;
    if (sub)   sub.textContent   = `${(file.size / 1024).toFixed(1)} KB`;
    if (icon)  icon.innerHTML    = '<svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#16a34a" stroke-width="1.5"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>';
    if (btn) {
      btn.disabled = false;
      btn.style.cssText = 'width:100%;justify-content:center;gap:8px;background:#16a34a;color:#fff;cursor:pointer';
    }
  }

  async function importBackup() {
    if (!_selectedFile) return;
    const user = Api.getUser();
    if (user?.role !== 'admin') {
      toast('Apenas administradores podem importar backups.', 'error');
      return;
    }

    if (_mode === 'replace') {
      const ok = confirm(
        '⚠️ ATENÇÃO: "Substituir tudo" apagará TODOS os dados atuais permanentemente.\n\n' +
        'Esta ação não pode ser desfeita. Deseja continuar?'
      );
      if (!ok) return;
    }

    const btn = document.getElementById('btn-import');
    const msg = document.getElementById('import-msg');
    if (btn) { btn.disabled = true; btn.innerHTML = '<div class="spinner" style="width:16px;height:16px;border-width:2px"></div> Importando...'; }

    try {
      const token = Api.getToken();
      const base  = window.location.port === '3000' ? 'http://localhost:8080/api/v1' : `${window.location.origin}/api/v1`;
      const form  = new FormData();
      form.append('file', _selectedFile);
      form.append('mode', _mode);

      const res = await fetch(`${base}/backup/import`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
        body: form,
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || 'Erro ao importar backup');

      if (msg) {
        msg.style.display = 'block';
        msg.innerHTML = `<div class="alert" style="background:#dcfce7;border:1px solid #86efac;color:#16a34a;padding:12px 16px;border-radius:8px;font-size:13px">
          ✓ ${data.message} — ${data.imported ?? 0} grupo(s) de registros restaurados.
        </div>`;
      }
      toast('Backup importado com sucesso!', 'success');
      loadStats();
    } catch (err) {
      if (msg) {
        msg.style.display = 'block';
        msg.innerHTML = `<div class="alert alert-error" style="font-size:13px">${err.message}</div>`;
      }
      toast(err.message, 'error');
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.style.cssText = 'width:100%;justify-content:center;gap:8px;background:#16a34a;color:#fff;cursor:pointer';
        btn.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg> Iniciar Importação';
      }
    }
  }

  return { render, exportBackup, importBackup, setMode, onFileSelect, onDragOver, onDragLeave, onDrop };
})();
