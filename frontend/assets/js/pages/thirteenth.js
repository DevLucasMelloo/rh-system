const PageThirteenth = (() => {

  // ── Render ─────────────────────────────────────────────────────────────────
  async function render(container) {
    const empOpts = await employeeSelectOptions();
    const yr = currentYear();
    container.innerHTML = `
      <div class="page-header">
        <div><h1>13º Salário</h1><p>Geração, controle e impressão do décimo terceiro salário</p></div>
      </div>

      <!-- Filtros e geração -->
      <div class="card" style="margin-bottom:24px">
        <div class="card-header">Registros de 13º</div>
        <div class="card-body">
          <div style="display:flex;align-items:flex-end;gap:12px;flex-wrap:wrap">
            <div class="form-group" style="flex:0 0 140px;margin-bottom:0">
              <label>Ano</label>
              <select class="form-control" id="t13-filter-year" onchange="PageThirteenth.loadList()">
                <option value="">Todos</option>${yearOptions(yr)}
              </select>
            </div>
            <div class="form-group" style="flex:0 0 180px;margin-bottom:0">
              <label>Parcela</label>
              <select class="form-control" id="t13-filter-parcela" onchange="PageThirteenth.loadList()">
                <option value="">Todas</option>
                <option value="1">1ª Parcela</option>
                <option value="2">2ª Parcela</option>
              </select>
            </div>
            <div style="flex:1"></div>
            <button class="btn btn-secondary" style="margin-bottom:0" onclick="PageThirteenth.imprimirTodos()">🖨 Imprimir Todos</button>
            <button class="btn btn-secondary" style="margin-bottom:0" onclick="PageThirteenth.exportar()">⬇ Exportar Excel</button>
          </div>
        </div>
        <div class="table-wrapper" style="margin:0">
          <table>
            <thead><tr>
              <th>Funcionário</th>
              <th style="text-align:center">Ano</th>
              <th style="text-align:center">Parcela</th>
              <th style="text-align:center">Meses</th>
              <th style="text-align:right">Bruto</th>
              <th style="text-align:right">INSS</th>
              <th style="text-align:right">Líquido</th>
              <th style="text-align:center">Pgto</th>
              <th style="text-align:center">Status</th>
              <th></th>
            </tr></thead>
            <tbody id="t13-tbody">
              <tr><td colspan="10" style="text-align:center;padding:32px;color:var(--text-muted)">Carregando...</td></tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Gerar -->
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:24px;align-items:start">
        <!-- Lote -->
        <div class="card">
          <div class="card-header">Gerar em Lote — Todos os Funcionários</div>
          <div class="card-body">
            <div class="form-row">
              <div class="form-group">
                <label>Ano</label>
                <select class="form-control" id="batch-year">${yearOptions(yr)}</select>
              </div>
              <div class="form-group">
                <label>Parcela</label>
                <select class="form-control" id="batch-parcela">
                  <option value="1">1ª Parcela — pag. 20/11</option>
                  <option value="2" selected>2ª Parcela — pag. 20/12</option>
                </select>
              </div>
            </div>
            <button class="btn btn-primary w-full" onclick="PageThirteenth.gerarLote()">
              Gerar / Atualizar Lote
            </button>
            <p style="font-size:11px;color:var(--text-muted);margin-top:8px">
              Gera ou recalcula o 13º de todos os funcionários ativos para o ano e parcela selecionados.
            </p>
          </div>
        </div>

        <!-- Individual -->
        <div class="card">
          <div class="card-header">Gerar Individual</div>
          <div class="card-body">
            <div class="form-group">
              <label>Funcionário</label>
              <select class="form-control" id="t13-emp">
                <option value="">Selecione...</option>${empOpts}
              </select>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label>Ano</label>
                <select class="form-control" id="t13-year">${yearOptions(yr)}</select>
              </div>
              <div class="form-group">
                <label>Parcela</label>
                <select class="form-control" id="t13-parcela">
                  <option value="1">1ª Parcela</option>
                  <option value="2" selected>2ª Parcela</option>
                </select>
              </div>
            </div>
            <button class="btn btn-primary w-full" onclick="PageThirteenth.gerarIndividual()">
              Gerar / Atualizar
            </button>
          </div>
        </div>
      </div>`;

    loadList();
  }

  // ── Lista ──────────────────────────────────────────────────────────────────
  async function loadList() {
    const year    = document.getElementById('t13-filter-year')?.value    || null;
    const parcela = document.getElementById('t13-filter-parcela')?.value || null;
    const tb = document.getElementById('t13-tbody');
    if (!tb) return;
    tb.innerHTML = `<tr><td colspan="10" style="text-align:center;padding:24px;color:var(--text-muted)">Carregando...</td></tr>`;
    try {
      const list = await Api.listThirteenth(year || null, parcela || null);
      if (!list.length) {
        tb.innerHTML = `<tr><td colspan="10" style="text-align:center;padding:32px;color:var(--text-muted)">Nenhum registro encontrado.</td></tr>`;
        return;
      }
      tb.innerHTML = list.map(r => {
        const paid   = r.status === 'pago';
        const badge  = paid
          ? `<span style="background:#dcfce7;color:#16a34a;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:600">Pago</span>`
          : `<span style="background:#fef9c3;color:#a16207;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:600">Pendente</span>`;
        const pgto   = r.payment_date ? r.payment_date.split('-').reverse().join('/') : '—';
        return `<tr>
          <td>${r.employee_name || '—'}</td>
          <td style="text-align:center">${r.year}</td>
          <td style="text-align:center">${r.parcela}ª</td>
          <td style="text-align:center">${r.worked_months}/12</td>
          <td style="text-align:right">${fmt.brl(r.bruto_13)}</td>
          <td style="text-align:right;color:var(--danger)">${r.parcela === 2 ? '– ' + fmt.brl(r.inss) : '—'}</td>
          <td style="text-align:right;font-weight:600;color:var(--success)">${fmt.brl(r.liquido)}</td>
          <td style="text-align:center;font-size:12px">${pgto}</td>
          <td style="text-align:center">${badge}</td>
          <td style="white-space:nowrap">
            <button class="btn-icon" title="Imprimir recibo" onclick="PageThirteenth.print(${JSON.stringify(r).replace(/"/g,'&quot;')})">🖨</button>
            ${!paid ? `<button class="btn-icon" title="Editar valores" onclick="PageThirteenth.openEdit(${JSON.stringify(r).replace(/"/g,'&quot;')})">✏</button>` : ''}
            ${!paid ? `<button class="btn-icon" title="Marcar como pago" onclick="PageThirteenth.marcarPago(${r.id})" style="color:var(--success)">✓</button>` : ''}
            <button class="btn-icon" title="Excluir" onclick="PageThirteenth.excluir(${r.id})" style="color:var(--danger)">✕</button>
          </td>
        </tr>`;
      }).join('');
    } catch (e) {
      tb.innerHTML = `<tr><td colspan="10"><div class="alert alert-error">${e.message}</div></td></tr>`;
    }
  }

  // ── Gerar lote ─────────────────────────────────────────────────────────────
  async function gerarLote() {
    const year    = parseInt(document.getElementById('batch-year').value);
    const parcela = parseInt(document.getElementById('batch-parcela').value);
    try {
      const list = await Api.generateThirteenthBatch({ year, parcela });
      toast(`${list.length} registro(s) gerado(s)/atualizados.`);
      loadList();
    } catch (e) { toast(e.message, 'error'); }
  }

  // ── Gerar individual ───────────────────────────────────────────────────────
  async function gerarIndividual() {
    const empId   = parseInt(document.getElementById('t13-emp').value);
    const year    = parseInt(document.getElementById('t13-year').value);
    const parcela = parseInt(document.getElementById('t13-parcela').value);
    if (!empId) { toast('Selecione um funcionário.', 'error'); return; }
    try {
      await Api.generateThirteenth({ employee_id: empId, year, parcela });
      toast('Registro gerado/atualizado.');
      loadList();
    } catch (e) { toast(e.message, 'error'); }
  }

  // ── Editar valores ─────────────────────────────────────────────────────────
  function openEdit(r) {
    if (typeof r === 'string') { try { r = JSON.parse(r); } catch { return; } }
    // Valor da parcela = líquido + inss (reconstruído)
    const valorParcela = (parseFloat(r.liquido) + parseFloat(r.inss || 0)).toFixed(2);
    const inssVal      = parseFloat(r.inss || 0).toFixed(2);

    openModal(`Editar 13º — ${r.employee_name}`, `
      <p style="font-size:13px;color:var(--text-muted);margin-bottom:16px">
        ${r.parcela}ª Parcela · ${r.year} · ${r.worked_months}/12 meses
      </p>
      <div class="form-group">
        <label>Valor da ${r.parcela}ª Parcela (R$)</label>
        <input class="form-control" type="number" step="0.01" id="edit13-valor" value="${valorParcela}"
          oninput="PageThirteenth._recalcEdit(${r.parcela})">
      </div>
      ${r.parcela === 2 ? `
      <div class="form-group">
        <label>INSS (R$)</label>
        <input class="form-control" type="number" step="0.01" id="edit13-inss" value="${inssVal}"
          oninput="PageThirteenth._recalcEdit(${r.parcela})">
      </div>` : ''}
      <div style="display:flex;justify-content:space-between;align-items:center;padding:10px 0;border-top:1px solid var(--border);margin-top:4px">
        <span style="font-weight:600">Líquido</span>
        <strong id="edit13-liquido-display" style="font-size:16px;color:var(--success)"></strong>
      </div>
      <div id="edit13-err"></div>`,
      `<button class="btn btn-secondary" onclick="closeModal()">Cancelar</button>
       <button class="btn btn-primary" onclick="PageThirteenth.saveEdit(${r.id}, ${r.parcela})">Salvar</button>`
    );
    _recalcEdit(r.parcela);
  }

  function _recalcEdit(parcela) {
    const valor = parseFloat(document.getElementById('edit13-valor')?.value) || 0;
    const inss  = parcela === 2 ? (parseFloat(document.getElementById('edit13-inss')?.value) || 0) : 0;
    const liq   = valor - inss;
    const el    = document.getElementById('edit13-liquido-display');
    if (el) el.textContent = fmt.brl(liq);
  }

  async function saveEdit(id, parcela) {
    const valor = parseFloat(document.getElementById('edit13-valor')?.value);
    const inss  = parcela === 2 ? (parseFloat(document.getElementById('edit13-inss')?.value) || 0) : 0;
    if (isNaN(valor) || valor <= 0) {
      document.getElementById('edit13-err').innerHTML = '<div class="alert alert-error">Informe o valor da parcela.</div>';
      return;
    }
    try {
      await Api.updateThirteenth(id, { valor_parcela: valor, inss });
      closeModal();
      toast('Valores atualizados.');
      loadList();
    } catch (e) {
      document.getElementById('edit13-err').innerHTML = `<div class="alert alert-error">${e.message}</div>`;
    }
  }

  // ── Marcar pago ────────────────────────────────────────────────────────────
  async function marcarPago(id) {
    try {
      await Api.markThirteenthPaid(id);
      toast('Marcado como pago.');
      loadList();
    } catch (e) { toast(e.message, 'error'); }
  }

  // ── Excluir ────────────────────────────────────────────────────────────────
  async function excluir(id) {
    if (!confirm('Excluir este registro de 13º?')) return;
    try {
      await Api.deleteThirteenth(id);
      toast('Registro excluído.', 'warning');
      loadList();
    } catch (e) { toast(e.message, 'error'); }
  }

  // ── Imprimir todos ─────────────────────────────────────────────────────────
  async function imprimirTodos() {
    const year    = document.getElementById('t13-filter-year')?.value    || null;
    const parcela = document.getElementById('t13-filter-parcela')?.value || null;
    try {
      const list = await Api.listThirteenth(year || null, parcela || null);
      if (!list.length) { toast('Nenhum registro para imprimir.', 'error'); return; }
      const receipts = list.map(_receiptHtml).join('');
      const win = window.open('', '_blank', 'width=720,height=800');
      win.document.write(`<!DOCTYPE html><html><head><meta charset="UTF-8">
        <title>13º Salário — Todos os Recibos</title>
        <style>body{font-family:Arial,sans-serif;color:#111}@media print{button{display:none}}</style>
        </head><body>${receipts}
        <div style="text-align:center;font-size:11px;color:#999;margin-top:8px">
          Emitido em ${new Date().toLocaleDateString('pt-BR')}
        </div>
        <script>window.onload=()=>window.print()<\/script></body></html>`);
      win.document.close();
    } catch (e) { toast(e.message, 'error'); }
  }

  // ── Exportar ───────────────────────────────────────────────────────────────
  async function exportar() {
    const year    = document.getElementById('t13-filter-year')?.value    || null;
    const parcela = document.getElementById('t13-filter-parcela')?.value || null;
    try { await Api.exportThirteenth(year || null, parcela || null); } catch (e) { toast(e.message, 'error'); }
  }

  // ── Impressão ──────────────────────────────────────────────────────────────
  function _receiptHtml(r) {
    const parcela  = r.parcela;
    const payDate  = r.payment_date ? r.payment_date.split('-').reverse().join('/') : (parcela === 1 ? `20/11/${r.year}` : `20/12/${r.year}`);
    const fmtR     = n => 'R$ ' + parseFloat(n).toFixed(2).replace('.', ',');
    return `
      <div style="page-break-after:always;padding:32px 0;max-width:560px;margin:0 auto">
        <h2 style="text-align:center;margin-bottom:4px;font-size:18px">Recibo de 13º Salário</h2>
        <p style="text-align:center;color:#666;margin-bottom:20px;font-size:13px">
          ${r.employee_name} — ${parcela}ª Parcela — ${r.year}
        </p>
        <table style="width:100%;border-collapse:collapse;margin-bottom:16px;font-size:13px">
          <tr style="background:#f5f5f5">
            <th style="padding:6px 8px;border:1px solid #ddd;text-align:left">Item</th>
            <th style="padding:6px 8px;border:1px solid #ddd;text-align:right">Valor</th>
          </tr>
          <tr>
            <td style="padding:6px 8px;border:1px solid #ddd">13º Bruto (${r.worked_months}/12 meses)</td>
            <td style="padding:6px 8px;border:1px solid #ddd;text-align:right">${fmtR(r.bruto_13)}</td>
          </tr>
          ${parcela === 2 ? `
          <tr style="background:#fff5f5">
            <td style="padding:6px 8px;border:1px solid #ddd">– INSS</td>
            <td style="padding:6px 8px;border:1px solid #ddd;text-align:right">– ${fmtR(r.inss)}</td>
          </tr>
          <tr style="background:#fff5f5">
            <td style="padding:6px 8px;border:1px solid #ddd">– 1ª Parcela (adiantamento)</td>
            <td style="padding:6px 8px;border:1px solid #ddd;text-align:right">– ${fmtR(r.primeira_parcela)}</td>
          </tr>` : ''}
          <tr style="font-weight:700;background:#e8f5e9">
            <td style="padding:7px 8px;border:1px solid #ddd;font-size:14px">LÍQUIDO ${parcela}ª PARCELA</td>
            <td style="padding:7px 8px;border:1px solid #ddd;text-align:right;font-size:14px">${fmtR(r.liquido)}</td>
          </tr>
        </table>
        <p style="font-size:12px;color:#555;margin-bottom:32px">
          Data de Pagamento: <strong>${payDate}</strong>
        </p>
        <div style="display:flex;justify-content:space-between;margin-top:40px">
          <div style="border-top:1px solid #333;padding-top:4px;width:200px;text-align:center;font-size:12px">Empregador</div>
          <div style="border-top:1px solid #333;padding-top:4px;width:200px;text-align:center;font-size:12px">Funcionário</div>
        </div>
      </div>`;
  }

  function print(r) {
    if (typeof r === 'string') { try { r = JSON.parse(r); } catch { return; } }
    const win = window.open('', '_blank', 'width=680,height=700');
    win.document.write(`<!DOCTYPE html><html><head><meta charset="UTF-8">
      <title>13º — ${r.employee_name}</title>
      <style>body{font-family:Arial,sans-serif;color:#111}@media print{button{display:none}}</style>
      </head><body>${_receiptHtml(r)}
      <div style="text-align:center;font-size:11px;color:#999;margin-top:8px">
        Emitido em ${new Date().toLocaleDateString('pt-BR')}
      </div>
      <script>window.onload=()=>window.print()<\/script></body></html>`);
    win.document.close();
  }

  return { render, loadList, gerarLote, gerarIndividual, openEdit, saveEdit, _recalcEdit, marcarPago, excluir, exportar, imprimirTodos, print };
})();
