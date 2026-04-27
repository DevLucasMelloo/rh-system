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

  // Recalcula totais a partir dos inputs de edição (férias unificada)
  function recalcFromInputs(prefix) {
    const v = (id) => parseFloat(document.getElementById(`${prefix}-${id}`)?.value || '0') || 0;
    const credits = v('saldo') + v('ferias') + v('terc-ferias') + v('dec13') + v('aviso-ind');
    const deducts = v('inss') + v('aviso-desc');
    const set = (id, val) => {
      const el = document.getElementById(`${prefix}-${id}`);
      if (el) el.textContent = fmt.brl(val);
    };
    set('tot-cred', credits);
    set('tot-desc', deducts);
    set('liquido',  credits - deducts);
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
              <div class="form-row" style="margin-bottom:8px">
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

              <!-- Opção de redução — só para sem justa causa + trabalhado (CLT art. 488) -->
              <div id="res-reduction-group" style="display:none;margin-top:6px">
                <label style="font-size:12px;color:var(--text-muted);display:block;margin-bottom:6px">
                  Opção do funcionário (CLT art. 488)
                </label>
                <div style="display:flex;gap:16px;font-size:13px">
                  <label style="display:flex;align-items:center;gap:6px;cursor:pointer">
                    <input type="radio" name="res-reduction" value="2h_dia" id="res-red-2h" checked
                           onchange="PageRescisao.onNoticeStartChange()">
                    Redução de 2h/dia (trabalha ${30} dias)
                  </label>
                  <label style="display:flex;align-items:center;gap:6px;cursor:pointer">
                    <input type="radio" name="res-reduction" value="7_dias" id="res-red-7d"
                           onchange="PageRescisao.onNoticeStartChange()">
                    Redução de 7 dias (trabalha ${30}-7 dias)
                  </label>
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

        <!-- Verbas calculadas -->
        <div class="card">
          <div class="card-header" style="display:flex;align-items:center;justify-content:space-between">
            <span>Verbas Rescisórias</span>
            <div id="res-edit-actions" style="display:none;gap:8px">
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
      document.getElementById('res-emp').dataset.admission = emp.admission_date;
    } catch { info.style.display = 'none'; }
    onReasonChange();
  }

  function onReasonChange() {
    const reason    = document.getElementById('res-reason')?.value;
    const termDate  = document.getElementById('res-date')?.value;
    const admission = document.getElementById('res-emp')?.dataset?.admission;
    const section   = document.getElementById('res-aviso-section');
    const infoEl    = document.getElementById('res-aviso-info');

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
    onNoticeTypeChange();
    onNoticeStartChange();
  }

  function onNoticeTypeChange() {
    const noticeType = document.getElementById('res-notice-type')?.value;
    const reason     = document.getElementById('res-reason')?.value;
    const startGroup = document.getElementById('res-notice-start-group');
    const redGroup   = document.getElementById('res-reduction-group');
    const endInfo    = document.getElementById('res-notice-end-info');

    if (startGroup) startGroup.style.display = noticeType === 'trabalhado' ? 'block' : 'none';
    if (redGroup)   redGroup.style.display =
      (noticeType === 'trabalhado' && reason === 'sem_justa_causa') ? 'block' : 'none';
    if (endInfo && noticeType !== 'trabalhado') endInfo.style.display = 'none';
    onNoticeStartChange();
  }

  function onNoticeStartChange() {
    const noticeType  = document.getElementById('res-notice-type')?.value;
    const startVal    = document.getElementById('res-notice-start')?.value;
    const endInfo     = document.getElementById('res-notice-end-info');
    const reason      = document.getElementById('res-reason')?.value;
    const admission   = document.getElementById('res-emp')?.dataset?.admission;
    const termDate    = document.getElementById('res-date')?.value;
    const reduction   = document.querySelector('input[name="res-reduction"]:checked')?.value;

    if (noticeType !== 'trabalhado' || !startVal) {
      if (endInfo) endInfo.style.display = 'none';
      return;
    }
    const noticeDays    = calcNoticeDays(reason, admission, termDate || startVal);
    const effectiveDays = noticeDays - (reduction === '7_dias' ? 7 : 0);
    const endDate       = addDays(startVal, Math.max(1, effectiveDays));

    // Update the radio label with actual days
    const label7d = document.getElementById('res-red-7d')?.parentElement;
    if (label7d) label7d.childNodes[1].textContent = ` Redução de 7 dias (trabalha ${noticeDays - 7} dias)`;
    const label2h = document.getElementById('res-red-2h')?.parentElement;
    if (label2h) label2h.childNodes[1].textContent = ` Redução de 2h/dia (trabalha ${noticeDays} dias)`;

    if (endInfo && endDate) {
      endInfo.style.display = 'block';
      const reductionDesc = reason === 'sem_justa_causa'
        ? (reduction === '7_dias'
            ? ` · Redução de 7 dias aplicada (trabalha ${noticeDays - 7} dias)`
            : ` · Redução de 2h/dia (${noticeDays} dias normais)`)
        : '';
      endInfo.innerHTML = `Término do aviso: <strong>${fmt.date(endDate)}</strong>${reductionDesc}`;
      const termEl = document.getElementById('res-date');
      if (termEl && !termEl.dataset.manual) termEl.value = endDate;
    }
  }

  // ── Registrar rescisão ───────────────────────────────────────────────────────

  async function calcular() {
    const empId       = parseInt(document.getElementById('res-emp').value) || 0;
    const reason      = document.getElementById('res-reason').value;
    const termDate    = document.getElementById('res-date').value;
    const noticeType  = document.getElementById('res-notice-type')?.value;
    const noticeStart = document.getElementById('res-notice-start')?.value;
    const reduction   = document.querySelector('input[name="res-reduction"]:checked')?.value;
    const notes       = document.getElementById('res-notes')?.value || '';
    const errEl       = document.getElementById('res-error');
    errEl.innerHTML   = '';

    if (!empId)    { errEl.innerHTML = '<div class="alert alert-error">Selecione um funcionário.</div>'; return; }
    if (!termDate) { errEl.innerHTML = '<div class="alert alert-error">Informe a data da rescisão.</div>'; return; }

    const noticeWorked = noticeType === 'trabalhado';
    const payload = {
      employee_id:       empId,
      termination_date:  termDate,
      reason,
      notice_worked:     noticeWorked,
      notice_start_date: noticeWorked && noticeStart ? noticeStart : null,
      notice_reduction:  (noticeWorked && reason === 'sem_justa_causa') ? (reduction || '2h_dia') : null,
      notes:             notes || null,
    };

    const resultEl = document.getElementById('res-result');
    resultEl.innerHTML = '<div style="text-align:center;padding:40px"><div class="spinner spinner-dark"></div></div>';

    try {
      const t = await Api.createTermination(payload);
      renderResult(t);
      loadHistory();
      document.getElementById('res-emp').value = '';
      document.getElementById('res-emp-info').style.display = 'none';
      document.getElementById('res-notes').value = '';
      toast('Rescisão registrada! Confirme quando concluir o processo.', 'success');
    } catch (e) {
      errEl.innerHTML = `<div class="alert alert-error">${e.message}</div>`;
      resultEl.innerHTML = '<div style="text-align:center;padding:40px;color:var(--text-muted)">Erro ao registrar.</div>';
    }
  }

  // ── Renderizar verbas (editáveis, férias unificada) ──────────────────────────

  let _currentTermId = null;

  function _verbRow(label, ref, inputHtml, colorLabel = '') {
    return `
      <div style="display:flex;justify-content:space-between;align-items:center;padding:6px 0;border-bottom:1px solid var(--border)">
        <div>
          <div style="font-size:13px;color:${colorLabel || 'var(--text-muted)'};">${label}</div>
          ${ref ? `<div style="font-size:11px;color:var(--text-muted);margin-top:1px">${ref}</div>` : ''}
        </div>
        ${inputHtml}
      </div>`;
  }

  function _inp(id, val) {
    return `<input id="${id}" type="number" step="0.01" min="0"
      style="width:110px;text-align:right;border:1px solid var(--border);border-radius:4px;padding:2px 6px;font-size:13px;font-weight:600"
      value="${parseFloat(val||0).toFixed(2)}"
      oninput="PageRescisao.recalcResult()">`;
  }

  function renderResult(t) {
    _currentTermId  = t.id;
    const resultEl  = document.getElementById('res-result');
    const actionsEl = document.getElementById('res-edit-actions');
    if (actionsEl) actionsEl.style.display = 'flex';

    const reason     = t.reason;
    const avisoLabel = noticeLabelFor(reason, t.notice_worked);
    const isPedido   = reason === 'pedido_demissao';

    // Totais unificados de férias
    const ferTotal  = (parseFloat(t.ferias_proporcionais)||0) + (parseFloat(t.ferias_vencidas)||0);
    const tercTotal = (parseFloat(t.um_terco_ferias_prop)||0) + (parseFloat(t.um_terco_ferias_venc)||0);

    // Referências
    const ferMeses   = (t.ferias_meses_prop||0) + (t.ferias_meses_venc||0);
    let   ferRef     = ferMeses + ' mês(es)';
    if (t.ferias_meses_prop > 0 && t.ferias_meses_venc > 0)
      ferRef = `${ferMeses} meses (${t.ferias_meses_prop} prop. + ${t.ferias_meses_venc} vencido(s))`;
    else if (t.ferias_meses_venc > 0)
      ferRef = `${t.ferias_meses_venc} período(s) vencido(s)`;
    else
      ferRef = `${t.ferias_meses_prop} mês(es) proporcional`;

    const saldoRef  = `${t.saldo_dias || t.termination_date?.split('-')[2] || '?'} dias`;
    const dec13Ref  = `${t.decimo_meses||0} mês(es) trabalhados${t.decimo_ja_pago > 0 ? ` · 1ª parcela já paga: ${fmt.brl(t.decimo_ja_pago)} descontado` : ''}`;

    const reductionLabel = t.notice_reduction === '7_dias'
      ? ' · Redução de 7 dias (CLT art. 488)'
      : t.notice_reduction === '2h_dia'
        ? ' · Redução de 2h/dia (CLT art. 488)'
        : '';
    const noticePeriodHtml = t.notice_start_date
      ? `<div style="font-size:11px;color:var(--text-muted);margin-bottom:10px;background:var(--bg);border-radius:6px;padding:8px">
           Aviso: ${fmt.date(t.notice_start_date)} → ${fmt.date(t.notice_end_date || t.termination_date)}
           · ${t.notice_days} dias · ${t.notice_worked ? 'Trabalhado' : 'Indenizado'}${reductionLabel}
         </div>`
      : `<div style="font-size:11px;color:var(--text-muted);margin-bottom:8px">
           Aviso: ${t.notice_days} dias · ${t.notice_worked ? 'Trabalhado' : 'Indenizado'}${reductionLabel}
         </div>`;

    resultEl.innerHTML = `
      <div style="font-size:13px">
        ${noticePeriodHtml}
        <div style="font-size:11px;color:var(--text-muted);margin-bottom:10px;font-style:italic">
          Valores editáveis. Clique em ↺ para recalcular totais.
        </div>

        ${_verbRow('Saldo de Salário', saldoRef, _inp('res-v-saldo', t.saldo_salario))}
        ${_verbRow('Férias', ferRef, _inp('res-v-ferias', ferTotal))}
        ${_verbRow('1/3 Férias', `sobre ${ferMeses} mês(es)`, _inp('res-v-terc-ferias', tercTotal))}
        ${_verbRow('13º Proporcional', dec13Ref, _inp('res-v-dec13', t.decimo_terceiro_prop))}
        ${parseFloat(t.aviso_previo_indenizado) > 0 || !isPedido
          ? _verbRow(avisoLabel, `${t.notice_days} dias`, _inp('res-v-aviso-ind', t.aviso_previo_indenizado))
          : `<input type="hidden" id="res-v-aviso-ind" value="0">`}

        <div style="display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid var(--border)">
          <strong style="color:var(--success);font-size:13px">Total Créditos</strong>
          <strong style="color:var(--success)" id="res-v-tot-cred">${fmt.brl(t.total_creditos)}</strong>
        </div>

        <div style="height:6px"></div>
        <div style="font-size:12px;font-weight:600;color:var(--text-muted);margin-bottom:4px">DESCONTOS</div>
        ${_verbRow('INSS Rescisão', '', _inp('res-v-inss', t.inss_rescisao), 'var(--danger)')}
        ${isPedido
          ? _verbRow('Desc. Aviso Prévio (não cumprido)', `${t.notice_days} dias`, _inp('res-v-aviso-desc', t.aviso_previo_desconto), 'var(--danger)')
          : `<input type="hidden" id="res-v-aviso-desc" value="0">`}

        <div style="display:flex;justify-content:space-between;align-items:center;padding:6px 0;border-bottom:2px solid var(--border)">
          <strong style="color:var(--danger);font-size:13px">Total Descontos</strong>
          <strong style="color:var(--danger)" id="res-v-tot-desc">- ${fmt.brl(t.total_descontos)}</strong>
        </div>

        <div style="display:flex;justify-content:space-between;align-items:center;padding:12px 0 4px">
          <span style="font-size:15px;font-weight:700">LÍQUIDO A RECEBER</span>
          <span style="font-size:18px;font-weight:700;color:var(--primary)" id="res-v-liquido">${fmt.brl(t.liquido)}</span>
        </div>

        <button class="btn btn-secondary w-full" style="margin-top:12px;font-size:12px"
                onclick="PageRescisao.printReceipt(${t.id})">🖨 Imprimir Recibo</button>
      </div>`;
  }

  function recalcResult() { recalcFromInputs('res-v'); }

  async function salvarEdicao() {
    if (!_currentTermId) return;
    const v = (id) => parseFloat(document.getElementById(`res-v-${id}`)?.value || '0') || 0;
    // Férias unificada → vai toda para ferias_proporcionais, zera ferias_vencidas
    try {
      const t = await Api.updateTermination(_currentTermId, {
        saldo_salario:           v('saldo'),
        ferias_proporcionais:    v('ferias'),
        um_terco_ferias_prop:    v('terc-ferias'),
        ferias_vencidas:         0,
        um_terco_ferias_venc:    0,
        decimo_terceiro_prop:    v('dec13'),
        aviso_previo_indenizado: v('aviso-ind'),
        multa_fgts:              0,
        inss_rescisao:           v('inss'),
        aviso_previo_desconto:   v('aviso-desc'),
      });
      renderResult(t);
      loadHistory();
      toast('Rescisão atualizada!', 'success');
    } catch (e) { toast(e.message, 'error'); }
  }

  // ── Recibo de impressão ───────────────────────────────────────────────────────

  async function printReceipt(id) {
    try {
      const t = await Api.getTermination(id);
      const ferTotal  = (parseFloat(t.ferias_proporcionais)||0) + (parseFloat(t.ferias_vencidas)||0);
      const tercTotal = (parseFloat(t.um_terco_ferias_prop)||0) + (parseFloat(t.um_terco_ferias_venc)||0);
      const ferMeses  = (t.ferias_meses_prop||0) + (t.ferias_meses_venc||0);
      let ferRef = `${ferMeses} mês(es)`;
      if (t.ferias_meses_prop > 0 && t.ferias_meses_venc > 0)
        ferRef = `${ferMeses} meses (${t.ferias_meses_prop} prop. + ${t.ferias_meses_venc} venc.)`;
      const saldoDias = t.saldo_dias || t.termination_date?.split('-')[2] || '?';
      const avisoLabel = noticeLabelFor(t.reason, t.notice_worked);
      const isPedido   = t.reason === 'pedido_demissao';

      const row = (label, ref, val, neg = false) => val == 0 ? '' : `
        <tr>
          <td style="padding:6px 8px;border-bottom:1px solid #e5e7eb">${label}${ref ? `<br><small style="color:#6b7280">${ref}</small>` : ''}</td>
          <td style="padding:6px 8px;border-bottom:1px solid #e5e7eb;text-align:right;font-weight:600;color:${neg?'#dc2626':'#111'}">${neg?'- ':''}${fmt.brl(val)}</td>
        </tr>`;

      const html = `<!DOCTYPE html><html lang="pt-BR"><head>
        <meta charset="UTF-8">
        <title>Recibo de Rescisão — ${t.employee_name}</title>
        <style>
          body{font-family:Arial,sans-serif;font-size:13px;color:#111;margin:0;padding:24px}
          h1{font-size:18px;margin:0 0 4px}
          h2{font-size:14px;font-weight:normal;color:#6b7280;margin:0 0 20px}
          table{width:100%;border-collapse:collapse}
          .section-title{font-size:11px;font-weight:700;color:#6b7280;letter-spacing:.05em;text-transform:uppercase;padding:10px 8px 4px;background:#f9fafb}
          .total-row td{font-weight:700;padding:8px;border-top:2px solid #111}
          .net-row td{font-size:16px;font-weight:700;padding:10px 8px;background:#f0fdf4;color:#15803d}
          .info-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px 24px;margin-bottom:20px;background:#f9fafb;padding:12px;border-radius:6px}
          .info-item label{font-size:11px;color:#6b7280;display:block}
          .info-item span{font-weight:600}
          .signatures{display:grid;grid-template-columns:1fr 1fr;gap:40px;margin-top:60px}
          .sig{border-top:1px solid #111;padding-top:8px;font-size:12px;color:#6b7280}
          @media print{body{padding:12px}button{display:none}}
        </style>
      </head><body>
        <h1>Recibo de Rescisão Contratual</h1>
        <h2>${fmtReason(t.reason)}</h2>

        <div class="info-grid">
          <div class="info-item"><label>Funcionário</label><span>${t.employee_name || '—'}</span></div>
          <div class="info-item"><label>Data da Rescisão</label><span>${fmt.date(t.termination_date)}</span></div>
          <div class="info-item"><label>Aviso Prévio</label><span>${t.notice_days} dias · ${t.notice_worked ? 'Trabalhado' : 'Indenizado'}${t.notice_reduction === '7_dias' ? ' · Redução de 7 dias' : t.notice_reduction === '2h_dia' ? ' · Redução de 2h/dia' : ''}</span></div>
          ${t.notice_start_date ? `<div class="info-item"><label>Período do Aviso</label><span>${fmt.date(t.notice_start_date)} → ${fmt.date(t.notice_end_date||t.termination_date)}</span></div>` : ''}
          ${t.decimo_ja_pago > 0 ? `<div class="info-item"><label>13º já pago (1ª parcela)</label><span>- ${fmt.brl(t.decimo_ja_pago)}</span></div>` : ''}
        </div>

        <table>
          <tr><td class="section-title" colspan="2">CRÉDITOS</td></tr>
          ${row('Saldo de Salário', `${saldoDias} dias`, t.saldo_salario)}
          ${row('Férias', ferRef, ferTotal)}
          ${row('1/3 Férias', `sobre ${ferMeses} mês(es)`, tercTotal)}
          ${row('13º Proporcional', `${t.decimo_meses||0} mês(es) trabalhados`, t.decimo_terceiro_prop)}
          ${parseFloat(t.aviso_previo_indenizado) > 0 ? row(avisoLabel, `${t.notice_days} dias`, t.aviso_previo_indenizado) : ''}
          <tr class="total-row"><td>Total Créditos</td><td style="text-align:right;color:#16a34a">${fmt.brl(t.total_creditos)}</td></tr>

          <tr><td class="section-title" colspan="2">DESCONTOS</td></tr>
          ${row('INSS Rescisão', '', t.inss_rescisao, true)}
          ${isPedido && parseFloat(t.aviso_previo_desconto) > 0 ? row('Desc. Aviso Prévio (não cumprido)', `${t.notice_days} dias`, t.aviso_previo_desconto, true) : ''}
          <tr class="total-row"><td>Total Descontos</td><td style="text-align:right;color:#dc2626">- ${fmt.brl(t.total_descontos)}</td></tr>

          <tr class="net-row"><td>LÍQUIDO A RECEBER</td><td style="text-align:right">${fmt.brl(t.liquido)}</td></tr>
        </table>

        <div class="signatures">
          <div class="sig">Assinatura do Funcionário<br>${t.employee_name || ''}</div>
          <div class="sig">Assinatura do Responsável RH<br>&nbsp;</div>
        </div>

        <div style="margin-top:40px;font-size:11px;color:#9ca3af;text-align:center">
          Documento gerado em ${new Date().toLocaleDateString('pt-BR')} às ${new Date().toLocaleTimeString('pt-BR','HH:mm')}
        </div>

        <script>window.onload = () => window.print();<\/script>
      </body></html>`;

      const w = window.open('', '_blank', 'width=800,height=700');
      w.document.write(html);
      w.document.close();
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
          </button>
          <button class="btn-icon" onclick="PageRescisao.printReceipt(${t.id})" title="Imprimir recibo" style="color:var(--text-muted)">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 6 2 18 2 18 9"/><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><rect x="6" y="14" width="12" height="8"/></svg>
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
      const t      = await Api.getTermination(id);
      const pId    = `md-${id}`;
      const reason = t.reason;
      const isPendente = t.status === 'pendente';
      const isPedido   = reason === 'pedido_demissao';
      const avisoLabel = noticeLabelFor(reason, t.notice_worked);

      const ferTotal  = (parseFloat(t.ferias_proporcionais)||0) + (parseFloat(t.ferias_vencidas)||0);
      const tercTotal = (parseFloat(t.um_terco_ferias_prop)||0) + (parseFloat(t.um_terco_ferias_venc)||0);
      const ferMeses  = (t.ferias_meses_prop||0) + (t.ferias_meses_venc||0);
      const saldoDias = t.saldo_dias || t.termination_date?.split('-')[2] || '?';

      let ferRef = `${ferMeses} mês(es)`;
      if (t.ferias_meses_prop > 0 && t.ferias_meses_venc > 0)
        ferRef = `${ferMeses} meses (${t.ferias_meses_prop} prop. + ${t.ferias_meses_venc} venc.)`;

      const dec13Ref = `${t.decimo_meses||0} mês(es)${t.decimo_ja_pago > 0 ? ` · 1ª parcela paga: ${fmt.brl(t.decimo_ja_pago)} descontado` : ''}`;

      const inp = (fId, val) =>
        `<input id="${pId}-${fId}" type="number" step="0.01" min="0"
          style="width:110px;text-align:right;border:1px solid var(--border);border-radius:4px;padding:2px 6px;font-size:13px;font-weight:600"
          value="${parseFloat(val||0).toFixed(2)}"
          oninput="PageRescisao._recalcModal('${pId}')">`;

      const row = (label, ref, inputHtml, colorLabel = '') => `
        <div style="display:flex;justify-content:space-between;align-items:center;padding:5px 0;border-bottom:1px solid var(--border)">
          <div>
            <div style="font-size:13px;color:${colorLabel||'var(--text-muted)'};">${label}</div>
            ${ref ? `<div style="font-size:11px;color:var(--text-muted)">${ref}</div>` : ''}
          </div>
          ${inputHtml}
        </div>`;

      const redLabel = t.notice_reduction === '7_dias' ? ' · Redução 7 dias'
                     : t.notice_reduction === '2h_dia' ? ' · Redução 2h/dia' : '';
      const noticePeriodHtml = t.notice_start_date
        ? `Aviso: ${fmt.date(t.notice_start_date)} → ${fmt.date(t.notice_end_date||t.termination_date)} · ${t.notice_days} dias${redLabel}`
        : `Aviso: ${t.notice_days} dias${redLabel}`;

      document.getElementById('modal-body').innerHTML = `
        <div class="detail-grid" style="margin-bottom:12px">
          <div class="detail-item"><label>Funcionário</label><span>${t.employee_name || '—'}</span></div>
          <div class="detail-item"><label>Motivo</label><span>${fmtReason(t.reason)}</span></div>
          <div class="detail-item"><label>Data Rescisão</label><span>${fmt.date(t.termination_date)}</span></div>
          <div class="detail-item"><label>Aviso Prévio</label><span>${noticePeriodHtml} · ${t.notice_worked ? 'Trabalhado' : 'Indenizado'}</span></div>
        </div>
        ${t.decimo_ja_pago > 0 ? `
          <div style="background:#fef3c7;border-radius:6px;padding:8px 12px;font-size:12px;margin-bottom:10px;color:#92400e">
            ⚠ 1ª parcela do 13º já paga: ${fmt.brl(t.decimo_ja_pago)} foi descontada do 13º proporcional.
          </div>` : ''}
        ${!isPendente ? `<div class="alert" style="background:#dcfce7;color:#15803d;border:none;margin-bottom:12px;font-size:13px">✓ Rescisão concluída — não é possível editar.</div>` : ''}
        <div style="font-size:11px;color:var(--text-muted);margin-bottom:10px;font-style:italic">
          ${isPendente ? 'Edite os valores e clique em Salvar.' : ''}
        </div>
        ${row('Saldo de Salário', `${saldoDias} dias`, inp('saldo', t.saldo_salario))}
        ${row('Férias', ferRef, inp('ferias', ferTotal))}
        ${row('1/3 Férias', `sobre ${ferMeses} mês(es)`, inp('terc-ferias', tercTotal))}
        ${row('13º Proporcional', dec13Ref, inp('dec13', t.decimo_terceiro_prop))}
        ${parseFloat(t.aviso_previo_indenizado) >= 0 ? row(avisoLabel, `${t.notice_days} dias`, inp('aviso-ind', t.aviso_previo_indenizado)) : ''}
        <div style="display:flex;justify-content:space-between;align-items:center;padding:6px 0;border-bottom:1px solid var(--border)">
          <strong style="color:var(--success);font-size:13px">Total Créditos</strong>
          <strong style="color:var(--success)" id="${pId}-tot-cred">${fmt.brl(t.total_creditos)}</strong>
        </div>
        <div style="height:4px"></div>
        ${row('INSS Rescisão', '', inp('inss', t.inss_rescisao), 'var(--danger)')}
        ${isPedido ? row('Desc. Aviso Prévio', `${t.notice_days} dias`, inp('aviso-desc', t.aviso_previo_desconto), 'var(--danger)') : `<input type="hidden" id="${pId}-aviso-desc" value="0">`}
        <div style="display:flex;justify-content:space-between;align-items:center;padding:6px 0;border-bottom:2px solid var(--border)">
          <strong style="color:var(--danger);font-size:13px">Total Descontos</strong>
          <strong style="color:var(--danger)" id="${pId}-tot-desc">- ${fmt.brl(t.total_descontos)}</strong>
        </div>
        <div style="display:flex;justify-content:space-between;align-items:center;padding:10px 0 0">
          <strong style="font-size:15px">LÍQUIDO</strong>
          <strong style="font-size:18px;color:var(--primary)" id="${pId}-liquido">${fmt.brl(t.liquido)}</strong>
        </div>`;

      if (!isPendente) {
        document.getElementById('modal-body').querySelectorAll('input[type=number]').forEach(el => {
          el.disabled = true;
          el.style.background = 'var(--bg)';
          el.style.color = 'var(--text-muted)';
        });
      }

      document.getElementById('modal-footer').innerHTML = isPendente ? `
        <button class="btn btn-secondary" onclick="closeModal()">Fechar</button>
        <button class="btn btn-secondary" onclick="PageRescisao._recalcModal('${pId}')">↺ Recalcular</button>
        <button class="btn btn-secondary" onclick="PageRescisao.printReceipt(${id})">🖨 Imprimir</button>
        <button class="btn btn-danger" onclick="PageRescisao.confirmDelete(${id},'${t.employee_name||''}');closeModal()">🗑 Excluir</button>
        <button class="btn btn-primary" onclick="PageRescisao._saveModal(${id},'${pId}')">💾 Salvar</button>
        <button class="btn btn-success" onclick="PageRescisao.confirmClose(${id},'${t.employee_name||''}');closeModal()">✓ Concluir</button>
      ` : `
        <button class="btn btn-secondary" onclick="closeModal()">Fechar</button>
        <button class="btn btn-secondary" onclick="PageRescisao.printReceipt(${id})">🖨 Imprimir Recibo</button>`;
    } catch (e) {
      document.getElementById('modal-body').innerHTML = `<div class="alert alert-error">${e.message}</div>`;
    }
  }

  function _recalcModal(pId) {
    const v = (id) => parseFloat(document.getElementById(`${pId}-${id}`)?.value || '0') || 0;
    const credits = v('saldo') + v('ferias') + v('terc-ferias') + v('dec13') + v('aviso-ind');
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
        ferias_proporcionais:    v('ferias'),
        um_terco_ferias_prop:    v('terc-ferias'),
        ferias_vencidas:         0,
        um_terco_ferias_venc:    0,
        decimo_terceiro_prop:    v('dec13'),
        aviso_previo_indenizado: v('aviso-ind'),
        multa_fgts:              0,
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
    calcular, recalcResult, salvarEdicao, printReceipt,
    openDetail, _recalcModal, _saveModal,
    confirmClose, confirmDelete,
  };
})();
