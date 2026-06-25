const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

async function fetchAPI(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `API error ${res.status}`);
  }
  return res.json();
}

export const api = {
  // Dashboard
  getDashboardStats: () => fetchAPI('/api/dashboard/stats'),

  // Quotations
  getQuotations: (params = {}) => {
    const qs = new URLSearchParams(params).toString();
    return fetchAPI(`/api/quotations${qs ? '?' + qs : ''}`);
  },
  getQuotation: (id) => fetchAPI(`/api/quotations/${id}`),
  updateStatus: (id, status, notes = '') =>
    fetchAPI(`/api/quotations/${id}/status?new_status=${status}&notes=${encodeURIComponent(notes)}`, {
      method: 'PATCH',
    }),
  deleteQuotation: (id) => fetchAPI(`/api/quotations/${id}`, { method: 'DELETE' }),

  // Suppliers
  getSuppliers: () => fetchAPI('/api/suppliers'),
  getSupplier: (id) => fetchAPI(`/api/suppliers/${id}`),

  // Projects
  getProjects: () => fetchAPI('/api/projects'),

  // Compare
  compareItems: (desc) => fetchAPI(`/api/compare?item_description=${encodeURIComponent(desc)}`),
  getDistinctItems: () => fetchAPI('/api/line-items/distinct'),

  // Intelligence
  getRiskAnalysis: (id) => fetchAPI(`/api/intelligence/risk/${id}`),
  getBenchmarks: () => fetchAPI('/api/intelligence/benchmarks'),
  getAllRisks: () => fetchAPI('/api/intelligence/risk-summary'),

  // Search
  search: (query, filters = {}) =>
    fetchAPI('/api/search', {
      method: 'POST',
      body: JSON.stringify({ query, ...filters }),
    }).catch(() =>
      // Fallback for GET-style search
      fetchAPI(`/api/search?query=${encodeURIComponent(query)}`, { method: 'POST' })
    ),

  // Observability
  getLogs: (params = {}) => {
    const qs = new URLSearchParams(params).toString();
    return fetchAPI(`/api/observability/logs${qs ? '?' + qs : ''}`);
  },
  getMetrics: () => fetchAPI('/api/observability/metrics'),

  // Upload
  uploadFile: (file, supplierId, projectId) => {
    const formData = new FormData();
    formData.append('file', file);
    if (supplierId) formData.append('supplier_id', supplierId);
    if (projectId) formData.append('project_id', projectId);
    return fetch(`${API_BASE}/api/upload`, { method: 'POST', body: formData })
      .then(r => r.json());
  },
};
