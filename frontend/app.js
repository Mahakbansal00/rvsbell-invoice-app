const state = {
  sortKey: 'invoice_id',
  sortAsc: false,
  invoices: []
};

const $ = (q) => document.querySelector(q);
async function fetchJSON(url) { const res = await fetch(url); return await res.json(); }
function fmt(n){ return n.toLocaleString(undefined,{style:'currency',currency:'USD'}); }

async function loadCustomers(){
  const data = await fetchJSON('/api/customers');
  const sel = $('#customerFilter');
  sel.innerHTML = '<option value="">All</option>' + data.map(c=>`<option value="${c.customer_id}">${c.name}</option>`).join('');
}

async function loadKPIs(){
  const d = await fetchJSON('/api/kpis');
  $('#kpiInvoiced').textContent = fmt(d.total_invoiced);
  $('#kpiReceived').textContent = fmt(d.total_received);
  $('#kpiOutstanding').textContent = fmt(d.total_outstanding);
  $('#kpiOverdue').textContent = d.percent_overdue + '%';
}

function buildQuery(){
  const params = new URLSearchParams();
  const cid = $('#customerFilter').value;
  const s = $('#startDate').value;
  const e = $('#endDate').value;
  if (cid) params.set('customer_id', cid);
  if (s) params.set('start', s);
  if (e) params.set('end', e);
  return '/api/invoices?' + params.toString();
}

function applySearchFilter(rows){
  const term = $('#searchInput').value.toLowerCase();
  if(!term) return rows;
  return rows.filter(r =>
    String(r.invoice_id).includes(term) ||
    r.customer_name.toLowerCase().includes(term) ||
    r.aging_bucket.toLowerCase().includes(term)
  );
}

function renderTable(){
  const tbody = $('#invoiceTable tbody');
  let rows = [...state.invoices];
  rows = applySearchFilter(rows);
  rows.sort((a,b)=>{
    const k = state.sortKey;
    let va = a[k], vb = b[k];
    if (typeof va === 'string') { va = va.toLowerCase(); vb = vb.toLowerCase(); }
    if (va < vb) return state.sortAsc ? -1 : 1;
    if (va > vb) return state.sortAsc ? 1 : -1;
    return 0;
  });
  tbody.innerHTML = rows.map(r=>{
    const overdue = (new Date(r.due_date) < new Date()) && r.outstanding > 0;
    return `<tr class="${overdue ? 'overdue' : ''}">
      <td>${r.invoice_id}</td>
      <td>${r.customer_name}</td>
      <td>${r.invoice_date}</td>
      <td>${r.due_date}</td>
      <td>${fmt(r.amount)}</td>
      <td>${fmt(r.total_paid)}</td>
      <td>${fmt(r.outstanding)}</td>
      <td>${r.aging_bucket}</td>
      <td><button data-id="${r.invoice_id}" class="payBtn">Record Payment</button></td>
    </tr>`;
  }).join('');

  document.querySelectorAll('.payBtn').forEach(btn=>{
    btn.addEventListener('click',()=> openModal(btn.getAttribute('data-id')));
  });
}

async function loadInvoices(){
  const url = buildQuery();
  state.invoices = await fetchJSON(url);
  renderTable();
}

async function loadChart(){
  const data = await fetchJSON('/api/top_customers_outstanding');
  const ctx = document.getElementById('topChart');
  if (window._chart) { window._chart.destroy(); }
  window._chart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: data.map(d=>d.name),
      datasets: [{ label: 'Outstanding', data: data.map(d=>d.total_outstanding) }]
    },
    options: { responsive: true, scales: { y: { beginAtZero: true } } }
  });
}

function openModal(invoiceId){
  $('#modalInvoiceId').value = invoiceId;
  $('#paymentDate').valueAsDate = new Date();
  $('#paymentAmount').value = '';
  $('#modalError').textContent = '';
  $('#modal').classList.remove('hidden');
}

function closeModal(){ $('#modal').classList.add('hidden'); }

async function savePayment(e){
  e.preventDefault();
  const payload = {
    invoice_id: Number($('#modalInvoiceId').value),
    amount: Number($('#paymentAmount').value),
    payment_date: $('#paymentDate').value
  };
  const res = await fetch('/api/payments', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify(payload)
  });
  if(!res.ok){
    const err = await res.json();
    $('#modalError').textContent = err.error || 'Failed to save payment';
    return;
  }
  closeModal();
  await Promise.all([loadKPIs(), loadInvoices(), loadChart()]);
}

document.addEventListener('DOMContentLoaded', async ()=>{
  await loadCustomers();
  await Promise.all([loadKPIs(), loadInvoices(), loadChart()]);

  $('#applyFilters').addEventListener('click', async ()=>{
    await loadInvoices();
    await loadChart();
  });
  $('#clearFilters').addEventListener('click', async ()=>{
    $('#customerFilter').value = '';
    $('#startDate').value = '';
    $('#endDate').value = '';
    $('#searchInput').value = '';
    await loadInvoices();
    await loadChart();
  });
  $('#searchInput').addEventListener('input', renderTable);
  $('#cancelModal').addEventListener('click', closeModal);
  document.querySelectorAll('#invoiceTable th').forEach(th=>{
    th.addEventListener('click', ()=>{
      const k = th.getAttribute('data-sort');
      if(!k) return;
      if (state.sortKey === k) state.sortAsc = !state.sortAsc; else { state.sortKey = k; state.sortAsc = true; }
      renderTable();
    });
  });
  $('#paymentForm').addEventListener('submit', savePayment);
});
