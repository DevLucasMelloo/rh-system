const PageRescisao = (() => {
  async function render(container) {
    const empOpts = await employeeSelectOptions();
    container.innerHTML = `
      <div class="page-header">
        <div><h1>Rescisão</h1><p>Cálculo e registro de rescisão de contrato</p></div>
      </div>

      <div style="display:grid;grid-template-columns:1fr 1fr;gap:24px">
        <!-- Formulário de cálculo -->
        <div class="card">
          <div class="card-header">Nova Rescisão</div>
          <div class="card-body">
            <div class="form-group">
              <label>Funcionário *</label>
              <select class="form-control" id="res-emp" onchange="PageRescisao.onEmpChange()">
                <option value="">Selecione...</option>${empOpts}
              </select>
            </div>
            <div id="res-emp-info" style="display:none;background:var(--bg);border-radius:8px;padding:12px;margin-bottom:16px;font-size:13px">
              <div style="display:flex;justify-content:space-between;margin-bottom:4px">
                <span style="color:var(--text-muted)">Salário</span><strong id="res-salary">—</strong>
              </div>
              <div style="display:flex;justify-content:space-between;margin-bottom:4px">
                <span style="color:var(--text-muted)">Admissão</span><strong id="res-admission">—</strong>
              </div>
              <div style="display:flex;justify-content:space-between">
                <span style="color:var(--text-muted)">Cargo</span><strong id="res-role">—</strong>
              </div>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label>Motivo *</label>
                <select class="form-control" id="res-reason">
                  <option value="sem_justa_causa">Sem Justa Causa (empresa)</option>
                  <option value="pedido_demissao">Pedido de Demissão</option>
                  <option value="acordo">Acordo (mútuo consenso)</option>
                  <option value="com_justa_causa">Com Justa Causa</option>
                  <option value="aposentadoria">Aposentadoria</option>
                </select>
              </div>
              <div class="form-group">
                <label>Data da Rescisão *</label>
                <input class="form-control" type="date" id="res-date" value="${new Date().toISOString().split('T')[0]}">
              </div>
            </div>
            <div id="res-error"></div>
            <button class="btn btn-primary w-full" onclick="PageRescisao.calcular()">Registrar Rescisão</button>
          </div>
        </div>

        <!-- Resultado do cálculo -->
        <div class="card">
          <div class="card-header">Verbas Rescisórias</div>
          <div class="card-body" id="res-result">
            <div style="text-align:center;padding:40px;color:var(--text-muted)">
              <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" style="margin-bottom:8px;opacity:0.4"><rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8M12 17v4"/></svg>
              <p>Preencha o formulário e clique em Calcular.</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Histórico de rescisões -->
      <div class="card" style="margin-top:24px">
        <div class="card-header">Histórico de Rescisões</div>
        <div class="table-wrapper" style="border:none">
          <table>
            <thead><tr><th>Funcionário</th><th>Motivo</th><th>Data</th><th>Aviso Prévio</th><th>Líquido</th><th></th></tr></thead>
            <tbody id="res-history-tbody">${loadingRow(6)}</tbody>
          </table>
        </div>
      </div>`;

    loadHistory();
  }

  async function loadHistory() {
    try {
      const list = await Api.getTerminations() || [];
      if (!list.length) {
        document.getElementById('res-history-tbody').innerHTML = emptyRow('Nenhuma rescisão registrada.', 6);
        return;
      }
      document.getElementById('res-history-tbody').innerHTML = list.map(t => `
        <tr>
          <td><strong>${t.employee_name || '—'}</strong></td>
          <td>${fmtReason(t.reason)}</td>
          <td>${fmt.date(t.termination_date)}</td>
          <td>${t.aviso_previo_days ? `${t.aviso_previo_days} dias` : '—'}</td>
          <td><strong>${fmt.brl(t.liquido)}</strong></td>
          <td class="td-actions">
            <button class="btn-icon" onclick="PageRescisao.openDetail(${t.id})" title="Ver detalhes">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
            </button>
          </td>
        </tr>`).join('');
    } catch (e) {
      document.getElementById('res-history-tbody').innerHTML = emptyRow(e.message, 6);
    }
  }

  function fmtReason(reason) {
    const map = {
      sem_justa_causa: 'Sem Justa Causa',
      com_justa_causa: 'Com Justa Causa',
      pedido_demissao: 'Pedido de Demissão',
      acordo:          'Acordo',
      aposentadoria:   'Aposentadoria',
    };
    return map[reason] || reason;
  }

  async function onEmpChange() {
    const sel = document.getElementById('res-emp');
    const id = parseInt(sel.value) || null;
    const infoEl = document.getElementById('res-emp-info');
    if (!id) { infoEl.style.display = 'none'; return; }
    try {
      const emp = await Api.getEmployee(id);
      document.getElementById('res-salary').textContent    = fmt.brl(emp.salary);
      document.getElementById('res-admission').textContent = fmt.date(emp.admission_date);
      document.getElementById('res-role').textContent      = emp.role;
      infoEl.style.display = 'block';
    } catch { infoEl.style.display = 'none'; }
  }

  async function calcular() {
    const empId  = parseInt(document.getElementById('res-emp').value);
    const reason = document.getElementById('res-reason').value;
    const date   = document.getElementById('res-date').value;
    const errEl  = document.getElementById('res-error');
    errEl.innerHTML = '';

    if (!empId) { errEl.innerHTML = '<div class="alert alert-error">Selecione um funcionário.</div>'; return; }
    if (!date)  { errEl.innerHTML = '<div class="alert alert-error">Informe a data da rescisão.</div>'; return; }

    const resultEl = document.getElementById('res-result');
    resultEl.innerHTML = '<div style="text-align:center;padding:40px"><div class="spinner spinner-dark"></div></div>';

    try {
      // Create termination directly (calculates all verbas and inactivates employee)
      const t = await Api.createTermination({ employee_id: empId, reason, termination_date: date });
      renderResult(t);
      loadHistory();
      // Reset form
      document.getElementById('res-emp').value = '';
      document.getElementById('res-emp-info').style.display = 'none';
      toast('Rescisão registrada! Funcionário inativado.', 'success');
    } catch (e) {
      errEl.innerHTML = `<div class="alert alert-error">${e.message}</div>`;
      resultEl.innerHTML = '<div style="text-align:center;padding:40px;color:var(--text-muted)">Erro ao calcular. Verifique os dados e tente novamente.</div>';
    }
  }

  function renderResult(t) {
    const resultEl = document.getElementById('res-result');
    const row = (label, val, color = '') =>
      `<div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid var(--border)">
        <span style="color:var(--text-muted)">${label}</span>
        <strong style="${color ? `color:${color}` : ''}">${val}</strong>
      </div>`;

    resultEl.innerHTML = `
      <div style="font-size:13px">
        ${row('Saldo de Salário', fmt.brl(t.saldo_salario))}
        ${row('Férias Proporcionais', fmt.brl(t.ferias_proporcionais))}
        ${row('1/3 de Férias Prop.', fmt.brl(t.um_terco_ferias_prop))}
        ${t.ferias_vencidas > 0 ? row('Férias Vencidas', fmt.brl(t.ferias_vencidas)) : ''}
        ${t.um_terco_ferias_venc > 0 ? row('1/3 Férias Vencidas', fmt.brl(t.um_terco_ferias_venc)) : ''}
        ${row('13º Proporcional', fmt.brl(t.decimo_terceiro_prop))}
        ${t.aviso_previo_indenizado > 0 ? row('Aviso Prévio Indenizado', fmt.brl(t.aviso_previo_indenizado)) : ''}
        ${t.multa_fgts > 0 ? row('Multa FGTS', fmt.brl(t.multa_fgts)) : ''}
        <div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid var(--border)">
          <span style="color:var(--success);font-weight:600">Total Créditos</span>
          <strong style="color:var(--success)">${fmt.brl(t.total_creditos)}</strong>
        </div>
        <div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid var(--border)">
          <span style="color:var(--danger)">INSS Rescisão</span>
          <strong style="color:var(--danger)">- ${fmt.brl(t.inss_rescisao)}</strong>
        </div>
        <div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:2px solid var(--border)">
          <span style="color:var(--danger)">Total Descontos</span>
          <strong style="color:var(--danger)">- ${fmt.brl(t.total_descontos)}</strong>
        </div>
        <div style="display:flex;justify-content:space-between;padding:12px 0 4px">
          <span style="font-size:15px;font-weight:700">LÍQUIDO A RECEBER</span>
          <span style="font-size:18px;font-weight:700;color:var(--primary)">${fmt.brl(t.liquido)}</span>
        </div>
        <p style="font-size:11px;color:var(--text-muted);margin-top:8px">
          Aviso prévio: ${t.aviso_previo_days || 0} dias &nbsp;·&nbsp;
          Motivo: ${fmtReason(t.reason)}
        </p>
      </div>`;
  }

  async function openDetail(id) {
    openModal('Detalhes da Rescisão', '<div style="padding:20px;text-align:center"><div class="spinner spinner-dark"></div></div>', '', true);
    try {
      const t = await Api.getTermination(id);
      const row = (label, val, color = '') =>
        `<div style="display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid var(--border);font-size:13px">
          <span style="color:var(--text-muted)">${label}</span>
          <strong ${color ? `style="color:${color}"` : ''}>${val}</strong>
        </div>`;

      document.getElementById('modal-body').innerHTML = `
        <div class="detail-grid" style="margin-bottom:16px">
          <div class="detail-item"><label>Funcionário</label><span>${t.employee_name || '—'}</span></div>
          <div class="detail-item"><label>Motivo</label><span>${fmtReason(t.reason)}</span></div>
          <div class="detail-item"><label>Data</label><span>${fmt.date(t.termination_date)}</span></div>
          <div class="detail-item"><label>Aviso Prévio</label><span>${t.aviso_previo_days || 0} dias</span></div>
        </div>
        ${row('Saldo de Salário', fmt.brl(t.saldo_salario))}
        ${row('Férias Proporcionais', fmt.brl(t.ferias_proporcionais))}
        ${row('1/3 Férias Prop.', fmt.brl(t.um_terco_ferias_prop))}
        ${t.ferias_vencidas > 0 ? row('Férias Vencidas', fmt.brl(t.ferias_vencidas)) : ''}
        ${t.um_terco_ferias_venc > 0 ? row('1/3 Férias Vencidas', fmt.brl(t.um_terco_ferias_venc)) : ''}
        ${row('13º Proporcional', fmt.brl(t.decimo_terceiro_prop))}
        ${t.aviso_previo_indenizado > 0 ? row('Aviso Prévio Indenizado', fmt.brl(t.aviso_previo_indenizado)) : ''}
        ${t.multa_fgts > 0 ? row('Multa FGTS', fmt.brl(t.multa_fgts)) : ''}
        <div style="display:flex;justify-content:space-between;padding:6px 0;font-size:13px">
          <strong style="color:var(--success)">Total Créditos</strong>
          <strong style="color:var(--success)">${fmt.brl(t.total_creditos)}</strong>
        </div>
        <div style="display:flex;justify-content:space-between;padding:6px 0;font-size:13px">
          <strong style="color:var(--danger)">Total Descontos</strong>
          <strong style="color:var(--danger)">- ${fmt.brl(t.total_descontos)}</strong>
        </div>
        <div style="display:flex;justify-content:space-between;padding:10px 0 0;border-top:2px solid var(--border);margin-top:8px">
          <strong style="font-size:15px">LÍQUIDO</strong>
          <strong style="font-size:18px;color:var(--primary)">${fmt.brl(t.liquido)}</strong>
        </div>`;
      document.getElementById('modal-footer').innerHTML =
        `<button class="btn btn-secondary" onclick="closeModal()">Fechar</button>`;
    } catch (e) {
      document.getElementById('modal-body').innerHTML = `<div class="alert alert-error">${e.message}</div>`;
    }
  }

  return { render, onEmpChange, calcular, openDetail };
})();
