const PageVales = (() => {
  async function render(container) {
    const empOpts = await employeeSelectOptions();
    container.innerHTML = `
      <div class="page-header">
        <div><h1>Vales</h1><p>Vales e adiantamentos com parcelamento automático</p></div>
        <button class="btn btn-primary" onclick="PageVales.openNew()">+ Novo Vale</button>
      </div>

      <div class="toolbar">
        <div class="search-box" style="max-width:280px">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/></svg>
          <select class="form-control" id="vale-emp-sel" onchange="PageVales.loadEmployee()" style="padding-left:32px">
            <option value="">Selecione o funcionário...</option>${empOpts}
          </select>
        </div>
      </div>

      <div class="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>Data Emissão</th><th>Valor Total</th><th>Parcelas</th>
              <th>Observações</th><th></th>
            </tr>
          </thead>
          <tbody id="vale-tbody">
            <tr><td colspan="5" style="text-align:center;padding:40px;color:var(--text-muted)">Selecione um funcionário para ver os vales.</td></tr>
          </tbody>
        </table>
      </div>`;
  }

  async function loadEmployee() {
    const id = parseInt(document.getElementById('vale-emp-sel').value) || null;
    if (!id) return;
    document.getElementById('vale-tbody').innerHTML = loadingRow(5);
    try {
      const vales = await Api.getVales(id) || [];
      if (!vales.length) {
        document.getElementById('vale-tbody').innerHTML = emptyRow('Nenhum vale cadastrado.', 5);
        return;
      }
      document.getElementById('vale-tbody').innerHTML = vales.map(v => {
        const paid = (v.installment_items || []).filter(i => i.is_paid).length;
        const total = v.installments;
        return `
          <tr>
            <td>${fmt.date(v.issued_date)}</td>
            <td><strong>${fmt.brl(v.total_amount)}</strong></td>
            <td>
              ${total}x
              <span style="font-size:11px;color:var(--text-muted);margin-left:4px">(${paid}/${total} pago${paid !== 1 ? 's' : ''})</span>
            </td>
            <td style="color:var(--text-muted)">${v.notes || '—'}</td>
            <td class="td-actions">
              <button class="btn-icon" onclick="PageVales.openDetail(${v.id})" title="Ver parcelas">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
              </button>
            </td>
          </tr>`;
      }).join('');
    } catch (e) {
      document.getElementById('vale-tbody').innerHTML = emptyRow(e.message, 5);
    }
  }

  async function openNew() {
    const empOpts = await employeeSelectOptions();
    openModal('Novo Vale', `
      <div class="form-group"><label>Funcionário *</label>
        <select class="form-control" id="nv-emp"><option value="">Selecione...</option>${empOpts}</select>
      </div>
      <div class="form-row">
        <div class="form-group"><label>Valor Total *</label>
          <input class="form-control" type="number" step="0.01" id="nv-amount" placeholder="0,00">
        </div>
        <div class="form-group"><label>Nº de Parcelas</label>
          <select class="form-control" id="nv-installments">
            <option value="1">1x (à vista)</option>
            <option value="2">2x</option>
            <option value="3">3x</option>
            <option value="6">6x</option>
            <option value="12">12x</option>
          </select>
        </div>
      </div>
      <div class="form-row">
        <div class="form-group"><label>Data de Emissão *</label>
          <input class="form-control" type="date" id="nv-date" value="${new Date().toISOString().split('T')[0]}">
        </div>
      </div>
      <div class="form-group"><label>Observações</label>
        <input class="form-control" id="nv-notes" placeholder="Ex: Compra de EPI, Adiantamento salarial...">
      </div>
      <div id="nv-error"></div>`, `
      <button class="btn btn-secondary" onclick="closeModal()">Cancelar</button>
      <button class="btn btn-primary" onclick="PageVales.saveNew()">Registrar</button>`);
  }

  async function saveNew() {
    const empId = parseInt(document.getElementById('nv-emp').value);
    if (!empId) {
      document.getElementById('nv-error').innerHTML = '<div class="alert alert-error">Selecione um funcionário.</div>';
      return;
    }
    const data = {
      total_amount:  parseFloat(document.getElementById('nv-amount').value),
      installments:  parseInt(document.getElementById('nv-installments').value),
      issued_date:   document.getElementById('nv-date').value,
      notes:         document.getElementById('nv-notes').value.trim() || null,
    };
    try {
      await Api.createVale(empId, data);
      closeModal();
      toast('Vale registrado!');
      const sel = document.getElementById('vale-emp-sel');
      if (sel && parseInt(sel.value) === empId) loadEmployee();
    } catch (e) {
      document.getElementById('nv-error').innerHTML = `<div class="alert alert-error">${e.message}</div>`;
    }
  }

  async function openDetail(id) {
    openModal('Parcelas do Vale', '<div style="padding:20px;text-align:center"><div class="spinner spinner-dark"></div></div>', '', true);
    try {
      const v = await Api.getVale(id);
      const rows = (v.installment_items || []).map(inst => `
        <tr>
          <td>${inst.installment_number}ª parcela</td>
          <td>${fmt.brl(inst.amount)}</td>
          <td>${inst.due_month ? `${fmt.month(inst.due_month)}/${inst.due_year}` : '—'}</td>
          <td>${inst.is_paid
            ? '<span class="badge badge-success">Pago</span>'
            : '<span class="badge badge-gray">Pendente</span>'}</td>
        </tr>`).join('') || '<tr><td colspan="4" style="text-align:center;padding:16px;color:var(--text-muted)">Sem parcelas.</td></tr>';

      document.getElementById('modal-body').innerHTML = `
        <div class="detail-grid" style="margin-bottom:16px">
          <div class="detail-item"><label>Emissão</label><span>${fmt.date(v.issued_date)}</span></div>
          <div class="detail-item"><label>Valor Total</label><span>${fmt.brl(v.total_amount)}</span></div>
          <div class="detail-item"><label>Parcelas</label><span>${v.installments}x</span></div>
          <div class="detail-item"><label>Obs.</label><span>${v.notes || '—'}</span></div>
        </div>
        <div class="table-wrapper" style="border:none">
          <table>
            <thead><tr><th>Parcela</th><th>Valor</th><th>Vencimento</th><th>Status</th></tr></thead>
            <tbody>${rows}</tbody>
          </table>
        </div>`;
      document.getElementById('modal-footer').innerHTML =
        `<button class="btn btn-secondary" onclick="closeModal()">Fechar</button>`;
    } catch (e) {
      document.getElementById('modal-body').innerHTML = `<div class="alert alert-error">${e.message}</div>`;
    }
  }

  return { render, loadEmployee, openNew, saveNew, openDetail };
})();
