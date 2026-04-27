const PageRescisao = (() => {
  // ── Helpers ─────────────────────────────────────────────────────────────────

  function statusBadge(status) {
    if (status === 'concluida')
      return `<span style="display:inline-block;padding:2px 10px;border-radius:12px;font-size:11px;font-weight:600;background:#dcfce7;color:#15803d">✓ Concluída</span>`;
    return `<span style="display:inline-block;padding:2px 10px;border-radius:12px;font-size:11px;font-weight:600;background:#fef3c7;color:#92400e">⏳ Pendente</span>`;
  }

  function fmtReason(reason) {
    const map = {
      sem_justa_causa: 'Sem Justa Causa',
      com_justa_causa: 'Com Justa Causa',
      pedido_demissao: 'Pedido de Demissão',
      acordo:          'Acordo Mútuo',
      aposentadoria:   'Aposentadoria',
    };
    return map[reason] || reason;
  }

  function calcNoticeDays(reason, admissionDate, terminationDate) {
    if (!admissionDate || !terminationDate) return 0;
    if (['com_justa_causa', 'aposentadoria'].includes(reason)) return 0;
    const adm  = new Date(admissionDate);
    const term = new Date(terminationDate);
    const years = Math.floor((term - adm) / (365.25 * 24 * 3600 * 1000));
    let days = Math.min(30 + Math.max(0, years) * 3, 90);
    if (reason === 'acordo') days = Math.floor(days / 2);
    return days;
  }

  function addDays(dateStr, days) {
    if (!dateStr) return null;
    const d = new Date(dateStr);
    d.setDate(d.getDate() + days - 1);
    return d.toISOString().split('T')[0];
  }

  function noticeLabelFor(reason, worked) {
    if (reason === 'sem_justa_causa' && !worked) return 'Aviso Prévio Proporcional (Lei 12.506/2011)';
    if (reason === 'acordo')                      return 'Aviso Prévio Indenizado (50%)';
    return 'Aviso Prévio Indenizado';
  }

  // Recalcula totais do lado do cliente a partir dos inputs do formulário de edição
  function recalcFromInputs(prefix) {
    const v = (id) => parseFloat(document.getElementById(`${prefix}-${id}`)?.value || '0') || 0;
    const credits = v('saldo') + v('fer-prop') + v('terc-prop') + v('fer-venc') +
                    v('terc-venc') + v('dec13') + v('aviso-ind') + v('multa');
    const deducts = v('inss') + v('aviso-desc');
    const net     = credits - deducts;
    const set = (id, val) => {
      const el = document.getElementById(`${prefix}-${id}`);
      if (el) el.textContent = fmt.brl(val);
    };
    set('tot-cred', credits);
    set('tot-desc', deducts);
    set('liquido',  net);
  }

  // ── Render principal ─────────────────────────────────────────────────────────

  async function render(container) {
    const empOpts = await employeeSelectOptions();
    container.innerHTML = `
      <div class="page-header">
        <div><h1>Rescisão</h1><p>Cálculo, aviso prévio e registro de rescisão</p></div>
      </div>

      <div style="display:grid;grid-template-columns:1fr 1fr;gap:24px">
        <!-- Formulário -->
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
                <select class="form-control" id="res-reason" onchange="PageRescisao.onReasonChange()">
                  <option value="sem_justa_causa">Sem Justa Causa (empresa)</option>
                  <option value="pedido_demissao">Pedido de Demissão</option>
                  <option value="acordo">Acordo Mútuo (art. 484-A)</option>
                  <option value="com_justa_causa">Com Justa Causa</option>
                  <option value="aposentadoria">Aposentadoria</option>
                </select>
              </div>
              <div class="form-group">
                <label>Data da Rescisão *</label>
                <input class="form-control" type="date" id="res-date"
                       value="${new Date().toISOString().split('T')[0]}"
                       onchange="PageRescisao.onReasonChange()">
              </div>
            </div>

            <!-- Aviso Prévio -->
            <div id="res-aviso-section" style="background:var(--bg);border-radius:8px;padding:12px;margin-bottom:16px">
              <div style="font-weight:600;font-size:13px;margin-bottom:10px">Aviso Prévio</div>

              <div id="res-aviso-info" style="font-size:12px;color:var(--text-muted);margin-bottom:10px"></div>

              <div class="form-row" style="margin-bottom:0">
                <div class="form-group" style="margin-bottom:0">
                  <label style="font-size:12px">Tipo de aviso</label>
                  <select class="form-control" id="res-notice-type" onchange="PageRescisao.onNoticeTypeChange()" style="font-size:13px">
                    <option value="indenizado">Indenizado (não trabalhado)</option>
                    <option value="trabalhado">Trabalhado pelo funcionário</option>
                    <option value="nao_cumprido">Não cumprido pelo funcionário</option>
                  </select>
                </div>
                <div class="form-group" style="margin-bottom:0" id="res-notice-start-group">
                  <label style="font-size:12px">Início do aviso</label>
                  <input class="form-control" type="date" id="res-notice-start"
                         onchange="PageRescisao.onNoticeStartChange()" style="font-size:13px">
                </div>
              </div>

              <div id="res-notice-end-info" style="font-size:12px;color:var(--primary);margin-top:8px;display:none"></div>
            </div>

            <div class="form-group">
              <label>Observações</label>
              <textarea class="form-control" id="res-notes" rows="2" style="resize:none"></textarea>
            </div>

            <div id="res-error"></div>
            <button class="btn btn-primary w-full" onclick="PageRescisao.calcular()">Registrar Rescisão</button>
          </div>
        </div>

        <!-- Verbas calculadas (editáveis) -->
        <div class="card">
          <div class="card-header" style="display:flex;align-items:center;justify-content:space-between">
            <span>Verbas Rescisórias</span>
            <div id="res-edit-actions" style="display:none;gap:8px;display:none">
              <button class="btn btn-secondary" style="font-size:12px;padding:4px 12px"
                      onclick="PageRescisao.recalcResult()">↺ Recalcular</button>
              <button class="btn btn-primary" style="font-size:12px;padding:4px 12px"
                      onclick="PageRescisao.salvarEdicao()">💾 Salvar</button>
            </div>
          </div>
          <div class="card-body" id="res-result">
            <div style="text-align:center;padding:40px;color:var(--text-muted)">
              <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                   stroke-width="1" style="margin-bottom:8px;opacity:0.4">
                <rect x="2" y="3" width="20" height="14" rx="2"/>
                <path d="M8 21h8M12 17v4"/>
              </svg>
              <p>Preencha o formulário e clique em Registrar.</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Histórico -->
      <div class="card" style="margin-top:24px">
        <div class="card-header">Histórico de Rescisões</div>
        <div class="table-wrapper" style="border:none">
          <table>
            <thead>
              <tr>
                <th>Funcionário</th><th>Motivo</th><th>Data Rescisão</th>
                <th>Aviso Prévio</th><th>Status</th><th>Líquido</th><th></th>
              </tr>
            </thead>
            <tbody id="res-history-tbody">${loadingRow(7)}</tbody>
          </table>
        </div>
      </div>`;

    onReasonChange();
    loadHistory();
  }

  // ── Eventos do formulário ────────────────────────────────────────────────────

  async function onEmpChange() {
    const id = parseInt(document.getElementById('res-emp').value) || null;
    const info = document.getElementById('res-emp-info');
    if (!id) { info.style.display = 'none'; return; }
    try {
      const emp = await Api.getEmployee(id);
      document.getElementById('res-salary').textContent    = fmt.brl(emp.salary);
      document.getElementById('res-admission').textContent = fmt.date(emp.admission_date);
      document.getElementById('res-role').textContent      = emp.role || '—';
      info.style.display = 'block';
      // Store admission date for notice calc
      document.getElementById('res-emp').dataset.admission = emp.admission_date;
    } catch { info.style.display = 'none'; }
    onReasonChange();
  }

  function onReasonChange() {
    const reason   = document.getElementById('res-reason')?.value;
    const termDate = document.getElementById('res-date')?.value;
    const admission = document.getElementById('res-emp')?.dataset?.admission;
    const section  = document.getElementById('res-aviso-section');
    const infoEl   = document.getElementById('res-aviso-info');
    const noticeType = document.getElementById('res-notice-type')?.value;

    if (['com_justa_causa', 'aposentadoria'].includes(reason)) {
      if (section) section.style.display = 'none';
      return;
    }
    if (section) section.style.display = 'block';

    const noticeDays = calcNoticeDays(reason, admission, termDate);
    const years = admission && termDate
      ? Math.floor((new Date(termDate) - new Date(admission)) / (365.25 * 24 * 3600 * 1000))
      : 0;

    if (infoEl) {
      const extra = Math.min(Math.max(0, years) * 3, 60);
      infoEl.innerHTML = `
        <strong>${noticeDays} dias</strong> de aviso prévio
        (30 base + ${extra} adicionais — Lei 12.506/2011)
        ${reason === 'acordo' ? '· <em>50% por acordo mútuo</em>' : ''}`;
    }

    // Ajusta tipo default por motivo
    const typeEl = document.getElementById('res-notice-type');
    if (typeEl && reason === 'pedido_demissao') {
      if (typeEl.querySelector('option[value="nao_cumprido"]')) {
        // already there
      }
    }

    onNoticeTypeChange();
    onNoticeStartChange();
  }

  function onNoticeTypeChange() {
    const noticeType = document.getElementById('res-notice-type')?.value;
    const startGroup = document.getElementById('res-notice-start-group');
    if (startGroup) {
      startGroup.style.display = noticeType === 'trabalhado' ? 'block' : 'none';
    }
    const endInfo = document.getElementById('res-notice-end-info');
    if (endInfo && noticeType !== 'trabalhado') {
      endInfo.style.display = 'none';
    }
    onNoticeStartChange();
  }

  function onNoticeStartChange() {
    const noticeType  = document.getElementById('res-notice-type')?.value;
    const startVal    = document.getElementById('res-notice-start')?.value;
    const endInfo     = document.getElementById('res-notice-end-info');
    const reason      = document.getElementById('res-reason')?.value;
    const admission   = document.getElementById('res-emp')?.dataset?.admission;
    const termDate    = document.getElementById('res-date')?.value;

    if (noticeType !== 'trabalhado' || !startVal) {
      if (endInfo) endInfo.style.display = 'none';
      return;
    }
    const noticeDays = calcNoticeDays(reason, admission, termDate || startVal);
    const endDate    = addDays(startVal, noticeDays);
    if (endInfo && endDate) {
      endInfo.style.display = 'block';
      endInfo.innerHTML = `Término do aviso: <strong>${fmt.date(endDate)}</strong>
        · O funcionário trabalha normalmente até essa data.
        O saldo de salário após o último holerite entra na rescisão.`;
      // Auto-fill termination date
      const termEl = document.getElementById('res-date');
      if (termEl && !termEl.dataset.manual) termEl.value = endDate;
    }
  }

  // ── Registrar rescisão ───────────────────────────────────────────────────────

  async function calcular() {
    const empId      = parseInt(document.getElementById('res-emp').value) || 0;
    const reason     = document.getElementById('res-reason').value;
    const termDate   = document.getElementById('res-date').value;
    const noticeType = document.getElementById('res-notice-type')?.value;
    const noticeStart = document.getElementById('res-notice-start')?.value;
    const notes      = document.getElementById('res-notes')?.value || '';
    const errEl      = document.getElementById('res-error');
    errEl.innerHTML  = '';

    if (!empId)    { errEl.innerHTML = '<div class="alert alert-error">Selecione um funcionário.</div>'; return; }
    if (!termDate) { errEl.innerHTML = '<div class="alert alert-error">Informe a data da rescisão.</div>'; return; }

    const noticeWorked = noticeType === 'trabalhado';
    const payload = {
      employee_id:       empId,
      termination_date:  termDate,
      reason,
      notice_worked:     noticeWorked,
      notice_start_date: noticeWorked && noticeStart ? noticeStart : null,
      notes:             notes || null,
    };

    // Para pedido de demissão sem cumprir: também marca notice_worked=false
    // A dedução é automática no backend

    const resultEl = document.getElementById('res-result');
    resultEl.innerHTML = '<div style="text-align:center;padding:40px"><div class="spinner spinner-dark"></div></div>';

    try {
      const t = await Api.createTermination(payload);
      renderResult(t);
      loadHistory();
      document.getElementById('res-emp').value          = '';
      document.getElementById('res-emp-info').style.display = 'none';
      document.getElementById('res-notes').value        = '';
      const futura = t.termination_date > new Date().toISOString().split('T')[0];
      toast(futura
        ? `Rescisão registrada! Funcionário será inativado em ${fmt.date(t.termination_date)}.`
        : 'Rescisão registrada! Funcionário inativado.', 'success');
    } catch (e) {
      errEl.innerHTML = `<div class="alert alert-error">${e.message}</div>`;
      resultEl.innerHTML = '<div style="text-align:center;padding:40px;color:var(--text-muted)">Erro ao registrar.</div>';
    }
  }

  // ── Renderizar verbas (editáveis) ────────────────────────────────────────────

  let _currentTermId = null;

  function renderResult(t) {
    _currentTermId = t.id;
    const resultEl  = document.getElementById('res-result');
    const actionsEl = document.getElementById('res-edit-actions');
    if (actionsEl) actionsEl.style.display = 'flex';

    const reason     = t.reason;
    const notWorked  = !t.notice_worked;
    const avisoLabel = noticeLabelFor(reason, t.notice_worked);
    const isPedido   = reason === 'pedido_demissao';

    const inp = (id, val) =>
      `<input id="res-v-${id}" type="number" step="0.01" min="0"
              style="width:110px;text-align:right;border:1px solid var(--border);border-radius:4px;padding:2px 6px;font-size:13px;font-weight:600"
              value="${parseFloat(val||0).toFixed(2)}"
              oninput="PageRescisao.recalcResult()">`;

    const row = (label, inputHtml, color = '') =>
      `<div style="display:flex;justify-content:space-between;align-items:center;padding:6px 0;border-bottom:1px solid var(--border)">
        <span style="color:${color || 'var(--text-muted)'};font-size:13px">${label}</span>
        ${inputHtml}
      </div>`;

    const noticePeriodHtml = t.notice_start_date
      ? `<div style="font-size:11px;color:var(--text-muted);margin-bottom:12px;background:var(--bg);border-radius:6px;padding:8px">
           Aviso: ${fmt.date(t.notice_start_date)} → ${fmt.date(t.notice_end_date || t.termination_date)}
           · ${t.notice_days} dias · ${t.notice_worked ? 'Trabalhado' : 'Indenizado'}
         </div>`
      : `<div style="font-size:11px;color:var(--text-muted);margin-bottom:12px">
           Aviso: ${t.notice_days} dias · ${t.notice_worked ? 'Trabalhado' : 'Indenizado'}
         </div>`;

    resultEl.innerHTML = `
      <div style="font-size:13px">
        ${noticePeriodHtml}

        <div style="font-size:11px;color:var(--text-muted);margin-bottom:8px;font-style:italic">
          Os valores abaixo podem ser editados manualmente. Clique em ↺ para recalcular totais.
        </div>

        ${row('Saldo de Salário',        inp('saldo',    t.saldo_salario))}
        ${row('Férias Proporcionais',    inp('fer-prop', t.ferias_proporcionais))}
        ${row('1/3 Férias Proporcionais',inp('terc-prop',t.um_terco_ferias_prop))}
        ${t.ferias_vencidas > 0 || true ? row('Férias Vencidas', inp('fer-venc', t.ferias_vencidas)) : ''}
        ${t.um_terco_ferias_venc > 0 || true ? row('1/3 Férias Vencidas', inp('terc-venc', t.um_terco_ferias_venc)) : ''}
        ${row('13º Proporcional',        inp('dec13',    t.decimo_terceiro_prop))}
        ${row(avisoLabel,                inp('aviso-ind',t.aviso_previo_indenizado))}
        ${row('Multa FGTS',              inp('multa',    t.multa_fgts))}

        <div style="display:flex;justify-content:space-between;align-items:center;padding:6px 0;border-bottom:1px solid var(--border)">
          <span style="color:var(--success);font-weight:600;font-size:13px">Total Créditos</span>
          <strong style="color:var(--success)" id="res-v-tot-cred">${fmt.brl(t.total_creditos)}</strong>
        </div>

        <div style="height:8px"></div>
        <div style="font-size:12px;font-weight:600;color:var(--text-muted);margin-bottom:4px">DESCONTOS</div>
        ${row('INSS Rescisão',           inp('inss',     t.inss_rescisao), 'var(--danger)')}
        ${isPedido ? row('Desc. Aviso Prévio ' + (notWorked ? '(não cumprido)' : ''), inp('aviso-desc', t.aviso_previo_desconto), 'var(--danger)') : ''}
        ${!isPedido ? `<input type="hidden" id="res-v-aviso-desc" value="0">` : ''}

        <div style="display:flex;justify-content:space-between;align-items:center;padding:6px 0;border-bottom:2px solid var(--border)">
          <span style="color:var(--danger);font-weight:600;font-size:13px">Total Descontos</span>
          <strong style="color:var(--danger)" id="res-v-tot-desc">- ${fmt.brl(t.total_descontos)}</strong>
        </div>

        <div style="display:flex;justify-content:space-between;align-items:center;padding:12px 0 4px">
          <span style="font-size:15px;font-weight:700">LÍQUIDO A RECEBER</span>
          <span style="font-size:18px;font-weight:700;color:var(--primary)" id="res-v-liquido">${fmt.brl(t.liquido)}</span>
        </div>
      </div>`;
  }

  function recalcResult() {
    recalcFromInputs('res-v');
  }

  async function salvarEdicao() {
    if (!_currentTermId) return;
    const v = (id) => parseFloat(document.getElementById(`res-v-${id}`)?.value || '0') || 0;
    try {
      const t = await Api.updateTermination(_currentTermId, {
        saldo_salario:           v('saldo'),
        ferias_proporcionais:    v('fer-prop'),
        um_terco_ferias_prop:    v('terc-prop'),
        ferias_vencidas:         v('fer-venc'),
        um_terco_ferias_venc:    v('terc-venc'),
        decimo_terceiro_prop:    v('dec13'),
        aviso_previo_indenizado: v('aviso-ind'),
        multa_fgts:              v('multa'),
        inss_rescisao:           v('inss'),
        aviso_previo_desconto:   v('aviso-desc'),
      });
      renderResult(t);
      loadHistory();
      toast('Rescisão atualizada!', 'success');
    } catch (e) { toast(e.message, 'error'); }
  }

  // ── Histórico ────────────────────────────────────────────────────────────────

  async function loadHistory() {
    try {
      const list = await Api.getTerminations() || [];
      if (!list.length) {
        document.getElementById('res-history-tbody').innerHTML = emptyRow('Nenhuma rescisão registrada.', 7);
        return;
      }
      document.getElementById('res-history-tbody').innerHTML = list.map(t => {
        const isPendente = t.status === 'pendente';
        const actionBtns = isPendente ? `
          <button class="btn-icon" onclick="PageRescisao.openDetail(${t.id})" title="Ver / editar" style="color:var(--primary)">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
          </button>
          <button class="btn-icon" onclick="PageRescisao.confirmClose(${t.id},'${(t.employee_name||'').replace(/'/g,'')}')" title="Concluir rescisão" style="color:#16a34a">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>
          </button>
          <button class="btn-icon" onclick="PageRescisao.confirmDelete(${t.id},'${(t.employee_name||'').replace(/'/g,'')}')" title="Excluir" style="color:var(--danger)">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6M14 11v6"/></svg>
          </button>` : `
          <button class="btn-icon" onclick="PageRescisao.openDetail(${t.id})" title="Ver detalhes">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
          </button>`;
        return `
          <tr>
            <td><strong>${t.employee_name || '—'}</strong></td>
            <td>${fmtReason(t.reason)}</td>
            <td>${fmt.date(t.termination_date)}</td>
            <td>${t.notice_days} dias · ${t.notice_worked ? 'Trabalhado' : 'Indenizado'}</td>
            <td>${statusBadge(t.status)}</td>
            <td><strong>${fmt.brl(t.liquido)}</strong></td>
            <td class="td-actions">${actionBtns}</td>
          </tr>`;
      }).join('');
    } catch (e) {
      document.getElementById('res-history-tbody').innerHTML = emptyRow(e.message, 7);
    }
  }

  async function confirmClose(id, name) {
    if (!confirm(`Concluir a rescisão de ${name}?\n\nAo concluir:\n• O funcionário será inativado\n• A rescisão ficará bloqueada para edição\n\nEssa ação não pode ser desfeita.`)) return;
    try {
      await Api.closeTermination(id);
      toast('Rescisão concluída! Funcionário inativado.', 'success');
      loadHistory();
    } catch (e) { toast(e.message, 'error'); }
  }

  async function confirmDelete(id, name) {
    if (!confirm(`Excluir a rescisão de ${name}?\n\nO funcionário voltará a estar ativo.\nEssa ação não pode ser desfeita.`)) return;
    try {
      await Api.deleteTermination(id);
      toast('Rescisão excluída.', 'success');
      loadHistory();
      // Limpa painel de resultado se era essa rescisão
      if (_currentTermId === id) {
        _currentTermId = null;
        document.getElementById('res-result').innerHTML =
          '<div style="text-align:center;padding:40px;color:var(--text-muted)"><p>Rescisão excluída.</p></div>';
        const acts = document.getElementById('res-edit-actions');
        if (acts) acts.style.display = 'none';
      }
    } catch (e) { toast(e.message, 'error'); }
  }

  // ── Modal de detalhe / edição ─────────────────────────────────────────────────

  async function openDetail(id) {
    openModal('Rescisão — Detalhe / Edição',
      '<div style="padding:20px;text-align:center"><div class="spinner spinner-dark"></div></div>',
      '', true);
    try {
      const t    = await Api.getTermination(id);
      const pId  = `md-${id}`;
      const reason = t.reason;
      const isPedido = reason === 'pedido_demissao';
      const avisoLabel = noticeLabelFor(reason, t.notice_worked);

      const inp = (fId, val) =>
        `<input id="${pId}-${fId}" type="number" step="0.01" min="0"
                style="width:110px;text-align:right;border:1px solid var(--border);border-radius:4px;padding:2px 6px;font-size:13px;font-weight:600"
                value="${parseFloat(val||0).toFixed(2)}"
                oninput="PageRescisao._recalcModal('${pId}')">`;

      const row = (label, inputHtml, color = '') =>
        `<div style="display:flex;justify-content:space-between;align-items:center;padding:5px 0;border-bottom:1px solid var(--border)">
          <span style="color:${color || 'var(--text-muted)'};font-size:13px">${label}</span>
          ${inputHtml}
        </div>`;

      const noticePeriodHtml = t.notice_start_date
        ? `Aviso: ${fmt.date(t.notice_start_date)} → ${fmt.date(t.notice_end_date || t.termination_date)} · ${t.notice_days} dias`
        : `Aviso: ${t.notice_days} dias`;

      document.getElementById('modal-body').innerHTML = `
        <div class="detail-grid" style="margin-bottom:12px">
          <div class="detail-item"><label>Funcionário</label><span>${t.employee_name || '—'}</span></div>
          <div class="detail-item"><label>Motivo</label><span>${fmtReason(t.reason)}</span></div>
          <div class="detail-item"><label>Data Rescisão</label><span>${fmt.date(t.termination_date)}</span></div>
          <div class="detail-item"><label>Aviso Prévio</label><span>${noticePeriodHtml} · ${t.notice_worked ? 'Trabalhado' : 'Indenizado'}</span></div>
        </div>
        <div style="font-size:11px;color:var(--text-muted);margin-bottom:10px;font-style:italic">
          Edite os valores e clique em Salvar para atualizar a rescisão.
        </div>
        ${row('Saldo de Salário',          inp('saldo',    t.saldo_salario))}
        ${row('Férias Proporcionais',      inp('fer-prop', t.ferias_proporcionais))}
        ${row('1/3 Férias Proporcionais',  inp('terc-prop',t.um_terco_ferias_prop))}
        ${row('Férias Vencidas',           inp('fer-venc', t.ferias_vencidas))}
        ${row('1/3 Férias Vencidas',       inp('terc-venc',t.um_terco_ferias_venc))}
        ${row('13º Proporcional',          inp('dec13',    t.decimo_terceiro_prop))}
        ${row(avisoLabel,                  inp('aviso-ind',t.aviso_previo_indenizado))}
        ${row('Multa FGTS',                inp('multa',    t.multa_fgts))}
        <div style="display:flex;justify-content:space-between;align-items:center;padding:5px 0;border-bottom:1px solid var(--border)">
          <strong style="color:var(--success);font-size:13px">Total Créditos</strong>
          <strong style="color:var(--success)" id="${pId}-tot-cred">${fmt.brl(t.total_creditos)}</strong>
        </div>
        <div style="height:6px"></div>
        ${row('INSS Rescisão', inp('inss', t.inss_rescisao), 'var(--danger)')}
        ${isPedido
          ? row('Desc. Aviso Prévio', inp('aviso-desc', t.aviso_previo_desconto), 'var(--danger)')
          : `<input type="hidden" id="${pId}-aviso-desc" value="0">`}
        <div style="display:flex;justify-content:space-between;align-items:center;padding:5px 0;border-bottom:2px solid var(--border)">
          <strong style="color:var(--danger);font-size:13px">Total Descontos</strong>
          <strong style="color:var(--danger)" id="${pId}-tot-desc">- ${fmt.brl(t.total_descontos)}</strong>
        </div>
        <div style="display:flex;justify-content:space-between;align-items:center;padding:10px 0 0">
          <strong style="font-size:15px">LÍQUIDO</strong>
          <strong style="font-size:18px;color:var(--primary)" id="${pId}-liquido">${fmt.brl(t.liquido)}</strong>
        </div>`;

      const isPendente = t.status === 'pendente';
      if (!isPendente) {
        // Bloqueia inputs se concluída
        document.getElementById('modal-body').querySelectorAll('input[type=number]').forEach(el => {
          el.disabled = true;
          el.style.background = 'var(--bg)';
          el.style.color = 'var(--text-muted)';
        });
        document.getElementById('modal-body').insertAdjacentHTML('afterbegin',
          `<div class="alert" style="background:#dcfce7;color:#15803d;border:none;margin-bottom:12px;font-size:13px">
            ✓ Rescisão concluída — não é possível editar.
           </div>`);
      }

      document.getElementById('modal-footer').innerHTML = isPendente ? `
        <button class="btn btn-secondary" onclick="closeModal()">Fechar</button>
        <button class="btn btn-secondary" onclick="PageRescisao._recalcModal('${pId}')">↺ Recalcular</button>
        <button class="btn btn-danger" onclick="PageRescisao.confirmDelete(${id},'${t.employee_name||''}');closeModal()">🗑 Excluir</button>
        <button class="btn btn-primary" onclick="PageRescisao._saveModal(${id},'${pId}')">💾 Salvar</button>
        <button class="btn btn-success" onclick="PageRescisao.confirmClose(${id},'${t.employee_name||''}');closeModal()">✓ Concluir Rescisão</button>
      ` : `
        <button class="btn btn-secondary" onclick="closeModal()">Fechar</button>`;
    } catch (e) {
      document.getElementById('modal-body').innerHTML = `<div class="alert alert-error">${e.message}</div>`;
    }
  }

  function _recalcModal(pId) {
    const v = (id) => parseFloat(document.getElementById(`${pId}-${id}`)?.value || '0') || 0;
    const credits = v('saldo') + v('fer-prop') + v('terc-prop') + v('fer-venc') +
                    v('terc-venc') + v('dec13') + v('aviso-ind') + v('multa');
    const deducts = v('inss') + v('aviso-desc');
    const el = (id) => document.getElementById(`${pId}-${id}`);
    if (el('tot-cred')) el('tot-cred').textContent = fmt.brl(credits);
    if (el('tot-desc')) el('tot-desc').textContent = '- ' + fmt.brl(deducts);
    if (el('liquido'))  el('liquido').textContent  = fmt.brl(credits - deducts);
  }

  async function _saveModal(termId, pId) {
    const v = (id) => parseFloat(document.getElementById(`${pId}-${id}`)?.value || '0') || 0;
    try {
      await Api.updateTermination(termId, {
        saldo_salario:           v('saldo'),
        ferias_proporcionais:    v('fer-prop'),
        um_terco_ferias_prop:    v('terc-prop'),
        ferias_vencidas:         v('fer-venc'),
        um_terco_ferias_venc:    v('terc-venc'),
        decimo_terceiro_prop:    v('dec13'),
        aviso_previo_indenizado: v('aviso-ind'),
        multa_fgts:              v('multa'),
        inss_rescisao:           v('inss'),
        aviso_previo_desconto:   v('aviso-desc'),
      });
      closeModal();
      loadHistory();
      toast('Rescisão atualizada!', 'success');
    } catch (e) { toast(e.message, 'error'); }
  }

  return {
    render, onEmpChange, onReasonChange, onNoticeTypeChange, onNoticeStartChange,
    calcular, recalcResult, salvarEdicao,
    openDetail, _recalcModal, _saveModal,
    confirmClose, confirmDelete,
  };
})();
