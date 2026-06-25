import { useState, useEffect } from 'react';
import { GitCompare, TrendingDown, TrendingUp, Minus } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, ReferenceLine } from 'recharts';
import { api } from '../api/client';

export default function Compare() {
  const [items, setItems] = useState([]);
  const [selected, setSelected] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [itemsLoading, setItemsLoading] = useState(true);

  useEffect(() => {
    api.getDistinctItems()
      .then(setItems)
      .catch(console.error)
      .finally(() => setItemsLoading(false));
  }, []);

  const handleCompare = (desc) => {
    if (!desc) return;
    setSelected(desc);
    setLoading(true);
    api.compareItems(desc)
      .then(setResult)
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  const chartData = (result?.comparisons || []).map(c => ({
    name: c.supplier_name?.substring(0, 18) + (c.supplier_name?.length > 18 ? '…' : ''),
    price: c.unit_price,
    supplier: c.supplier_name,
    doc: c.doc_no,
  }));

  const getBarColor = (price) => {
    if (!result?.stats) return '#3b82f6';
    if (price <= result.stats.min * 1.05) return '#10b981';
    if (price >= result.stats.max * 0.95) return '#ef4444';
    return '#3b82f6';
  };

  return (
    <div>
      <div className="page-header">
        <h1>Price Comparison</h1>
        <p>Compare unit prices across suppliers for the same line items</p>
      </div>

      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-header">
          <span className="card-title">Select Line Item</span>
          <span className="card-subtitle">{items.length} distinct items available</span>
        </div>
        {itemsLoading ? (
          <div className="loading"><div className="spinner" /> Loading items...</div>
        ) : (
          <select
            className="select"
            value={selected}
            onChange={e => handleCompare(e.target.value)}
            id="compare-item-select"
          >
            <option value="">— Choose a line item to compare —</option>
            {items.map(item => (
              <option key={item.description} value={item.description}>
                {item.description} ({item.count} quotes)
              </option>
            ))}
          </select>
        )}
      </div>

      {loading && <div className="loading"><div className="spinner" /> Comparing prices...</div>}

      {result && !loading && (
        <>
          {/* Stats Overview */}
          {result.stats && (
            <div className="kpi-grid" style={{ marginBottom: 20 }}>
              <div className="kpi-card emerald">
                <div className="kpi-icon emerald"><TrendingDown size={20} /></div>
                <div className="kpi-value">₹{result.stats.min?.toLocaleString()}</div>
                <div className="kpi-label">Lowest Price</div>
              </div>
              <div className="kpi-card red">
                <div className="kpi-icon red"><TrendingUp size={20} /></div>
                <div className="kpi-value">₹{result.stats.max?.toLocaleString()}</div>
                <div className="kpi-label">Highest Price</div>
              </div>
              <div className="kpi-card blue">
                <div className="kpi-icon blue"><Minus size={20} /></div>
                <div className="kpi-value">₹{result.stats.median?.toLocaleString()}</div>
                <div className="kpi-label">Median Price</div>
              </div>
              <div className="kpi-card amber">
                <div className="kpi-icon amber"><GitCompare size={20} /></div>
                <div className="kpi-value">{result.stats.spread_pct}%</div>
                <div className="kpi-label">Price Spread</div>
              </div>
            </div>
          )}

          {/* Chart */}
          {chartData.length > 0 && (
            <div className="card" style={{ marginBottom: 20 }}>
              <div className="card-header">
                <span className="card-title">Price by Supplier</span>
                <span className="card-subtitle">{result.stats?.count} data points</span>
              </div>
              <ResponsiveContainer width="100%" height={Math.max(250, chartData.length * 40)}>
                <BarChart data={chartData} layout="vertical" margin={{ left: 10, right: 20 }}>
                  <XAxis
                    type="number"
                    tick={{ fill: '#94a3b8', fontSize: 11 }}
                    tickFormatter={v => `₹${v.toLocaleString()}`}
                  />
                  <YAxis dataKey="name" type="category" tick={{ fill: '#94a3b8', fontSize: 11 }} width={150} />
                  <Tooltip
                    contentStyle={{ background: '#1a2332', border: '1px solid rgba(148,163,184,0.1)', borderRadius: 8, color: '#f1f5f9' }}
                    formatter={(val) => [`₹${val.toLocaleString()}`, 'Unit Price']}
                    labelFormatter={(label, payload) => payload?.[0]?.payload?.supplier || label}
                  />
                  {result.stats && (
                    <ReferenceLine x={result.stats.median} stroke="#f59e0b" strokeDasharray="5 5" label={{ value: 'Median', fill: '#f59e0b', fontSize: 10 }} />
                  )}
                  <Bar dataKey="price" radius={[0, 6, 6, 0]}>
                    {chartData.map((entry, i) => (
                      <Cell key={i} fill={getBarColor(entry.price)} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Detail Table */}
          <div className="card">
            <div className="card-header">
              <span className="card-title">Detailed Comparison</span>
            </div>
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>Supplier</th>
                    <th>Doc No</th>
                    <th>Project</th>
                    <th>Date</th>
                    <th>Qty</th>
                    <th>Unit</th>
                    <th>Unit Price</th>
                    <th>vs Median</th>
                  </tr>
                </thead>
                <tbody>
                  {result.comparisons.map((c, i) => {
                    const devPct = result.stats?.median
                      ? (((c.unit_price - result.stats.median) / result.stats.median) * 100).toFixed(1)
                      : 0;
                    return (
                      <tr key={i}>
                        <td style={{ fontWeight: 600 }}>{c.supplier_name}</td>
                        <td style={{ color: '#38bdf8' }}>{c.doc_no}</td>
                        <td>{c.project}</td>
                        <td>{c.date}</td>
                        <td style={{ textAlign: 'right' }}>{c.quantity}</td>
                        <td>{c.unit}</td>
                        <td style={{ textAlign: 'right', fontFamily: 'monospace', fontWeight: 600 }}>
                          {c.currency === 'USD' ? '$' : '₹'}{c.unit_price?.toLocaleString()}
                        </td>
                        <td style={{
                          textAlign: 'right',
                          fontFamily: 'monospace',
                          color: devPct > 10 ? 'var(--accent-red)' : devPct < -10 ? 'var(--accent-emerald)' : 'var(--text-secondary)',
                        }}>
                          {devPct > 0 ? '+' : ''}{devPct}%
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {result.comparisons.length === 0 && (
            <div className="empty-state">No comparison data found for this item</div>
          )}
        </>
      )}

      {!result && !loading && !selected && (
        <div className="card">
          <div className="empty-state">
            <GitCompare size={48} />
            <div style={{ marginTop: 12 }}>Select a line item above to compare prices across all suppliers</div>
          </div>
        </div>
      )}
    </div>
  );
}
