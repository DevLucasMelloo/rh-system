const PageVacation = (() => {
  // ── Render ────────────────────────────────────────────────────────────────
  async function render(container) {
    const empOpts = await employeeSelectOptions();
    container.innerHTML = `
      <div class="page-header">
        <div><h1>Férias</h1><p>Agendamento, cálculo e gestão de períodos de férias</p></div>
        <button class="btn btn-primary" onclick="PageVacation.openNew()">+ Agendar Férias</button>
      </div>

      <div id="vac-alert-bar" style="margin-bottom:16px"></div>

      <div class="card" style="margin-bottom:24px">
        <div class="card-header">Situação de Férias</div>
        <div class="table-wrapper" style="margin:0">
          <table>
            <thead><tr>
              <th>Funcionário</th>
              <th>Registro</th>
              <th>Vencimento</th>
              <th>Status</th>
              <th>Período Agendado</th>
              <th></th>
            </tr></thead>
            <tbody id="vac-overview-tbody">
              <tr><td colspan="6" style="text-align:center;padding:40px;color:var(--text-muted)">Carregando...</td></tr>
            </tbody>
          </table>
        </div>
      </div>

      <div class="card">
        <div class="card-header">Consultar Férias por Funcionário</div>
        <div class="card-body">
          <div class="form-group">
            <select class="form-control" id="vac-emp-sel" onchange="PageVacation.loadEmployee()">
              <option value="">Selecione...</option>${empOpts}
            </select>
          </div>
          <div id="vac-emp-list"></div>
        </div>
      </div>`;

    loadOverview();
  }

  // ── Overview: todos os funcionários ───────────────────────────────────────
  async function loadOverview() {
    const tb   = document.getElementById('vac-overview-tbody');
    const alert = document.getElementById('vac-alert-bar');
    try {
      const list = await Api.getVacationOverview();

      const overdueCount = list.filter(e => e.vacation_status === 'vencida').length;
      if (overdueCount > 0) {
        alert.innerHTML = `
          <div class="alert alert-warning" style="display:flex;align-items:center;gap:8px">
            ⚠ <strong>${overdueCount} funcionário(s) com férias vencidas.</strong> Ação necessária.
          </div>`;
      } else {
        alert.innerHTML = '';
      }

      if (!list.length) {
        tb.innerHTML = '<tr><td colspan="6" style="text-align:center;padding:40px;color:var(--text-muted)">Nenhum funcionário ativo.</td></tr>';
        return;
      }

      tb.innerHTML = list.map(e => {
        const statusBadge = _overviewStatusBadge(e.vacation_status);

        let periodoHtml = '—';
        if (e.vacation_status === 'agendada' || e.vacation_status === 'em_gozo') {
          if (e.sell_all_days) {
            periodoHtml = '<span style="color:var(--text-muted);font-size:12px">Venda total</span>';
          } else if (e.scheduled_start) {
            const start = fmt.date(e.scheduled_start);
            const end   = e.scheduled_end ? fmt.date(e.scheduled_end) : '?';
            periodoHtml = `<span style="font-size:12px">${start} a ${end}</span>`;
          }
        }

        const vencimento = e.vencimento ? fmt.date(e.vencimento) : '—';

        return `<tr>
          <td><strong>${e.employee_name}</strong></td>
          <td style="font-size:12px;color:var(--text-muted)">${fmt.date(e.registration_date)}</td>
          <td style="font-size:12px${e.vacation_status==='vencida'?';color:var(--danger);font-weight:600':''}">${vencimento}</td>
          <td>${statusBadge}</td>
          <td>${periodoHtml}</td>
          <td style="text-align:right">
            <button class="btn btn-secondary btn-sm" style="white-space:nowrap"
              onclick="PageVacation.openNew(${e.employee_id})">
              📅 Programar
            </button>
          </td>
        </tr>`;
      }).join('');
    } catch (err) {
      tb.innerHTML = `<tr><td colspan="6" style="text-align:center;padding:20px;color:var(--danger)">${err.message}</td></tr>`;
    }
  }

  function _overviewStatusBadge(status) {
    const map = {
      vencida:   ['#dc2626', '#fee2e2', 'Vencida'],
      agendada:  ['#2563eb', '#dbeafe', 'Agendada'],
      disponivel:['#d97706', '#fef3c7', 'Disponível'],
      regular:   ['#16a34a', '#dcfce7', 'Regular'],
      inelegivel:['#6b7280', '#f3f4f6', 'Inelegível'],
      concluida: ['#16a34a', '#dcfce7', 'Concluída'],
      em_gozo:   ['#0891b2', '#e0f2fe', 'Em Gozo'],
    };
    const [color, bg, label] = map[status] || ['#6b7280', '#f3f4f6', status];
    return `<span style="display:inline-block;padding:2px 10px;border-radius:12px;font-size:11px;font-weight:600;color:${color};background:${bg}">${label}</span>`;
  }

  // ── Lista por funcionário (card secundário) ───────────────────────────────
  async function loadEmployee() {
    const id = parseInt(document.getElementById('vac-emp-sel').value) || null;
    const el = document.getElementById('vac-emp-list');
    if (!id) { el.innerHTML = ''; return; }
    el.innerHTML = `<div style="text-align:center;padding:20px;color:var(--text-muted)">Carregando...</div>`;
    try {
      const vacs = await Api.getEmpVacations(id);
      if (!vacs || !vacs.length) {
        el.innerHTML = `<div style="color:var(--text-muted);font-size:13px;padding-top:8px">Nenhuma férias cadastrada.</div>`;
        return;
      }
      el.innerHTML = vacs.map(v => {
        const abonoDays = v.abono_days || 0;
        let label;
        if (v.sell_all_days) label = 'Venda total';
        else if (abonoDays > 0) label = `${v.enjoyment_days}d gozo + ${abonoDays}d abono`;
        else label = `${v.enjoyment_days} dias`;
        return `<div style="display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid var(--border);font-size:13px;cursor:pointer"
          onclick="PageVacation.openDetail(${v.id})">
          <div>
            <div style="font-weight:600">${fmt.date(v.acquisition_start)} – ${fmt.date(v.acquisition_end)}</div>
            <div style="font-size:11px;color:var(--text-muted)">${label} · ${v.net_vacation_pay ? fmt.brl(v.net_vacation_pay) : '—'}</div>
          </div>
          ${_overviewStatusBadge(v.status)}
        </div>`;
      }).join('');
    } catch (e) {
      el.innerHTML = `<div class="alert alert-error">${e.message}</div>`;
    }
  }

  // ── Novo agendamento ──────────────────────────────────────────────────────
  let _newEligibility = null;

  async function openNew(preEmpId = null) {
    const empOpts = await employeeSelectOptions();
    openModal('Agendar Férias', `
      <div class="form-group">
        <label>Funcionário *</label>
        <select class="form-control" id="nv-emp" onchange="PageVacation._onNewEmpChange()">
          <option value="">Selecione...</option>${empOpts}
        </select>
      </div>

      <div id="nv-eligibility" style="margin-bottom:12px"></div>

      <div id="nv-form-body" style="display:none">
        <div class="form-group">
          <label>Período de Férias *</label>
          <select class="form-control" id="nv-period" onchange="PageVacation._onPeriodChange()">
            <option value="">Selecione o período...</option>
          </select>
        </div>
        <div id="nv-period-info" style="font-size:12px;color:var(--text-muted);margin:-8px 0 12px 0"></div>

        <div class="form-group" style="margin-bottom:8px">
          <label style="display:flex;align-items:center;gap:8px;cursor:pointer">
            <input type="checkbox" id="nv-sell-all" onchange="PageVacation._onSellAllChange()">
            <span>Vender todas as férias (recebe os 30 dias em dinheiro, sem gozo)</span>
          </label>
        </div>
        <div id="nv-gozo-fields">
          <div class="form-row">
            <div class="form-group">
              <label>Início do Gozo</label>
              <input class="form-control" type="date" id="nv-enjoy-start">
            </div>
            <div class="form-group">
              <label>Dias de Gozo</label>
              <input class="form-control" type="number" id="nv-days" value="30" min="5" max="30"
                onchange="PageVacation._onNewDaysChange()">
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>Abono Pecuniário (dias vendidos)</label>
              <input class="form-control" type="number" id="nv-abono" value="0" min="0" max="10"
                onchange="PageVacation._onNewDaysChange()" placeholder="0">
            </div>
            <div class="form-group" style="display:flex;align-items:flex-end;padding-bottom:4px">
              <small style="color:var(--text-muted);font-size:11px">
                Dias convertidos em dinheiro além do gozo.<br>
                Total pago = Gozo + Abono (máx. 30 dias).
              </small>
            </div>
          </div>
        </div>

        <div id="nv-calc" style="display:none;background:var(--bg);border-radius:8px;padding:14px;margin-top:8px">
          <div style="font-weight:600;margin-bottom:6px;color:var(--text-muted);font-size:12px;text-transform:uppercase;letter-spacing:.5px">
            Cálculo (editável)
          </div>
          <div id="nv-total-paid-info" style="font-size:12px;color:var(--primary);margin-bottom:10px"></div>
          <div class="form-row">
            <div class="form-group">
              <label>Base Férias (R$)</label>
              <input class="form-control" type="number" step="0.01" id="nv-base" oninput="PageVacation._onNewCalcChange()">
            </div>
            <div class="form-group">
              <label>1/3 Constitucional (R$)</label>
              <input class="form-control" type="number" step="0.01" id="nv-third" oninput="PageVacation._onNewCalcChange()">
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>INSS (R$)</label>
              <input class="form-control" type="number" step="0.01" id="nv-inss" oninput="PageVacation._onNewCalcChange()">
            </div>
            <div class="form-group">
              <label>Líquido Estimado</label>
              <input class="form-control" type="text" id="nv-net" readonly
                style="font-weight:700;color:var(--success)">
            </div>
          </div>
        </div>

        <div class="form-group">
          <label>Observações</label>
          <input class="form-control" type="text" id="nv-notes" placeholder="Opcional">
        </div>
      </div>
      <div id="nv-error"></div>`, `
      <button class="btn btn-secondary" onclick="closeModal()">Cancelar</button>
      <button class="btn btn-primary" onclick="PageVacation.saveNew()">Agendar</button>`);

    // Pre-fill employee if provided
    if (preEmpId) {
      const sel = document.getElementById('nv-emp');
      if (sel) {
        sel.value = String(preEmpId);
        await _onNewEmpChange();
      }
    }
  }

  async function _onNewEmpChange() {
    const id    = parseInt(document.getElementById('nv-emp').value);
    const elInfo = document.getElementById('nv-eligibility');
    const elForm = document.getElementById('nv-form-body');
    const elPer  = document.getElementById('nv-period');
    if (!id) { elInfo.innerHTML = ''; elForm.style.display = 'none'; return; }

    try {
      const e = _newEligibility = await Api.getVacationEligibility(id);

      if (!e.is_eligible) {
        let msg = e.months_registered < 12
          ? `✗ Não elegível — ${e.months_registered} mês(es) de registro (mínimo 12)`
          : '✗ Funcionário não possui períodos disponíveis para agendamento.';
        elInfo.innerHTML = `<div class="alert alert-error" style="margin-bottom:8px">${msg}</div>`;
        elForm.style.display = 'none';
        return;
      }

      elPer.innerHTML = '<option value="">Selecione o período...</option>' +
        e.available_periods.map(p => {
          const tag = p.is_overdue ? ' ⚠ VENCIDO' : '';
          return `<option value="${p.period_number}"
            data-start="${p.acq_start}" data-end="${p.acq_end}" data-overdue="${p.is_overdue}">
            ${p.period_number}º Período — ${fmt.date(p.acq_start)} a ${fmt.date(p.acq_end)}${tag}
          </option>`;
        }).join('');

      const ovMsg = e.overdue_periods > 0
        ? `<div class="alert alert-error" style="margin-bottom:6px">⚠ ${e.overdue_periods} período(s) vencido(s) — prazo concessivo expirado.</div>`
        : '';
      elInfo.innerHTML = ovMsg +
        `<div style="font-size:12px;color:var(--success);padding:2px 0">
          ✓ ${e.months_registered} meses de registro — ${e.unclaimed_periods} período(s) disponível(is)
        </div>`;
      elForm.style.display = '';

      // Auto-select single available period
      if (e.available_periods.length === 1) {
        elPer.selectedIndex = 1;
        await _onPeriodChange();
      }
    } catch (err) {
      elInfo.innerHTML = `<div class="alert alert-error">${err.message}</div>`;
      elForm.style.display = 'none';
    }
  }

  async function _onPeriodChange() {
    const sel   = document.getElementById('nv-period');
    const opt   = sel.options[sel.selectedIndex];
    const infoEl = document.getElementById('nv-period-info');
    if (!opt.value) { infoEl.textContent = ''; return; }

    const isOverdue = opt.dataset.overdue === 'true';
    infoEl.innerHTML = isOverdue
      ? `<span style="color:var(--danger)">⚠ Período vencido — agende imediatamente para regularizar.</span>`
      : `<span style="color:var(--text-muted)">Período aquisitivo: ${fmt.date(opt.dataset.start)} → ${fmt.date(opt.dataset.end)}</span>`;

    const id = parseInt(document.getElementById('nv-emp').value);
    const abono = parseInt(document.getElementById('nv-abono')?.value) || 0;
    if (id) await _loadNewPreview(id, 30, document.getElementById('nv-sell-all').checked, abono);
  }

  async function _onSellAllChange() {
    const sellAll = document.getElementById('nv-sell-all').checked;
    document.getElementById('nv-gozo-fields').style.display = sellAll ? 'none' : '';
    const id = parseInt(document.getElementById('nv-emp').value);
    if (id) await _loadNewPreview(id, 30, sellAll, 0);
  }

  async function _onNewDaysChange() {
    const id      = parseInt(document.getElementById('nv-emp').value);
    const days    = parseInt(document.getElementById('nv-days').value) || 30;
    const abono   = parseInt(document.getElementById('nv-abono')?.value) || 0;
    const sellAll = document.getElementById('nv-sell-all').checked;
    if (id) await _loadNewPreview(id, days, sellAll, abono);
  }

  async function _loadNewPreview(empId, days, sellAll, abono = 0) {
    try {
      const p = await Api.previewVacation({ employee_id: empId, enjoyment_days: days, sell_all_days: sellAll, abono_days: abono });
      document.getElementById('nv-calc').style.display = '';
      document.getElementById('nv-base').value  = parseFloat(p.base_salary).toFixed(2);
      document.getElementById('nv-third').value = parseFloat(p.one_third_bonus).toFixed(2);
      document.getElementById('nv-inss').value  = parseFloat(p.inss_discount).toFixed(2);
      const totalEl = document.getElementById('nv-total-paid-info');
      if (totalEl) {
        const total = p.total_paid_days || (days + abono);
        totalEl.textContent = sellAll ? 'Venda total: 30 dias pagos' : `Gozo: ${days} dias + Abono: ${abono} dias = ${total} dias pagos`;
      }
      _updateNewNet();
    } catch {}
  }

  function _onNewCalcChange() { _updateNewNet(); }

  function _updateNewNet() {
    const base  = parseFloat(document.getElementById('nv-base')?.value  || 0);
    const third = parseFloat(document.getElementById('nv-third')?.value || 0);
    const inss  = parseFloat(document.getElementById('nv-inss')?.value  || 0);
    const el    = document.getElementById('nv-net');
    if (el) el.value = fmt.brl(base + third - inss);
  }

  async function saveNew() {
    const sellAll = document.getElementById('nv-sell-all').checked;
    const days    = sellAll ? 0 : (parseInt(document.getElementById('nv-days').value) || 30);
    const abono   = sellAll ? 0 : (parseInt(document.getElementById('nv-abono')?.value) || 0);

    const sel = document.getElementById('nv-period');
    const opt = sel ? sel.options[sel.selectedIndex] : null;
    if (!opt || !opt.value) {
      document.getElementById('nv-error').innerHTML = '<div class="alert alert-error">Selecione o período de férias.</div>';
      return;
    }

    const calcVisible = document.getElementById('nv-calc').style.display !== 'none';
    const data = {
      employee_id:       parseInt(document.getElementById('nv-emp').value),
      acquisition_start: opt.dataset.start,
      acquisition_end:   opt.dataset.end,
      enjoyment_start:   !sellAll ? (document.getElementById('nv-enjoy-start').value || null) : null,
      enjoyment_days:    days,
      sell_all_days:     sellAll,
      abono_days:        abono,
      notes:             document.getElementById('nv-notes')?.value || null,
    };
    if (calcVisible) {
      data.base_salary     = parseFloat(document.getElementById('nv-base').value)  || null;
      data.one_third_bonus = parseFloat(document.getElementById('nv-third').value) || null;
      data.inss_discount   = parseFloat(document.getElementById('nv-inss').value)  || null;
    }
    try {
      await Api.createVacation(data);
      closeModal();
      toast('Férias agendadas!');
      loadOverview();
    } catch (e) {
      document.getElementById('nv-error').innerHTML = `<div class="alert alert-error">${e.message}</div>`;
    }
  }

  // ── Detalhe / Recibo ──────────────────────────────────────────────────────
  async function openDetail(id) {
    try {
      const v = await Api.getVacation(id);
      _renderDetail(v);
    } catch (e) { toast(e.message, 'error'); }
  }

  function _renderDetail(v) {
    const isScheduled = v.status === 'agendada';
    const isActive    = v.status === 'em_gozo';
    const canEdit     = isScheduled;

    const base  = parseFloat(v.base_salary  || 0);
    const third = parseFloat(v.one_third_bonus || 0);
    const inss  = parseFloat(v.inss_discount || 0);
    const gross = base + third;

    const itemsHtml = (v.items || []).map(it => {
      const isCredit = it.item_type === 'credito';
      return `<div style="display:flex;justify-content:space-between;align-items:center;padding:6px 0;border-bottom:1px solid var(--border)">
        <span style="color:${isCredit?'var(--success)':'var(--danger)'}">
          ${isCredit?'+ ':'– '}${it.description}
        </span>
        <span style="display:flex;align-items:center;gap:8px">
          <strong style="color:${isCredit?'var(--success)':'var(--danger)'}">${fmt.brl(it.value)}</strong>
          ${canEdit ? `<button class="btn-icon" title="Remover" onclick="PageVacation.removeItem(${v.id},${it.id})">✕</button>` : ''}
        </span>
      </div>`;
    }).join('');

    const extraItems = (v.items || []).reduce((acc, it) =>
      acc + (it.item_type === 'credito' ? parseFloat(it.value) : -parseFloat(it.value)), 0);
    const net  = base + third - inss + extraItems;
    const abonoDays = v.abono_days || 0;
    let gozo;
    if (v.sell_all_days) {
      gozo = 'Venda total (sem gozo)';
    } else if (abonoDays > 0) {
      gozo = `${v.enjoyment_days} dias gozo + ${abonoDays} dias abono`;
    } else {
      gozo = v.enjoyment_days + ' dias';
    }

    openModal(`Férias — ${v.employee_name}`, `
      <div style="font-size:13px;color:var(--text-muted);margin-bottom:16px">
        <span>${_overviewStatusBadge(v.status)}</span>
        &nbsp;|&nbsp;
        <span>Aquisitivo: ${fmt.date(v.acquisition_start)} – ${fmt.date(v.acquisition_end)}</span>
        ${v.enjoyment_start ? `&nbsp;|&nbsp;<span>Gozo: ${fmt.date(v.enjoyment_start)}</span>` : ''}
        &nbsp;|&nbsp;<span>${gozo}</span>
      </div>

      <div style="background:var(--bg);border-radius:8px;padding:16px;margin-bottom:16px">
        <div style="font-weight:600;margin-bottom:10px;color:var(--text-muted);font-size:11px;text-transform:uppercase;letter-spacing:.5px">
          Cálculo das Férias
        </div>
        ${_calcRow('Base de Férias', base, false, canEdit, `vd-base-${v.id}`)}
        ${_calcRow('1/3 Constitucional', third, false, canEdit, `vd-third-${v.id}`)}
        <div style="border-top:1px solid var(--border);margin:6px 0"></div>
        ${_calcRow('Bruto', gross, false, false, null)}
        ${_calcRow('INSS', inss, true, canEdit, `vd-inss-${v.id}`)}
        <div style="border-top:2px solid var(--border);margin:8px 0"></div>
        ${(v.items||[]).length > 0 ? itemsHtml : ''}
        <div style="display:flex;justify-content:space-between;padding:8px 0">
          <span style="font-weight:700;font-size:15px">Líquido</span>
          <strong style="font-size:18px;color:var(--success)" id="vd-net-${v.id}">${fmt.brl(net)}</strong>
        </div>
      </div>

      ${canEdit ? `
      <div style="margin-bottom:16px">
        <div style="font-weight:600;font-size:12px;color:var(--text-muted);margin-bottom:8px;text-transform:uppercase;letter-spacing:.5px">
          Adicionar Item
        </div>
        <div class="form-row" style="margin-bottom:0">
          <div class="form-group" style="flex:0 0 110px">
            <select class="form-control" id="vd-itype-${v.id}">
              <option value="credito">+ Crédito</option>
              <option value="debito">– Débito</option>
            </select>
          </div>
          <div class="form-group">
            <input class="form-control" type="text" id="vd-idesc-${v.id}" placeholder="Descrição">
          </div>
          <div class="form-group" style="flex:0 0 120px">
            <input class="form-control" type="number" step="0.01" id="vd-ival-${v.id}" placeholder="R$ 0,00">
          </div>
          <div class="form-group" style="flex:0 0 80px">
            <button class="btn btn-secondary w-full" onclick="PageVacation.addItem(${v.id})">+ Add</button>
          </div>
        </div>
      </div>` : ''}

      <div class="form-group">
        <label>Observações</label>
        <input class="form-control" type="text" id="vd-notes-${v.id}" value="${v.notes || ''}"
          ${canEdit ? `onblur="PageVacation._saveNotes(${v.id})"` : 'readonly'} placeholder="—">
      </div>
      <div id="vd-err-${v.id}"></div>`,

      `${canEdit ? `
        <button class="btn btn-secondary" onclick="PageVacation.openEdit(${v.id})">Editar Datas</button>
        <button class="btn btn-warning" onclick="PageVacation._saveCalc(${v.id})">Salvar Valores</button>
        <button class="btn btn-danger" onclick="PageVacation.deleteVac(${v.id})">Excluir</button>` : ''}
      ${isActive ? `<button class="btn btn-success" onclick="PageVacation.completeVac(${v.id})">✓ Dar Baixa</button>` : ''}
      ${isScheduled && v.sell_all_days ? `<button class="btn btn-success" onclick="PageVacation.completeVac(${v.id})">✓ Dar Baixa</button>` : ''}
      ${isScheduled && !v.sell_all_days ? `<button class="btn btn-primary" onclick="PageVacation.startVac(${v.id})">Iniciar Gozo</button>` : ''}
      <button class="btn btn-secondary" onclick="PageVacation.printVac(${JSON.stringify(v).replace(/"/g,'&quot;')})">🖨 Imprimir</button>
      <button class="btn btn-secondary" onclick="closeModal()">Fechar</button>`
    );

    if (canEdit) {
      [`vd-base-${v.id}`, `vd-third-${v.id}`, `vd-inss-${v.id}`].forEach(fid => {
        const el = document.getElementById(fid);
        if (el) el.addEventListener('input', () => _recalcDetailNet(v.id, (v.items||[])));
      });
    }
  }

  function _calcRow(label, value, isDeduct, editable, fieldId) {
    const color  = isDeduct ? 'var(--danger)' : '';
    const prefix = isDeduct ? '– ' : '';
    if (editable && fieldId) {
      return `<div style="display:flex;justify-content:space-between;align-items:center;padding:4px 0">
        <span style="color:${color}">${prefix}${label}</span>
        <input type="number" step="0.01" id="${fieldId}" value="${value.toFixed(2)}"
          style="width:120px;text-align:right;border:1px solid var(--border);border-radius:4px;padding:2px 6px;font-size:13px;color:${color||'inherit'}">
      </div>`;
    }
    return `<div style="display:flex;justify-content:space-between;padding:4px 0">
      <span style="color:${color}">${prefix}${label}</span>
      <strong style="color:${color}">${fmt.brl(value)}</strong>
    </div>`;
  }

  function _recalcDetailNet(vacId, items) {
    const base  = parseFloat(document.getElementById(`vd-base-${vacId}`)?.value  || 0);
    const third = parseFloat(document.getElementById(`vd-third-${vacId}`)?.value || 0);
    const inss  = parseFloat(document.getElementById(`vd-inss-${vacId}`)?.value  || 0);
    const extra = (items||[]).reduce((a,i) => a + (i.item_type==='credito'?parseFloat(i.value):-parseFloat(i.value)), 0);
    const el = document.getElementById(`vd-net-${vacId}`);
    if (el) el.textContent = fmt.brl(base + third - inss + extra);
  }

  async function _saveCalc(vacId) {
    const base  = parseFloat(document.getElementById(`vd-base-${vacId}`)?.value);
    const third = parseFloat(document.getElementById(`vd-third-${vacId}`)?.value);
    const inss  = parseFloat(document.getElementById(`vd-inss-${vacId}`)?.value);
    try {
      const v = await Api.updateVacation(vacId, { base_salary: base, one_third_bonus: third, inss_discount: inss });
      toast('Valores salvos!');
      _renderDetail(v);
      loadEmployee();
    } catch (e) { toast(e.message, 'error'); }
  }

  async function _saveNotes(vacId) {
    const notes = document.getElementById(`vd-notes-${vacId}`)?.value || null;
    try { await Api.updateVacation(vacId, { notes }); } catch {}
  }

  // ── Itens de Férias ───────────────────────────────────────────────────────
  async function addItem(vacId) {
    const type = document.getElementById(`vd-itype-${vacId}`)?.value;
    const desc = document.getElementById(`vd-idesc-${vacId}`)?.value?.trim();
    const val  = parseFloat(document.getElementById(`vd-ival-${vacId}`)?.value);
    if (!desc || !val || val <= 0) { toast('Preencha descrição e valor.', 'error'); return; }
    try {
      const v = await Api.addVacationItem(vacId, { item_type: type, description: desc, value: val });
      toast('Item adicionado.');
      _renderDetail(v);
      loadEmployee();
    } catch (e) { toast(e.message, 'error'); }
  }

  async function removeItem(vacId, itemId) {
    try {
      const v = await Api.deleteVacationItem(vacId, itemId);
      toast('Item removido.', 'warning');
      _renderDetail(v);
      loadEmployee();
    } catch (e) { toast(e.message, 'error'); }
  }

  // ── Editar datas ──────────────────────────────────────────────────────────
  async function openEdit(id) {
    let v;
    try { v = await Api.getVacation(id); } catch (e) { toast(e.message, 'error'); return; }
    const sellAll = v.sell_all_days;
    openModal('Editar Férias', `
      <div class="form-row">
        <div class="form-group">
          <label>Início Aquisitivo</label>
          <input class="form-control" type="date" id="ed-acq-start" value="${v.acquisition_start}">
        </div>
        <div class="form-group">
          <label>Fim Aquisitivo</label>
          <input class="form-control" type="date" id="ed-acq-end" value="${v.acquisition_end}">
        </div>
      </div>
      <div class="form-group">
        <label style="display:flex;align-items:center;gap:8px;cursor:pointer">
          <input type="checkbox" id="ed-sell-all" ${sellAll?'checked':''} onchange="PageVacation._onEditSellAll()">
          <span>Vender todas as férias</span>
        </label>
      </div>
      <div id="ed-gozo-fields" style="${sellAll?'display:none':''}">
        <div class="form-row">
          <div class="form-group">
            <label>Início Gozo</label>
            <input class="form-control" type="date" id="ed-enjoy-start" value="${v.enjoyment_start||''}">
          </div>
          <div class="form-group">
            <label>Dias de Gozo</label>
            <input class="form-control" type="number" id="ed-days" value="${v.enjoyment_days||30}" min="5" max="30">
          </div>
        </div>
      </div>
      <div class="form-group">
        <label>Observações</label>
        <input class="form-control" type="text" id="ed-notes" value="${v.notes||''}">
      </div>
      <div id="ed-error"></div>`, `
      <button class="btn btn-secondary" onclick="closeModal()">Cancelar</button>
      <button class="btn btn-primary" onclick="PageVacation.saveEdit(${id})">Salvar</button>`);
  }

  function _onEditSellAll() {
    document.getElementById('ed-gozo-fields').style.display =
      document.getElementById('ed-sell-all').checked ? 'none' : '';
  }

  async function saveEdit(id) {
    const sellAll = document.getElementById('ed-sell-all').checked;
    const days    = sellAll ? 0 : (parseInt(document.getElementById('ed-days').value) || 30);
    const data    = {
      acquisition_start: document.getElementById('ed-acq-start').value || null,
      acquisition_end:   document.getElementById('ed-acq-end').value   || null,
      enjoyment_start:   !sellAll ? (document.getElementById('ed-enjoy-start').value || null) : null,
      enjoyment_days:    days,
      sell_all_days:     sellAll,
      notes:             document.getElementById('ed-notes').value || null,
    };
    try {
      await Api.updateVacation(id, data);
      closeModal();
      toast('Férias atualizadas!');
      loadOverview();
    } catch (e) {
      document.getElementById('ed-error').innerHTML = `<div class="alert alert-error">${e.message}</div>`;
    }
  }

  // ── Excluir ───────────────────────────────────────────────────────────────
  async function deleteVac(id) {
    if (!confirm('Excluir estas férias? Esta ação não pode ser desfeita.')) return;
    try {
      await Api.deleteVacation(id);
      closeModal();
      toast('Férias excluídas.', 'warning');
      loadOverview();
    } catch (e) { toast(e.message, 'error'); }
  }

  // ── Ciclo de vida ─────────────────────────────────────────────────────────
  function startVac(id) {
    const today = new Date().toISOString().split('T')[0];
    openModal('Iniciar Gozo de Férias',
      `<div class="form-group">
        <label>Data de início do gozo</label>
        <input class="form-control" type="date" id="start-vac-dt" value="${today}">
      </div>`,
      `<button class="btn btn-secondary" onclick="closeModal()">Cancelar</button>
       <button class="btn btn-primary" onclick="PageVacation._confirmStart(${id})">Confirmar</button>`
    );
  }

  async function _confirmStart(id) {
    const dt = document.getElementById('start-vac-dt')?.value;
    if (!dt) { toast('Informe a data de início.', 'error'); return; }
    try {
      await Api.startVacation(id, { enjoyment_start: dt });
      toast('Gozo iniciado!');
      loadOverview();
    } catch (e) { toast(e.message, 'error'); }
  }

  async function completeVac(id) {
    try {
      await Api.completeVacation(id);
      closeModal();
      toast('Férias concluídas — baixa dada!');
      loadOverview();
    } catch (e) { toast(e.message, 'error'); }
  }

  // ── Imprimir recibo ───────────────────────────────────────────────────────
  function printVac(v) {
    if (typeof v === 'string') { try { v = JSON.parse(v); } catch { return; } }
    const base  = parseFloat(v.base_salary  || 0);
    const third = parseFloat(v.one_third_bonus || 0);
    const inss  = parseFloat(v.inss_discount || 0);
    const gross = base + third;
    const itemsHtml = (v.items || []).map(it => {
      const sign = it.item_type === 'credito' ? '+' : '–';
      return `<tr><td>${sign} ${it.description}</td><td style="text-align:right">R$ ${parseFloat(it.value).toFixed(2).replace('.',',')}</td></tr>`;
    }).join('');
    const extra = (v.items||[]).reduce((a,i)=>a+(i.item_type==='credito'?parseFloat(i.value):-parseFloat(i.value)),0);
    const net   = base + third - inss + extra;
    const gozo  = v.sell_all_days ? 'Venda total (sem gozo)' : `${v.enjoyment_days} dias de gozo`;
    const fmtR  = n => 'R$ ' + parseFloat(n).toFixed(2).replace('.', ',');
    const fmtD  = s => s ? s.split('-').reverse().join('/') : '—';

    const win = window.open('', '_blank', 'width=680,height=700');
    win.document.write(`<!DOCTYPE html><html><head><meta charset="UTF-8">
      <title>Recibo de Férias — ${v.employee_name}</title>
      <style>
        body{font-family:Arial,sans-serif;font-size:13px;color:#111;padding:32px;max-width:600px;margin:0 auto}
        h2{text-align:center;margin-bottom:4px}p.sub{text-align:center;color:#666;margin-bottom:24px}
        table{width:100%;border-collapse:collapse;margin-bottom:16px}
        td,th{padding:6px 8px;border:1px solid #ddd}th{background:#f5f5f5;font-weight:600}
        .total{font-weight:700;font-size:15px;background:#e8f5e9}.danger{background:#fff5f5}
        .footer{margin-top:40px;border-top:1px solid #ccc;padding-top:16px;font-size:11px;color:#999;text-align:center}
        @media print{button{display:none}}
      </style></head><body>
      <h2>Recibo de Férias</h2>
      <p class="sub">${v.employee_name}</p>
      <table>
        <tr><th colspan="2">Período Aquisitivo</th></tr>
        <tr><td>De</td><td>${fmtD(v.acquisition_start)}</td></tr>
        <tr><td>Até</td><td>${fmtD(v.acquisition_end)}</td></tr>
        <tr><td>Modalidade</td><td>${gozo}</td></tr>
        ${v.enjoyment_start ? `<tr><td>Início do Gozo</td><td>${fmtD(v.enjoyment_start)}</td></tr>` : ''}
        ${v.registration_date ? `<tr><td>Data de Registro</td><td>${fmtD(v.registration_date)}</td></tr>` : ''}
      </table>
      <table>
        <tr><th>Item</th><th style="text-align:right">Valor</th></tr>
        <tr><td>Base de Férias (${v.sell_all_days?30:v.enjoyment_days} dias)</td><td style="text-align:right">${fmtR(base)}</td></tr>
        <tr><td>1/3 Constitucional</td><td style="text-align:right">${fmtR(third)}</td></tr>
        <tr><td><strong>Bruto</strong></td><td style="text-align:right"><strong>${fmtR(gross)}</strong></td></tr>
        <tr class="danger"><td>– INSS</td><td style="text-align:right">– ${fmtR(inss)}</td></tr>
        ${itemsHtml}
        <tr class="total"><td>LÍQUIDO A RECEBER</td><td style="text-align:right">${fmtR(net)}</td></tr>
      </table>
      ${v.notes ? `<p><strong>Obs:</strong> ${v.notes}</p>` : ''}
      <div style="margin-top:48px;display:flex;justify-content:space-between">
        <div style="border-top:1px solid #333;padding-top:4px;width:200px;text-align:center;font-size:12px">Empregador</div>
        <div style="border-top:1px solid #333;padding-top:4px;width:200px;text-align:center;font-size:12px">Funcionário</div>
      </div>
      <div class="footer">Emitido em ${new Date().toLocaleDateString('pt-BR')}</div>
      <script>window.onload=()=>window.print()<\/script></body></html>`);
    win.document.close();
  }

  return {
    render, loadOverview, loadEmployee,
    openNew, _onNewEmpChange, _onPeriodChange, _onSellAllChange, _onNewDaysChange, _onNewCalcChange, saveNew,
    openDetail, _saveCalc, _saveNotes,
    addItem, removeItem,
    openEdit, _onEditSellAll, saveEdit,
    deleteVac, startVac, _confirmStart, completeVac,
    printVac,
  };
})();
