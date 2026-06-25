import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { api } from '../api/client';

export default function SupplierDetail() {
  const { id } = useParams();
  const nav = useNavigate();
  const [supplier, setSupplier] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getSupplier(id).then(setSupplier).catch(console.error).finally(() => setLoading(false));
  }, [id]);

  if (loading) return <div className="loading"><div className="spinner" /> Loading...</div>;
  if (!supplier) return <div className="empty-state">Supplier not found</div>;

  const pricingData = (supplier.pricing_profile?.pricing_position || [])
    .slice(0, 15)
    .map(p => ({
      name: p.description?.substring(0, 20) + '...',
      deviation: p.deviation_pct,
    }));

  return (
    <div>
      <div className="flex items-center gap-3" style={{ marginBottom: 20 }}>
        <button className="btn btn-secondary btn-sm" onClick={() => nav('/suppliers')}>
          <ArrowLeft size={14} /> Back
        </button>
        <div className="page-header" style={{ marginBottom: 0 }}>
          <h1>{supplier.name}</h1>
          <p>{supplier.id} • {supplier.email}</p>
        </div>
      </div>

      <div className="grid-2" style={{ marginBottom: 20 }}>
        <div className="card">
          <div className="detail-section-title">Supplier Information</div>
          <div className="detail-grid">
            <div className="detail-item"><div className="detail-label">Contact</div><div className="detail-value">{supplier.contact}</div></div>
            <div className="detail-item"><div className="detail-label">Phone</div><div className="detail-value">{supplier.phone}</div></div>
            <div className="detail-item"><div className="detail-label">Email</div><div className="detail-value">{supplier.email}</div></div>
            <div className="detail-item"><div className="detail-label">Address</div><div className="detail-value">{supplier.address}</div></div>
            <div className="detail-item"><div className="detail-label">GST</div><div className="detail-value">{supplier.gst || 'N/A'}</div></div>
            <div className="detail-item"><div className="detail-label">Currency</div><div className="detail-value">{supplier.currency}</div></div>
            <div className="detail-item"><div className="detail-label">Typical Lead</div><div className="detail-value">{supplier.typical_lead_days} days</div></div>
            <div className="detail-item"><div className="detail-label">Avg Price Deviation</div>
              <div className="detail-value" style={{ color: (supplier.pricing_profile?.avg_deviation_pct || 0) > 20 ? 'var(--accent-red)' : 'var(--accent-emerald)' }}>
                {supplier.pricing_profile?.avg_deviation_pct > 0 ? '+' : ''}{supplier.pricing_profile?.avg_deviation_pct || 0}%
              </div>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="detail-section-title">Price Deviation from Market Median (%)</div>
          {pricingData.length > 0 ? (
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={pricingData} layout="vertical" margin={{ left: 10 }}>
                <XAxis type="number" tick={{ fill: '#94a3b8', fontSize: 11 }} />
                <YAxis dataKey="name" type="category" tick={{ fill: '#94a3b8', fontSize: 10 }} width={130} />
                <Tooltip contentStyle={{ background: '#1a2332', border: '1px solid rgba(148,163,184,0.1)', borderRadius: 8 }} />
                <Bar dataKey="deviation" fill="#3b82f6" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : <div className="empty-state">No pricing data</div>}
        </div>
      </div>

      <div className="card">
        <div className="detail-section-title">Quotation History ({supplier.quotations?.length || 0})</div>
        <div className="table-container">
          <table>
            <thead>
              <tr><th>Doc No</th><th>Project</th><th>Date</th><th>Format</th><th>Value</th><th>Status</th><th>Risk</th></tr>
            </thead>
            <tbody>
              {(supplier.quotations || []).map(q => (
                <tr key={q.id} onClick={() => nav(`/quotations/${q.id}`)} style={{ cursor: 'pointer' }}>
                  <td style={{ fontWeight: 600, color: '#38bdf8' }}>{q.doc_no}</td>
                  <td>{q.project_id}</td>
                  <td>{q.doc_date}</td>
                  <td><span className={`badge ${q.format?.includes('pdf') ? 'pdf' : q.format}`}>{q.format}</span></td>
                  <td style={{ textAlign: 'right', fontFamily: 'monospace' }}>{q.currency === 'USD' ? '$' : '₹'}{(q.total_excl_tax || 0).toLocaleString()}</td>
                  <td><span className={`badge ${q.status}`}>{q.status}</span></td>
                  <td>{q.risk_score}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
