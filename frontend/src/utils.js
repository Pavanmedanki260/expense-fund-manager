const API = process.env.REACT_APP_BACKEND_URL || '';

function getAuthHeaders() {
  const token = localStorage.getItem('fundtrack_token');
  const h = { 'Content-Type': 'application/json' };
  if (token) h['Authorization'] = `Bearer ${token}`;
  return h;
}

export const api = {
  get: (path) => fetch(`${API}${path}`, { headers: getAuthHeaders() }).then(r => { if (!r.ok) throw new Error(r.statusText); return r.json(); }),
  post: (path, body) => fetch(`${API}${path}`, { method: 'POST', headers: getAuthHeaders(), body: JSON.stringify(body) }).then(r => { if (!r.ok) throw new Error(r.statusText); return r.json(); }),
  put: (path, body) => fetch(`${API}${path}`, { method: 'PUT', headers: getAuthHeaders(), body: JSON.stringify(body) }).then(r => { if (!r.ok) throw new Error(r.statusText); return r.json(); }),
  del: (path) => fetch(`${API}${path}`, { method: 'DELETE', headers: getAuthHeaders() }).then(r => { if (!r.ok) throw new Error(r.statusText); return r.json(); }),
  download: (path) => fetch(`${API}${path}`, { headers: getAuthHeaders() }).then(r => { if (!r.ok) throw new Error(r.statusText); return r.blob(); }),
  getPublic: (path) => fetch(`${API}${path}`).then(r => { if (!r.ok) throw new Error(r.statusText); return r.json(); }),
};

export function setToken(token) {
  if (token) localStorage.setItem('fundtrack_token', token);
  else localStorage.removeItem('fundtrack_token');
}

export function getToken() {
  return localStorage.getItem('fundtrack_token');
}

export function formatINR(amount) {
  return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(amount);
}

export function formatDate(dateStr) {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
}
