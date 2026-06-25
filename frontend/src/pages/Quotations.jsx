import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Trash2 } from 'lucide-react';
import { api } from '../api/client';

export default function Quotations() {
  const [data, setData] = useState({ items: [], total: 0 });
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({ supplier_id: '', project_id: '', status: '' });
  const [page, setPage] = useState(1);
  const [suppliers, setSuppliers] = useState([]);
  const [projects, setProjects] = useState([]);
  const nav = useNavigate();

  useEffect(() => {
    api.getSuppliers().then(setSuppliers).catch(() => {});
    api.getProjects().then(setProjects).catch(() => {});
  }, []);

  const fetchQuotations = () => {
    setLoading(true);
    const params = { page, page_size: 20 };
    if (filters.supplier_id) params.supplier_id = filters.supplier_id;
    if (filters.project_id) params.project_id = filters.project_id;
    if (filters.status) params.status = filters.status;
    api.getQuotations(params).then(setData).catch(console.error).finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchQuotations();
  }, [page, filters]);

  const handleDelete = async (e, id) => {
    e.stopPropagation();
    if (window.confirm("Are you sure you want to delete this quotation? This action cannot be undone.")) {
      try {
        await api.deleteQuotation(id);
        fetchQuotations(); // Refresh the list
      } catch (err) {
        alert("Failed to delete quotation: " + err.message);
      }
    }
  };

  return (
    <div>
      <div className="page-header">
        <h1>Quotations</h1>
        <p>{data.total} quotations across all suppliers and projects</p>
      </div>

      <div className="flex gap-3" style={{ marginBottom: 16 }}>
        <select className="select" value={filters.supplier_id}
                onChange={e => { setFilters(f => ({ ...f, supplier_id: e.target.value })); setPage(1); }}>
          <option value="">All Suppliers</option>
          {suppliers.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
        </select>
        <select className="select" value={filters.project_id}
                onChange={e => { setFilters(f => ({ ...f, project_id: e.target.value })); setPage(1); }}>
          <option value="">All Projects</option>
          {projects.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
        </select>
        <select className="select" value={filters.status}
                onChange={e => { setFilters(f => ({ ...f, status: e.target.value })); setPage(1); }}>
          <option value="">All Statuses</option>
          <option value="received">Received</option>
          <option value="reviewed">Reviewed</option>
          <option value="approved">Approved</option>
          <option value="rejected">Rejected</option>
        </select>
      </div>

      <div className="card">
        {loading ? <div className="loading"><div className="spinner" /> Loading...</div> : (
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Doc No</th>
                  <th>Supplier</th>
                  <th>Project</th>
                  <th>Date</th>
                  <th>Format</th>
                  <th>Value (excl tax)</th>
                  <th>Status</th>
                  <th>Risk</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {data.items.map(q => (
                  <tr key={q.id} onClick={() => nav(`/quotations/${q.id}`)} style={{ cursor: 'pointer' }}>
                    <td style={{ fontWeight: 600, color: '#38bdf8' }}>{q.doc_no}</td>
                    <td>{q.supplier_id}</td>
                    <td>{q.project_id}</td>
                    <td>{q.doc_date}</td>
                    <td><span className={`badge ${q.format?.includes('pdf') ? 'pdf' : q.format}`}>{q.format}</span></td>
                    <td style={{ textAlign: 'right', fontFamily: 'monospace' }}>
                      {q.currency === 'USD' ? '$' : '₹'}{(q.total_excl_tax || 0).toLocaleString()}
                    </td>
                    <td><span className={`badge ${q.status}`}>{q.status}</span></td>
                    <td>
                      <span className="risk-bar">
                        <span className={`risk-bar-fill ${q.risk_score >= 50 ? 'high' : q.risk_score >= 25 ? 'medium' : 'low'}`}
                              style={{ width: `${Math.min(q.risk_score, 100)}%` }} />
                      </span>
                      {q.risk_score}
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <button 
                        className="btn btn-secondary btn-sm text-red-500 hover:text-red-700" 
                        onClick={(e) => handleDelete(e, q.id)}
                        title="Delete Quotation"
                      >
                        <Trash2 size={16} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {data.total > 20 && (
          <div className="flex items-center justify-between mt-4" style={{ padding: '0 16px' }}>
            <button className="btn btn-secondary btn-sm" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>Previous</button>
            <span style={{ color: 'var(--text-secondary)', fontSize: 13 }}>Page {page} of {Math.ceil(data.total / 20)}</span>
            <button className="btn btn-secondary btn-sm" disabled={page >= Math.ceil(data.total / 20)} onClick={() => setPage(p => p + 1)}>Next</button>
          </div>
        )}
      </div>
    </div>
  );
}
