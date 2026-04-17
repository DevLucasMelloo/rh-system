/**
 * Utilitários globais — formatação, toast, modal, helpers.
 */

// ── Formatters ────────────────────────────────────────────────────────────────
const fmt = {
  brl:  v => 'R$ ' + Number(v || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }),
  date: v => { if (!v) return '—'; const [y,m,d] = String(v).split('-'); return `${d}/${m}/${y}`; },
  dateInput: v => { if (!v) return ''; const [d,m,y] = String(v).split('/'); return `${y}-${m}-${d}`; },
  cpf:  v => { if (!v) return ''; const d = String(v).replace(/\D/g,''); return d.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/,'$1.$2.$3-$4'); },
  mins: v => { const h = Math.floor(Math.abs(v)/60); const m = Math.abs(v)%60; return `${v<0?'-':''}${h}h${String(m).padStart(2,'0')}min`; },
  month: m => ['','Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez'][m] || m,
  status: (s) => ({
    ativo: '<span class="badge badge-success">● Ativo</span>',
    inativo: '<span class="badge badge-danger">● Inativo</span>',
    rascunho: '<span class="badge badge-warning">Rascunho</span>',
    fechado: '<span class="badge badge-success">Fechado</span>',
    agendada: '<span class="badge badge-primary">Agendada</span>',
    em_gozo: '<span class="badge badge-success">Em Gozo</span>',
    concluida: '<span class="badge badge-gray">Concluída</span>',
    cancelada: '<span class="badge badge-danger">Cancelada</span>',
  })[s] || `<span class="badge badge-gray">${s}</span>`,
};

// ── Toast ─────────────────────────────────────────────────────────────────────
function toast(msg, type = 'success') {
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  const icon = type === 'success' ? '✓' : type === 'error' ? '✕' : '⚠';
  el.innerHTML = `<span>${icon}</span><span>${msg}</span>`;
  document.getElementById('toast-container').appendChild(el);
  setTimeout(() => el.remove(), 3500);
}

// ── Modal ─────────────────────────────────────────────────────────────────────
function openModal(title, bodyHtml, footerHtml = '', large = false) {
  document.getElementById('modal-title').textContent = title;
  document.getElementById('modal-body').innerHTML = bodyHtml;
  document.getElementById('modal-footer').innerHTML = footerHtml;
  const modal = document.getElementById('modal');
  modal.className = large ? 'modal modal-lg' : 'modal';
  document.getElementById('modal-overlay').classList.add('open');
}

function closeModal() {
  document.getElementById('modal-overlay').classList.remove('open');
}

// Close on overlay click
document.getElementById('modal-overlay').addEventListener('click', e => {
  if (e.target === e.currentTarget) closeModal();
});

// ── Dropdown toggle ───────────────────────────────────────────────────────────
document.addEventListener('click', e => {
  if (!e.target.closest('.dropdown')) {
    document.querySelectorAll('.dropdown-menu.open').forEach(m => m.classList.remove('open'));
  }
});

function toggleDropdown(id) {
  const menu = document.getElementById(id);
  const wasOpen = menu.classList.contains('open');
  document.querySelectorAll('.dropdown-menu.open').forEach(m => m.classList.remove('open'));
  if (!wasOpen) menu.classList.add('open');
}

// ── Months / Years helpers ────────────────────────────────────────────────────
function monthOptions(selected) {
  const names = ['Janeiro','Fevereiro','Março','Abril','Maio','Junho',
                 'Julho','Agosto','Setembro','Outubro','Novembro','Dezembro'];
  return names.map((n,i) =>
    `<option value="${i+1}" ${selected==i+1?'selected':''}>${n}</option>`
  ).join('');
}

function yearOptions(selected, from = 2020) {
  const yr = new Date().getFullYear();
  let opts = '';
  for (let y = yr+1; y >= from; y--)
    opts += `<option value="${y}" ${selected==y?'selected':''}>${y}</option>`;
  return opts;
}

function currentMonth() { return new Date().getMonth() + 1; }
function currentYear()  { return new Date().getFullYear(); }

// ── Loading HTML ──────────────────────────────────────────────────────────────
function loadingRow(cols = 6) {
  return `<tr class="loading-row"><td colspan="${cols}"><div class="flex items-center gap-2" style="justify-content:center"><div class="spinner spinner-dark"></div> Carregando...</div></td></tr>`;
}

function emptyRow(msg = 'Nenhum registro encontrado.', cols = 6) {
  return `<tr><td colspan="${cols}" style="text-align:center;padding:40px;color:var(--text-muted)">${msg}</td></tr>`;
}

// ── CNPJ mask ─────────────────────────────────────────────────────────────────
function maskCnpj(v) {
  return v.replace(/\D/g,'').replace(/(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})/,'$1.$2.$3/$4-$5');
}

// ── Debounce ──────────────────────────────────────────────────────────────────
function debounce(fn, ms = 300) {
  let t;
  return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms); };
}

// ── Employee select options ───────────────────────────────────────────────────
async function employeeSelectOptions(selected = null) {
  try {
    const emps = await Api.getEmployees();
    const active = (emps || []).filter(e => e.status === 'ativo');
    return active.map(e =>
      `<option value="${e.id}" ${selected==e.id?'selected':''}>${e.name}</option>`
    ).join('');
  } catch { return ''; }
}
