import { useState, useEffect, useCallback } from 'react';
import { Activity, Clock, AlertCircle, Zap, RefreshCw } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { api } from '../api/client';

function LogsTab() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [stage, setStage] = useState('');

  const fetchLogs = useCallback(() => {
    setLoading(true);
    const params = { limit: 200 };
    if (stage) params.stage = stage;
    api.getLogs(params).then(setLogs).catch(console.error).finally(() => setLoading(false));
  }, [stage]);

  useEffect(() => { fetchLogs(); }, [fetchLogs]);

  return (
    <div>
      <div className="flex items-center gap-3" style={{ marginBottom: 16 }}>
        <select className="select" value={stage} onChange={e => setStage(e.target.value)} style={{ maxWidth: 180 }}>
          <option value="">All Stages</option>
          <option value="ingestion">Ingestion</option>
          <option value="search">Search</option>
          <option value="llm">LLM</option>
          <option value="api">API</option>
          <option value="risk">Risk</option>
        </select>
        <button className="btn btn-secondary btn-sm" onClick={fetchLogs}>
          <RefreshCw size={13} /> Refresh
        </button>
        <span style={{ fontSize: 12, color: 'var(--text-muted)', marginLeft: 'auto' }}>
          {logs.length} log entries
        </span>
      </div>

      <div className="card">
        {loading ? (
          <div className="loading"><div className="spinner" /> Loading logs...</div>
        ) : logs.length === 0 ? (
          <div className="empty-state">No logs found</div>
        ) : (
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>Stage</th>
                  <th>Operation</th>
                  <th>Duration</th>
                  <th>Tokens</th>
                  <th>Error</th>
                </tr>
              </thead>
              <tbody>
                {logs.map(log => (
                  <tr key={log.id}>
                    <td style={{ fontFamily: 'monospace', fontSize: 11, whiteSpace: 'nowrap', color: 'var(--text-muted)' }}>
                      {log.timestamp ? new Date(log.timestamp).toLocaleString() : '—'}
                    </td>
                    <td>
                      <span className={`badge ${
                        log.stage === 'ingestion' ? 'received' :
                        log.stage === 'search' ? 'approved' :
                        log.stage === 'llm' ? '' :
                        log.stage === 'api' ? 'reviewed' : ''
                      }`} style={log.stage === 'llm' ? { background: 'rgba(139,92,246,0.15)', color: 'var(--accent-purple)' } : {}}>
                        {log.stage}
                      </span>
                    </td>
                    <td style={{ fontSize: 12, maxWidth: 250, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {log.operation}
                    </td>
                    <td style={{ textAlign: 'right', fontFamily: 'monospace', fontSize: 12 }}>
                      {log.duration_ms != null ? (
                        <span style={{ color: log.duration_ms > 1000 ? 'var(--accent-amber)' : 'var(--text-secondary)' }}>
                          {log.duration_ms.toFixed(1)}ms
                        </span>
                      ) : '—'}
                    </td>
                    <td style={{ textAlign: 'right', fontFamily: 'monospace', fontSize: 12 }}>
                      {log.tokens_used || '—'}
                    </td>
                    <td style={{ fontSize: 12 }}>
                      {log.error ? (
                        <span style={{ color: 'var(--accent-red)', display: 'flex', alignItems: 'center', gap: 4 }}>
                          <AlertCircle size={12} /> {log.error.substring(0, 50)}
                        </span>
                      ) : (
                        <span style={{ color: 'var(--accent-emerald)' }}>✓</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

function MetricsTab() {
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getMetrics().then(setMetrics).catch(console.error).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="loading"><div className="spinner" /> Loading metrics...</div>;
  if (!metrics) return <div className="empty-state">No metrics available</div>;

  // Extract useful data from metrics response (flexible shape)
  const stages = metrics.by_stage || metrics.stages || {};
  const stageData = Object.entries(stages).map(([name, data]) => ({
    name,
    count: data.count || data.total || 0,
    avg_ms: data.avg_duration_ms || data.avg_ms || 0,
  }));

  const totalOps = metrics.total_operations || metrics.total || stageData.reduce((s, d) => s + d.count, 0);
  const avgLatency = metrics.avg_duration_ms || metrics.avg_latency || 0;
  const errorRate = metrics.error_rate || 0;
  const totalTokens = metrics.total_tokens || 0;

  return (
    <div>
      {/* KPIs */}
      <div className="kpi-grid" style={{ marginBottom: 20 }}>
        <div className="kpi-card blue">
          <div className="kpi-icon blue"><Zap size={20} /></div>
          <div className="kpi-value">{totalOps.toLocaleString()}</div>
          <div className="kpi-label">Total Operations</div>
        </div>
        <div className="kpi-card amber">
          <div className="kpi-icon amber"><Clock size={20} /></div>
          <div className="kpi-value">{typeof avgLatency === 'number' ? avgLatency.toFixed(1) : avgLatency}ms</div>
          <div className="kpi-label">Avg Latency</div>
        </div>
        <div className="kpi-card red">
          <div className="kpi-icon red"><AlertCircle size={20} /></div>
          <div className="kpi-value">{typeof errorRate === 'number' ? errorRate.toFixed(1) : errorRate}%</div>
          <div className="kpi-label">Error Rate</div>
        </div>
        <div className="kpi-card purple">
          <div className="kpi-icon purple"><Activity size={20} /></div>
          <div className="kpi-value">{totalTokens.toLocaleString()}</div>
          <div className="kpi-label">Total Tokens</div>
        </div>
      </div>

      {/* Stage breakdown chart */}
      {stageData.length > 0 && (
        <div className="grid-2" style={{ marginBottom: 20 }}>
          <div className="card">
            <div className="card-header">
              <span className="card-title">Operations by Stage</span>
            </div>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={stageData}>
                <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 12 }} />
                <YAxis tick={{ fill: '#94a3b8', fontSize: 12 }} />
                <Tooltip contentStyle={{ background: '#1a2332', border: '1px solid rgba(148,163,184,0.1)', borderRadius: 8, color: '#f1f5f9' }} />
                <Bar dataKey="count" fill="#3b82f6" radius={[4, 4, 0, 0]} name="Operations" />
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="card">
            <div className="card-header">
              <span className="card-title">Avg Latency by Stage (ms)</span>
            </div>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={stageData}>
                <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 12 }} />
                <YAxis tick={{ fill: '#94a3b8', fontSize: 12 }} />
                <Tooltip
                  contentStyle={{ background: '#1a2332', border: '1px solid rgba(148,163,184,0.1)', borderRadius: 8, color: '#f1f5f9' }}
                  formatter={v => [`${v.toFixed(1)}ms`, 'Avg Latency']}
                />
                <Bar dataKey="avg_ms" fill="#f59e0b" radius={[4, 4, 0, 0]} name="Avg Latency" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Stage details table */}
      {stageData.length > 0 && (
        <div className="card">
          <div className="card-header">
            <span className="card-title">Stage Details</span>
          </div>
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Stage</th>
                  <th>Operations</th>
                  <th>Avg Duration</th>
                </tr>
              </thead>
              <tbody>
                {stageData.map(s => (
                  <tr key={s.name}>
                    <td>
                      <span className={`badge ${
                        s.name === 'ingestion' ? 'received' :
                        s.name === 'search' ? 'approved' :
                        s.name === 'api' ? 'reviewed' : ''
                      }`} style={s.name === 'llm' ? { background: 'rgba(139,92,246,0.15)', color: 'var(--accent-purple)' } : {}}>
                        {s.name}
                      </span>
                    </td>
                    <td style={{ textAlign: 'right', fontFamily: 'monospace' }}>{s.count}</td>
                    <td style={{ textAlign: 'right', fontFamily: 'monospace' }}>
                      <span style={{ color: s.avg_ms > 500 ? 'var(--accent-amber)' : 'var(--text-secondary)' }}>
                        {s.avg_ms.toFixed(1)}ms
                      </span>
                    </td>
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

export default function Observability() {
  const [tab, setTab] = useState('logs');

  return (
    <div>
      <div className="page-header">
        <h1>Observability</h1>
        <p>Pipeline logs, performance metrics, and system health</p>
      </div>

      <div className="tab-group">
        <button className={`tab-btn ${tab === 'logs' ? 'active' : ''}`} onClick={() => setTab('logs')}>
          <Activity size={14} style={{ marginRight: 4, verticalAlign: -2 }} /> Logs
        </button>
        <button className={`tab-btn ${tab === 'metrics' ? 'active' : ''}`} onClick={() => setTab('metrics')}>
          <Zap size={14} style={{ marginRight: 4, verticalAlign: -2 }} /> Metrics
        </button>
      </div>

      {tab === 'logs' && <LogsTab />}
      {tab === 'metrics' && <MetricsTab />}
    </div>
  );
}
