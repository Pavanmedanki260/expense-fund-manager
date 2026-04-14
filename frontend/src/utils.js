const API = process.env.REACT_APP_BACKEND_URL;

const headers = { 'Content-Type': 'application/json' };
const opts = (method, body) => ({
  method,
  headers,
  credentials: 'include',
  ...(body && { body: JSON.stringify(body) }),
});

export const api = {
  get: (path) => fetch(`${API}${path}`, { credentials: 'include' }).then(r => { if (!r.ok) throw new Error(r.statusText); return r.json(); }),
  post: (path, body) => fetch(`${API}${path}`, opts('POST', body)).then(r => { if (!r.ok) throw new Error(r.statusText); return r.json(); }),
  put: (path, body) => fetch(`${API}${path}`, opts('PUT', body)).then(r => { if (!r.ok) throw new Error(r.statusText); return r.json(); }),
  del: (path) => fetch(`${API}${path}`, { method: 'DELETE', credentials: 'include' }).then(r => { if (!r.ok) throw new Error(r.statusText); return r.json(); }),
  download: (path) => fetch(`${API}${path}`, { credentials: 'include' }).then(r => {
    if (!r.ok) throw new Error(r.statusText);
    return r.blob();
  }),
};

export function formatINR(amount) {
  return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(amount);
}

export function formatDate(dateStr) {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
}

export function getStatusBadge(collected, utilized) {
  if (collected === 0) return { class: 'badge-healthy', text: 'No Funds' };
  const pct = (utilized / collected) * 100;
  if (pct > 100) return { class: 'badge-danger', text: 'Over-utilized' };
  if (pct > 80) return { class: 'badge-warning', text: 'High Usage' };
  return { class: 'badge-healthy', text: 'Healthy' };
}
