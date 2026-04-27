const PageTimesheet = (() => {
  const MONTHS = ['Janeiro','Fevereiro','Março','Abril','Maio','Junho',
                  'Julho','Agosto','Setembro','Outubro','Novembro','Dezembro'];

  let view     = 'period';
  let curMonth = currentMonth();
  let curYear  = currentYear();
  let selEmpId   = null;
  let selEmpName = '';
  let periodData = null;
  let daysData   = [];

  // ── Render principal ────────────────────────────────────────────────────────

  async function render(container) {
    container.innerHTML = `
      <div class="page-header">
        <div><h1>Ponto</h1><p>Controle de frequência mensal</p></div>
        <div id="ts-header-actions"></div>
      </div>
      <div id="ts-content"></div>`;
    await loadPeriod();
  }

  function periodOptions() {
    let html = '';
    for (let y = curYear; y >= curYear - 1; y--) {
      for (let m = 12; m >= 1; m--) {
        const sel = (m === curMonth && y === curYear) ? 'selected' : '';
        html += `<option value="${m}|${y}" ${sel}>${MONTHS[m-1]}/${y}</option>`;
      }
    }
    return html;
  }

  // ── View: período ───────────────────────────────────────────────────────────

  async function loadPeriod() {
    view = 'period';
    const content = document.getElementById('ts-content');
    if (!content) return;
    content.innerHTML = `
      <div style="display:flex;gap:12px;align-items:center;margin-bottom:20px;flex-wrap:wrap">
        <select class="form-control" id="ts-period-sel" style="width:200px" onchange="PageTimesheet.onPeriodChange()">
          ${periodOptions()}
        </select>
        <div id="ts-period-badge"></div>
        <div style="flex:1"></div>
        <button class="btn" style="background:#1e3a5f;color:#fff;border:none" onclick="PageTimesheet.openBatchModal()" title="Lançar feriado, recesso ou compensar para vários funcionários">⚡ Lançamento em Lote</button>
      </div>
      <div id="ts-employees-content">${loadingRow(5)}</div>`;
    _updateHeaderActions();
    await fetchAndRenderPeriod();
  }

  async function onPeriodChange() {
    const [m, y] = _getPeriodSel();
    curMonth = m; curYear = y;
    await fetchAndRenderPeriod();
  }

  async function fetchAndRenderPeriod() {
    try {
      periodData = await Api.getTimesheetPeriod(curMonth, curYear);
      renderPeriodView();
    } catch (e) {
      const el = document.getElementById('ts-employees-content');
      if (el) el.innerHTML = `<div class="alert alert-error">${e.message}</div>`;
    }
  }

  function renderPeriodView() {
    if (!periodData) return;
    _updateHeaderActions();

    const badge = document.getElementById('ts-period-badge');
    if (badge) {
      badge.innerHTML = periodData.status === 'not_opened'
        ? '<span class="badge badge-gray">Não aberto</span>'
        : periodData.status === 'open'
          ? '<span class="badge badge-warning">Aberto</span>'
          : '<span class="badge badge-success">Fechado</span>';
    }

    const el = document.getElementById('ts-employees-content');
    if (!el) return;

    if (periodData.status === 'not_opened') {
      el.innerHTML = `
        <div style="text-align:center;padding:48px;color:var(--text-muted)">
          <p style="margin-bottom:16px">O período <strong>${MONTHS[curMonth-1]}/${curYear}</strong> ainda não foi aberto.</p>
          <button class="btn btn-primary" onclick="PageTimesheet.openPeriod()">Abrir Período</button>
        </div>`;
      return;
    }

    if (!periodData.employees.length) {
      el.innerHTML = `<div class="alert alert-warning">Nenhum funcionário ativo para este período.</div>`;
      return;
    }

    const isClosed = periodData.status === 'closed';
    const rows = periodData.employees.map(e => {
      const adm   = e.admission_date ? fmt.date(e.admission_date) : '—';
      const since = e.start_date !== `${curYear}-${String(curMonth).padStart(2,'0')}-01`
        ? `<span style="color:var(--text-muted);font-size:12px"> (desde ${fmt.date(e.start_date)})</span>`
        : '';
      const pct      = e.total_workdays > 0 ? Math.round(e.filled_workdays / e.total_workdays * 100) : 0;
      const barColor = pct === 100 ? 'var(--success)' : pct > 50 ? 'var(--warning)' : 'var(--danger)';
      const bal      = e.balance_minutes || 0;
      const balStr   = _fmtMins(bal);
      const balColor = bal > 0 ? 'var(--success)' : bal < 0 ? 'var(--danger)' : 'inherit';

      return `<tr>
        <td><strong>${e.name}</strong>${since}</td>
        <td>${adm}</td>
        <td style="font-size:12px;color:var(--text-muted)">${fmt.date(e.start_date)} a ${fmt.date(e.end_date)}</td>
        <td style="font-weight:600;color:${balColor};white-space:nowrap">${balStr}</td>
        <td>
          <div style="display:flex;align-items:center;gap:8px">
            <div style="flex:1;background:var(--border);border-radius:4px;height:6px">
              <div style="width:${pct}%;background:${barColor};border-radius:4px;height:6px"></div>
            </div>
            <span style="font-size:12px;white-space:nowrap">${e.filled_workdays}/${e.total_workdays}</span>
          </div>
        </td>
        <td>
          <button class="btn btn-sm ${isClosed ? 'btn-secondary' : 'btn-primary'}"
            onclick="PageTimesheet.openEmployeeDays(${e.employee_id},'${_esc(e.name)}')">
            ${isClosed ? 'Ver' : 'Lançar'}
          </button>
        </td>
      </tr>`;
    }).join('');

    el.innerHTML = `
      <div class="table-wrapper">
        <table>
          <thead><tr><th>Funcionário</th><th>Admissão</th><th>Período</th><th>Saldo Banco</th><th>Preenchimento</th><th></th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>`;
  }

  function _updateHeaderActions() {
    const el = document.getElementById('ts-header-actions');
    if (!el) return;
    if (!periodData || periodData.status === 'not_opened') { el.innerHTML = ''; return; }
    if (periodData.status === 'open') {
      el.innerHTML = `<button class="btn btn-primary" onclick="PageTimesheet.confirmClosePeriod()">Fechar Ponto</button>`;
    } else {
      el.innerHTML = `<span class="badge badge-success" style="font-size:13px;padding:8px 14px">Ponto Fechado</span>`;
    }
  }

  async function openPeriod() {
    try {
      periodData = await Api.openTimesheetPeriod({ competence_month: curMonth, competence_year: curYear });
      toast(`Período ${MONTHS[curMonth-1]}/${curYear} aberto!`);
      renderPeriodView();
    } catch (e) { toast(e.message, 'error'); }
  }

  function confirmClosePeriod() {
    openModal(`Fechar Ponto — ${MONTHS[curMonth-1]}/${curYear}`,
      `<p>Confirma o fechamento do ponto de <strong>${MONTHS[curMonth-1]}/${curYear}</strong>?</p>
       <p style="margin-top:8px;color:var(--text-muted);font-size:13px">Após fechar, os registros ficam bloqueados para edição em lote.</p>`,
      `<button class="btn btn-secondary" onclick="closeModal()">Cancelar</button>
       <button class="btn btn-primary" onclick="PageTimesheet.doClosePeriod()">Confirmar</button>`);
  }

  async function doClosePeriod() {
    try {
      await Api.closeTimesheetPeriod(curMonth, curYear);
      closeModal();
      toast('Ponto fechado com sucesso!');
      await fetchAndRenderPeriod();
    } catch (e) { toast(e.message, 'error'); }
  }

  // ── Lançamento em Lote ──────────────────────────────────────────────────────

  let _batchEmployees = [];

  async function openBatchModal() {
    try {
      _batchEmployees = await Api.getEmployees() || [];
    } catch (e) { _batchEmployees = []; }

    const empRows = _batchEmployees.map(e =>
      `<label style="display:flex;align-items:center;gap:8px;padding:4px 0;cursor:pointer">
        <input type="checkbox" class="batch-emp-chk" value="${e.id}" checked>
        <span>${_esc(e.name)}</span>
      </label>`
    ).join('');

    openModal('Lançamento em Lote',
      `<div style="display:flex;flex-direction:column;gap:16px">
        <div class="form-group" style="margin:0">
          <label>Tipo</label>
          <select class="form-control" id="batch-type" onchange="PageTimesheet._onBatchTypeChange()">
            <option value="feriado">Feriado</option>
            <option value="recesso">Recesso</option>
            <option value="compensar">Compensar</option>
          </select>
        </div>

        <!-- Feriado / Compensar: dia único -->
        <div id="batch-single-date">
          <div class="form-group" style="margin:0">
            <label>Data</label>
            <input class="form-control" type="date" id="batch-date">
          </div>
        </div>

        <!-- Recesso: intervalo -->
        <div id="batch-range-date" style="display:none">
          <div style="display:flex;gap:12px">
            <div class="form-group" style="flex:1;margin:0">
              <label>Data Início</label>
              <input class="form-control" type="date" id="batch-start">
            </div>
            <div class="form-group" style="flex:1;margin:0">
              <label>Data Fim</label>
              <input class="form-control" type="date" id="batch-end">
            </div>
          </div>
          <p style="font-size:12px;color:var(--text-muted);margin-top:6px">
            Fins de semana dentro do recesso serão descontados automaticamente quando a semana estiver completa (Seg–Sex).
          </p>
        </div>

        <!-- Funcionários -->
        <div class="form-group" style="margin:0">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
            <label style="margin:0">Funcionários</label>
            <div style="display:flex;gap:8px">
              <button class="btn btn-sm btn-secondary" onclick="PageTimesheet._batchSelectAll(true)">Selecionar Todos</button>
              <button class="btn btn-sm btn-secondary" onclick="PageTimesheet._batchSelectAll(false)">Desmarcar Todos</button>
            </div>
          </div>
          <div style="max-height:200px;overflow-y:auto;border:1px solid var(--border);border-radius:6px;padding:8px 12px">
            ${empRows || '<span style="color:var(--text-muted)">Nenhum funcionário encontrado.</span>'}
          </div>
        </div>
      </div>`,
      `<button class="btn btn-secondary" onclick="closeModal()">Cancelar</button>
       <button class="btn btn-primary" onclick="PageTimesheet.doBatchLaunch()">Lançar</button>`
    );
  }

  function _onBatchTypeChange() {
    const type = document.getElementById('batch-type')?.value;
    document.getElementById('batch-single-date').style.display = type === 'recesso' ? 'none' : '';
    document.getElementById('batch-range-date').style.display  = type === 'recesso' ? ''     : 'none';
  }

  function _batchSelectAll(checked) {
    document.querySelectorAll('.batch-emp-chk').forEach(chk => { chk.checked = checked; });
  }

  async function doBatchLaunch() {
    const type = document.getElementById('batch-type')?.value;
    const empIds = [...document.querySelectorAll('.batch-emp-chk:checked')].map(c => parseInt(c.value));

    if (!empIds.length) { toast('Selecione ao menos um funcionário.', 'error'); return; }

    let body = { type, employee_ids: empIds };

    if (type === 'recesso') {
      const s = document.getElementById('batch-start')?.value;
      const e = document.getElementById('batch-end')?.value;
      if (!s || !e) { toast('Informe a data de início e fim do recesso.', 'error'); return; }
      if (e < s)    { toast('Data fim deve ser após a data início.', 'error'); return; }
      body.start_date = s;
      body.end_date   = e;
    } else {
      const d = document.getElementById('batch-date')?.value;
      if (!d) { toast('Informe a data.', 'error'); return; }
      body.launch_date = d;
    }

    try {
      const r = await Api.batchDayLaunch(body);
      closeModal();
      const typeLabel = { feriado: 'Feriado', recesso: 'Recesso', compensar: 'Compensar' }[type];
      toast(`${typeLabel} lançado para ${r.employees} funcionário(s) — ${r.created} entrada(s) criadas.`);
      await fetchAndRenderPeriod();
    } catch (e) { toast(e.message, 'error'); }
  }

  // ── View: dias de um funcionário ────────────────────────────────────────────

  async function openEmployeeDays(empId, empName) {
    selEmpId   = empId;
    selEmpName = empName;
    view = 'days';

    const content = document.getElementById('ts-content');
    if (!content) return;
    content.innerHTML = `
      <div style="display:flex;align-items:center;gap:16px;margin-bottom:16px;flex-wrap:wrap">
        <button class="btn btn-secondary" onclick="PageTimesheet.backToPeriod()">← Voltar</button>
        <strong style="font-size:16px">${_esc(empName)} — ${MONTHS[curMonth-1]}/${curYear}</strong>
        <div id="ts-save-status" style="color:var(--text-muted);font-size:13px"></div>
      </div>
      <div id="ts-days-content">${loadingRow(8)}</div>
      <div style="display:flex;gap:12px;margin-top:16px" id="ts-days-footer"></div>`;

    const hdr = document.getElementById('ts-header-actions');
    if (hdr) hdr.innerHTML = '';

    try {
      daysData = await Api.getEmployeeDays(empId, curMonth, curYear) || [];
      renderDaysGrid();
    } catch (e) {
      const el = document.getElementById('ts-days-content');
      if (el) el.innerHTML = `<div class="alert alert-error">${e.message}</div>`;
    }
  }

  function backToPeriod() { loadPeriod(); }

  // Mapeia situação de um DayRead para o valor do select
  function _dayToSit(d) {
    if (d.is_annulled)          return 'annulled';
    if (d.is_dsr_deducted && d.is_holiday) return 'feriado_descontado';
    if (d.is_dsr_deducted)      return 'dsr';
    if (d.is_recess)            return 'recesso';
    if (d.is_compensar)         return 'compensar';
    if (d.is_holiday)           return 'feriado';
    if (d.is_absence && !d.is_medical_certificate)   return 'falta';
    if (d.is_medical_certificate && !d.certificate_hours) return 'atestado_dia';
    if (d.is_medical_certificate && d.certificate_hours)  return 'atestado_horas';
    return 'normal';
  }

  function renderDaysGrid() {
    const el = document.getElementById('ts-days-content');
    if (!el) return;
    const isClosed = periodData?.status === 'closed';

    const rows = daysData.map((d, i) => {
      if (d.is_vacation) {
        return `<tr style="background:#f0f9ff" data-idx="${i}" data-vacation="1">
          <td style="white-space:nowrap">
            <strong>${fmt.date(d.work_date)}</strong>
            <span style="color:var(--text-muted);font-size:11px;margin-left:4px">${d.weekday_name}</span>
          </td>
          <td colspan="4" style="color:#0369a1;font-size:12px;font-style:italic;text-align:center">— Férias —</td>
          <td colspan="2"><span style="display:inline-block;padding:2px 10px;border-radius:12px;font-size:11px;font-weight:600;color:#0369a1;background:#bae6fd">Férias</span></td>
          <td style="color:var(--text-muted);font-size:12px">—</td>
        </tr>`;
      }

      const sit      = _dayToSit(d);
      const isAuto   = d.is_dsr_deducted || (d.is_recess && d.is_weekend);
      const disabled = (isClosed || isAuto) ? 'disabled' : '';
      const rowBg    = d.is_weekend ? 'background:var(--bg)' :
                       d.is_recess  ? 'background:#fef9c3' :
                       d.is_compensar ? 'background:#fce7f3' :
                       d.is_dsr_deducted ? 'background:#fee2e2' : '';
      const certHours = d.certificate_hours || '';

      // Badge automático para dias gerados pela regra DSR
      const autoBadge = isAuto
        ? `<span style="font-size:10px;padding:1px 6px;border-radius:8px;background:#fee2e2;color:#991b1b;margin-left:4px">auto</span>`
        : '';

      return `<tr style="${rowBg}" data-idx="${i}">
        <td style="white-space:nowrap">
          <strong>${fmt.date(d.work_date)}</strong>
          <span style="color:var(--text-muted);font-size:11px;margin-left:4px">${d.weekday_name}</span>
          ${d.is_weekend ? '<span class="badge badge-gray" style="font-size:10px">FDS</span>' : ''}
          ${autoBadge}
        </td>
        <td><input class="form-control ts-time" type="time" data-field="entry_time" value="${d.entry_time||''}" ${disabled} style="width:90px;padding:4px 6px"></td>
        <td><input class="form-control ts-time" type="time" data-field="lunch_out_time" value="${d.lunch_out_time||''}" ${disabled} style="width:90px;padding:4px 6px"></td>
        <td><input class="form-control ts-time" type="time" data-field="lunch_in_time" value="${d.lunch_in_time||''}" ${disabled} style="width:90px;padding:4px 6px"></td>
        <td><input class="form-control ts-time" type="time" data-field="exit_time" value="${d.exit_time||''}" ${disabled} style="width:90px;padding:4px 6px"></td>
        <td>
          <select class="form-control ts-sit" data-idx="${i}" onchange="PageTimesheet._onSitChange(${i})" ${disabled} style="width:170px;padding:4px 6px">
            <option value="normal"              ${sit==='normal'?'selected':''}>Normal</option>
            <option value="feriado"             ${sit==='feriado'?'selected':''}>Feriado</option>
            <option value="falta"               ${sit==='falta'?'selected':''}>Falta</option>
            <option value="atestado_dia"        ${sit==='atestado_dia'?'selected':''}>Atestado (dia)</option>
            <option value="atestado_horas"      ${sit==='atestado_horas'?'selected':''}>Atestado (horas)</option>
            <option value="recesso"             ${sit==='recesso'?'selected':''}>Recesso</option>
            <option value="compensar"           ${sit==='compensar'?'selected':''}>Compensar</option>
            ${sit==='dsr'              ? '<option value="dsr" selected>DSR Descontado</option>' : ''}
            ${sit==='feriado_descontado' ? '<option value="feriado_descontado" selected>Feriado Descontado</option>' : ''}
            ${sit==='annulled'         ? '<option value="annulled" selected>Anulado</option>' : ''}
          </select>
        </td>
        <td id="cert-col-${i}">
          ${sit==='atestado_horas'
            ? `<input class="form-control ts-cert-h" type="number" min="0.5" max="12" step="0.5" value="${certHours}" placeholder="h" ${disabled} style="width:60px;padding:4px 6px">`
            : ''}
        </td>
        <td style="font-size:12px;color:var(--text-muted)">
          ${_sitLabel(sit, d)}
        </td>
      </tr>`;
    }).join('');

    el.innerHTML = `
      <div class="table-wrapper" style="max-height:calc(100vh - 280px);overflow-y:auto">
        <table>
          <thead><tr>
            <th>Data</th><th>Entrada</th><th>S.Almoço</th><th>R.Almoço</th><th>Saída</th>
            <th>Situação</th><th>Cert.h</th><th>Info</th>
          </tr></thead>
          <tbody id="ts-days-tbody">${rows}</tbody>
        </table>
      </div>`;

    const footer = document.getElementById('ts-days-footer');
    if (footer) {
      const recalcBtn = `<button class="btn btn-secondary" onclick="PageTimesheet.recalcBank()" title="Recalcula banco de horas do zero">↻ Recalcular Banco</button>`;
      footer.innerHTML = isClosed
        ? `<span style="color:var(--text-muted)">Período fechado — somente leitura.</span>${recalcBtn}`
        : `<button class="btn btn-primary" onclick="PageTimesheet.saveAll()">Salvar Tudo</button>
           <button class="btn btn-secondary" onclick="PageTimesheet.backToPeriod()">Cancelar</button>
           ${recalcBtn}`;
    }
  }

  function _sitLabel(sit, d) {
    if (sit === 'normal' && d.worked_minutes > 0) {
      return fmt.mins(d.worked_minutes) +
             (d.overtime_minutes > 0 ? ` <span style="color:var(--success)">+${fmt.mins(d.overtime_minutes)}</span>` : '');
    }
    const labels = {
      feriado:             '<span style="color:#0369a1">Feriado pago</span>',
      falta:               '<span style="color:var(--danger)">Falta</span>',
      atestado_dia:        '<span style="color:var(--warning)">Atestado</span>',
      atestado_horas:      '<span style="color:var(--warning)">Atestado parcial</span>',
      recesso:             '<span style="color:#854d0e">Recesso</span>',
      compensar:           '<span style="color:#7c3aed">Compensar</span>',
      dsr:                 '<span style="color:var(--danger)">DSR descontado</span>',
      feriado_descontado:  '<span style="color:var(--danger)">Feriado descontado</span>',
      annulled:            '<span style="color:var(--text-muted)">Anulado</span>',
    };
    return labels[sit] || '—';
  }

  function _onSitChange(idx) {
    const sit    = document.querySelector(`.ts-sit[data-idx="${idx}"]`)?.value;
    const certCol = document.getElementById(`cert-col-${idx}`);
    if (certCol) {
      certCol.innerHTML = sit === 'atestado_horas'
        ? `<input class="form-control ts-cert-h" type="number" min="0.5" max="12" step="0.5" placeholder="h" style="width:60px;padding:4px 6px">`
        : '';
    }
    const row = document.querySelector(`tr[data-idx="${idx}"]`);
    if (!row) return;
    const times       = row.querySelectorAll('.ts-time');
    const disableTimes = ['falta','atestado_dia','feriado','recesso','compensar','dsr','feriado_descontado'].includes(sit);
    times.forEach(inp => {
      inp.disabled = disableTimes;
      if (disableTimes) inp.value = '';
    });
  }

  async function saveAll() {
    const tbody = document.getElementById('ts-days-tbody');
    if (!tbody) return;

    const entries = [];
    tbody.querySelectorAll('tr[data-idx]').forEach(row => {
      if (row.dataset.vacation) return;
      const idx = parseInt(row.dataset.idx);
      const day = daysData[idx];
      if (!day) return;

      // Dias auto-gerados (DSR) não são enviados manualmente
      if (day.is_dsr_deducted) return;

      const timeVal = f => row.querySelector(`[data-field="${f}"]`)?.value || null;
      const sit     = row.querySelector('.ts-sit')?.value || 'normal';
      const certHEl = row.querySelector('.ts-cert-h');
      const certH   = certHEl ? parseFloat(certHEl.value) || null : null;

      const noTimes = ['feriado','falta','atestado_dia','recesso','compensar'].includes(sit);
      entries.push({
        work_date:              day.work_date,
        entry_time:             noTimes ? null : timeVal('entry_time'),
        lunch_out_time:         noTimes ? null : timeVal('lunch_out_time'),
        lunch_in_time:          noTimes ? null : timeVal('lunch_in_time'),
        exit_time:              noTimes ? null : timeVal('exit_time'),
        is_absence:             sit === 'falta',
        is_medical_certificate: sit === 'atestado_dia' || sit === 'atestado_horas',
        certificate_hours:      sit === 'atestado_horas' ? certH : null,
        is_holiday:             sit === 'feriado',
        is_recess:              sit === 'recesso',
        is_compensar:           sit === 'compensar',
        justification:          null,
      });
    });

    const status = document.getElementById('ts-save-status');
    if (status) status.textContent = 'Salvando...';
    try {
      const r = await Api.saveEmployeeDays(selEmpId, curMonth, curYear, { entries });
      toast(`${r.saved} registro(s) salvos!`);
      if (status) status.textContent = '';
      daysData = await Api.getEmployeeDays(selEmpId, curMonth, curYear) || [];
      renderDaysGrid();
      await fetchAndRenderPeriod();
      openEmployeeDays(selEmpId, selEmpName);
    } catch (e) {
      if (status) status.textContent = '';
      toast(e.message, 'error');
    }
  }

  async function recalcBank() {
    if (!selEmpId) return;
    try {
      const r = await Api.recalculateHourBank(selEmpId);
      toast(`Banco de horas recalculado: ${r.balance_hours}`);
    } catch (e) { toast(e.message, 'error'); }
  }

  // ── Helpers ─────────────────────────────────────────────────────────────────

  function _getPeriodSel() {
    const sel = document.getElementById('ts-period-sel');
    if (!sel) return [curMonth, curYear];
    return sel.value.split('|').map(Number);
  }

  function _fmtMins(min) {
    if (min === 0) return '0';
    const sign = min > 0 ? '+' : '-';
    const abs  = Math.abs(min);
    return sign + Math.floor(abs / 60) + 'h' + String(abs % 60).padStart(2, '0');
  }

  function _esc(v) {
    if (!v) return '';
    return String(v).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }

  return {
    render, onPeriodChange, openPeriod, confirmClosePeriod, doClosePeriod,
    openBatchModal, _onBatchTypeChange, _batchSelectAll, doBatchLaunch,
    openEmployeeDays, backToPeriod, _onSitChange, saveAll, recalcBank,
  };
})();
