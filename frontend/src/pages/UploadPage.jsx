import { useState, useEffect, useRef } from 'react';
import { Upload, FileText, CheckCircle, AlertCircle, X } from 'lucide-react';
import { api } from '../api/client';

const FILE_ICONS = {
  'application/pdf': { label: 'PDF', color: 'var(--accent-red)' },
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': { label: 'XLSX', color: 'var(--accent-emerald)' },
  'application/vnd.ms-excel': { label: 'XLS', color: 'var(--accent-emerald)' },
  'text/csv': { label: 'CSV', color: 'var(--accent-blue)' },
  'text/plain': { label: 'TXT', color: 'var(--accent-amber)' },
};

function getFileInfo(file) {
  const ext = file.name.split('.').pop().toLowerCase();
  if (FILE_ICONS[file.type]) return FILE_ICONS[file.type];
  if (ext === 'pdf') return { label: 'PDF', color: 'var(--accent-red)' };
  if (ext === 'xlsx' || ext === 'xls') return { label: 'XLSX', color: 'var(--accent-emerald)' };
  if (ext === 'csv') return { label: 'CSV', color: 'var(--accent-blue)' };
  return { label: ext.toUpperCase(), color: 'var(--accent-amber)' };
}

export default function UploadPage() {
  const [file, setFile] = useState(null);
  const [dragover, setDragover] = useState(false);
  const [supplierId, setSupplierId] = useState('');
  const [projectId, setProjectId] = useState('');
  const [suppliers, setSuppliers] = useState([]);
  const [projects, setProjects] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const inputRef = useRef(null);

  useEffect(() => {
    api.getSuppliers().then(setSuppliers).catch(() => {});
    api.getProjects().then(setProjects).catch(() => {});
  }, []);

  const handleFile = (f) => {
    setFile(f);
    setResult(null);
    setError(null);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragover(false);
    if (e.dataTransfer.files?.length) handleFile(e.dataTransfer.files[0]);
  };

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    setError(null);
    setResult(null);
    try {
      const res = await api.uploadFile(file, supplierId || null, projectId || null);
      if (res.error) {
        setError(res.error || res.detail || 'Upload failed');
      } else {
        setResult(res);
      }
    } catch (err) {
      setError(err.message || 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  const clearFile = () => {
    setFile(null);
    setResult(null);
    setError(null);
    if (inputRef.current) inputRef.current.value = '';
  };

  const fileInfo = file ? getFileInfo(file) : null;

  return (
    <div>
      <div className="page-header">
        <h1>Upload Document</h1>
        <p>Upload a quotation document for automatic extraction and ingestion</p>
      </div>

      <div className="grid-2" style={{ marginBottom: 20, alignItems: 'start' }}>
        {/* Upload Zone */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">Document</span>
            <span className="card-subtitle">PDF, XLSX, CSV, or TXT</span>
          </div>

          {!file ? (
            <div
              id="upload-dropzone"
              className={`upload-zone ${dragover ? 'dragover' : ''}`}
              onDragOver={e => { e.preventDefault(); setDragover(true); }}
              onDragLeave={() => setDragover(false)}
              onDrop={handleDrop}
              onClick={() => inputRef.current?.click()}
            >
              <div className="upload-icon"><Upload size={48} /></div>
              <div style={{ fontSize: 15, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 4 }}>
                Drop file here or click to browse
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                Supported: .pdf, .xlsx, .xls, .csv, .txt
              </div>
              <input
                ref={inputRef}
                type="file"
                accept=".pdf,.xlsx,.xls,.csv,.txt"
                style={{ display: 'none' }}
                onChange={e => e.target.files?.[0] && handleFile(e.target.files[0])}
              />
            </div>
          ) : (
            <div style={{
              display: 'flex', alignItems: 'center', gap: 14,
              padding: 16, borderRadius: 'var(--radius-md)',
              background: 'var(--bg-input)', border: '1px solid var(--border-color)',
            }}>
              <div style={{
                width: 44, height: 44, borderRadius: 'var(--radius-md)',
                background: fileInfo.color + '22', color: fileInfo.color,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontWeight: 700, fontSize: 12,
              }}>
                {fileInfo.label}
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 600, fontSize: 14, color: 'var(--text-primary)' }}>{file.name}</div>
                <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                  {(file.size / 1024).toFixed(1)} KB
                </div>
              </div>
              <button className="btn btn-secondary btn-sm" onClick={clearFile} title="Remove file">
                <X size={14} />
              </button>
            </div>
          )}
        </div>

        {/* Options */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">Options</span>
            <span className="card-subtitle">Optional metadata</span>
          </div>

          <div style={{ marginBottom: 14 }}>
            <label style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 4, display: 'block' }}>
              Supplier
            </label>
            <select className="select" value={supplierId} onChange={e => setSupplierId(e.target.value)} id="upload-supplier">
              <option value="">Auto-detect</option>
              {suppliers.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
          </div>

          <div style={{ marginBottom: 20 }}>
            <label style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 4, display: 'block' }}>
              Project
            </label>
            <select className="select" value={projectId} onChange={e => setProjectId(e.target.value)} id="upload-project">
              <option value="">Auto-detect</option>
              {projects.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
          </div>

          <button
            id="upload-submit-btn"
            className="btn btn-primary btn-lg w-full"
            style={{ justifyContent: 'center' }}
            onClick={handleUpload}
            disabled={!file || uploading}
          >
            {uploading ? (
              <><div className="spinner" style={{ width: 18, height: 18, borderWidth: 2, marginRight: 6 }} /> Processing...</>
            ) : (
              <><Upload size={16} /> Upload & Ingest</>
            )}
          </button>
        </div>
      </div>

      {/* Result */}
      {result && (
        <div className="card" style={{
          borderLeft: '4px solid var(--accent-emerald)',
          animation: 'fadeIn 0.3s ease',
        }}>
          <div className="flex items-center gap-3" style={{ marginBottom: 16 }}>
            <CheckCircle size={22} style={{ color: 'var(--accent-emerald)' }} />
            <div>
              <div style={{ fontWeight: 700, fontSize: 15, color: 'var(--text-primary)' }}>
                Document Ingested Successfully
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                {result.doc_id} — {result.format} format detected
              </div>
            </div>
          </div>
          <div className="detail-grid">
            <div className="detail-item">
              <div className="detail-label">Document ID</div>
              <div className="detail-value" style={{ color: '#38bdf8', fontFamily: 'monospace' }}>{result.doc_id}</div>
            </div>
            <div className="detail-item">
              <div className="detail-label">Doc Number</div>
              <div className="detail-value">{result.doc_no}</div>
            </div>
            <div className="detail-item">
              <div className="detail-label">Format</div>
              <div className="detail-value"><span className={`badge ${result.format?.includes('pdf') ? 'pdf' : result.format}`}>{result.format}</span></div>
            </div>
            <div className="detail-item">
              <div className="detail-label">Line Items</div>
              <div className="detail-value" style={{ fontWeight: 700 }}>{result.line_items_count}</div>
            </div>
            <div className="detail-item">
              <div className="detail-label">Total</div>
              <div className="detail-value" style={{ fontWeight: 700, color: '#38bdf8' }}>₹{(result.total || 0).toLocaleString()}</div>
            </div>
            <div className="detail-item">
              <div className="detail-label">Quotation ID</div>
              <div className="detail-value">{result.quotation_id}</div>
            </div>
          </div>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="card" style={{
          borderLeft: '4px solid var(--accent-red)',
          animation: 'fadeIn 0.3s ease',
        }}>
          <div className="flex items-center gap-3">
            <AlertCircle size={22} style={{ color: 'var(--accent-red)' }} />
            <div>
              <div style={{ fontWeight: 700, fontSize: 15, color: 'var(--text-primary)' }}>
                Upload Failed
              </div>
              <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 4 }}>{error}</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
