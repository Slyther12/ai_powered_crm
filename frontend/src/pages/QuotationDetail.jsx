import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, CheckCircle, XCircle, Eye, AlertTriangle, Trash2, Inbox } from 'lucide-react';
import { api } from '../api/client';

export default function QuotationDetail() {
  const { id } = useParams();
  const nav = useNavigate();
  const [q, setQ] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getQuotation(id).then(setQ).catch(console.error).finally(() => setLoading(false));
  }, [id]);

  const updateStatus = async (status) => {
    await api.updateStatus(id, status);
    const updated = await api.getQuotation(id);
    setQ(updated);
  };

  const handleDelete = async () => {
    if (window.confirm("Are you sure you want to delete this quotation? This action cannot be undone.")) {
      try {
        await api.deleteQuotation(id);
        nav('/quotations');
      } catch (err) {
        alert("Failed to delete quotation: " + err.message);
      }
    }
  };

  if (loading) return <div className="loading"><div className="spinner" /> Loading quotation...</div>;
  if (!q) return <div className="empty-state">Quotation not found</div>;

  const riskLevel = q.risk_score >= 50 ? 'high' : q.risk_score >= 25 ? 'medium' : 'low';

  return (
    <div>
      <div className="flex items-center gap-3" style={{ marginBottom: 20 }}>
        <button className="btn btn-secondary btn-sm" onClick={() => nav('/quotations')}>
          <ArrowLeft size={14} /> Back
        </button>
        <div className="page-header" style={{ marginBottom: 0 }}>
          <h1>{q.doc_no}</h1>
          <p>{q.supplier?.name} • {q.project?.name}</p>
        </div>
        <div style={{ marginLeft: 'auto' }} className="flex gap-2">
          <button className="btn btn-secondary btn-sm" onClick={() => updateStatus('received')} title="Mark as Received">
            <Inbox size={14} /> Received
          </button>
          <button className="btn btn-primary btn-sm" onClick={() => updateStatus('reviewed')} title="Mark as Reviewed">
            <Eye size={14} /> Review
          </button>
          <button className="btn btn-success btn-sm" onClick={() => updateStatus('approved')}>
            <CheckCircle size={14} /> Approve
          </button>
          <button className="btn btn-danger btn-sm" onClick={() => updateStatus('rejected')}>
            <XCircle size={14} /> Reject
          </button>
          <div style={{ width: '1px', background: 'var(--border)', margin: '0 4px' }} />
          <button className="btn btn-secondary btn-sm text-red-500 hover:text-red-700" onClick={handleDelete} title="Delete Quotation">
            <Trash2 size={14} /> Delete
          </button>
        </div>
      </div>

      <div className="grid-2" style={{ marginBottom: 20 }}>
        <div className="card">
          <div className="detail-section">
            <div className="detail-section-title">Quotation Details</div>
            <div className="detail-grid">
              <div className="detail-item">
                <div className="detail-label">Status</div>
                <div className="detail-value"><span className={`badge ${q.status}`}>{q.status}</span></div>
              </div>
              <div className="detail-item">
                <div className="detail-label">Date</div>
                <div className="detail-value">{q.doc_date || 'N/A'}</div>
              </div>
              <div className="detail-item">
                <div className="detail-label">Format</div>
                <div className="detail-value"><span className={`badge ${q.format?.includes('pdf') ? 'pdf' : q.format}`}>{q.format}</span></div>
              </div>
              <div className="detail-item">
                <div className="detail-label">Currency</div>
                <div className="detail-value">{q.currency}</div>
              </div>
              <div className="detail-item">
                <div className="detail-label">Validity</div>
                <div className="detail-value">{q.validity_days} days (until {q.valid_until || 'N/A'})</div>
              </div>
              <div className="detail-item">
                <div className="detail-label">Payment Terms</div>
                <div className="detail-value">{q.payment_terms || 'N/A'}</div>
              </div>
              <div className="detail-item">
                <div className="detail-label">Total (excl tax)</div>
                <div className="detail-value" style={{ fontSize: 18, fontWeight: 700, color: '#38bdf8' }}>
                  {q.currency === 'USD' ? '$' : '₹'}{(q.total_excl_tax || 0).toLocaleString()}
                </div>
              </div>
              <div className="detail-item">
                <div className="detail-label">Total (incl tax)</div>
                <div className="detail-value" style={{ fontSize: 16 }}>
                  {q.currency === 'USD' ? '$' : '₹'}{(q.total_incl_tax || 0).toLocaleString()}
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="detail-section">
            <div className="detail-section-title flex items-center gap-2">
              <AlertTriangle size={14} /> Risk Assessment
              <span className={`badge ${riskLevel}`} style={{ marginLeft: 'auto' }}>
                Score: {q.risk_score}
              </span>
            </div>
            <div style={{ marginBottom: 12 }}>
              <div className="risk-bar" style={{ width: '100%', height: 8 }}>
                <span className={`risk-bar-fill ${riskLevel}`}
                      style={{ width: `${Math.min(q.risk_score, 100)}%` }} />
              </div>
            </div>
            {q.risk_summary && (
              <div style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.6, marginBottom: 12,
                           whiteSpace: 'pre-wrap', background: 'var(--bg-input)', padding: 12, borderRadius: 8 }}>
                {q.risk_summary}
              </div>
            )}
            {q.risk_flags?.length > 0 && q.risk_flags.map((f, i) => (
              <div key={i} className={`risk-flag ${f.severity}`}>
                <div className="risk-flag-header">
                  <span className={`badge ${f.severity}`}>{f.severity}</span>
                  <span className="risk-flag-type">{f.flag_type.replace(/_/g, ' ')}</span>
                  <span className="risk-flag-field">{f.field}</span>
                </div>
                <div className="risk-flag-explanation">{f.explanation}</div>
              </div>
            ))}
            {(!q.risk_flags || q.risk_flags.length === 0) && (
              <div style={{ color: 'var(--accent-emerald)', fontSize: 13 }}>✓ No risk flags detected</div>
            )}
          </div>
        </div>
      </div>

      <div className="card" style={{ marginBottom: 20 }}>
        <div className="detail-section-title">Line Items ({q.line_items?.length || 0})</div>
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>#</th>
                <th>Description</th>
                <th>Unit</th>
                <th>Qty</th>
                <th>Unit Price</th>
                <th>Amount</th>
              </tr>
            </thead>
            <tbody>
              {(q.line_items || []).map(li => (
                <tr key={li.id}>
                  <td>{li.seq_no}</td>
                  <td>{li.description}</td>
                  <td>{li.unit}</td>
                  <td style={{ textAlign: 'right' }}>{li.quantity}</td>
                  <td style={{ textAlign: 'right', fontFamily: 'monospace' }}>
                    {(li.unit_price || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                  </td>
                  <td style={{ textAlign: 'right', fontFamily: 'monospace', fontWeight: 600 }}>
                    {(li.amount || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {q.delivery_term && (
        <div className="card" style={{ marginBottom: 20 }}>
          <div className="detail-section-title">Delivery & Terms</div>
          <div className="detail-grid">
            <div className="detail-item">
              <div className="detail-label">Delivery</div>
              <div className="detail-value">{q.delivery_term.delivery_text || `${q.delivery_term.delivery_days} days`}</div>
            </div>
            <div className="detail-item">
              <div className="detail-label">Freight</div>
              <div className="detail-value">{q.delivery_term.freight_terms || 'N/A'}</div>
            </div>
            <div className="detail-item">
              <div className="detail-label">Warranty</div>
              <div className="detail-value">{q.delivery_term.warranty || 'N/A'}</div>
            </div>
          </div>
        </div>
      )}

      {q.status_history?.length > 0 && (
        <div className="card">
          <div className="detail-section-title">Status History</div>
          <div className="table-container">
            <table>
              <thead>
                <tr><th>Timestamp</th><th>From</th><th>To</th><th>By</th><th>Notes</th></tr>
              </thead>
              <tbody>
                {q.status_history.map((h, i) => (
                  <tr key={i}>
                    <td>{h.changed_at ? new Date(h.changed_at).toLocaleString() : 'N/A'}</td>
                    <td>{h.old_status ? <span className={`badge ${h.old_status}`}>{h.old_status}</span> : '—'}</td>
                    <td><span className={`badge ${h.new_status}`}>{h.new_status}</span></td>
                    <td>{h.changed_by}</td>
                    <td style={{ color: 'var(--text-secondary)' }}>{h.notes}</td>
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
