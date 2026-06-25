import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { FileText, Users, FolderOpen, AlertTriangle, IndianRupee, TrendingUp } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import { api } from '../api/client';

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4'];

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const nav = useNavigate();

  useEffect(() => {
    api.getDashboardStats().then(setStats).catch(console.error).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="loading"><div className="spinner" /> Loading dashboard...</div>;
  if (!stats) return <div className="empty-state">Failed to load dashboard data</div>;

  const formatData = Object.entries(stats.format_breakdown || {}).map(([name, value]) => ({ name, value }));
  const statusData = Object.entries(stats.status_breakdown || {}).map(([name, value]) => ({ name, value }));

  return (
    <div>
      <div className="page-header">
        <h1>Dashboard</h1>
        <p>Manufacturing CRM Intelligence — Overview</p>
      </div>

      <div className="kpi-grid">
        <div className="kpi-card blue">
          <div className="kpi-icon blue"><FileText size={20} /></div>
          <div className="kpi-value">{stats.total_quotations}</div>
          <div className="kpi-label">Total Quotations</div>
        </div>
        <div className="kpi-card emerald">
          <div className="kpi-icon emerald"><Users size={20} /></div>
          <div className="kpi-value">{stats.total_suppliers}</div>
          <div className="kpi-label">Active Suppliers</div>
        </div>
        <div className="kpi-card purple">
          <div className="kpi-icon purple"><IndianRupee size={20} /></div>
          <div className="kpi-value">₹{(stats.avg_quote_value / 100000).toFixed(1)}L</div>
          <div className="kpi-label">Avg Quote Value</div>
        </div>
        <div className="kpi-card amber">
          <div className="kpi-icon amber"><AlertTriangle size={20} /></div>
          <div className="kpi-value">{stats.high_risk_quotations}</div>
          <div className="kpi-label">High Risk Quotes</div>
        </div>
        <div className="kpi-card red">
          <div className="kpi-icon red"><TrendingUp size={20} /></div>
          <div className="kpi-value">{stats.total_risk_flags}</div>
          <div className="kpi-label">Risk Flags</div>
        </div>
      </div>

      <div className="grid-2" style={{ marginBottom: 24 }}>
        <div className="card">
          <div className="card-header">
            <span className="card-title">Format Distribution</span>
          </div>
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie data={formatData} cx="50%" cy="50%" innerRadius={50} outerRadius={80}
                   dataKey="value" label={({ name, value }) => `${name} (${value})`}
                   labelLine={false}>
                {formatData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
              </Pie>
              <Tooltip contentStyle={{ background: '#1a2332', border: '1px solid rgba(148,163,184,0.1)', borderRadius: 8 }} />
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div className="card">
          <div className="card-header">
            <span className="card-title">Status Overview</span>
          </div>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={statusData}>
              <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 12 }} />
              <YAxis tick={{ fill: '#94a3b8', fontSize: 12 }} />
              <Tooltip contentStyle={{ background: '#1a2332', border: '1px solid rgba(148,163,184,0.1)', borderRadius: 8 }} />
              <Bar dataKey="value" fill="#3b82f6" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <span className="card-title">Recent Quotations</span>
          <button className="btn btn-secondary btn-sm" onClick={() => nav('/quotations')}>View All</button>
        </div>
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Doc No</th>
                <th>Supplier</th>
                <th>Project</th>
                <th>Date</th>
                <th>Value</th>
                <th>Status</th>
                <th>Risk</th>
              </tr>
            </thead>
            <tbody>
              {(stats.recent_quotations || []).map(q => (
                <tr key={q.id} onClick={() => nav(`/quotations/${q.id}`)} style={{ cursor: 'pointer' }}>
                  <td style={{ fontWeight: 600, color: '#38bdf8' }}>{q.doc_no}</td>
                  <td>{q.supplier_id}</td>
                  <td>{q.project_id}</td>
                  <td>{q.doc_date}</td>
                  <td style={{ textAlign: 'right' }}>₹{(q.total_excl_tax || 0).toLocaleString()}</td>
                  <td><span className={`badge ${q.status}`}>{q.status}</span></td>
                  <td>
                    <span className="risk-bar">
                      <span className={`risk-bar-fill ${q.risk_score >= 50 ? 'high' : q.risk_score >= 25 ? 'medium' : 'low'}`}
                            style={{ width: `${q.risk_score}%` }} />
                    </span>
                    {q.risk_score}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
