import { useState, useEffect } from 'react';
import { Search, FileText, ArrowRight } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';

export default function SearchPage() {
  const [query, setQuery] = useState('');
  const [supplierId, setSupplierId] = useState('');
  const [projectId, setProjectId] = useState('');
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [suppliers, setSuppliers] = useState([]);
  const [projects, setProjects] = useState([]);
  const nav = useNavigate();

  useEffect(() => {
    api.getSuppliers().then(setSuppliers).catch(() => {});
    api.getProjects().then(setProjects).catch(() => {});
  }, []);

  const handleSearch = async (e) => {
    e?.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    setError(null);
    setResults(null);
    try {
      const filters = {};
      if (supplierId) filters.supplier_id = supplierId;
      if (projectId) filters.project_id = projectId;
      const data = await api.search(query.trim(), filters);
      setResults(data);
    } catch (err) {
      setError(err.message || 'Search failed');
    } finally {
      setLoading(false);
    }
  };

  const resultItems = results?.results || results?.items || (Array.isArray(results) ? results : []);
  const hasAnswer = results?.answer || results?.summary;

  return (
    <div>
      <div className="page-header">
        <h1>AI Search</h1>
        <p>Natural language search across all quotation data</p>
      </div>

      {/* Search Bar */}
      <form onSubmit={handleSearch}>
        <div className="search-bar">
          <div style={{ position: 'relative', flex: 1 }}>
            <Search size={16} style={{
              position: 'absolute', left: 14, top: '50%', transform: 'translateY(-50%)',
              color: 'var(--text-muted)', pointerEvents: 'none',
            }} />
            <input
              id="search-input"
              className="input"
              type="text"
              placeholder='Try "cheapest supplier for MS Plate" or "quotations above 5 lakhs"...'
              value={query}
              onChange={e => setQuery(e.target.value)}
              style={{ paddingLeft: 40 }}
              autoFocus
            />
          </div>
          <button
            id="search-submit-btn"
            className="btn btn-primary"
            type="submit"
            disabled={!query.trim() || loading}
          >
            {loading ? <div className="spinner" style={{ width: 16, height: 16, borderWidth: 2 }} /> : <Search size={14} />}
            Search
          </button>
        </div>
      </form>

      {/* Filters */}
      <div className="flex gap-3" style={{ marginBottom: 20 }}>
        <select className="select" value={supplierId} onChange={e => setSupplierId(e.target.value)} style={{ maxWidth: 200 }}>
          <option value="">All Suppliers</option>
          {suppliers.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
        </select>
        <select className="select" value={projectId} onChange={e => setProjectId(e.target.value)} style={{ maxWidth: 200 }}>
          <option value="">All Projects</option>
          {projects.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
        </select>
      </div>

      {/* Loading */}
      {loading && (
        <div className="card" style={{ marginBottom: 20 }}>
          <div className="loading"><div className="spinner" /> Searching across quotation data...</div>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="card" style={{ borderLeft: '4px solid var(--accent-red)', marginBottom: 20 }}>
          <div style={{ color: 'var(--accent-red)', fontWeight: 600, marginBottom: 4 }}>Search Error</div>
          <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>{error}</div>
        </div>
      )}

      {/* AI Answer */}
      {hasAnswer && (
        <div className="card" style={{
          marginBottom: 20, borderLeft: '4px solid var(--accent-purple)',
          background: 'linear-gradient(135deg, rgba(139,92,246,0.05), rgba(59,130,246,0.05))',
        }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--accent-purple)', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
            AI Summary
          </div>
          <div style={{ fontSize: 14, color: 'var(--text-primary)', lineHeight: 1.7, whiteSpace: 'pre-wrap' }}>
            {results.answer || results.summary}
          </div>
        </div>
      )}

      {/* Results */}
      {results && !loading && (
        <div className="card">
          <div className="card-header">
            <span className="card-title">
              {resultItems.length} Result{resultItems.length !== 1 ? 's' : ''}
            </span>
            {results.query_type && (
              <span className="badge" style={{ background: 'rgba(139,92,246,0.15)', color: 'var(--accent-purple)' }}>
                {results.query_type}
              </span>
            )}
          </div>

          {resultItems.length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {resultItems.map((item, i) => (
                <div
                  key={i}
                  style={{
                    padding: '14px 16px', borderRadius: 'var(--radius-md)',
                    background: 'var(--bg-input)', border: '1px solid var(--border-color)',
                    cursor: item.id || item.quotation_id ? 'pointer' : 'default',
                    transition: 'all var(--transition-fast)',
                  }}
                  onClick={() => {
                    const qId = item.id || item.quotation_id;
                    if (qId) nav(`/quotations/${qId}`);
                  }}
                  onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--border-hover)'; e.currentTarget.style.background = 'var(--bg-card-hover)'; }}
                  onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border-color)'; e.currentTarget.style.background = 'var(--bg-input)'; }}
                >
                  <div className="flex items-center justify-between" style={{ marginBottom: 6 }}>
                    <div className="flex items-center gap-2">
                      <FileText size={14} style={{ color: 'var(--accent-blue)' }} />
                      <span style={{ fontWeight: 600, color: '#38bdf8' }}>
                        {item.doc_no || item.doc_id || `Result ${i + 1}`}
                      </span>
                      {item.supplier_name && (
                        <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>• {item.supplier_name}</span>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      {item.score != null && (
                        <span style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'monospace' }}>
                          {typeof item.score === 'number' ? (item.score * 100).toFixed(0) + '%' : item.score}
                        </span>
                      )}
                      {(item.id || item.quotation_id) && <ArrowRight size={14} style={{ color: 'var(--text-muted)' }} />}
                    </div>
                  </div>
                  {(item.snippet || item.description || item.text) && (
                    <div style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                      {item.snippet || item.description || item.text}
                    </div>
                  )}
                  <div className="flex gap-2" style={{ marginTop: 6 }}>
                    {item.total_excl_tax != null && (
                      <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                        ₹{(item.total_excl_tax || 0).toLocaleString()}
                      </span>
                    )}
                    {item.status && <span className={`badge ${item.status}`}>{item.status}</span>}
                    {item.risk_score != null && (
                      <span className={`badge ${item.risk_score >= 50 ? 'high' : item.risk_score >= 25 ? 'medium' : 'low'}`}>
                        Risk: {item.risk_score}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-state">No results found for "{query}"</div>
          )}
        </div>
      )}

      {/* Initial State */}
      {!results && !loading && !error && (
        <div className="card">
          <div className="empty-state">
            <Search size={48} />
            <div style={{ marginTop: 12, fontWeight: 500 }}>Search across your quotation database</div>
            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>
              Try queries like "most expensive line items", "supplier with best lead time", or "quotations for PROJ-ALPHA"
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
