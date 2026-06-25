import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';

export default function Suppliers() {
  const [suppliers, setSuppliers] = useState([]);
  const [loading, setLoading] = useState(true);
  const nav = useNavigate();

  useEffect(() => {
    api.getSuppliers()
      .then(data => setSuppliers(data.filter(s => s.id !== 'UNKNOWN')))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="loading"><div className="spinner" /> Loading suppliers...</div>;

  return (
    <div>
      <div className="page-header">
        <h1>Suppliers</h1>
        <p>{suppliers.length} registered suppliers</p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: 16 }}>
        {suppliers.map(s => (
          <div key={s.id} className="card" onClick={() => nav(`/suppliers/${s.id}`)}
               style={{ cursor: 'pointer' }}>
            <div className="flex items-center justify-between" style={{ marginBottom: 12 }}>
              <div>
                <div style={{ fontSize: 15, fontWeight: 600, color: 'var(--text-primary)' }}>{s.name}</div>
                <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{s.id} • {s.contact}</div>
              </div>
              <div className={`badge ${s.avg_risk_score >= 40 ? 'high' : s.avg_risk_score >= 20 ? 'medium' : 'low'}`}>
                Risk: {Math.round(s.avg_risk_score)}
              </div>
            </div>
            <div className="detail-grid">
              <div className="detail-item">
                <div className="detail-label">Quotations</div>
                <div className="detail-value">{s.quotation_count}</div>
              </div>
              <div className="detail-item">
                <div className="detail-label">Total Value</div>
                <div className="detail-value">₹{(s.total_value / 100000).toFixed(1)}L</div>
              </div>
              <div className="detail-item">
                <div className="detail-label">Lead Time</div>
                <div className="detail-value">{s.typical_lead_days} days</div>
              </div>
              <div className="detail-item">
                <div className="detail-label">Currency</div>
                <div className="detail-value">{s.currency}</div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}