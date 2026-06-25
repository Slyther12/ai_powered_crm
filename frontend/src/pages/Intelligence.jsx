import { useState, useEffect } from 'react';
import { ShieldAlert, TrendingUp, Truck, AlertTriangle } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { api } from '../api/client';

function RiskSummaryTab() {
  const [risks, setRisks] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getAllRisks().then(setRisks).catch(console.error).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="loading"><div className="spinner" /> Loading risk data...</div>;
  if (!risks.length) return <div className="empty-state">No risk data available</div>;

  const chartData = risks.slice(0, 15).map(r => ({
    name: r.doc_no?.substring(0, 18) || `#${r.id}`,
    score: r.risk_score,
  }));

  return (
    <div>
      {/* Risk chart */}
      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-header">
          <span className="card-title">Risk Scores — Top Quotations</span>
          <span className="card-subtitle">{risks.length} quotations with risk flags</span>
        </div>
        <ResponsiveContainer width="100%" height={Math.max(250, chartData.length * 35)}>
          <BarChart data={chartData} layout="vertical" margin={{ left: 10, right: 20 }}>
            <XAxis type="number" domain={[0, 100]} tick={{ fill: '#94a3b8', fontSize: 11 }} />
            <YAxis dataKey="name" type="category" tick={{ fill: '#94a3b8', fontSize: 11 }} width={140} />
            <Tooltip
              contentStyle={{ background: '#1a2332', border: '1px solid rgba(148,163,184,0.1)', borderRadius: 8, color: '#f1f5f9' }}
              formatter={v => [v, 'Risk Score']}
            />
            <Bar dataKey="score" radius={[0, 6, 6, 0]}>
              {chartData.map((entry, i) => (
                <Cell key={i} fill={entry.score >= 50 ? '#ef4444' : entry.score >= 25 ? '#f59e0b' : '#10b981'} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Risk cards */}
      {risks.map(r => (
        <div key={r.id} className="card" style={{ marginBottom: 12 }}>
          <div className="flex items-center justify-between" style={{ marginBottom: 10 }}>
            <div className="flex items-center gap-3">
              <AlertTriangle
                size={16}
                style={{ color: r.risk_score >= 50 ? 'var(--accent-red)' : r.risk_score >= 25 ? 'var(--accent-amber)' : 'var(--accent-emerald)' }}
              />
              <div>
                <span style={{ fontWeight: 700, fontSize: 14, color: '#38bdf8', marginRight: 8 }}>{r.doc_no}</span>
                <span style={{ color: 'var(--text-secondary)', fontSize: 13 }}>{r.supplier_name}</span>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <span className={`badge ${r.risk_score >= 50 ? 'high' : r.risk_score >= 25 ? 'medium' : 'low'}`}>
                Score: {r.risk_score}
              </span>
              <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>{r.flags_count} flags</span>
            </div>
          </div>

          {r.risk_summary && (
            <div style={{
              fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.6,
              background: 'var(--bg-input)', padding: 10, borderRadius: 'var(--radius-sm)',
              marginBottom: r.flags?.length ? 10 : 0, whiteSpace: 'pre-wrap',
            }}>
              {r.risk_summary}
            </div>
          )}

          {r.flags?.length > 0 && (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              {r.flags.map((f, i) => (
                <div key={i} className={`risk-flag ${f.severity}`} style={{ flex: '1 1 calc(50% - 6px)', minWidth: 250 }}>
                  <div className="risk-flag-header">
                    <span className={`badge ${f.severity}`}>{f.severity}</span>
                    <span className="risk-flag-type">{f.flag_type.replace(/_/g, ' ')}</span>
                    <span className="risk-flag-field">{f.field}</span>
                  </div>
                  <div className="risk-flag-explanation">{f.explanation}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

function BenchmarksTab() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getBenchmarks().then(setData).catch(console.error).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="loading"><div className="spinner" /> Loading benchmarks...</div>;
  if (!data) return <div className="empty-state">No benchmark data available</div>;

  const benchmarks = data.price_benchmarks || [];
  const escalations = data.escalations || [];
  const delivery = data.delivery_benchmarks || [];

  return (
    <div>
      {/* Price Benchmarks */}
      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-header">
          <span className="card-title"><TrendingUp size={14} style={{ marginRight: 6 }} /> Price Benchmarks</span>
          <span className="card-subtitle">{benchmarks.length} items tracked</span>
        </div>
        {benchmarks.length > 0 ? (
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Item</th>
                  <th>Min Price</th>
                  <th>Max Price</th>
                  <th>Avg Price</th>
                  <th>Suppliers</th>
                  <th>Spread</th>
                </tr>
              </thead>
              <tbody>
                {benchmarks.slice(0, 25).map((b, i) => (
                  <tr key={i}>
                    <td style={{ fontWeight: 500, maxWidth: 250, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {b.description || b.item}
                    </td>
                    <td style={{ textAlign: 'right', fontFamily: 'monospace', color: 'var(--accent-emerald)' }}>
                      ₹{(b.min_price || 0).toLocaleString()}
                    </td>
                    <td style={{ textAlign: 'right', fontFamily: 'monospace', color: 'var(--accent-red)' }}>
                      ₹{(b.max_price || 0).toLocaleString()}
                    </td>
                    <td style={{ textAlign: 'right', fontFamily: 'monospace' }}>
                      ₹{(b.avg_price || 0).toLocaleString()}
                    </td>
                    <td style={{ textAlign: 'center' }}>{b.supplier_count || b.count || '—'}</td>
                    <td style={{ textAlign: 'right', fontFamily: 'monospace' }}>
                      <span style={{ color: (b.spread_pct || 0) > 30 ? 'var(--accent-red)' : 'var(--text-secondary)' }}>
                        {b.spread_pct || 0}%
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="empty-state">No price benchmark data</div>
        )}
      </div>

      {/* Escalations */}
      {escalations.length > 0 && (
        <div className="card" style={{ marginBottom: 20 }}>
          <div className="card-header">
            <span className="card-title" style={{ color: 'var(--accent-amber)' }}>⚠ Price Escalations</span>
            <span className="card-subtitle">{escalations.length} detected</span>
          </div>
          <div className="table-container">
            <table>
              <thead>
                <tr><th>Item</th><th>Supplier</th><th>Old Price</th><th>New Price</th><th>Change</th></tr>
              </thead>
              <tbody>
                {escalations.map((e, i) => (
                  <tr key={i}>
                    <td>{e.description || e.item}</td>
                    <td>{e.supplier_name || e.supplier_id}</td>
                    <td style={{ textAlign: 'right', fontFamily: 'monospace' }}>₹{(e.old_price || 0).toLocaleString()}</td>
                    <td style={{ textAlign: 'right', fontFamily: 'monospace' }}>₹{(e.new_price || 0).toLocaleString()}</td>
                    <td style={{ textAlign: 'right', fontFamily: 'monospace', color: 'var(--accent-red)', fontWeight: 600 }}>
                      +{e.change_pct || 0}%
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Delivery */}
      {delivery.length > 0 && (
        <div className="card">
          <div className="card-header">
            <span className="card-title"><Truck size={14} style={{ marginRight: 6 }} /> Delivery Benchmarks</span>
          </div>
          <div className="table-container">
            <table>
              <thead>
                <tr><th>Supplier</th><th>Avg Lead Days</th><th>Min</th><th>Max</th><th>Quotes</th></tr>
              </thead>
              <tbody>
                {delivery.map((d, i) => (
                  <tr key={i}>
                    <td style={{ fontWeight: 500 }}>{d.supplier_name || d.supplier_id}</td>
                    <td style={{ textAlign: 'right', fontWeight: 600 }}>{d.avg_days || 0}</td>
                    <td style={{ textAlign: 'right', color: 'var(--accent-emerald)' }}>{d.min_days || 0}</td>
                    <td style={{ textAlign: 'right', color: 'var(--accent-red)' }}>{d.max_days || 0}</td>
                    <td style={{ textAlign: 'center' }}>{d.count || 0}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

export default function Intelligence() {
  const [tab, setTab] = useState('risk');

  return (
    <div>
      <div className="page-header">
        <h1>Intelligence</h1>
        <p>AI-powered risk analysis, price benchmarking, and delivery insights</p>
      </div>

      <div className="tab-group">
        <button className={`tab-btn ${tab === 'risk' ? 'active' : ''}`} onClick={() => setTab('risk')}>
          <ShieldAlert size={14} style={{ marginRight: 4, verticalAlign: -2 }} />
          Risk Summary
        </button>
        <button className={`tab-btn ${tab === 'benchmarks' ? 'active' : ''}`} onClick={() => setTab('benchmarks')}>
          <TrendingUp size={14} style={{ marginRight: 4, verticalAlign: -2 }} />
          Benchmarks
        </button>
      </div>

      {tab === 'risk' && <RiskSummaryTab />}
      {tab === 'benchmarks' && <BenchmarksTab />}
    </div>
  );
}
