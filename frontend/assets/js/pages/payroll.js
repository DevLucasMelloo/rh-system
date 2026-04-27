/**
 * Folha de Pagamento — visão por período com todos os funcionários elegíveis.
 */
const PagePayroll = (() => {
  let month = currentMonth();
  let year  = currentYear();
  let rows  = [];   // EligibleEmployeeRead[]
  let periodStatus = null;   // 'not_opened' | 'open' | 'closed'
  let _currentPayroll = null;  // holerite aberto no modal de detalhe

  // ── Render principal ──────────────────────────────────────────────────────
  async function render(container) {
    container.innerHTML = `
      <div class="page-header">
        <div><h1>Folha de Pagamento</h1><p>Holerites por competência</p></div>
        <div style="display:flex;gap:8px">
          <button class="btn btn-secondary" id="btn-close-all" onclick="PagePayroll.openCloseAll()" style="display:none">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>
            Fechar Folha
          </button>
          <button class="btn btn-primary" id="btn-batch" onclick="PagePayroll.openBatch()">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
            Gerar Folha
          </button>
        </div>
      </div>

      <div style="display:flex;align-items:center;gap:16px;margin-bottom:20px;flex-wrap:wrap">
        <div class="period-selector">
          <label>Competência</label>
          <select id="sel-month" onchange="PagePayroll.changePeriod()">${monthOptions(month)}</select>
          <select id="sel-year"  onchange="PagePayroll.changePeriod()">${yearOptions(year)}</select>
        </div>
        <div id="ponto-badge"></div>
        <div id="folha-summary" style="margin-left:auto;font-size:13px;color:var(--text-muted)"></div>
      </div>

      <div class="table-wrapper" style="overflow-x:auto">
        <table id="payroll-table" style="min-width:1100px">
          <thead>
            <tr>
              <th style="min-width:160px">Funcionário</th>
              <th style="text-align:center">Dias</th>
              <th style="text-align:center">Banco H.</th>
              <th style="text-align:right">Sal. Bruto</th>
              <th style="text-align:right">VT</th>
              <th style="text-align:right">Auxílio</th>
              <th style="text-align:right">INSS</th>
              <th style="text-align:right">Vales</th>
              <th style="text-align:right">Faltas</th>
              <th style="text-align:right">Outros</th>
              <th style="text-align:right;font-weight:700">Líquido</th>
              <th style="text-align:center">Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody id="payroll-tbody">${loadingRow(13)}</tbody>
        </table>
      </div>`;

    await loadData();
  }

  async function loadData() {
    try {
      // Carregar status do ponto e funcionários elegíveis em paralelo
      const [periodData, eligible] = await Promise.all([
        Api.getTimesheetPeriod(month, year).catch(() => null),
        Api.getEligible(month, year),
      ]);

      rows = eligible || [];
      periodStatus = periodData ? periodData.status : 'not_opened';

      renderBadge();
      renderButtons();
      renderTable();
    } catch (e) {
      document.getElementById('payroll-tbody').innerHTML =
        `<tr><td colspan="13" style="padding:24px;text-align:center;color:var(--danger)">${e.message}</td></tr>`;
    }
  }

  function renderBadge() {
    const el = document.getElementById('ponto-badge');
    if (!el) return;
    const map = {
      closed: `<span class="badge badge-success" style="padding:5px 12px;font-size:12px">✓ Ponto Fechado</span>`,
      open:   `<span class="badge badge-warning" style="padding:5px 12px;font-size:12px">⚠ Ponto Aberto</span>`,
      not_opened: `<span class="badge badge-gray" style="padding:5px 12px;font-size:12px">Ponto Não Aberto</span>`,
    };
    el.innerHTML = map[periodStatus] || '';
  }

  function renderButtons() {
    const hasDraft = rows.some(r => r.payroll && r.payroll.status === 'rascunho');
    const hasAny   = rows.some(r => r.has_payroll);
    const allDone  = hasAny && rows.every(r => r.has_payroll);

    const btnBatch   = document.getElementById('btn-batch');
    const btnCloseAll = document.getElementById('btn-close-all');
    if (btnBatch) btnBatch.style.display = allDone ? 'none' : '';
    if (btnCloseAll) btnCloseAll.style.display = hasDraft ? '' : 'none';

    const total = rows.filter(r => r.payroll)
      .reduce((s, r) => s + parseFloat(r.payroll.net_salary || 0), 0);
    const summary = document.getElementById('folha-summary');
    if (summary && hasAny) {
      const closed = rows.filter(r => r.payroll && r.payroll.status === 'fechado').length;
      summary.innerHTML = `${rows.filter(r=>r.has_payroll).length} holerite(s) &nbsp;·&nbsp; Total líquido: <strong>${fmt.brl(total)}</strong> &nbsp;·&nbsp; ${closed} fechado(s)`;
    } else if (summary) {
      summary.innerHTML = '';
    }
  }

  function renderTable() {
    if (!rows.length) {
      document.getElementById('payroll-tbody').innerHTML =
        `<tr><td colspan="13" style="padding:40px;text-align:center;color:var(--text-muted)">Nenhum funcionário elegível para este período.</td></tr>`;
      return;
    }

    document.getElementById('payroll-tbody').innerHTML = rows.map(r => rowHtml(r)).join('');
  }

  function _getItem(items, types, credit = null) {
    return (items || [])
      .filter(i => types.includes(i.item_type) && (credit === null || i.is_credit === credit))
      .reduce((s, i) => s + parseFloat(i.amount), 0);
  }

  function rowHtml(r) {
    if (!r.has_payroll) {
      return `
        <tr style="background:var(--bg-subtle,#fafafa)">
          <td><strong>${r.name}</strong><br><span style="font-size:11px;color:var(--text-muted)">${r.admission_date ? fmt.date(r.admission_date) : ''}</span></td>
          <td colspan="10" style="text-align:center;color:var(--text-muted);font-size:13px">Sem holerite gerado</td>
          <td style="text-align:center"><span class="badge badge-gray">—</span></td>
          <td class="td-actions">
            <button class="btn btn-sm btn-secondary" onclick="PagePayroll.generateOne(${r.employee_id})">Gerar</button>
          </td>
        </tr>`;
    }

    const p     = r.payroll;
    const items = p.items || [];
    const isClosed = p.status === 'fechado';

    const vt      = _getItem(items, ['vale_transporte'], true);
    const aux     = _getItem(items, ['auxilio'], true);
    const inss    = _getItem(items, ['inss'], false);
    const vales   = _getItem(items, ['vale_desconto'], false);
    const faltas  = _getItem(items, ['falta', 'dsr'], false);
    const outrosC = _getItem(items, ['outros_credito'], true);
    const outrosD = _getItem(items, ['outros_desconto'], false);
    const outros  = outrosC - outrosD;
    const bankH = parseFloat(p.total_overtime_hours || 0);

    const statusBadge = isClosed
      ? `<span class="badge badge-success">Fechado</span>`
      : `<span class="badge badge-warning">Rascunho</span>`;

    return `
      <tr style="cursor:pointer" onclick="PagePayroll.openDetail(${p.id})">
        <td>
          <strong>${r.name}</strong>
          ${p.notes ? `<br><span style="font-size:11px;color:var(--text-muted)">${p.notes}</span>` : ''}
          ${p.pay_overtime ? `<span style="font-size:10px;color:var(--primary);margin-left:4px">HE</span>` : ''}
          ${p.use_hour_bank_for_absences ? `<span style="font-size:10px;color:var(--warning,#b45309);margin-left:4px">BH</span>` : ''}
        </td>
        <td style="text-align:center">${p.worked_days}</td>
        <td style="text-align:center;color:${bankH > 0 ? 'var(--success)' : bankH < 0 ? 'var(--danger)' : 'var(--text-muted)'}">${bankH !== 0 ? (bankH > 0 ? '+' : '') + bankH.toFixed(1)+'h' : '—'}</td>
        <td style="text-align:right">${fmt.brl(p.gross_salary)}</td>
        <td style="text-align:right;color:var(--text-muted)">${vt > 0 ? fmt.brl(vt) : '—'}</td>
        <td style="text-align:right;color:var(--text-muted)">${aux > 0 ? fmt.brl(aux) : '—'}</td>
        <td style="text-align:right;color:var(--danger)">${inss > 0 ? fmt.brl(inss) : '—'}</td>
        <td style="text-align:right;color:var(--danger)">${vales > 0 ? fmt.brl(vales) : '—'}</td>
        <td style="text-align:right;color:var(--danger)">${faltas > 0 ? fmt.brl(faltas) : '—'}</td>
        <td style="text-align:right;color:${outros >= 0 ? 'var(--text-muted)' : 'var(--danger)'}">${outros !== 0 ? fmt.brl(Math.abs(outros)) : '—'}</td>
        <td style="text-align:right;font-weight:700;color:var(--primary)">${fmt.brl(p.net_salary)}</td>
        <td style="text-align:center">${statusBadge}</td>
        <td class="td-actions" onclick="event.stopPropagation()">
          <div class="dropdown">
            <button class="btn-icon" onclick="toggleDropdown('pdd-${p.id}')">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="5" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="12" cy="19" r="1"/></svg>
            </button>
            <div class="dropdown-menu" id="pdd-${p.id}">
              <button class="dropdown-item" onclick="PagePayroll.openDetail(${p.id})">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
                Ver / Editar
              </button>
              ${!isClosed ? `
              <button class="dropdown-item" onclick="PagePayroll.recalc(${p.id})">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 .49-3"/></svg>
                Recalcular
              </button>
              <button class="dropdown-item" onclick="PagePayroll.openClose(${p.id})">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>
                Fechar Holerite
              </button>` : ''}
              <button class="dropdown-item" onclick="Api.getPayrollPdf(${p.id}).catch(e=>toast(e.message,'error'))">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                Baixar PDF
              </button>
              <hr style="margin:4px 0;border:none;border-top:1px solid var(--border)">
              <button class="dropdown-item" style="color:var(--danger)" onclick="PagePayroll.confirmDelete(${p.id}, '${r.name}')">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/></svg>
                Excluir Holerite
              </button>
            </div>
          </div>
        </td>
      </tr>`;
  }

  // ── Geração ───────────────────────────────────────────────────────────────

  function openBatch() {
    openModal('Gerar Folha de Pagamento', `
      <p style="color:var(--text-muted);margin-bottom:16px">
        Gera holerites para todos os funcionários elegíveis em <strong>${fmt.month(month)}/${year}</strong> que ainda não têm holerite.
      </p>
      <div class="form-row">
        <div class="form-group">
          <label style="display:flex;align-items:center;gap:8px;cursor:pointer">
            <input type="checkbox" id="batch-he" style="width:16px;height:16px">
            Pagar Banco de Horas positivo
          </label>
          <p style="font-size:12px;color:var(--text-muted);margin-top:4px">Paga saldo positivo do banco: Salário ÷ 220 × 1,6 × horas</p>
        </div>
        <div class="form-group">
          <label style="display:flex;align-items:center;gap:8px;cursor:pointer">
            <input type="checkbox" id="batch-bh" style="width:16px;height:16px">
            Usar Banco de Horas para Faltas
          </label>
          <p style="font-size:12px;color:var(--text-muted);margin-top:4px">Debita horas do banco em vez de descontar em dinheiro</p>
        </div>
      </div>
      <div id="batch-error"></div>`, `
      <button class="btn btn-secondary" onclick="closeModal()">Cancelar</button>
      <button class="btn btn-primary" onclick="PagePayroll.doBatch()">Gerar Todos</button>`);
  }

  async function doBatch() {
    const pay_overtime = document.getElementById('batch-he').checked;
    const use_hour_bank = document.getElementById('batch-bh').checked;
    try {
      const created = await Api.batchCreatePayroll({
        competence_month: month,
        competence_year: year,
        pay_overtime,
        use_hour_bank_for_absences: use_hour_bank,
      });
      closeModal();
      toast(`${created.length} holerite(s) gerado(s)!`);
      await loadData();
    } catch (e) {
      document.getElementById('batch-error').innerHTML =
        `<div class="alert alert-error">${e.message}</div>`;
    }
  }

  async function generateOne(empId) {
    try {
      await Api.createPayroll({
        employee_id: empId,
        competence_month: month,
        competence_year: year,
      });
      toast('Holerite gerado!');
      await loadData();
    } catch (e) { toast(e.message, 'error'); }
  }

  // ── Detail / Edição ───────────────────────────────────────────────────────

  async function openDetail(id) {
    openModal('Holerite — Detalhes e Edição',
      '<div style="padding:32px;text-align:center"><div class="spinner spinner-dark"></div></div>',
      '', true);
    try {
      const p = await Api.getPayroll(id);
      _renderDetail(p);
    } catch (e) {
      document.getElementById('modal-body').innerHTML =
        `<div class="alert alert-error">${e.message}</div>`;
    }
  }

  function _renderDetail(p) {
    _currentPayroll = p;
    const isClosed = p.status === 'fechado';
    const items    = p.items || [];
    const credits  = items.filter(i =>  i.is_credit);
    const debits   = items.filter(i => !i.is_credit);

    const itemRow = (i) => `
      <div style="display:flex;justify-content:space-between;align-items:center;padding:6px 0;border-bottom:1px solid var(--border)">
        <div style="flex:1">
          <span style="font-size:13px">${i.description}</span>
          ${i.is_manual ? '<span class="badge badge-gray" style="font-size:10px;margin-left:6px">manual</span>' : ''}
          ${i.notes ? `<span style="font-size:11px;color:var(--text-muted);display:block">${i.notes}</span>` : ''}
        </div>
        <div style="display:flex;align-items:center;gap:8px">
          <span style="font-weight:600;color:${i.is_credit ? 'var(--success)' : 'var(--danger)'}">
            ${i.is_credit ? '+' : '-'} ${fmt.brl(i.amount)}
          </span>
          ${!isClosed ? `
          <button class="btn-icon" title="Editar" onclick="PagePayroll.openEditItem(${p.id},${i.id})">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
          </button>
          <button class="btn-icon" title="Remover" onclick="PagePayroll.removeItem(${p.id},${i.id})" style="color:var(--danger)">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
          </button>` : ''}
        </div>
      </div>`;

    document.getElementById('modal-body').innerHTML = `
      <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;margin-bottom:20px">
        <div class="detail-item"><label>Funcionário</label><span style="font-weight:600">${p.employee_name||'—'}</span></div>
        <div class="detail-item"><label>Competência</label><span>${fmt.month(p.competence_month)}/${p.competence_year}</span></div>
        <div class="detail-item"><label>Status</label><span>${fmt.status(p.status)}</span></div>
        <div class="detail-item"><label>Dias Trabalhados</label><span>${p.worked_days}</span></div>
        <div class="detail-item"><label>Banco Horas</label><span style="color:${parseFloat(p.total_overtime_hours||0) > 0 ? 'var(--success)' : parseFloat(p.total_overtime_hours||0) < 0 ? 'var(--danger)' : 'inherit'}">${(() => { const bh = parseFloat(p.total_overtime_hours||0); const abs = Math.abs(bh); const h = Math.floor(abs); const m = Math.round((abs - h) * 60); return bh === 0 ? '0h00' : (bh > 0 ? '+' : '-') + h + 'h' + String(m).padStart(2,'0'); })()}</span></div>
        <div class="detail-item"><label>Data Pagamento</label><span>${p.payment_date ? fmt.date(p.payment_date) : '—'}</span></div>
      </div>

      ${!isClosed ? `
      <div style="background:var(--bg-subtle,#f8f9fa);border-radius:8px;padding:12px 16px;margin-bottom:16px">
        <div class="form-group" style="margin:0">
          <label style="font-size:12px">Observação / Comentário</label>
          <div style="display:flex;gap:8px">
            <input class="form-control" id="notes-input" value="${p.notes || ''}" placeholder="Observação para este funcionário...">
            <button class="btn btn-secondary btn-sm" onclick="PagePayroll.saveNotes(${p.id})">Salvar</button>
          </div>
        </div>
      </div>` : p.notes ? `<div class="alert" style="margin-bottom:16px">${p.notes}</div>` : ''}

      <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:16px">
        <div>
          <p style="font-size:12px;font-weight:700;color:var(--success);margin-bottom:8px;text-transform:uppercase">Proventos</p>
          ${credits.map(itemRow).join('') || '<p style="color:var(--text-muted);font-size:13px">Nenhum.</p>'}
        </div>
        <div>
          <p style="font-size:12px;font-weight:700;color:var(--danger);margin-bottom:8px;text-transform:uppercase">Descontos</p>
          ${debits.map(itemRow).join('') || '<p style="color:var(--text-muted);font-size:13px">Nenhum.</p>'}
        </div>
      </div>

      <div style="border-top:2px solid var(--border);padding-top:12px;display:flex;justify-content:space-between;align-items:center">
        <span style="font-weight:600">Salário Líquido</span>
        <span style="font-size:20px;font-weight:700;color:var(--primary)">${fmt.brl(p.net_salary)}</span>
      </div>

      ${!isClosed ? `
      <div style="margin-top:16px;display:flex;gap:8px;flex-wrap:wrap;align-items:center">
        <button class="btn btn-secondary btn-sm" onclick="PagePayroll.openAddItem(${p.id})">+ Item Manual</button>
        <button class="btn btn-secondary btn-sm" onclick="PagePayroll.recalc(${p.id})">↺ Recalcular</button>
      </div>
      <div style="margin-top:8px;display:flex;gap:8px;flex-wrap:wrap;align-items:center">
        <button class="btn btn-sm" style="background:#16a34a;color:#fff;border:none" onclick="PagePayroll.payPositiveBank(${p.id},${p.employee_id})" title="Paga saldo positivo do banco: Salário ÷ 220 × horas">💰 Pagar Banco Positivo</button>
        <button class="btn btn-sm" style="background:#7c3aed;color:#fff;border:none" onclick="PagePayroll.deductNegativeBank(${p.id},${p.employee_id})" title="Desconta horas negativas do banco: Salário ÷ 220 × horas devidas">⚠ Descontar Banco Negativo</button>
        <button class="btn btn-sm" style="background:${p.use_hour_bank_for_absences ? '#0e7490' : '#0891b2'};color:#fff;border:${p.use_hour_bank_for_absences ? '2px solid #164e63' : 'none'}" onclick="PagePayroll.toggleBancoFaltas(${p.id},${p.use_hour_bank_for_absences})" title="Usa horas do banco para cobrir faltas em vez de descontar em dinheiro">${p.use_hour_bank_for_absences ? '✓ Banco p/ Faltas (ON)' : '🔄 Banco p/ Faltas'}</button>
      </div>` : ''}`;

    document.getElementById('modal-footer').innerHTML = `
      <button class="btn btn-secondary" onclick="closeModal()">Fechar</button>
      <button class="btn btn-danger" style="margin-right:auto;order:-1" onclick="PagePayroll.confirmDeleteFromDetail(${p.id},'${(p.employee_name||'').replace(/'/g,"\\'")}')">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/></svg>
        Excluir Holerite
      </button>
      ${!isClosed ? `<button class="btn btn-primary" onclick="PagePayroll.openClose(${p.id})">Fechar Holerite</button>` : ''}`;
  }

  async function toggleFlag(payrollId, flag, value) {
    try {
      const p = await Api.updatePayrollFlags(payrollId, { [flag]: value });
      toast('Atualizado e recalculado!');
      _renderDetail(p);
      await loadData();
    } catch (e) { toast(e.message, 'error'); }
  }

  async function saveNotes(payrollId) {
    const notes = document.getElementById('notes-input').value.trim() || null;
    try {
      const p = await Api.updatePayrollFlags(payrollId, { notes });
      toast('Observação salva!');
      _renderDetail(p);
      await loadData();
    } catch (e) { toast(e.message, 'error'); }
  }

  // ── Itens manuais ─────────────────────────────────────────────────────────

  function openAddItem(payrollId) {
    openModal('Adicionar Item — Outros', `
      <div class="form-group"><label>Descrição *</label>
        <input class="form-control" id="item-desc" placeholder="Ex: Bônus, desconto disciplinar..."></div>
      <div class="form-row">
        <div class="form-group"><label>Valor *</label>
          <input class="form-control" type="number" step="0.01" min="0" id="item-amount"></div>
        <div class="form-group"><label>Tipo</label>
          <select class="form-control" id="item-credit">
            <option value="true">Crédito (provento)</option>
            <option value="false">Débito (desconto)</option>
          </select></div>
      </div>
      <div class="form-group"><label>Observação</label>
        <input class="form-control" id="item-notes" placeholder="Comentário sobre este item (opcional)"></div>
      <div id="item-error"></div>`, `
      <button class="btn btn-secondary" onclick="PagePayroll.openDetail(${payrollId})">Voltar</button>
      <button class="btn btn-primary" onclick="PagePayroll.saveItem(${payrollId})">Adicionar</button>`);
  }

  async function saveItem(payrollId) {
    const desc   = document.getElementById('item-desc').value.trim();
    const amount = parseFloat(document.getElementById('item-amount').value);
    const credit = document.getElementById('item-credit').value === 'true';
    const notes  = document.getElementById('item-notes').value.trim() || null;
    if (!desc || !amount || amount <= 0) {
      document.getElementById('item-error').innerHTML =
        '<div class="alert alert-error">Preencha descrição e valor válido.</div>';
      return;
    }
    try {
      await Api.addPayrollItem(payrollId, {
        item_type:    credit ? 'outros_credito' : 'outros_desconto',
        description:  desc,
        amount,
        is_credit:    credit,
        notes,
      });
      toast('Item adicionado!');
      openDetail(payrollId);
    } catch (e) {
      document.getElementById('item-error').innerHTML =
        `<div class="alert alert-error">${e.message}</div>`;
    }
  }

  function openEditItem(payrollId, itemId) {
    const item = (_currentPayroll?.items || []).find(i => i.id === itemId);
    if (!item) { toast('Item não encontrado', 'error'); return; }
    openModal('Editar Item', `
      <div class="form-group"><label>Descrição</label>
        <input class="form-control" id="edit-desc" value="${(item.description || '').replace(/"/g, '&quot;')}"></div>
      <div class="form-row">
        <div class="form-group"><label>Valor</label>
          <input class="form-control" type="number" step="0.01" min="0" id="edit-amount" value="${item.amount}"></div>
      </div>
      <div class="form-group"><label>Observação</label>
        <input class="form-control" id="edit-notes" value="${(item.notes || '').replace(/"/g, '&quot;')}"></div>
      <div id="edit-error"></div>`, `
      <button class="btn btn-secondary" onclick="PagePayroll.openDetail(${payrollId})">Cancelar</button>
      <button class="btn btn-primary" onclick="PagePayroll.doEditItem(${payrollId},${itemId})">Salvar</button>`);
  }

  async function doEditItem(payrollId, itemId) {
    const desc   = document.getElementById('edit-desc').value.trim();
    const amount = parseFloat(document.getElementById('edit-amount').value);
    const notes  = document.getElementById('edit-notes').value.trim() || null;
    if (!desc || !amount || amount < 0) {
      document.getElementById('edit-error').innerHTML =
        '<div class="alert alert-error">Valor inválido.</div>';
      return;
    }
    try {
      await Api.updatePayrollItem(payrollId, itemId, { description: desc, amount, notes });
      toast('Item atualizado!');
      openDetail(payrollId);
    } catch (e) {
      document.getElementById('edit-error').innerHTML =
        `<div class="alert alert-error">${e.message}</div>`;
    }
  }

  async function removeItem(payrollId, itemId) {
    try {
      await Api.deletePayrollItem(payrollId, itemId);
      toast('Item removido!');
      openDetail(payrollId);
    } catch (e) { toast(e.message, 'error'); }
  }

  // ── Fechar ────────────────────────────────────────────────────────────────

  function openClose(id) {
    const today = new Date().toISOString().split('T')[0];
    openModal('Fechar Holerite', `
      <p style="color:var(--text-muted);margin-bottom:16px">
        Após o fechamento o holerite não poderá ser editado. Para corrigir, exclua e recrie.
      </p>
      <div class="form-group"><label>Data de Pagamento</label>
        <input class="form-control" type="date" id="close-date" value="${today}">
      </div>`, `
      <button class="btn btn-secondary" onclick="closeModal()">Cancelar</button>
      <button class="btn btn-primary" onclick="PagePayroll.doClose(${id})">Fechar Holerite</button>`);
  }

  async function doClose(id) {
    const dt = document.getElementById('close-date').value;
    try {
      await Api.closePayroll(id, dt);
      closeModal();
      toast('Holerite fechado!');
      await loadData();
    } catch (e) { toast(e.message, 'error'); }
  }

  function openCloseAll() {
    const today = new Date().toISOString().split('T')[0];
    const draft = rows.filter(r => r.payroll && r.payroll.status === 'rascunho').length;
    const pontoWarning = periodStatus !== 'closed'
      ? `<div class="alert alert-error" style="margin-bottom:16px">
           <strong>Atenção:</strong> O ponto de ${fmt.month(month)}/${year} ainda não está fechado.
           Feche o ponto antes de fechar a folha para garantir que as faltas foram contabilizadas.
         </div>`
      : '';
    openModal('Fechar Folha Completa', `
      ${pontoWarning}
      <p style="color:var(--text-muted);margin-bottom:16px">
        Serão fechados <strong>${draft}</strong> holerite(s) em rascunho de <strong>${fmt.month(month)}/${year}</strong>.
      </p>
      <div class="form-group"><label>Data de Pagamento</label>
        <input class="form-control" type="date" id="ca-date" value="${today}">
      </div>`, `
      <button class="btn btn-secondary" onclick="closeModal()">Cancelar</button>
      <button class="btn btn-primary" onclick="PagePayroll.doCloseAll()">Confirmar Fechamento</button>`);
  }

  async function doCloseAll() {
    const dt = document.getElementById('ca-date').value;
    try {
      await Api.closeAllPayrolls(month, year, dt);
      closeModal();
      toast('Folha fechada com sucesso!');
      await loadData();
    } catch (e) { toast(e.message, 'error'); }
  }

  // ── Recalcular / Excluir ──────────────────────────────────────────────────

  async function recalc(id) {
    try {
      await Api.recalcPayroll(id);
      toast('Holerite recalculado!');
      await loadData();
      openDetail(id);
    } catch (e) { toast(e.message, 'error'); }
  }

  function confirmDelete(id, name) {
    openModal('Excluir Holerite', `
      <p>Tem certeza que deseja excluir o holerite de <strong>${name}</strong>?</p>
      <p style="color:var(--danger);font-size:13px;margin-top:8px">
        Se o holerite estiver fechado, as parcelas de vale serão revertidas para pendente.
      </p>`, `
      <button class="btn btn-secondary" onclick="closeModal()">Cancelar</button>
      <button class="btn btn-danger" onclick="PagePayroll.doDelete(${id})">Excluir</button>`);
  }

  function confirmDeleteFromDetail(id, name) {
    openModal('Excluir Holerite', `
      <p>Tem certeza que deseja excluir o holerite de <strong>${name}</strong>?</p>
      <p style="color:var(--danger);font-size:13px;margin-top:8px">
        O holerite será excluído e poderá ser gerado novamente.<br>
        Se estiver fechado, as parcelas de vale retornam para pendente.
      </p>`, `
      <button class="btn btn-secondary" onclick="PagePayroll.openDetail(${id})">Cancelar</button>
      <button class="btn btn-danger" onclick="PagePayroll.doDelete(${id})">Excluir</button>`);
  }

  async function doDelete(id) {
    try {
      await Api.deletePayroll(id);
      closeModal();
      toast('Holerite excluído.');
      await loadData();
    } catch (e) { toast(e.message, 'error'); }
  }

  // ── Period selector ───────────────────────────────────────────────────────

  function changePeriod() {
    month = parseInt(document.getElementById('sel-month').value);
    year  = parseInt(document.getElementById('sel-year').value);
    document.getElementById('payroll-tbody').innerHTML = loadingRow(13);
    loadData();
  }

  async function deductNegativeBank(payrollId, employeeId) {
    try {
      const bank = await Api.getHourBank(employeeId);
      const balMin = bank.balance_minutes || 0;
      if (balMin >= 0) {
        toast('Este funcionário não possui horas negativas no banco.', 'error');
        return;
      }
      const absMin  = Math.abs(balMin);
      const absHrs  = absMin / 60;
      const p       = _currentPayroll;
      const salary  = parseFloat(p.gross_salary || 0);
      const hourRate = salary / 220;
      const deduction = Math.round(hourRate * absHrs * 100) / 100;
      const hStr    = Math.floor(absMin / 60) + 'h' + String(absMin % 60).padStart(2,'0');

      openModal('Descontar Banco de Horas Negativo',
        `<div style="display:flex;flex-direction:column;gap:12px">
          <div style="background:#fef3c7;border:1px solid #fcd34d;border-radius:8px;padding:12px 16px">
            <p style="font-weight:600;margin-bottom:4px">Resumo do desconto</p>
            <p style="font-size:13px">Horas devidas: <strong>${hStr}</strong></p>
            <p style="font-size:13px">Taxa horária: <strong>${fmt.brl(hourRate)}/h</strong> (Salário ÷ 220)</p>
            <p style="font-size:16px;margin-top:8px">Desconto: <strong style="color:var(--danger)">${fmt.brl(deduction)}</strong></p>
          </div>
          <div class="form-group" style="margin:0">
            <label>Observação (opcional)</label>
            <input class="form-control" id="bank-deduct-notes" placeholder="Ex: Compensação de horas negativas — ${hStr}">
          </div>
        </div>`,
        `<button class="btn btn-secondary" onclick="closeModal()">Cancelar</button>
         <button class="btn btn-primary" onclick="PagePayroll._confirmBankDeduct(${payrollId},${deduction},'${hStr}')">Descontar</button>`
      );
    } catch (e) { toast(e.message, 'error'); }
  }

  async function _confirmBankDeduct(payrollId, amount, hStr) {
    const notes = document.getElementById('bank-deduct-notes')?.value || `Desconto banco de horas — ${hStr}`;
    try {
      await Api.addPayrollItem(payrollId, {
        item_type:      'banco_desconto',
        description:    `Desconto Banco de Horas (${hStr})`,
        amount:         amount,
        is_credit:      false,
        notes:          notes,
        show_on_payslip: true,
      });
      toast('Desconto de banco de horas lançado!');
      await loadData();
      openDetail(payrollId);
    } catch (e) { toast(e.message, 'error'); }
  }

  async function payPositiveBank(payrollId, employeeId) {
    try {
      const bank = await Api.getHourBank(employeeId);
      const balMin = bank.balance_minutes || 0;
      if (balMin <= 0) {
        toast('Este funcionário não possui horas positivas no banco.', 'error');
        return;
      }
      const absHrs   = balMin / 60;
      const p        = _currentPayroll;
      const salary   = parseFloat(p.gross_salary || 0);
      const hourRate = salary / 220;
      const heRate   = hourRate * 1.6;
      const payment  = Math.round(heRate * absHrs * 100) / 100;
      const hStr     = Math.floor(balMin / 60) + 'h' + String(balMin % 60).padStart(2,'0');

      openModal('Pagar Banco de Horas Positivo',
        `<div style="display:flex;flex-direction:column;gap:12px">
          <div style="background:#dcfce7;border:1px solid #86efac;border-radius:8px;padding:12px 16px">
            <p style="font-weight:600;margin-bottom:4px">Resumo do pagamento</p>
            <p style="font-size:13px">Horas a pagar: <strong>${hStr}</strong></p>
            <p style="font-size:13px">Taxa horária: <strong>${fmt.brl(heRate)}/h</strong> (Salário ÷ 220 × 1,6)</p>
            <p style="font-size:16px;margin-top:8px">Pagamento: <strong style="color:#16a34a">${fmt.brl(payment)}</strong></p>
          </div>
          <div class="form-group" style="margin:0">
            <label>Observação (opcional)</label>
            <input class="form-control" id="bank-pay-notes" placeholder="Ex: Pagamento banco de horas — ${hStr}">
          </div>
        </div>`,
        `<button class="btn btn-secondary" onclick="closeModal()">Cancelar</button>
         <button class="btn btn-primary" style="background:#16a34a;border-color:#16a34a" onclick="PagePayroll._confirmBankPay(${payrollId},${payment},'${hStr}')">Pagar</button>`
      );
    } catch (e) { toast(e.message, 'error'); }
  }

  async function _confirmBankPay(payrollId, amount, hStr) {
    const notes = document.getElementById('bank-pay-notes')?.value || `Pagamento banco de horas — ${hStr}`;
    try {
      await Api.addPayrollItem(payrollId, {
        item_type:      'banco_credito',
        description:    `Horas Extras (${hStr})`,
        amount:         amount,
        is_credit:      true,
        notes:          notes,
        show_on_payslip: true,
      });
      toast('Horas extras lançadas!');
      await loadData();
      openDetail(payrollId);
    } catch (e) { toast(e.message, 'error'); }
  }

  async function toggleBancoFaltas(payrollId, currentValue) {
    try {
      const p = await Api.updatePayrollFlags(payrollId, { use_hour_bank_for_absences: !currentValue });
      toast(!currentValue ? 'Banco de Horas ativado para cobrir faltas!' : 'Banco de Horas desativado para faltas.');
      _renderDetail(p);
      await loadData();
    } catch (e) { toast(e.message, 'error'); }
  }

  return {
    render, changePeriod,
    openBatch, doBatch, generateOne,
    openDetail, toggleFlag, saveNotes,
    openAddItem, saveItem, openEditItem, doEditItem, removeItem,
    openClose, doClose, openCloseAll, doCloseAll,
    recalc, confirmDelete, confirmDeleteFromDetail, doDelete,
    deductNegativeBank, _confirmBankDeduct,
    payPositiveBank, _confirmBankPay,
    toggleBancoFaltas,
  };
})();
